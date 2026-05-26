# Complete Build Plan: Local CodeRabbit Alternative
## Self-Hosted AI Code Review System (PR-Agent + Ollama)

**Last Updated:** January 26, 2026  
**Target Stack:** Docker Compose, Ollama, PR-Agent, DeepSeek-Coder, GitHub  
**Deployment Model:** Single-machine or VPS (localhost architecture)

---

## Executive Summary

This document outlines a **production-ready architecture** for building a fully self-hosted, privacy-first alternative to CodeRabbit. Instead of relying on CodeRabbit's enterprise-only self-hosted licensing (restricted to 500+ seat organizations), we architect a **composable system** using:

- **Ollama** (inference engine) – Runs local LLMs with OpenAI-compatible API
- **PR-Agent** (logic layer) – CodiumAI's open-source code review automation
- **GitHub/GitLab integration** – Webhook or GitHub Actions-based triggering
- **Docker Compose** – Orchestrates both services with one command

**Key Value Propositions:**
- ✅ **Zero external API calls for code processing** (all inference local)
- ✅ **Unrestricted by seat licenses** (truly self-hosted)
- ✅ **Customizable prompts** for your team's coding standards
- ✅ **Multi-LLM support** (DeepSeek, Llama, Qwen, Mistral)
- ✅ **Deterministic cost** (single-time compute, no per-review fees)

**Trade-offs:**
- ⚠️ **Latency:** Local inference slower than cloud (5-30s vs <5s)
- ⚠️ **Model quality:** 7B-14B models less reasoning than GPT-4o
- ⚠️ **Infrastructure:** Requires 16GB+ RAM or GPU for acceptable speed

---

## System Architecture

### 1. High-Level Data Flow

```
GitHub Event (PR opened/updated)
    ↓
[GitHub Webhook] OR [GitHub Actions]
    ↓
PR-Agent Container (Logic Layer)
    ├─ Fetches PR diff from GitHub API
    ├─ Tokenizes code (prepares prompt context)
    ↓
[Ollama Container] (Inference Layer)
    ├─ Receives prompt over HTTP (OpenAI-compatible /v1/chat/completions)
    ├─ Runs LLM inference locally
    ├─ Returns tokens back to PR-Agent
    ↓
PR-Agent (continued)
    ├─ Parses LLM response
    ├─ Formats into PR comments/review
    ↓
[GitHub API] – Post review back to PR
    ↓
Developer sees AI-generated code feedback in PR UI
```

### 2. Container Network Diagram

```
┌─────────────────────────────────────────────────┐
│         Docker Compose Network                  │
│  ("local-coderabbit" bridge network)            │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐      ┌──────────────────┐ │
│  │  PR-Agent        │      │    Ollama        │ │
│  │  Container       │◄────►│   Container      │ │
│  │                  │      │                  │ │
│  │ Port: 3000       │      │ Port: 11434      │ │
│  │ (webhook server) │      │ (LLM API)        │ │
│  │                  │      │                  │ │
│  │ Routes:          │      │ Models:          │ │
│  │ /review          │      │ deepseek-coder   │ │
│  │ /describe        │      │ llama3.1         │ │
│  │ /improve         │      │ qwen2.5-coder    │ │
│  │                  │      │                  │ │
│  └──────────────────┘      └──────────────────┘ │
│         ▲                            ▲           │
│         │                            │           │
│    [GitHub API]              [Model Storage]    │
│    (GITHUB_TOKEN)            (Volume: /ollama) │
│                                                 │
└─────────────────────────────────────────────────┘
         ▲ (port 3000 exposed to host)
         │
    [GitHub Webhook]
    [GitHub Actions]
```

---

## Implementation Plan

### Phase 1: Infrastructure Setup (30 minutes)

#### 1.1 Directory Structure

```bash
~/projects/local-coderabbit/
├── docker-compose.yml          # Orchestration
├── .env                          # Secrets & config
├── .env.example                  # Template
├── ollama/
│   └── Dockerfile               # Custom Ollama with models pre-loaded
├── pr-agent/
│   ├── .secrets.toml            # PR-Agent config (generated)
│   ├── settings/
│   │   ├── configuration.toml   # Model & behavior settings
│   │   └── pr_reviewer_prompts.toml  # Customizable system prompts
│   └── docker-compose.override.yml  # Optional local overrides
├── scripts/
│   ├── setup.sh                 # One-time initialization
│   ├── start.sh                 # Boot services
│   ├── test-review.sh           # Trigger test PR review
│   └── cleanup.sh               # Teardown
└── docs/
    ├── ARCHITECTURE.md          # This document
    ├── TROUBLESHOOTING.md       # Common issues
    └── CUSTOMIZATION.md         # Prompt engineering
```

#### 1.2 Create Base `.env` File

**File:** `.env`
```bash
# =====================================================
# GitHub Configuration
# =====================================================
GITHUB_TOKEN=ghp_YOUR_ACTUAL_TOKEN_HERE
GITHUB_WEBHOOK_SECRET=your_webhook_secret_string_min_32_chars_long

# Generate a secure webhook secret:
# python3 -c "import secrets; print(secrets.token_hex(32))"

# =====================================================
# Ollama Configuration (Local LLM)
# =====================================================
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=deepseek-coder-v2
OLLAMA_MEMORY_GB=8  # Allocate memory to Ollama container

# Model options:
# - deepseek-coder-v2 (recommended: best code understanding)
# - qwen2.5-coder (faster, good for smaller repos)
# - llama3.1 (general purpose, good for complex logic)
# - mistral (lightweight, good for CI/CD)

# =====================================================
# PR-Agent Configuration
# =====================================================
PR_AGENT_PORT=3000
PR_AGENT_AUTO_REVIEW=true
PR_AGENT_AUTO_DESCRIBE=true
PR_AGENT_AUTO_IMPROVE=true

# Verbosity: debug, info, warning, error
PR_AGENT_LOG_LEVEL=info

# =====================================================
# Infrastructure
# =====================================================
DOCKER_COMPOSE_PROJECT_NAME=local-coderabbit
ENVIRONMENT=development  # or production

# For production, set to HTTPS webhook URL exposed via reverse proxy
WEBHOOK_URL=http://localhost:3000  # Local development
# WEBHOOK_URL=https://your-domain.com/pr-agent  # Production with ngrok/nginx
```

#### 1.3 GitHub Personal Access Token (PAT) Setup

1. **Navigate to GitHub → Settings → Developer settings → Personal access tokens (Fine-grained)**
2. **Create new token:**
   - Token name: `local-coderabbit-review`
   - Expiration: 90 days (rotate periodically)
   - Repository access: Select your test repos
   - Permissions (minimum required):
     - `Contents`: `Read-only` (read PR diffs)
     - `Pull requests`: `Read & write` (post reviews/comments)
     - `Issues`: `Read & write` (optional, for issue linking)

3. **Copy token to `.env`:**
   ```bash
   GITHUB_TOKEN=ghp_1a2b3c4d5e6f7g8h9i0j...
   ```

### Phase 2: Docker Compose Setup (20 minutes)

#### 2.1 Main Orchestration File

**File:** `docker-compose.yml`
```yaml
version: '3.9'

services:
  # =====================================================
  # Ollama: Local LLM Inference Engine
  # =====================================================
  ollama:
    image: ollama/ollama:latest
    container_name: local-coderabbit-ollama
    
    # Resource constraints (adjust for your machine)
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G  # Must accommodate model size
        reservations:
          cpus: '2'
          memory: 4G
    
    # Networking
    networks:
      - coderabbit-net
    ports:
      - "11434:11434"  # Expose for manual testing
    
    # Persistent storage for models
    volumes:
      - ollama_models:/root/.ollama
      - ./ollama/Modelfile:/app/Modelfile:ro
    
    # Start command (ensure server is always listening)
    command: serve
    
    # Health check (wait for Ollama to be ready)
    healthcheck:
      test:
        [
          "CMD",
          "curl",
          "-f",
          "http://localhost:11434/api/tags"
        ]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    
    restart: unless-stopped

  # =====================================================
  # PR-Agent: Code Review Logic Layer
  # =====================================================
  pr-agent:
    image: qodo-ai/pr-agent:latest
    container_name: local-coderabbit-pr-agent
    
    # Networking
    networks:
      - coderabbit-net
    ports:
      - "3000:3000"  # Webhook endpoint
    
    environment:
      # GitHub
      GITHUB_TOKEN: ${GITHUB_TOKEN}
      GITHUB_WEBHOOK_SECRET: ${GITHUB_WEBHOOK_SECRET}
      
      # Ollama (internal Docker DNS)
      OPENAI_API_BASE: ${OLLAMA_BASE_URL}
      OPENAI_API_KEY: sk-dummy  # Ollama doesn't validate
      OPENAI_API_TYPE: openai
      
      # Model
      CONFIG__MODEL: ${OLLAMA_MODEL}
      CONFIG__MODEL_TURBO: ${OLLAMA_MODEL}
      
      # Logging
      LOG_LEVEL: ${PR_AGENT_LOG_LEVEL:-info}
      
      # Feature flags
      github_action_config__auto_review: ${PR_AGENT_AUTO_REVIEW:-true}
      github_action_config__auto_describe: ${PR_AGENT_AUTO_DESCRIBE:-true}
      github_action_config__auto_improve: ${PR_AGENT_AUTO_IMPROVE:-true}
    
    # Persistent configuration
    volumes:
      - ./pr-agent/.secrets.toml:/app/pr_agent/settings/.secrets.toml:ro
      - ./pr-agent/settings:/app/pr_agent/settings:ro
    
    # Wait for Ollama to be healthy before starting
    depends_on:
      ollama:
        condition: service_healthy
    
    # Health check
    healthcheck:
      test:
        [
          "CMD",
          "curl",
          "-f",
          "http://localhost:3000/health"
        ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 45s
    
    restart: unless-stopped

# =====================================================
# Docker Network (shared communication)
# =====================================================
networks:
  coderabbit-net:
    driver: bridge

# =====================================================
# Persistent Volumes
# =====================================================
volumes:
  ollama_models:
    driver: local
```

#### 2.2 Custom Ollama Dockerfile (Pre-load Model)

**File:** `ollama/Dockerfile`
```dockerfile
FROM ollama/ollama:latest

# Set working directory
WORKDIR /app

# Copy custom Modelfile if using quantization
COPY Modelfile .

# Pre-download model at build time
# This ensures the model is ready immediately on container start
RUN ollama serve &  sleep 10 && \
    ollama pull deepseek-coder-v2 && \
    pkill -f "ollama serve"

# Expose API port
EXPOSE 11434

# Default command
CMD ["serve"]
```

**Why pre-load?** First-time model downloads can take 5-15 minutes. Pre-loading in the image ensures fast startup.

### Phase 3: PR-Agent Configuration (15 minutes)

#### 3.1 Core Settings File

**File:** `pr-agent/settings/configuration.toml`
```toml
# =====================================================
# MODEL CONFIGURATION
# =====================================================
[config]
# Primary model for most tasks
model = "deepseek-coder-v2"

# Turbo model for complex analysis (can be same)
model_turbo = "deepseek-coder-v2"

# Fallback if primary fails
fallback_models = ["qwen2.5-coder"]

# Temperature: 0 = deterministic, 1 = creative
temperature = 0.2

# Token limits (adjust for model context window)
max_tokens = 4000

# =====================================================
# GITHUB CONFIGURATION
# =====================================================
[git_provider]
provider_type = "github"

[github]
# GitHub App ID (if using app instead of PAT)
# Leave empty to use GITHUB_TOKEN from env
github_app_id = ""

# Automatically review opened/ready PRs
auto_review = true
auto_describe = true
auto_improve = true

# PR events to trigger on
pr_actions = ["opened", "reopened", "ready_for_review", "review_requested"]

# =====================================================
# REVIEW BEHAVIOR
# =====================================================
[pr_reviewer]
# Only review files matching these patterns
# Leave empty to review all
# file_patterns = ["src/**", "app/**"]

# Skip certain file types
skip_files = ["*.md", "*.json", "package.lock", "yarn.lock"]

# Number of code suggestion to generate per review
max_code_suggestions = 5

# Focus areas (one per line)
focus_on_security = true
focus_on_performance = true
focus_on_maintainability = true

# =====================================================
# DESCRIPTION GENERATION
# =====================================================
[pr_description]
# Auto-generate PR title and description from diff
enabled = true
max_length = 500

# =====================================================
# CODE SUGGESTIONS (Auto-Improve)
# =====================================================
[pr_code_suggestions]
# Maximum suggestions to generate
max_suggestions = 3

# Include refactoring suggestions
include_refactoring = true

# Include security fixes
include_security_fixes = true

# =====================================================
# OUTPUT FORMATTING
# =====================================================
[output]
# How to present reviews
format = "markdown"

# Include complexity analysis
analyze_complexity = true

# =====================================================
# LOGGING & DEBUGGING
# =====================================================
[logging]
level = "info"
# levels: debug, info, warning, error

output_file = "/var/log/pr-agent.log"

# =====================================================
# PERFORMANCE TUNING
# =====================================================
[performance]
# Timeout for LLM inference (seconds)
llm_timeout = 120

# Max concurrent reviews
max_concurrent_reviews = 1

# Batch processing
enable_batch = false
```

#### 3.2 GitHub Secrets File

**File:** `pr-agent/.secrets.toml`
```toml
# Generated from template. Kept out of version control.
# DO NOT COMMIT THIS FILE.

[github]
user_token = "${GITHUB_TOKEN}"

[openai]
# Not used (using Ollama instead), but required by SDK
api_key = "sk-dummy"
api_type = "openai"
api_base = "${OPENAI_API_BASE}"
```

#### 3.3 Custom Review Prompts (Optional)

**File:** `pr-agent/settings/pr_reviewer_prompts.toml`
```toml
# Customize the system prompts to focus on your team's standards

[system_prompts]
# Main review instruction
main_prompt = """
You are a Senior Software Architect and code reviewer with expertise in Next.js, 
React, Python FastAPI, and full-stack systems design. 

Review the provided pull request with focus on:
1. **Scalability & Architecture**: Can this solution handle 10x traffic?
2. **Next.js Best Practices**: App Router, Server Components, proper use of hooks
3. **TypeScript Strictness**: Proper typing, no implicit any
4. **Error Handling**: Comprehensive try-catch, proper logging
5. **Security**: No SQL injection, proper auth/RBAC, input validation
6. **Performance**: Unnecessary re-renders, API optimization, caching strategies
7. **Code Clarity**: Variable naming, DRY principle, unit-testability

Be constructive and specific. Suggest fixes, not just problems.
Prioritize security > performance > style.
"""

# Summarization prompt
summarize_prompt = """
Provide a concise executive summary of this PR in 100-150 words.
Highlight key changes, risks, and recommendations.
"""

# Code suggestion prompt
suggest_prompt = """
Generate 2-3 specific, actionable code improvements for this change.
Include the refactored code snippet and explanation of why it's better.
"""
```

### Phase 4: GitHub Integration Setup (15 minutes)

#### 4.1 Webhook Configuration (For Production)

If running on a remote server (VPS), expose the PR-Agent webhook:

**Option A: ngrok (Free, Easy)**
```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Expose local port 3000 to public URL
ngrok http 3000
# Output: https://abc123.ngrok.io

# Update .env
WEBHOOK_URL=https://abc123.ngrok.io
```

**Option B: Nginx Reverse Proxy (Production)**
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 4.2 GitHub Webhook Registration (Option 1: GitHub App)

For best security and automation:

1. **Go to GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. **Fill in form:**
   - App name: `local-coderabbit`
   - Homepage URL: `https://your-domain.com` (or ngrok URL)
   - Webhook URL: `https://your-domain.com/github-webhook`
   - Webhook secret: `${GITHUB_WEBHOOK_SECRET}` (from `.env`)

3. **Set permissions:**
   - Contents: `Read-only`
   - Pull requests: `Read & write`
   - Checks: `Read & write` (optional)
   - Issues: `Read & write` (optional)

4. **Subscribe to events:**
   - Pull request
   - Pull request review comment
   - Issue comment

5. **Install app on test repository**

#### 4.3 Manual Trigger (Option 2: GitHub Actions)

If you don't want webhooks, trigger reviews via GitHub Actions:

**File:** `.github/workflows/pr-agent-review.yml`
```yaml
name: PR Agent Review

on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]

jobs:
  pr_review:
    runs-on: ubuntu-latest
    
    steps:
      - name: Trigger PR Agent
        run: |
          # Get PR details
          PR_NUMBER=${{ github.event.pull_request.number }}
          REPO=${{ github.repository }}
          
          # Call your local PR-Agent endpoint
          curl -X POST http://your-pr-agent-url.com/review \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" \
            -d "{
              \"repo\": \"$REPO\",
              \"pr_number\": $PR_NUMBER
            }"
```

### Phase 5: Deployment & Initialization (10 minutes)

#### 5.1 Initialization Script

**File:** `scripts/setup.sh`
```bash
#!/bin/bash

set -e  # Exit on error

echo "🚀 Initializing Local CodeRabbit System..."

# 1. Check prerequisites
echo "📋 Checking prerequisites..."
command -v docker &> /dev/null || { echo "❌ Docker not installed"; exit 1; }
command -v docker-compose &> /dev/null || { echo "❌ Docker Compose not installed"; exit 1; }

# 2. Create .env if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your GITHUB_TOKEN"
    exit 1
fi

# 3. Create PR-Agent secrets file
echo "🔐 Generating PR-Agent secrets..."
mkdir -p pr-agent/settings
cp pr-agent/.secrets_template.toml pr-agent/.secrets.toml

# Source .env for substitution
set -a
source .env
set +a

# Replace placeholders
sed -i "s|\${GITHUB_TOKEN}|$GITHUB_TOKEN|g" pr-agent/.secrets.toml
sed -i "s|\${OPENAI_API_BASE}|$OLLAMA_BASE_URL|g" pr-agent/.secrets.toml

# 4. Create Docker networks and volumes
echo "🐳 Setting up Docker infrastructure..."
docker network create coderabbit-net 2>/dev/null || true
docker volume create ollama_models 2>/dev/null || true

# 5. Pull images
echo "📥 Pulling Docker images..."
docker-compose pull

# 6. Build custom Ollama image if needed
if [ -f ollama/Dockerfile ]; then
    echo "🔨 Building custom Ollama image..."
    docker build -t ollama:custom -f ollama/Dockerfile ./ollama
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Review .env configuration"
echo "2. Run: ./scripts/start.sh"
echo "3. Check logs: docker-compose logs -f"
```

#### 5.2 Start Script

**File:** `scripts/start.sh`
```bash
#!/bin/bash

echo "🚀 Starting Local CodeRabbit System..."

# Validate .env
if [ ! -f .env ]; then
    echo "❌ .env file not found. Run ./scripts/setup.sh first"
    exit 1
fi

# Load environment
set -a
source .env
set +a

# Start services
echo "📦 Starting Docker Compose services..."
docker-compose up -d

# Wait for services
echo "⏳ Waiting for services to be healthy..."
echo ""

MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Check Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is healthy"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo "⏳ Waiting... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ Ollama failed to start"
    docker-compose logs ollama
    exit 1
fi

# Check PR-Agent
sleep 5
if curl -s http://localhost:3000/health > /dev/null 2>&1; then
    echo "✅ PR-Agent is healthy"
else
    echo "⚠️  PR-Agent starting... (may take 30-60 seconds)"
fi

echo ""
echo "🎉 Services started!"
echo ""
echo "Access points:"
echo "  - Ollama API:   http://localhost:11434"
echo "  - PR-Agent:     http://localhost:3000"
echo "  - Webhook URL:  $WEBHOOK_URL"
echo ""
echo "View logs:"
echo "  docker-compose logs -f ollama"
echo "  docker-compose logs -f pr-agent"
```

#### 5.3 Test Script

**File:** `scripts/test-review.sh`
```bash
#!/bin/bash

# Trigger a manual review on an existing PR

if [ $# -lt 2 ]; then
    echo "Usage: ./scripts/test-review.sh <repo> <pr_number>"
    echo "Example: ./scripts/test-review.sh username/repo 42"
    exit 1
fi

REPO=$1
PR_NUM=$2

source .env

echo "🧪 Testing PR-Agent review on $REPO#$PR_NUM..."

curl -X POST http://localhost:3000/review \
  -H "Content-Type: application/json" \
  -d "{
    \"repository\": \"$REPO\",
    \"pr_number\": $PR_NUM,
    \"action\": \"review\"
  }"

echo ""
echo "✅ Review triggered. Check GitHub PR for results."
```

### Phase 6: Model Selection & Optimization (Optional)

#### 6.1 Model Comparison

| Model | Size | Speed | Accuracy | RAM | Use Case |
|-------|------|-------|----------|-----|----------|
| **DeepSeek-Coder-V2** | 16B | Medium | Excellent | 8-16GB | ⭐ Recommended: Best code understanding |
| **Qwen2.5-Coder** | 7B | Fast | Good | 4-8GB | Fast reviews, CI/CD integration |
| **Llama 3.1** | 8B/70B | Medium/Slow | Very Good | 4-8GB / 40GB+ | Complex logic, reasoning |
| **Mistral** | 7B | Very Fast | Good | 4GB | Lightweight, edge devices |

#### 6.2 Model-Specific Configuration

**For DeepSeek-Coder (Recommended):**
```bash
docker exec -it local-coderabbit-ollama ollama pull deepseek-coder-v2
# Update .env: OLLAMA_MODEL=deepseek-coder-v2
# Ideal for: Full code reviews, security analysis, refactoring suggestions
```

**For Qwen2.5-Coder (Speed Focus):**
```bash
docker exec -it local-coderabbit-ollama ollama pull qwen2.5-coder
# Update .env: OLLAMA_MODEL=qwen2.5-coder
# Ideal for: CI/CD pipelines, fast turnaround, cost-sensitive
```

**For Llama 3.1 (Reasoning Focus):**
```bash
docker exec -it local-coderabbit-ollama ollama pull llama3.1
# Update .env: OLLAMA_MODEL=llama3.1
# Ideal for: Complex architectural decisions, documentation
```

### Phase 7: Production Hardening

#### 7.1 Security Best Practices

```yaml
# docker-compose.yml additions for production
services:
  pr-agent:
    # Run as non-root user
    user: "1000:1000"
    
    # Read-only filesystem (except /tmp and /var)
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
      - /var/run
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    
    # Secrets management (Docker Secrets for swarm)
    secrets:
      - github_token
    
    environment:
      GITHUB_TOKEN_FILE: /run/secrets/github_token

  ollama:
    # Restrict network
    networks:
      - coderabbit-net  # Only internal communication
    
    # No public port exposure (remove ports section)
    # Only PR-Agent connects internally
```

#### 7.2 Monitoring & Logging

```yaml
services:
  pr-agent:
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"
        labels: "service=pr-agent,env=production"

  ollama:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "2"
        labels: "service=ollama,env=production"
```

**Monitoring via Prometheus (Optional):**
```bash
# Add metrics exporter to PR-Agent
# Expose /metrics endpoint on port 8000
# Scrape from Prometheus
```

---

## Deployment Steps (Quick Start)

### For Local Development (macOS/Linux with Docker)

```bash
# 1. Clone/create project
mkdir ~/local-coderabbit && cd ~/local-coderabbit

# 2. Copy structure (see Phase 1)
# ... create all files mentioned above ...

# 3. Setup
bash scripts/setup.sh

# 4. Edit .env with GitHub token
nano .env

# 5. Start
bash scripts/start.sh

# 6. Verify
docker-compose ps
curl http://localhost:11434/api/tags
curl http://localhost:3000/health

# 7. Create test PR on GitHub and watch webhook trigger
```

### For VPS Deployment (Ubuntu 22.04 LTS)

```bash
# On VPS
sudo apt update && sudo apt install -y docker.io docker-compose git

# Clone your repo (or upload docker-compose files)
git clone <your-repo> local-coderabbit && cd local-coderabbit

# Setup
bash scripts/setup.sh

# Use reverse proxy (nginx/caddy) for HTTPS
# Set WEBHOOK_URL in .env to public domain

# Start
bash scripts/start.sh

# Tail logs
docker-compose logs -f pr-agent
```

---

## Customization Examples

### Example 1: Strict TypeScript Reviews

**File:** `pr-agent/settings/pr_reviewer_prompts.toml`
```toml
[system_prompts]
main_prompt = """
Focus on TypeScript correctness:
1. No implicit 'any' types
2. Strict null checks enabled
3. Proper generics usage
4. Type narrowing where needed
5. Union type handling

Reject PRs with loose typing unless justified in comments.
"""
```

### Example 2: Security-First Reviews

```toml
[system_prompts]
main_prompt = """
SECURITY-FIRST CODE REVIEW

Check for:
1. SQL Injection vulnerabilities (parameterized queries)
2. XSS attack vectors (HTML escaping)
3. CSRF protection tokens present
4. Authentication/Authorization bypass risks
5. Secrets in code (API keys, credentials)
6. Dependency vulnerabilities
7. Input validation completeness
8. Error handling leaks information

REJECT if security issues found. Suggest fixes.
"""
```

### Example 3: Performance-Optimized

```toml
[system_prompts]
main_prompt = """
PERFORMANCE-CRITICAL REVIEW

Analyze:
1. Database queries - N+1 problems?
2. API calls - batching opportunities?
3. Re-renders - unnecessary React updates?
4. Bundle size impact
5. Caching strategies
6. Lazy loading implemented?
7. Asset optimization (images, fonts)
8. Memory leaks potential

Suggest performance improvements with impact metrics.
"""
```

---

## Troubleshooting

### Issue: "Ollama connection refused"

```bash
# Check if Ollama is running
docker-compose ps

# Restart Ollama
docker-compose restart ollama

# Check logs
docker-compose logs ollama

# Verify health
curl http://localhost:11434/api/tags
```

### Issue: "Model not found"

```bash
# List available models
docker exec local-coderabbit-ollama ollama list

# Pull model manually
docker exec local-coderabbit-ollama ollama pull deepseek-coder-v2

# Update .env with correct model name
sed -i 's/OLLAMA_MODEL=.*/OLLAMA_MODEL=deepseek-coder-v2/' .env

# Restart PR-Agent
docker-compose restart pr-agent
```

### Issue: "Review not posting to GitHub"

```bash
# Check PR-Agent logs
docker-compose logs pr-agent | tail -50

# Verify GitHub token is valid
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Check webhook secret matches
grep GITHUB_WEBHOOK_SECRET .env
# Compare with GitHub App settings

# Test manual trigger
bash scripts/test-review.sh myuser/myrepo 1
```

---

## Maintenance & Updates

### Weekly Tasks
- Review PR-Agent logs for errors
- Monitor disk usage (`docker system df`)
- Test on a real PR manually

### Monthly Tasks
- Update models: `docker exec ollama ollama update`
- Clean old containers: `docker system prune`
- Rotate GitHub PAT tokens (90-day expiration)

### Quarterly Tasks
- Upgrade Docker Compose version
- Review PR-Agent release notes for new features
- Benchmark inference speed (note baseline)

---

## Cost & Performance Analysis

### Self-Hosted vs CodeRabbit SaaS

| Metric | Self-Hosted | CodeRabbit |
|--------|-------------|-----------|
| **Setup Cost** | $0 | $0 |
| **Per-Review** | ~$0.01 (electricity) | $5-50 (depends on plan) |
| **Monthly (100 PRs)** | $1-5 | $500-5000+ |
| **Latency** | 10-30s (local) | <5s (cloud) |
| **Data Residency** | 100% local | 3rd-party SaaS |
| **Customization** | Full (open-source) | Limited |
| **Scalability** | Single machine | Unlimited |

### Hardware Requirements

| Tier | Machine | RAM | Inference Speed | Setup |
|------|---------|-----|-----------------|-------|
| **Dev** | MacBook M1/M2 | 16GB | 20-30s/review | Easiest |
| **Small Team** | Ubuntu VM (4 vCPU) | 16GB | 15-20s/review | Medium |
| **Production** | GPU VM (RTX 4060 / A100) | 16-40GB | 5-10s/review | Complex |

---

## Next Steps & Future Enhancements

### Immediate (Week 1)
- [ ] Deploy locally and test on 5 real PRs
- [ ] Customize system prompts for your team
- [ ] Document your team's coding standards in prompts

### Short-term (Month 1)
- [ ] Set up ngrok/reverse proxy for webhook
- [ ] Deploy on VPS for team access
- [ ] Integrate with Slack notifications
- [ ] Set up logging/monitoring (Grafana)

### Medium-term (Quarter 1)
- [ ] Add fine-tuned models specific to your codebase
- [ ] Implement PR auto-fix capabilities (propose commits)
- [ ] Add custom metrics dashboard
- [ ] Integrate with Jira/Linear for issue linking

### Long-term (Year 1)
- [ ] Deploy GPU acceleration (CUDA/ROCm) for 10x speed
- [ ] Add context-awareness (learn codebase patterns)
- [ ] Multi-repo shared state (cross-repo impact analysis)
- [ ] Custom language models trained on your code

---

## Resources & References

- **PR-Agent GitHub:** https://github.com/qodo-ai/pr-agent
- **Ollama Docs:** https://ollama.ai
- **DeepSeek-Coder:** https://github.com/deepseek-ai/deepseek-coder
- **Docker Compose Ref:** https://docs.docker.com/compose/compose-file/
- **GitHub Webhooks:** https://docs.github.com/en/developers/webhooks-and-events/webhooks

---

**Document Version:** 1.0  
**Last Updated:** January 26, 2026  
**Status:** Production-Ready  
**Maintainer:** Your Team
