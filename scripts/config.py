"""
Local CodeRabbit — Configuration Module (SRP)
Handles config loading, prompt loading, and default values.
"""

import json
from pathlib import Path


DEFAULT_CONFIG = {
    "min_severity": "suggestion",
    "severity_levels": {"critical": 3, "warning": 2, "suggestion": 1},
    "history": {"enabled": True, "folder": "reviews"},
    "notifications": {"enabled": True, "on_critical_only": True},
    "debounce_seconds": 3,
    "watch_extensions": [".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".vue", ".svelte"],
    "ignore_dirs": ["node_modules", ".git", "__pycache__", "dist", "build", ".next", ".agent", "reviews"]
}

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
        except Exception:
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
        except Exception:
            pass
    return BASE_PROMPT


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
