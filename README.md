# 🐰 Local CodeRabbit

> **AI-Powered Code Review Running 100% Locally** — Privacy-first, real-time code analysis with Ollama.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-Required-orange.svg)](https://ollama.ai)

---

## 📖 What Is This?

Local CodeRabbit is a **self-hosted AI code reviewer** that watches your files and provides instant feedback — all running on your machine with no data leaving your network.

Think of it as having a senior developer constantly reviewing your code as you write it.

### Why Local?

| Cloud Code Review | Local CodeRabbit |
|-------------------|------------------|
| ❌ Data sent to external servers | ✅ 100% local, your code never leaves |
| ❌ Requires API keys & subscriptions | ✅ Free with Ollama |
| ❌ Rate limits & quotas | ✅ Unlimited reviews |
| ❌ Internet dependency | ✅ Works offline |
| ❌ Privacy concerns | ✅ Complete privacy |

---

## ✨ Features

### Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Real-time Watcher** | Monitors files and triggers AI review on save | ✅ Implemented |
| **Multi-Model Support** | Works with any Ollama model | ✅ Implemented |
| **Live Dashboard** | Beautiful web UI with charts and activity | ✅ Implemented |
| **Severity Classification** | Critical, Warning, Suggestion categories | ✅ Implemented |
| **Review History** | Tracks all reviews with timestamps | ✅ Implemented |
| **Custom Prompts** | Tailored review instructions per project | ✅ Implemented |

### Security Scanning (Pillar 2)

| Feature | Description | Status |
|---------|-------------|--------|
| **Secret Detection** | 38 patterns for API keys, tokens, passwords | ✅ Implemented |
| **SAST Scanner** | 22 OWASP-based security rules | ✅ Implemented |
| **Dependency Scanner** | npm, pip, Go, Rust vulnerability scanning | ✅ Implemented |
| **Unified Scanner** | Combined security score with SARIF export | ✅ Implemented |

### Analytics & Insights (Pillar 3)

| Feature | Description | Status |
|---------|-------------|--------|
| **Code Health Score** | Complexity, maintainability, security metrics | ✅ Implemented |
| **Report Generator** | Standup, detailed, executive reports | ✅ Implemented |
| **Trend Analytics** | 7-day trend visualization in dashboard | ✅ Implemented |
| **SARIF Export** | Standard security format for CI/CD | ✅ Implemented |

### AI Enhancements (Pillar 4)

| Feature | Description | Status |
|---------|-------------|--------|
| **Model Router** | Automatic model selection by task type | ✅ Implemented |
| **Auto-Fix Generator** | AI-powered fix suggestions with diff preview | ✅ Implemented |
| **Test Generator** | Generate pytest/Jest tests from code | ✅ Implemented |
| **Multi-Model Config** | Different models for security/docs/general | ✅ Implemented |

### Team & Enterprise (Pillar 5)

| Feature | Description | Status |
|---------|-------------|--------|
| **Multi-Project Manager** | Manage multiple projects with aggregate stats | ✅ Implemented |
| **Team Manager** | Code ownership, CODEOWNERS generation | ✅ Implemented |
| **Review Queue** | Track issues with status workflow | ✅ Implemented |
| **Webhook Notifications** | Slack & Discord integration | ✅ Implemented |

### IDE Integration (Pillar 1)

| Feature | Description | Status |
|---------|-------------|--------|
| **VS Code Extension** | Inline diagnostics, status bar, commands | ✅ Implemented |
| **Pre-commit Hook** | Block commits with critical issues | ✅ Implemented |
| **Real-time SSE** | WebSocket-like updates to dashboard | ✅ Implemented |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install Ollama
# Windows: Download from https://ollama.ai
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh

# Pull a coding model
ollama pull qwen2.5-coder
```

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/local-coderabbit.git
cd local-coderabbit

# Run setup
.\scripts\setup.ps1  # Windows
# or
./scripts/setup.sh   # Linux/macOS
```

### Start Watching

```bash
# Start the file watcher
python scripts/watcher.py

# Or use PowerShell script
.\scripts\start-watcher.ps1
```

### Open Dashboard

```bash
# Open in browser
start dashboard.html  # Windows
open dashboard.html   # macOS
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL CODERABBIT                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Watcher   │───▶│   Ollama    │───▶│  Dashboard  │     │
│  │   (Python)  │    │   (LLM)     │    │   (HTML)    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                                     ▲             │
│         │           ┌─────────────┐          │             │
│         └──────────▶│  stats.json │──────────┘             │
│                     └─────────────┘                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Security Scanners                                    │   │
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐ │   │
│  │ │ Secrets │ │  SAST   │ │  Deps   │ │   Unified   │ │   │
│  │ └─────────┘ └─────────┘ └─────────┘ └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Team Features                                        │   │
│  │ ┌───────────┐ ┌──────────┐ ┌────────────────────┐   │   │
│  │ │ Projects  │ │   Team   │ │   Review Queue     │   │   │
│  │ └───────────┘ └──────────┘ └────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Local Rabbit/
├── 📄 README.md                 # This file
├── 📄 config.json               # Main configuration
├── 📄 prompts.json              # Custom review prompts
├── 📄 dashboard.html            # Live dashboard UI
├── 📄 prompt-builder.html       # Prompt customization UI
├── 📄 docker-compose.yml        # Docker setup
│
├── 📂 scripts/
│   ├── watcher.py               # Core file watcher
│   ├── model_provider.py        # Multi-model backend
│   ├── pre-commit.py            # Git hook script
│   ├── auto-fix.py              # Original auto-fix
│   │
│   ├── # Security Scanners
│   ├── secret_scanner.py        # Secret/credential detection
│   ├── sast_scanner.py          # Static security analysis
│   ├── dependency_scanner.py    # Dependency vulnerabilities
│   ├── security_scan.py         # Unified security scanner
│   │
│   ├── # Analytics
│   ├── health_score.py          # Code health metrics
│   ├── report_generator.py      # Scheduled reports
│   │
│   ├── # AI Enhancements
│   ├── model_router.py          # Multi-model routing
│   ├── auto_fixer.py            # AI fix generator
│   ├── test_generator.py        # Test generation
│   │
│   ├── # Team Features
│   ├── multi_project.py         # Project management
│   ├── team_manager.py          # Team & ownership
│   ├── review_queue.py          # Issue tracking
│   │
│   ├── # Utilities
│   ├── webhooks.py              # Slack/Discord notifications
│   ├── git_blame.py             # Author tracking
│   ├── realtime_server.py       # SSE server
│   └── test_features.py         # Test suite
│
├── 📂 vscode-extension/         # VS Code integration
│   ├── package.json
│   └── src/
│       ├── extension.ts
│       ├── diagnostics.ts
│       ├── statusBar.ts
│       └── sseClient.ts
│
├── 📂 reviews/                  # Generated review data
│   ├── stats.json               # Dashboard statistics
│   └── history/                 # Review history
│
└── 📂 docs/
    ├── PLAN-feature-roadmap.md  # Feature roadmap
    ├── IMPLEMENTED-features.md  # Implementation status
    └── PLAN-testing-guide.md    # Testing guide
```

---

## ⚙️ Configuration

### config.json

```json
{
  "watch_paths": ["."],
  "extensions": [".py", ".js", ".ts", ".jsx", ".tsx"],
  "min_severity": "warning",
  "model": "qwen2.5-coder",
  "webhooks": {
    "enabled": false,
    "slack_url": "",
    "discord_url": ""
  }
}
```

### Supported Models

| Model | Best For | Size |
|-------|----------|------|
| `qwen2.5-coder` | General code review | 1.5B-7B |
| `deepseek-coder` | Deep code analysis | 6.7B |
| `llama3.1` | Security review | 8B |
| `codellama` | Code completion | 7B |

---

## 🔒 Security Features

### Secret Detection Patterns

- AWS Keys, Secret Keys
- GitHub/GitLab Tokens  
- Slack Webhooks & Tokens
- Database Connection Strings
- Private Keys (RSA, PGP, SSH)
- Generic API Keys & Secrets
- **38 total patterns**

### SAST Rules Coverage

- **A03:2021** – Injection (SQL, Command, XPath)
- **A02:2021** – Cryptographic Failures
- **A07:2021** – XSS Vulnerabilities
- **A04:2021** – Insecure Design
- **A05:2021** – Security Misconfiguration
- **22 security rules** with CWE mapping

---

## 🚧 Known Limitations

### What's NOT Implemented Yet

| Feature | Status | Priority |
|---------|--------|----------|
| LSP Server | 🔲 Planned | High |
| Neovim Plugin | 🔲 Planned | Medium |
| JetBrains Plugin | 🔲 Planned | Low |
| Codebase Learning | 🔲 Planned | Medium |
| Documentation Generator | 🔲 Planned | Low |
| Audit Logging | 🔲 Planned | Medium |
| Role-based Access | 🔲 Planned | Enterprise |
| SSO Integration | 🔲 Planned | Enterprise |

### Current Limitations

1. **No Real-time Streaming** — Reviews wait for full response
2. **Single Machine** — No distributed team server yet
3. **Manual VS Code Install** — Not published to marketplace
4. **No Remote Ollama** — Assumes localhost:11434
5. **English Only** — No i18n support

---

## 🆚 Comparison

### vs. CodeRabbit Cloud

| Feature | CodeRabbit Cloud | Local CodeRabbit |
|---------|------------------|------------------|
| Privacy | ❌ Cloud-based | ✅ 100% local |
| Cost | 💰 $12-25/user/mo | ✅ Free |
| Internet | ❌ Required | ✅ Works offline |
| Models | Fixed | ✅ Any Ollama model |
| PR Review | ✅ Yes | ✅ Yes (via PR-Agent) |
| IDE Integration | ⚠️ Limited | ✅ VS Code |

### vs. GitHub Copilot

| Feature | GitHub Copilot | Local CodeRabbit |
|---------|----------------|------------------|
| Focus | Code completion | Code review |
| Privacy | ❌ Cloud | ✅ Local |
| Security Scanning | ❌ No | ✅ Yes |
| Team Features | ❌ No | ✅ Yes |

---

## 🧪 Testing

```bash
# Run all tests
python scripts/test_features.py

# Run security scan
python scripts/security_scan.py .

# Check code health
python scripts/health_score.py scripts/
```

---

## 📊 Dashboard Preview

The dashboard provides:
- **Real-time stats** — Files reviewed, issue counts
- **Trend charts** — 7-day issue history
- **Activity feed** — Recent reviews with author info
- **Live updates** — SSE connection for instant refresh

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python scripts/test_features.py`
4. Submit a pull request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai) — Local LLM runtime
- [CodeRabbit](https://coderabbit.ai) — Inspiration
- [PR-Agent](https://github.com/Codium-ai/pr-agent) — PR review integration

---

<p align="center">
  <b>Built with 🐰 for developers who value privacy</b>
</p>
