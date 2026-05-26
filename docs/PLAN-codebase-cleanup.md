# Local Rabbit — Full Codebase Audit & Cleanup Plan

> 🤖 **Applying knowledge of `@project-planner` + `@security-auditor`...**

## Overview

Comprehensive audit of the Local Rabbit codebase reveals **7 critical weakness categories** across 49 scripts and 15 root files. This plan prioritizes fixes by impact: security → reliability → code quality → architecture.

## Project Type: **BACKEND** (Python CLI + Services)

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Bare `except:` blocks | 36 | 0 |
| Exposed secrets in `.env` | 2 (GitHub + ZAI) | 0 |
| CORS wildcards | 2 servers | 0 (restricted origins) |
| `.gitignore` coverage | 7 rules | 20+ rules |
| Dead/duplicate files | 5+ | 0 |
| Model init systems | 3 competing | 1 unified |
| Hardcoded URLs | 13+ | 0 (all config-driven) |
| Test coverage | 20 file-structure tests | + integration tests |

---

## 🔴 CATEGORY 1: SECURITY (P0 — Critical)

### 1.1 Exposed Secrets in `.env`
**Files:** [.env](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/.env)

| Line | Secret | Risk |
|------|--------|------|
| 9 | `GITHUB_TOKEN=ghp_keGVAN...` | Full repo access if leaked |
| 16 | `ZAI_API_KEY=d6813a...` | API billing abuse |

**Fix:** Rotate both tokens immediately. Add `.env` validation on startup.

### 1.2 CORS Wildcard `*`
**Files:** [api_server.py:50](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/api_server.py#L50), [server.py:40](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/server.py#L40)

Both servers allow `Access-Control-Allow-Origin: *`, enabling any website to call the API.
**Fix:** Restrict to `localhost` origins or make configurable via `config.json`.

### 1.3 Weak `.gitignore`
**File:** [.gitignore](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/.gitignore)

Missing entries that could leak data:

```diff
+__pycache__/
+*.pyc
+data/
+reviews/
+*.patch
+watcher.log
+node_modules/
+vscode-extension/out/
+.patches/
```

---

## 🟡 CATEGORY 2: ERROR HANDLING (P1 — High)

### 2.1 Bare `except:` Blocks (36 instances)
Silent error swallowing across the codebase. Errors are caught and discarded with no logging, making debugging impossible.

**Top offenders:**

| File | Count | Lines |
|------|-------|-------|
| [watcher.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/watcher.py) | 5 | 110, 122, 169, 285, 372 |
| [realtime_server.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/realtime_server.py) | 3 | 70, 114, 129 |
| [report_generator.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/report_generator.py) | 3 | 83, 292, 312 |
| [model_provider.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/model_provider.py) | 2 | 48, 70 |
| [context_loader.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/context_loader.py) | 5 | 106, 125, 146, 162, 174 |
| 15 other files | 18 | various |

**Fix:** Replace `except:` → `except Exception as e:` + `logging.warning(...)` or `logging.error(...)`.

---

## 🟡 CATEGORY 3: HARDCODED VALUES (P1 — High)

### 3.1 Hardcoded Model Names

| File | Line | Hardcoded Value | Should Be |
|------|------|-----------------|-----------|
| [auto_fixer.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/auto_fixer.py) | 42 | `deepseek-coder:6.7b` | `config.json` or env var |
| [test_generator.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/test_generator.py) | 28 | `deepseek-coder:6.7b` | `config.json` or env var |
| [model_provider.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/model_provider.py) | 29 | `glm-4` | Already uses env, but fallback is stale |
| [auto-fix.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/auto-fix.py) | 46 | `glm-4` | Should match `config.json` model |

### 3.2 Hardcoded Localhost URLs (13 instances)

| File | Line | Hardcoded URL |
|------|------|---------------|
| [model_router.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/model_router.py) | 84 | `http://localhost:11434/v1` |
| [auto_fixer.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/auto_fixer.py) | 42 | `http://localhost:11434` |
| [test_generator.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/test_generator.py) | 28 | `http://localhost:11434` |
| [test_stream.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/test_stream.py) | 6 | `http://localhost:8765` |
| [test_memory.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/test_memory.py) | 7,25 | `http://localhost:8765` |
| [server.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/server.py) | 8 | `PORT = 8080` |

**Fix:** All should read from `OLLAMA_HOST` env var or `config.json`.

---

## 🔵 CATEGORY 4: DEAD & DUPLICATE CODE (P2)

### 4.1 Duplicate Script Pair
**`auto-fix.py`** (201 lines) and **`auto_fixer.py`** (312 lines) do the same thing — generate AI-powered code fixes.

| Feature | auto-fix.py | auto_fixer.py |
|---------|-------------|---------------|
| AI Backend | OpenAI (Z.AI) | Ollama (urllib) |
| Interactive | Yes (stdin prompt) | No |
| Diff Generation | Basic | Rich (colored) |
| Confidence Score | No | Yes |
| Batch Report | No | Yes |

**Fix:** Merge into one `auto_fixer.py` that supports both backends via `model_provider.py`.

### 4.2 Dead Modules (never imported)

| File | Size | Status |
|------|------|--------|
| [model_router.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/model_router.py) | 8.5KB | **Never imported** by any file |
| [review_queue.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/review_queue.py) | 11KB | Scaffolded, not integrated |
| [team_manager.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/team_manager.py) | 12KB | Scaffolded, not integrated |
| [team_sharing.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/team_sharing.py) | 6KB | Scaffolded, not integrated |
| [analytics.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/analytics.py) | 2KB | Scaffolded, not integrated |
| [multi_project.py](file:///c:/Users/zakio/Desktop/Work/Local%20Rabbit/scripts/multi_project.py) | 11KB | Scaffolded, not integrated |

### 4.3 Debug/Test Files in Production

| File | Purpose | Action |
|------|---------|--------|
| `test.js` (root) | 896B test file | Delete or move to `tests/` |
| `test_clean.js` (root) | 393B test file | Delete or move to `tests/` |
| `test_path.py` (root) | 247B test file | Delete or move to `tests/` |
| `debug_rag.py` | Debug script | Move to `scripts/debug/` |
| `debug_zai_content.py` | Debug script | Move to `scripts/debug/` |
| `debug_zai_latency.py` | Debug script | Move to `scripts/debug/` |

---

## 🔵 CATEGORY 5: ARCHITECTURE FRAGMENTATION (P2)

### 5.1 Three Competing Model Init Systems

The codebase has **3 different ways** to initialize an AI client:

| System | File | How It Works |
|--------|------|-------------|
| **Direct init** | `watcher.py` → `get_client()` | Reads env vars, creates OpenAI client |
| **ModelProvider** | `model_provider.py` | Class-based, priority-ordered, fallback |
| **ModelRouter** | `model_router.py` | Routes by file type/complexity, never used |

**Fix:** Unify into `model_provider.py` as the single source. Wire `watcher.py` and `api_server.py` through it.

### 5.2 Two Separate HTTP Servers

| Server | File | Port | Purpose |
|--------|------|------|---------|
| FastAPI | `api_server.py` | dynamic | Full API (reviews, chat, feedback) |
| stdlib | `server.py` | 8080 | Dashboard file server + prompt save |

**Fix:** Merge `server.py` into `api_server.py` (FastAPI can serve static files).

---

## 🟢 CATEGORY 6: CONFIGURATION GAPS (P3)

### 6.1 Missing Config Validation
No startup validation of `config.json`. Missing or malformed fields silently use defaults.

### 6.2 Z.AI API Base URL Inconsistency

| File | URL Used |
|------|----------|
| `.env` | `https://api.z.ai/api/paas/v4/` |
| `auto-fix.py` | `https://api.z.ai/v1` |
| `model_provider.py` | reads from env (correct) |

Two different Z.AI base URLs in the project.

### 6.3 Watcher Uses Polling Instead of Events
`watcher.py` uses `time.sleep(1)` polling which is CPU-inefficient. The new `orchestrator.py` already uses `watchdog`, so `watcher.py` standalone mode should too.

---

## 🟢 CATEGORY 7: TESTING GAPS (P3)

### 7.1 Current Tests

`test_features.py` only tests file structure and JSON validity (20 tests). No logic/integration tests for:
- AI review pipeline
- Security scanner accuracy
- Report generation correctness
- Config loading edge cases
- Webhook delivery

### 7.2 Missing Error Path Tests
No tests for failure scenarios:
- API key missing
- Ollama unreachable
- Malformed config.json
- Large file handling

---

## Task Breakdown

### Phase 1: Security Fixes (P0)
- [ ] **T1.1** Rotate exposed tokens in `.env`, add `.env.example` warnings
- [ ] **T1.2** Replace CORS `*` with localhost-only in `api_server.py` and `server.py`
- [ ] **T1.3** Expand `.gitignore` with all missing patterns
  - INPUT: Current 7-rule `.gitignore`
  - OUTPUT: 20+ rule `.gitignore`
  - VERIFY: `git status` shows no untracked sensitive files

### Phase 2: Error Handling Cleanup (P1)
- [ ] **T2.1** Replace all 36 bare `except:` with typed exceptions + logging (batch fix across 20+ files)
  - INPUT: `grep -rn "except:" scripts/`
  - OUTPUT: All `except:` → `except <Type> as e:` + `logging.error/warning`
  - VERIFY: `grep -rn "except:\s*$" scripts/` returns 0 results

### Phase 3: Hardcoded Value Extraction (P1)
- [ ] **T3.1** Extract hardcoded model names → env vars / `config.json`
- [ ] **T3.2** Extract hardcoded URLs → env vars / `config.json`
- [ ] **T3.3** Fix Z.AI base URL inconsistency

### Phase 4: Dead Code Cleanup (P2)
- [ ] **T4.1** Merge `auto-fix.py` into `auto_fixer.py`, delete `auto-fix.py`
- [ ] **T4.2** Move dead scaffolded modules to `scripts/experimental/`
- [ ] **T4.3** Move debug/test files to proper directories
- [ ] **T4.4** Delete or archive root-level test files

### Phase 5: Architecture Unification (P2)
- [ ] **T5.1** Make `model_provider.py` the single model init system
- [ ] **T5.2** Wire `watcher.py` through `model_provider.py`
- [ ] **T5.3** Merge `server.py` into `api_server.py`

### Phase 6: Config & Robustness (P3)
- [ ] **T6.1** Add `config.json` schema validation on startup
- [ ] **T6.2** Add startup health checks (API connectivity, model availability)

### Phase 7: Testing (P3)
- [ ] **T7.1** Add integration tests for the review pipeline
- [ ] **T7.2** Add failure-path tests for missing API keys, offline Ollama

---

## Phase X: Verification

- [ ] `grep -rn "except:\s*$" scripts/` → 0 results
- [ ] `grep -rn "localhost" scripts/` → only in env-var fallbacks
- [ ] `.gitignore` covers all sensitive directories
- [ ] No CORS wildcard `*` in any server
- [ ] All tests pass: `python scripts/test_features.py`
- [ ] Orchestrator dry-run works: `python scripts/orchestrator.py --dry-run --once`
- [ ] No duplicate script functionality
