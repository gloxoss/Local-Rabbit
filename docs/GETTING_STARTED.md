# Local CodeRabbit - Complete Real-World Guide

## Step-by-Step: Your First AI-Reviewed PR

---

### STEP 1: Pick a Target Repository

Choose a GitHub repository where you want AI code reviews.
For this example, let's say: `zakio/my-project`

---

### STEP 2: Add the GitHub Action

Copy the PR-Agent workflow to your target repository:

```powershell
# From your target repo root
mkdir -p .github/workflows

# Copy the workflow file
cp "c:\Users\zakio\Desktop\Work\Local Rabbit\.github\workflows\pr-agent.yml" .github/workflows/pr-agent.yml

git add .github/workflows/pr-agent.yml
git commit -m "chore: add AI code review workflow"
git push origin main
```

---

### STEP 3: Add Repository Secrets

Go to your GitHub repo: `https://github.com/zakio/my-project/settings/secrets/actions`

Click **"New repository secret"** and add:

| Secret Name | Value |
|-------------|-------|
| `ZAI_API_BASE` | `https://api.z.ai/v1` |
| `ZAI_API_KEY` | Your Z.AI API key |

---

### STEP 4: Create a Feature Branch

```bash
git checkout -b feature/new-feature
```

---

### STEP 5: Write Some Code

Create or edit a file, for example `src/utils.ts`:

```typescript
// This code has intentional issues for the AI to catch
export function processUsers(data: any) {
  let results = [];
  for (let i = 0; i < data.length; i++) {
    results.push(data[i]);
  }
  return results;
}
```

---

### STEP 6: Commit and Push

```bash
git add .
git commit -m "feat: add user processing"
git push origin feature/new-feature
```

---

### STEP 7: Open a Pull Request

1. Go to `https://github.com/zakio/my-project`
2. Click **"Compare & pull request"**
3. Fill in title and description
4. Click **"Create pull request"**

---

### STEP 8: Wait for AI Review (30-60 seconds)

The GitHub Action will:
1. Detect the new PR
2. Send your code diff to Z.AI (GLM-4)
3. Post review comments directly on the PR

---

### STEP 9: Read the AI Feedback

You'll see comments like:

> 🔴 **Critical**: Using `any` type. Replace with a proper interface or Zod schema.
>
> 🟡 **Warning**: Mutable `let` binding. Use `const` with `.filter()` or `.map()`.
>
> 🔵 **Suggestion**: Consider adding input validation before processing.

---

### STEP 10: Fix and Push

```bash
# Make the suggested fixes
git add .
git commit -m "fix: address AI review feedback"
git push origin feature/new-feature
```

The AI will automatically re-review on push.

---

## Local Testing (Before Pushing)

If you want to test locally before pushing:

```powershell
cd "c:\Users\zakio\Desktop\Work\Local Rabbit"
.\scripts\test-review.ps1 zakio/my-project 1
```

This runs PR-Agent CLI against an existing PR.

---

## Summary Checklist

- [ ] Copy `pr-agent.yml` to target repo
- [ ] Add `ZAI_API_BASE` and `ZAI_API_KEY` secrets
- [ ] Create branch, write code, push
- [ ] Open PR
- [ ] Read AI comments, fix, push again
