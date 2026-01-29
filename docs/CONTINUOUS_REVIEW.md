# Continuous Local Review - Watching Any Repository

## Overview

The **Context-Aware Watcher** monitors your code files and triggers AI reviews on every save, using the `.agent` folder rules from your repository.

---

## Quick Start

```powershell
# Start Docker (if not running)
cd "c:\Users\zakio\Desktop\Work\Local Rabbit"
docker compose up -d

# Watch the current repo (Local Rabbit itself)
.\scripts\start-watcher.ps1

# Watch a DIFFERENT repo
.\scripts\start-watcher.ps1 "C:\Users\zakio\Desktop\Work\MyProject"
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────┐
│                    YOUR CODEBASE                          │
│  src/                                                     │
│  ├── components/Button.tsx  ←── file saved               │
│  ├── utils/api.ts                                        │
│  .agent/                     ←── rules loaded             │
│  ├── GEMINI.md                                           │
│  ├── agents/frontend-specialist.md                       │
│  └── skills/clean-code/SKILL.md                          │
└──────────────────────────────────────────────────────────┘
         │
         ▼ (3 second debounce)
┌──────────────────────────────────────────────────────────┐
│                    Z.AI API (GLM-4)                       │
│  Prompt = .agent rules + your code                        │
└──────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│                    TERMINAL OUTPUT                        │
│  📝 Reviewing: src/components/Button.tsx                  │
│  🔴 CRITICAL: Missing aria-label on interactive button   │
│  🟡 WARNING: Inline styles, use design tokens             │
│  🔵 SUGGESTION: Extract to ButtonVariants enum            │
└──────────────────────────────────────────────────────────┘
```

---

## What .agent Files Are Loaded

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `.agent/GEMINI.md` | Main project rules |
| 2 | `.agent/agents/frontend-specialist.md` | Frontend-specific |
| 3 | `.agent/agents/backend-specialist.md` | Backend-specific |
| 4 | `.agent/skills/clean-code/SKILL.md` | Clean code rules |
| 5 | `.agent/skills/frontend-design/SKILL.md` | Design rules |
| 6 | `GEMINI.md` (root) | Fallback |

---

## Configuration

Edit `scripts/watcher.py` to customize:

```python
# File types to watch
WATCH_EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx', '.py'}

# Folders to ignore
IGNORE_DIRS = {'node_modules', '.git', 'dist'}

# Wait time after save before reviewing
DEBOUNCE_SECONDS = 3
```

---

## Example Output

```
==============================================================
  LOCAL CODERABBIT - Context-Aware Watcher
==============================================================
📁 Watching: C:\Users\zakio\Desktop\Work\MyProject
📄 Extensions: .ts, .tsx, .js, .jsx, .py
⏱️  Debounce: 3s

🤖 Loading .agent context...
   📖 Loaded: .agent/GEMINI.md
   📖 Loaded: .agent/skills/clean-code/SKILL.md
   ✅ Agent rules loaded (2340 chars)
------------------------------------------------------------
👁️  Watching for changes... (Ctrl+C to stop)

📝 Reviewing: src/utils/api.ts
----------------------------------------
🔴 CRITICAL: Using `any` type on line 15
🟡 WARNING: Missing error handling in fetch call
🔵 SUGGESTION: Add Zod schema validation for response
```
