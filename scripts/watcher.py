#!/usr/bin/env python3
"""
Local CodeRabbit - Context-Aware Continuous Review Watcher
v3.0: + Desktop Notifications + Custom Prompts
"""

import os
import sys
import json
import time
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from openai import OpenAI

# Force UTF-8 output for Windows PowerShell
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Import local modules
try:
    from webhooks import notify_webhooks
except ImportError:
    notify_webhooks = None  # Graceful fallback

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

# Default configuration
DEFAULT_CONFIG = {
    "min_severity": "suggestion",
    "severity_levels": {"critical": 3, "warning": 2, "suggestion": 1},
    "history": {"enabled": True, "folder": "reviews"},
    "notifications": {"enabled": True, "on_critical_only": True},
    "debounce_seconds": 3,
    "watch_extensions": [".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".vue", ".svelte"],
    "ignore_dirs": ["node_modules", ".git", "__pycache__", "dist", "build", ".next", ".agent", "reviews"]
}

# Agent context files to read
AGENT_CONTEXT_FILES = [
    '.agent/GEMINI.md',
    '.agent/agents/frontend-specialist.md',
    '.agent/agents/backend-specialist.md', 
    '.agent/skills/clean-code/SKILL.md',
    '.agent/skills/frontend-design/SKILL.md',
    'GEMINI.md',
]

BASE_PROMPT = """
You are an Automated Code Analysis Tool.
Your ONLY job is to list issues in the provided code.
DO NOT provide conversational text, summaries, intros, or markdown headers.

STRICT OUTPUT FORMAT (one issue per line):
[CRITICAL] Line N: <message>
[WARNING] Line N: <message>
[SUGGESTION] Line N: <message>

If you can fix the issue, provide the REPLACEMENT CODE in a code block with language 'suggestion' immediately after the issue:
[WARNING] Line 15: Use strict equality.
```suggestion
if (a === b) {
```

If the code is fine, output exactly: [CLEAN]
"""

def load_config(root_dir):
    """Load config from config.json or use defaults."""
    config_path = Path(root_dir) / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                user_config = json.load(f)
                return {**DEFAULT_CONFIG, **user_config}
        except:
            pass
    return DEFAULT_CONFIG

def load_custom_prompt(root_dir):
    """Load custom prompt from prompts.json if exists."""
    prompt_path = Path(root_dir) / "prompts.json"
    if prompt_path.exists():
        try:
            with open(prompt_path) as f:
                prompts = json.load(f)
                return prompts.get("review_prompt", BASE_PROMPT)
        except:
            pass
    return BASE_PROMPT

def get_client():
    """Get OpenAI-compatible client (Ollama or Z.AI)."""
    use_ollama = os.environ.get('USE_OLLAMA', 'false').lower() == 'true'
    use_groq = os.environ.get('USE_GROQ', 'false').lower() == 'true'
    
    if use_ollama:
        ollama_host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        return OpenAI(
            api_key='ollama',  # Ollama doesn't need a real key
            base_url=f"{ollama_host}/v1"
        )
    elif use_groq:
        return OpenAI(
            api_key=os.environ.get('GROQ_API_KEY'),
            base_url="https://api.groq.com/openai/v1"
        )
    else:
        return OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY', os.environ.get('ZAI_API_KEY')),
            base_url=os.environ.get('OPENAI_API_BASE', os.environ.get('ZAI_API_BASE', 'https://api.z.ai/v1'))
        )

def send_notification(title, message, is_critical=False):
    """Send desktop notification via PowerShell (Windows)."""
    try:
        # Write notification to a file that can be picked up by host
        notif_file = Path("/workspace/.notifications")
        notif_file.mkdir(exist_ok=True)
        
        notif_data = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message[:200],  # Truncate for notification
            "critical": is_critical
        }
        
        notif_path = notif_file / f"{int(time.time())}.json"
        with open(notif_path, "w") as f:
            json.dump(notif_data, f)
        
        # Also print with special marker for host to detect
        if is_critical:
            print(f"\n🔔 [NOTIFY] {title}: {message[:100]}")
    except:
        pass  # Notifications are best-effort

def load_agent_context(root_dir):
    """Load .agent folder rules from the repository being watched."""
    context_parts = []
    root = Path(root_dir)
    
    for rel_path in AGENT_CONTEXT_FILES:
        full_path = root / rel_path
        if full_path.exists():
            try:
                content = full_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                in_frontmatter = False
                filtered = []
                for line in lines:
                    if line.strip() == '---':
                        in_frontmatter = not in_frontmatter
                        continue
                    if not in_frontmatter:
                        filtered.append(line)
                context_parts.append(f"### FROM {rel_path}:\n{''.join(filtered[:100])}\n")
                print(f"   📖 Loaded: {rel_path}")
            except Exception as e:
                print(f"   ⚠️  Error reading {rel_path}: {e}")
    
    if context_parts:
        return "\n---\nPROJECT-SPECIFIC RULES (from .agent folder):\n" + "\n".join(context_parts)
    return ""

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

def save_to_history(root_dir, config, filepath, review_text, issues):
    """Save review to history file."""
    if not config.get("history", {}).get("enabled", True):
        return
    
    history_folder = Path(root_dir) / config["history"]["folder"]
    history_folder.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    history_file = history_folder / f"{today}.md"
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    rel_path = os.path.relpath(filepath, root_dir)
    
    critical_count = len(issues["critical"])
    warning_count = len(issues["warning"])
    suggestion_count = len(issues["suggestion"])
    
    entry = f"""
## {timestamp} - `{rel_path}`

| Severity | Count |
|----------|-------|
| 🔴 Critical | {critical_count} |
| 🟡 Warning | {warning_count} |
| 🔵 Suggestion | {suggestion_count} |

{review_text}

---
"""
    
    with open(history_file, "a", encoding="utf-8") as f:
        if history_file.stat().st_size == 0:
            f.write(f"# Code Review Log - {today}\n\n")
        f.write(entry)
    
    print(f"   📝 Saved to: {history_file.name}")
    
    # Update JSON stats for dashboard
    update_dashboard_stats(root_dir, config, rel_path, issues)

def update_dashboard_stats(root_dir, config, filepath, issues):
    """Update JSON stats file for dashboard consumption."""
    history_folder = Path(root_dir) / config["history"]["folder"]
    stats_file = history_folder / "stats.json"
    
    # Load existing stats or create new
    if stats_file.exists():
        try:
            with open(stats_file) as f:
                stats = json.load(f)
        except:
            stats = {"totals": {"critical": 0, "warning": 0, "suggestion": 0, "files": 0}, "recent": [], "daily": {}}
    else:
        stats = {"totals": {"critical": 0, "warning": 0, "suggestion": 0, "files": 0}, "recent": [], "daily": {}}
    
    # Get file extension for type
    ext = Path(filepath).suffix.lstrip('.')
    file_type = {'ts': 'ts', 'tsx': 'ts', 'js': 'js', 'jsx': 'js', 'py': 'py'}.get(ext, ext)
    
    # Count issues
    critical = len(issues["critical"])
    warning = len(issues["warning"])
    suggestion = len(issues["suggestion"])
    
    # Update totals
    stats["totals"]["critical"] += critical
    stats["totals"]["warning"] += warning
    stats["totals"]["suggestion"] += suggestion
    stats["totals"]["files"] += 1
    
    # Add to recent (keep last 10)
    timestamp = datetime.now().strftime("%H:%M")
    recent_entry = {
        "file": filepath,
        "abs_path": str((Path(root_dir) / filepath).resolve()),
        "type": file_type,
        "time": f"{timestamp}",
        "critical": critical,
        "warning": warning,
        "suggestion": suggestion,
        "status": "critical" if critical > 0 else "warning" if warning > 0 else "clean",
        "issues": issues
    }
    
    # Add git blame info if available
    if get_file_last_author:
        try:
            full_path = Path(root_dir) / filepath
            blame_info = get_file_last_author(str(full_path))
            if blame_info:
                recent_entry["author"] = blame_info.get("author", "")
                recent_entry["author_date"] = blame_info.get("relative_date", "")
                recent_entry["commit_msg"] = blame_info.get("commit_message", "")[:40]
        except:
            pass
    
    stats["recent"].insert(0, recent_entry)
    stats["recent"] = stats["recent"][:10]
    
    # Update daily breakdown
    today = datetime.now().strftime("%Y-%m-%d")
    day_name = datetime.now().strftime("%a")
    if today not in stats["daily"]:
        stats["daily"][today] = {"day": day_name, "critical": 0, "warning": 0, "suggestion": 0}
    stats["daily"][today]["critical"] += critical
    stats["daily"][today]["warning"] += warning
    stats["daily"][today]["suggestion"] += suggestion
    
    # Keep only last 7 days
    if len(stats["daily"]) > 7:
        sorted_days = sorted(stats["daily"].keys())
        for old_day in sorted_days[:-7]:
            del stats["daily"][old_day]
    
    # Save
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)

def get_file_hash(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def review_file(client, filepath, agent_context, custom_prompt):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        if len(code) < 10:
            return None
        
        # Split into system and user messages for better model handling
        # Using simplified context for stability with Z.AI
        system_content = custom_prompt + "\n\nCONTEXT RULES:\n" + agent_context
        # Previous reduced context: custom_prompt + "\n\n(Context reduced for stability)"
        
        user_content = f"Please review this code ({filepath}):\n```\n{code[:4000]}\n```\n\nREMINDER: OUTPUT ONLY [CRITICAL], [WARNING], [SUGGESTION] ENTRIES. DO NOT ADD SUMMARIES."
        
        # Select model based on provider
        # Select model based on provider
        use_ollama = os.environ.get('USE_OLLAMA', 'false').lower() == 'true'
        use_groq = os.environ.get('USE_GROQ', 'false').lower() == 'true'
        
        if use_ollama:
            model = os.environ.get('OLLAMA_MODEL', 'qwen2.5-coder:7b')
        elif use_groq:
            model = os.environ.get('GROQ_MODEL', 'llama3-70b-8192')
        else:
            model = os.environ.get('ZAI_MODEL', 'glm-4')
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_content},
                {'role': 'user', 'content': user_content}
            ],
            max_tokens=1000
        )
        content = response.choices[0].message.content
        if not content:
            return "Error reviewing: API returned empty response"
        return content
    except Exception as e:
        return f"Error reviewing: {e}"

def find_files(root_dir, config):
    files = {}
    extensions = set(config.get("watch_extensions", DEFAULT_CONFIG["watch_extensions"]))
    ignore_dirs = set(config.get("ignore_dirs", DEFAULT_CONFIG["ignore_dirs"]))
    
    for path in Path(root_dir).rglob('*'):
        if path.is_file() and path.suffix in extensions:
            if not any(ignored in path.parts for ignored in ignore_dirs):
                files[str(path)] = get_file_hash(path)
    return files

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    abs_root = os.path.abspath(root)
    
    config = load_config(abs_root)
    custom_prompt = load_custom_prompt(abs_root)
    
    print("=" * 60)
    print("  LOCAL CODERABBIT v3.0 - Context-Aware Watcher")
    print("=" * 60)
    print(f"📁 Watching: {abs_root}")
    print(f"📄 Extensions: {', '.join(config['watch_extensions'])}")
    print(f"⏱️  Debounce: {config['debounce_seconds']}s")
    print(f"🎚️  Min Severity: {config.get('min_severity', 'suggestion')}")
    print(f"📝 History: {'Enabled' if config.get('history', {}).get('enabled') else 'Disabled'}")
    print(f"🔔 Notifications: {'Critical Only' if config.get('notifications', {}).get('on_critical_only') else 'All'}")
    
    if custom_prompt != BASE_PROMPT:
        print(f"📋 Custom Prompt: Loaded from prompts.json")
    
    # Start real-time server for dashboard
    if SSE_AVAILABLE and start_sse_server:
        try:
            start_sse_server(8765)
            print(f"🌐 Real-time: http://localhost:8765 (SSE)")
        except Exception as e:
            print(f"⚠️  Real-time server failed: {e}")
    
    print()
    
    print("🤖 Loading .agent context...")
    agent_context = load_agent_context(abs_root)
    if agent_context:
        print(f"   ✅ Agent rules loaded ({len(agent_context)} chars)")
    else:
        print("   ℹ️  No .agent folder found - using default rules")
    print("-" * 60)
    print("👁️  Watching for changes... (Ctrl+C to stop)")
    print()
    
    client = get_client()
    known_files = find_files(root, config)
    pending_review = {}
    
    while True:
        current_files = find_files(root, config)
        
        for filepath, filehash in current_files.items():
            if filepath not in known_files or known_files[filepath] != filehash:
                pending_review[filepath] = time.time()
        
        now = time.time()
        to_review = [f for f, t in pending_review.items() if now - t >= config["debounce_seconds"]]
        
        for filepath in to_review:
            rel_path = os.path.relpath(filepath, abs_root)
            print(f"\n📝 Reviewing: {rel_path}")
            print("-" * 40)
            
            # Notify dashboard that review is starting
            if notify_status:
                notify_status(f"Reviewing {rel_path}...", "reviewing")
            
            result = review_file(client, filepath, agent_context, custom_prompt)
            if result:
                print(f"\n======== [DEBUG] RAW AI RESPONSE ========\n{result}\n=========================================\n")
                issues = parse_severity(result)
                filtered = filter_by_severity(
                    issues, 
                    config.get("min_severity", "suggestion"),
                    config.get("severity_levels", DEFAULT_CONFIG["severity_levels"])
                )
                
                # Display results
                if "Error reviewing" in result:
                    print(f"❌ {result}")
                elif filtered:
                    for issue in filtered:
                        print(issue)
                elif "✅" in result or "No issues" in result.lower():
                    print("✅ No issues found")
                else:
                    print("✅ All issues below severity threshold")
                
                # Send notification if critical issues found
                notif_config = config.get("notifications", {})
                if notif_config.get("enabled", True):
                    has_critical = len(issues["critical"]) > 0
                    if has_critical:
                        send_notification(
                            f"🔴 Critical Issue in {rel_path}",
                            issues["critical"][0] if issues["critical"] else "Critical issue detected",
                            is_critical=True
                        )
                    elif not notif_config.get("on_critical_only", True) and filtered:
                        send_notification(
                            f"Code Review: {rel_path}",
                            f"{len(filtered)} issues found",
                            is_critical=False
                        )
                
                save_to_history(abs_root, config, filepath, result, issues)
                
                # Send webhook notifications
                if notify_webhooks:
                    try:
                        # Read code snippet for context
                        with open(filepath, 'r', encoding='utf-8') as f:
                            code_snippet = f.read()[:300]
                        notify_webhooks(config, rel_path, issues, code_snippet)
                    except Exception as e:
                        print(f"   [WEBHOOK] Error: {e}")
                
                # Send real-time SSE notification
                if notify_file_review:
                    notify_file_review(rel_path, issues, "complete")
            
            print()
            del pending_review[filepath]
        
        known_files = current_files
        time.sleep(1)

if __name__ == '__main__':
    main()
