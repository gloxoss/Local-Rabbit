# Operational Playbook

## Tri-Agent Workflow

### Phase 1: Creator (Antigravity IDE)
**Role:** Drafting, creating initial logic

```
Prompt → "Create a Next.js 15 Server Component that fetches user data..."
```
Review the Plan and Code artifacts in the Agent Manager.

---

### Phase 2: Utility (Gemini CLI)
**Role:** Bulk refactoring, documentation, grunt work

```powershell
docker exec -it local-coderabbit-gemini sh
gemini chat "Generate Jest tests for all .ts files in /lib/utils"
```

---

### Phase 3: Reviewer (PR-Agent + Z.AI)
**Role:** Gatekeeper before merge

```bash
git push origin feature/branch
# Wait ~30s for review comments on GitHub PR
```

---

## System Test: Operation "Strict Architect"

### Step 1: Bad Code Created
File: `src/bad-legacy.ts` (intentionally violates rules)

### Step 2: Test Sequence

**Gemini CLI Test:**
```powershell
docker exec -it local-coderabbit-gemini gemini chat "Analyze src/bad-legacy.ts. List 3 violations."
```

**PR-Agent Test:**
```bash
git checkout -b test/ai-check
git add src/bad-legacy.ts
git commit -m "feat: add user processor"
git push origin test/ai-check
# Open PR → Watch for Z.AI review comments
```

### Expected Results
- `any` type flagged
- `let` mutation flagged
- `for` loop → suggest `.filter()`

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Gemini CLI fails | `GEMINI_API_KEY` in `.env` |
| PR-Agent silent | ngrok terminal for 200 OK |
| Z.AI hallucinates | `.secrets.toml` model = `glm-4` |
