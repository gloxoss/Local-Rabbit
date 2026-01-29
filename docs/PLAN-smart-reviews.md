# 🧠 Smart Reviews - Hybrid Intelligence Plan

> **Option D**: Context-Aware + Multi-Model Router + Learning from Feedback

---

## Phase 1️⃣: Context-Aware Reviews
**Effort:** Low | **Impact:** High | **ETA:** 1-2 hours

### Goal
Inject project context (README, architecture, coding standards) into every review.

### Changes

#### [MODIFY] `scripts/api_server.py`
- Add `ContextLoader` class that reads:
  - `README.md` (project overview)
  - `ARCHITECTURE.md` or `docs/` folder
  - `.eslintrc`, `tsconfig.json` (coding standards)
  - `.agent/` folder (custom rules)
- Summarize context to fit within token limits (~2000 tokens)
- Inject into system prompt

#### [NEW] `scripts/context_loader.py`
```python
class ContextLoader:
    def load(project_root: str) -> str:
        # Read key files, summarize, return context string
```

### Verification
- [ ] Review output references project-specific terms
- [ ] Token usage stays reasonable
- [ ] Performance not impacted (cache context)

---

## Phase 2️⃣: Multi-Model Router
**Effort:** Medium | **Impact:** High | **ETA:** 3-4 hours

### Goal
Select best AI model based on file type, complexity, and cost.

### Routing Strategy
| Trigger | Model | Reason |
|---------|-------|--------|
| Security files (`auth`, `crypt`) | GPT-4 | Thorough |
| Simple files (<100 lines) | Llama 3 8B | Fast/Cheap |
| Complex files (>500 lines) | Claude 3.5 | Large context |
| Default | Groq Llama 3.3 | Balanced |

### Changes

#### [NEW] `scripts/model_router.py`
```python
class ModelRouter:
    def select_model(filename: str, code: str, config: dict) -> ModelConfig:
        # Analyze file, return best model
```

#### [MODIFY] `scripts/api_server.py`
- Use `ModelRouter.select_model()` before calling AI
- Return model used in response for transparency

#### [MODIFY] `.env`
- Add keys for multiple providers

### Verification
- [ ] Security files use GPT-4
- [ ] Simple files are fast
- [ ] Fallback works if provider fails

---

## Phase 3️⃣: Learning from Feedback
**Effort:** High | **Impact:** Very High | **ETA:** 6-8 hours

### Goal
Remember which suggestions were accepted/rejected and personalize future reviews.

### Changes

#### [NEW] `scripts/feedback_store.py`
- SQLite or JSON-based storage
- Track accept/reject actions
- Calculate preference weights

#### [NEW] `/api/feedback` endpoint
- `POST /api/feedback` - Record user action
- Extension calls this when user accepts/dismisses fix

#### [MODIFY] `vscode-extension/src/quickFix.ts`
- Send feedback when fix applied or dismissed

### Verification
- [ ] Preferences persist across sessions
- [ ] Rejected issues appear less often
- [ ] Can reset preferences

---

## Next Steps

After approval:
1. Start Phase 1 (Context-Aware)
2. Test and verify
3. Move to Phase 2, then Phase 3

**Ready to start Phase 1?** Reply "go" to begin implementation!
