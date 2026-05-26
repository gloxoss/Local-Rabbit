#!/usr/bin/env python3
"""
Local CodeRabbit - Context-Aware Continuous Review Watcher
v4.0: SOLID refactor — config, client, stats extracted to modules
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

# Force UTF-8 output for Windows PowerShell
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# SOLID imports — extracted modules
from config import (
    DEFAULT_CONFIG, BASE_PROMPT,
    load_config, load_custom_prompt, load_agent_context
)
from client import get_client, get_model_name
from stats import update_dashboard_stats

# Optional imports — graceful fallback
try:
    from webhooks import notify_webhooks
except ImportError:
    notify_webhooks = None

try:
    from git_blame import get_file_last_author, format_blame_for_display
except ImportError:
    get_file_last_author = None
    format_blame_for_display = None

try:
    from realtime_server import start_server as start_sse_server, notify_file_review, notify_status
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    start_sse_server = None
    notify_file_review = None
    notify_status = None

try:
    from secret_scanner import SecretScanner
    SECRET_SCANNER_AVAILABLE = True
    def get_secret_scanner():
        return SecretScanner()
except ImportError:
    SECRET_SCANNER_AVAILABLE = False
    get_secret_scanner = None

try:
    if str(Path(__file__).parent) not in sys.path:
        sys.path.append(str(Path(__file__).parent))
    from cortex.retriever import get_retriever
    retriever_instance = get_retriever()
    RAG_AVAILABLE = True
    print("🧠 RAG: Context retrieval enabled")
except Exception:
    RAG_AVAILABLE = False
    retriever_instance = None


# ─── Severity Parsing ────────────────────────────────────────────

def parse_severity(review_text):
    """Parse review text and extract issues by severity."""
    issues = {"critical": [], "warning": [], "suggestion": []}
    for line in review_text.split('\n'):
        line = line.strip()
        if '🔴' in line or 'CRITICAL' in line.upper():
            issues["critical"].append(line)
        elif '🟡' in line or 'WARNING' in line.upper():
            issues["warning"].append(line)
        elif '🔵' in line or 'SUGGESTION' in line.upper():
            issues["suggestion"].append(line)
    return issues


def filter_by_severity(issues, min_severity, severity_levels):
    """Filter issues by minimum severity level."""
    min_level = severity_levels.get(min_severity, 1)
    filtered = []
    for severity, items in issues.items():
        if severity_levels.get(severity, 0) >= min_level:
            filtered.extend(items)
    return filtered


# ─── Notifications ───────────────────────────────────────────────

def send_notification(title, message, is_critical=False):
    """Send desktop notification via filesystem marker."""
    try:
        notif_file = Path("/workspace/.notifications")
        notif_file.mkdir(exist_ok=True)
        notif_data = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message[:200],
            "critical": is_critical
        }
        notif_path = notif_file / f"{int(time.time())}.json"
        with open(notif_path, "w") as f:
            json.dump(notif_data, f)
        if is_critical:
            print(f"\n🔔 [NOTIFY] {title}: {message[:100]}")
    except Exception:
        pass


# ─── History ─────────────────────────────────────────────────────

def save_to_history(root_dir, config, filepath, review_text, issues):
    """Save review to daily markdown history file."""
    if not config.get("history", {}).get("enabled", True):
        return

    history_folder = Path(root_dir) / config["history"]["folder"]
    history_folder.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    history_file = history_folder / f"{today}.md"
    timestamp = datetime.now().strftime("%H:%M:%S")
    rel_path = os.path.relpath(filepath, root_dir)

    entry = f"""
## {timestamp} - `{rel_path}`

| Severity | Count |
|----------|-------|
| 🔴 Critical | {len(issues["critical"])} |
| 🟡 Warning | {len(issues["warning"])} |
| 🔵 Suggestion | {len(issues["suggestion"])} |

{review_text}

---
"""
    with open(history_file, "a", encoding="utf-8") as f:
        if history_file.stat().st_size == 0:
            f.write(f"# Code Review Log - {today}\n\n")
        f.write(entry)

    print(f"   📝 Saved to: {history_file.name}")
    update_dashboard_stats(root_dir, config, rel_path, issues)


# ─── File Review ─────────────────────────────────────────────────

def review_file(client, filepath, agent_context, custom_prompt):
    """Send file to AI for review."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        if len(code) < 10:
            return None

        # Security pre-flight
        if SECRET_SCANNER_AVAILABLE:
            try:
                scanner = get_secret_scanner()
                secret_issues = scanner.scan(code)
                if secret_issues:
                    print(f"🚨 SECURITY: {len(secret_issues)} secrets detected in {filepath}")
                    return "\n".join(
                        f"[{issue.type}] Line {issue.line}: {issue.message}"
                        for issue in secret_issues
                    )
            except Exception as e:
                print(f"⚠️ Security scan error: {e}")

        system_content = custom_prompt + "\n\nCONTEXT RULES:\n" + agent_context

        # RAG injection
        if RAG_AVAILABLE and retriever_instance:
            try:
                print(f"   🧠 RAG: Retrieving context for {os.path.basename(filepath)}...")
                rag_context = retriever_instance.retrieve_context(code[:1000], current_file=filepath)
                if rag_context:
                    system_content += f"\n\nRELATED CODEBASE CONTEXT:\n{rag_context}\n"
                    print(f"   🧠 RAG: Injected {len(rag_context.splitlines())} lines of context")
            except Exception as e:
                print(f"   ⚠️ RAG Error: {e}")

        user_content = (
            f"Please review this code ({filepath}):\n```\n{code[:4000]}\n```\n\n"
            "REMINDER: OUTPUT ONLY [CRITICAL], [WARNING], [SUGGESTION] ENTRIES. DO NOT ADD SUMMARIES."
        )

        response = client.chat.completions.create(
            model=get_model_name(),
            messages=[
                {'role': 'system', 'content': system_content},
                {'role': 'user', 'content': user_content}
            ],
            max_tokens=1000
        )
        content = response.choices[0].message.content
        return content if content else "Error reviewing: API returned empty response"
    except Exception as e:
        return f"Error reviewing: {e}"


# ─── File Discovery ──────────────────────────────────────────────

def get_file_hash(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def find_files(root_dir, config):
    files = {}
    extensions = set(config.get("watch_extensions", DEFAULT_CONFIG["watch_extensions"]))
    ignore_dirs = set(config.get("ignore_dirs", DEFAULT_CONFIG["ignore_dirs"]))
    for path in Path(root_dir).rglob('*'):
        if path.is_file() and path.suffix in extensions:
            if not any(ignored in path.parts for ignored in ignore_dirs):
                files[str(path)] = get_file_hash(path)
    return files


# ─── Main Loop ───────────────────────────────────────────────────

def setup_watcher(root_dir):
    """Initialize configuration and context."""
    abs_root = os.path.abspath(root_dir)
    config = load_config(abs_root)
    custom_prompt = load_custom_prompt(abs_root)

    print("=" * 60)
    print("  LOCAL CODERABBIT v4.0 - SOLID Architecture")
    print("=" * 60)
    print(f"📁 Watching: {abs_root}")
    print(f"📄 Extensions: {', '.join(config['watch_extensions'])}")
    print(f"⏱️  Debounce: {config['debounce_seconds']}s")

    if custom_prompt != BASE_PROMPT:
        print("📋 Custom Prompt: Loaded from prompts.json")

    print()
    print("🤖 Loading .agent context...")
    agent_context = load_agent_context(abs_root)
    if agent_context:
        print(f"   ✅ Agent rules loaded ({len(agent_context)} chars)")
    else:
        print("   ℹ️  No .agent folder found - using default rules")

    return abs_root, config, custom_prompt, agent_context


def start_services():
    """Start background services like SSE."""
    if SSE_AVAILABLE and start_sse_server:
        try:
            start_sse_server(8765)
            print("🌐 Real-time: http://localhost:8765 (SSE)")
        except Exception as e:
            print(f"⚠️  Real-time server failed: {e}")


def process_file_review(filepath, abs_root, config, client, agent_context, custom_prompt):
    """Handle individual file review and notifications."""
    rel_path = os.path.relpath(filepath, abs_root)
    print(f"\n📝 Reviewing: {rel_path}")
    print("-" * 40)

    if notify_status:
        notify_status(f"Reviewing {rel_path}...", "reviewing")

    result = review_file(client, filepath, agent_context, custom_prompt)
    if not result:
        return

    issues = parse_severity(result)
    filtered = filter_by_severity(
        issues,
        config.get("min_severity", "suggestion"),
        config.get("severity_levels", DEFAULT_CONFIG["severity_levels"])
    )

    # Display
    if "Error reviewing" in result:
        print(f"❌ {result}")
    elif filtered:
        for issue in filtered:
            print(issue)
    elif "✅" in result or "No issues" in result.lower():
        print("✅ No issues found")
    else:
        print("✅ All issues below severity threshold")

    # Notify
    notif_config = config.get("notifications", {})
    if notif_config.get("enabled", True):
        if issues["critical"]:
            send_notification(f"🔴 Critical Issue in {rel_path}", issues["critical"][0], is_critical=True)
        elif not notif_config.get("on_critical_only", True) and filtered:
            send_notification(f"Code Review: {rel_path}", f"{len(filtered)} issues found")

    # Save & webhook
    save_to_history(abs_root, config, filepath, result, issues)

    if notify_webhooks:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code_snippet = f.read()[:300]
            notify_webhooks(config, rel_path, issues, code_snippet)
        except Exception as e:
            print(f"   [WEBHOOK] Error: {e}")

    if notify_file_review:
        notify_file_review(rel_path, issues, "complete")
    print()


def watch_loop(abs_root, config, custom_prompt, agent_context, client):
    """Main file watching loop."""
    print("-" * 60)
    print("👁️  Watching for changes... (Ctrl+C to stop)")
    print()

    known_files = find_files(abs_root, config)
    pending_review = {}

    while True:
        try:
            current_files = find_files(abs_root, config)
            for filepath, filehash in current_files.items():
                if filepath not in known_files or known_files[filepath] != filehash:
                    pending_review[filepath] = time.time()

            now = time.time()
            to_review = [f for f, t in pending_review.items() if now - t >= config["debounce_seconds"]]
            for filepath in to_review:
                process_file_review(filepath, abs_root, config, client, agent_context, custom_prompt)
                del pending_review[filepath]

            known_files = current_files
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping watcher...")
            break
        except Exception as e:
            print(f"\n⚠️  Watcher Loop Error: {e}")
            time.sleep(1)


def main():
    root_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    abs_root, config, custom_prompt, agent_context = setup_watcher(root_dir)
    start_services()
    client = get_client()
    watch_loop(abs_root, config, custom_prompt, agent_context, client)


if __name__ == '__main__':
    main()
