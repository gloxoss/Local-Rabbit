# Local CodeRabbit - Complete Testing Guide

> Step-by-step manual to verify all features work correctly.

---

## Quick Start Checklist

```bash
# Run automated tests first
python scripts/test_features.py

# Expected: 20/20 PASS
```

---

## Prerequisites

| Requirement | Check Command | Expected |
|-------------|---------------|----------|
| Python 3.10+ | `python --version` | 3.10+ |
| Node.js 18+ | `node --version` | 18+ (for VS Code extension) |
| Ollama running | `curl http://localhost:11434/api/tags` | JSON response |
| Git installed | `git --version` | Any version |

---

## Test 1: Core Watcher

### 1.1 Start the Watcher

```powershell
# Option A: PowerShell script
.\scripts\start-watcher.ps1

# Option B: Direct Python
python scripts/watcher.py
```

**Expected Output:**
```
🐰 Local CodeRabbit v3.0
📁 Watching: C:\path\to\project
🤖 Model: qwen2.5-coder via Ollama
⏳ Waiting for file changes...
```

### 1.2 Trigger a Review

1. Edit any `.py`, `.js`, or `.ts` file
2. Save the file
3. Watch the terminal for AI review output

**Expected:**
- Review appears within 5-30 seconds
- Issues categorized as 🔴 CRITICAL, 🟡 WARNING, 🔵 SUGGESTION
- Stats saved to `reviews/stats.json`

### 1.3 Verify Stats File

```bash
cat reviews/stats.json
```

**Expected:** JSON with `totals`, `daily`, `recent` arrays

---

## Test 2: Dashboard

### 2.1 Open Dashboard

```powershell
# Option A: Start server and open
python -m http.server 8080
# Then open: http://localhost:8080/dashboard.html

# Option B: Direct file open
start dashboard.html
```

### 2.2 Verify Dashboard Elements

| Element | Location | Expected |
|---------|----------|----------|
| Stats cards | Top row | Files, Critical, Warning, Suggestion counts |
| Trend chart | Left chart | Line chart with 7-day history |
| Donut chart | Right chart | Issue distribution |
| Activity list | Bottom | Recent file reviews |
| Live badge | Header | Green when SSE connected |

### 2.3 Test Auto-Refresh

1. Make a file change while dashboard is open
2. Watch for automatic update (within 10 seconds)

---

## Test 3: Security Scanners

### 3.1 Secret Scanner

```bash
python scripts/secret_scanner.py . text
```

**Expected Output:**
- List of detected secrets (if any)
- File paths with line numbers
- Masked secret values

**Test with Known Secret:**
```bash
echo "AWS_KEY=AKIAIOSFODNN7EXAMPLE" > test_secret.txt
python scripts/secret_scanner.py . text
rm test_secret.txt
```

### 3.2 SAST Scanner

```bash
python scripts/sast_scanner.py scripts/ text
```

**Expected:**
- Security findings with severity levels
- CWE IDs and fix hints
- OWASP category references

### 3.3 Dependency Scanner

```bash
# In a project with package.json or requirements.txt:
python scripts/dependency_scanner.py /path/to/project
```

### 3.4 Unified Security Scan

```bash
python scripts/security_scan.py . text
```

**Expected:**
- Combined report from all scanners
- Security score (0-100)
- Summary table

---

## Test 4: Analytics & Reports

### 4.1 Health Score

```bash
python scripts/health_score.py scripts/
```

**Expected Output:**
```
OVERALL: XX/100  Grade: X

BREAKDOWN:
  Complexity       ████████░░ XX%
  Maintainability  ████████░░ XX%
  Security         ████████░░ XX%
  Test Coverage    ████░░░░░░ XX%
  Documentation    ██████░░░░ XX%
```

### 4.2 Report Generator

```bash
# Standup format
python scripts/report_generator.py . standup

# Detailed format
python scripts/report_generator.py . detailed

# Executive format
python scripts/report_generator.py . executive
```

---

## Test 5: AI Enhancements

### 5.1 Model Router

```bash
python scripts/model_router.py
```

**Expected:**
```
Available models: [list of Ollama models]
Task 'general' -> Model 'deepseek-coder'
Task 'security' -> Model 'llama3.1'
```

### 5.2 Test Generator (Requires Ollama)

```bash
python scripts/test_generator.py scripts/health_score.py
```

**Expected:**
- Generated pytest tests for the file
- Coverage of functions detected

### 5.3 Auto-Fixer (Requires Ollama)

```bash
python scripts/auto_fixer.py
```

**Expected:**
- Demo fix for SQL injection
- Diff preview output

---

## Test 6: Team Features

### 6.1 Multi-Project Manager

```bash
# Initialize
python scripts/multi_project.py add "TestProject" .

# List projects
python scripts/multi_project.py list

# Get stats
python scripts/multi_project.py stats

# Cleanup
python scripts/multi_project.py remove testproject
```

### 6.2 Team Manager

```bash
# Initialize team config
python scripts/team_manager.py init

# List members
python scripts/team_manager.py list

# Add member
python scripts/team_manager.py add "John Doe" john@email.com johndoe

# Get file owners
python scripts/team_manager.py owners scripts/watcher.py

# Generate CODEOWNERS
python scripts/team_manager.py codeowners
```

### 6.3 Review Queue

```bash
# View queue stats
python scripts/review_queue.py stats

# List pending items
python scripts/review_queue.py list
```

---

## Test 7: VS Code Extension

### 7.1 Build Extension

```bash
cd vscode-extension
npm install
npm run compile
```

**Expected:** No errors, `out/` folder created

### 7.2 Test in VS Code

1. Open `vscode-extension/` folder in VS Code
2. Press `F5` to launch Extension Development Host
3. Open a project folder
4. Check for:
   - Status bar item (bottom right)
   - Commands in Command Palette (`Ctrl+Shift+P` → "CodeRabbit")

### 7.3 Test Commands

| Command | How to Test |
|---------|-------------|
| Review Current File | `Ctrl+Shift+R` or Command Palette |
| Review Workspace | Command Palette → "Review Workspace" |
| Clear Diagnostics | Command Palette → "Clear Diagnostics" |
| Show Dashboard | Command Palette → "Show Dashboard" |

---

## Test 8: Pre-Commit Hook

### 8.1 Install Hook

```powershell
.\scripts\install-hook.ps1
```

### 8.2 Test Hook

```bash
# Make a change with a "bug"
echo "password = 'admin123'" >> test_file.py
git add test_file.py
git commit -m "test commit"
```

**Expected:**
- Hook runs review
- Blocks commit if critical issues found
- Shows review output

**Cleanup:**
```bash
rm test_file.py
git reset HEAD
```

---

## Test 9: Webhooks (Optional)

### 9.1 Configure Webhook

Edit `config.json`:
```json
{
  "webhooks": {
    "enabled": true,
    "slack_url": "https://hooks.slack.com/services/YOUR/WEBHOOK",
    "discord_url": "https://discord.com/api/webhooks/YOUR/WEBHOOK",
    "notify_on": ["critical", "warning"]
  }
}
```

### 9.2 Test Webhook

1. Start watcher
2. Save a file with known issues
3. Check Slack/Discord for notification

---

## Test 10: Docker Setup (Optional)

### 10.1 Build and Run

```bash
docker-compose up -d
```

### 10.2 Verify Services

```bash
docker-compose ps
```

**Expected:**
- `ollama` container running
- `pr-agent` container running (if configured)

### 10.3 Test PR-Agent

1. Create a PR on GitHub
2. Add comment: `/review`
3. Wait for PR-Agent response

---

## Troubleshooting

### Ollama Not Responding

```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve
```

### Dashboard Not Updating

```bash
# Check stats.json exists
cat reviews/stats.json

# Regenerate stats
python -c "from scripts.watcher import update_dashboard_stats; print('OK')"
```

### VS Code Extension Not Loading

```bash
# Rebuild
cd vscode-extension
npm run compile

# Check for errors in Output panel → "Extension Host"
```

### Permission Errors on Windows

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Test Summary Checklist

| # | Feature | Tested | Notes |
|---|---------|--------|-------|
| 1 | Core Watcher | ☐ | |
| 2 | Dashboard | ☐ | |
| 3 | Secret Scanner | ☐ | |
| 4 | SAST Scanner | ☐ | |
| 5 | Dependency Scanner | ☐ | |
| 6 | Health Score | ☐ | |
| 7 | Report Generator | ☐ | |
| 8 | Model Router | ☐ | |
| 9 | Test Generator | ☐ | |
| 10 | Auto-Fixer | ☐ | |
| 11 | Multi-Project | ☐ | |
| 12 | Team Manager | ☐ | |
| 13 | Review Queue | ☐ | |
| 14 | VS Code Extension | ☐ | |
| 15 | Pre-Commit Hook | ☐ | |
| 16 | Webhooks | ☐ | |
| 17 | Docker | ☐ | |

---

## Quick Smoke Test Script

Run this for a quick verification:

```bash
python -c "
import sys
sys.path.insert(0, 'scripts')

tests = [
    ('watcher', 'FileWatcher'),
    ('secret_scanner', 'SECRET_PATTERNS'),
    ('sast_scanner', 'SECURITY_RULES'),
    ('health_score', 'calculate_health_score'),
    ('model_router', 'ModelRouter'),
    ('multi_project', 'ProjectManager'),
    ('team_manager', 'TeamManager'),
    ('review_queue', 'ReviewQueue'),
]

for module, attr in tests:
    try:
        m = __import__(module)
        assert hasattr(m, attr)
        print(f'[OK] {module}')
    except Exception as e:
        print(f'[FAIL] {module}: {e}')
"
```

**Expected:** All `[OK]`
