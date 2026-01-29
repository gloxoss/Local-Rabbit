# 🖥️ IDE Sidebar GUI Plan

> **Approach:** Option C (Hybrid) - TreeView for Issues + WebView for Dashboard
> **Design:** Minimalistic, VS Code native look

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│           VS Code Sidebar               │
├─────────────────────────────────────────┤
│  🐰 CODERABBIT: ISSUES                  │
│  ────────────────────────────────────   │
│  ▼ Critical (2)          [TreeView]     │
│    └ ⚠️ auth.ts:15                      │
│    └ ⚠️ api.py:42                       │
│  ▼ Warning (3)                          │
│    └ ⚡ utils.js:10                      │
│  ▼ Suggestions (1)                      │
│                                         │
├─────────────────────────────────────────┤
│  📊 CODERABBIT: DASHBOARD               │
│  ────────────────────────────────────   │
│  Health Score: 85/100    [WebView]      │
│  ████████░░ 85%                         │
│                                         │
│  Today: 5 reviews                       │
│  Acceptance: 72%                        │
│                                         │
│  Model: Llama 3.3 70B                   │
│  Status: Connected ✅                   │
│                                         │
│  [Reset Learning] [Settings]            │
└─────────────────────────────────────────┘
```

---

## Phase 1️⃣: Issues TreeView
**Effort:** Medium | **ETA:** 2-3 hours

### Goal
Create a native TreeView panel showing all current issues, grouped by severity.

### New Files

#### [NEW] `src/issuesTreeView.ts`
- `IssuesTreeDataProvider` class implementing `vscode.TreeDataProvider`
- `IssueTreeItem` class for individual issue nodes
- Methods: `refresh()`, `getChildren()`, `getTreeItem()`
- Click handler to navigate to issue location

#### [MODIFY] `src/extension.ts`
- Register TreeView: `vscode.window.createTreeView('localCoderabbit.issues', ...)`
- Add refresh command: `localCoderabbit.refreshIssues`

#### [NEW] `package.json` contributions
```json
{
  "views": {
    "localCoderabbit": [
      { "id": "localCoderabbit.issues", "name": "Issues" }
    ]
  },
  "viewsContainers": {
    "activitybar": [
      { "id": "localCoderabbit", "title": "CodeRabbit", "icon": "resources/rabbit.svg" }
    ]
  }
}
```

### Features
- [x] Group by severity (Critical > Warning > Suggestion)
- [x] Show file name and line number
- [x] Click to navigate to issue
- [x] Right-click context menu (Apply Fix, Dismiss)
- [x] Badge showing total count
- [x] Auto-refresh on review completion

---

## Phase 2️⃣: Dashboard WebView
**Effort:** Medium | **ETA:** 2-3 hours

### Goal
Create a WebView panel with health stats, learning info, and quick actions.

### New Files

#### [NEW] `src/dashboardWebView.ts`
- `DashboardPanel` class extending `vscode.WebviewView`
- HTML/CSS for minimalistic dashboard
- Real-time updates via message passing

#### [NEW] `src/webview/dashboard.html`
Minimal HTML structure:
```html
<div class="stat-row">
  <span class="label">Health Score</span>
  <div class="bar"><div class="fill" style="width: 85%"></div></div>
  <span class="value">85</span>
</div>
```

#### [NEW] `src/webview/dashboard.css`
- VS Code CSS variables for theming
- Dark mode compatible
- Minimal, clean aesthetic

### Features
- [x] Health Score with progress bar
- [x] Today's review count
- [x] Acceptance rate (from feedback)
- [x] Current model & status
- [x] Quick action buttons
- [x] Auto-refresh every 30s

---

## Phase 3️⃣: Activity Bar Icon
**Effort:** Low | **ETA:** 30 mins

### Goal
Add CodeRabbit icon to the VS Code activity bar (left sidebar icons).

### Changes

#### [NEW] `resources/rabbit.svg`
Minimalistic rabbit icon (16x16, monochrome)

#### [MODIFY] `package.json`
```json
"activationEvents": ["onView:localCoderabbit.issues"],
"viewsContainers": {
  "activitybar": [{
    "id": "localCoderabbit",
    "title": "CodeRabbit",
    "icon": "resources/rabbit.svg"
  }]
}
```

---

## Phase 4️⃣: Integration & Polish
**Effort:** Low | **ETA:** 1 hour

### Goal
Wire everything together, add commands, polish UX.

### Tasks
- [ ] Add `localCoderabbit.openSidebar` command
- [ ] Keyboard shortcut: `Ctrl+Shift+C` to focus sidebar
- [ ] Status bar click opens sidebar
- [ ] Smooth transitions between views
- [ ] Loading states
- [ ] Error handling

---

## File Structure After Implementation

```
vscode-extension/
├── src/
│   ├── extension.ts        (modified)
│   ├── issuesTreeView.ts   (new)
│   ├── dashboardWebView.ts (new)
│   ├── diagnostics.ts
│   ├── reviewService.ts
│   └── ...
├── resources/
│   └── rabbit.svg          (new)
├── src/webview/
│   ├── dashboard.html      (new)
│   └── dashboard.css       (new)
└── package.json            (modified)
```

---

## Verification Checklist

- [ ] Sidebar appears in activity bar
- [ ] Issues TreeView shows current issues
- [ ] Clicking issue navigates to file:line
- [ ] Dashboard shows health score
- [ ] Dashboard shows learning stats
- [ ] Dark mode looks correct
- [ ] Light mode looks correct
- [ ] Refresh works after review
- [ ] No performance regression

---

## Design Mockup

```
┌─────────────────────────┐
│ 🐰 ISSUES          🔄   │
├─────────────────────────┤
│ ▼ 🔴 Critical (1)       │
│   └ auth.ts:15          │
│     SQL injection risk  │
│                         │
│ ▼ 🟡 Warning (2)        │
│   └ api.py:42           │
│   └ utils.js:88         │
│                         │
│ ▶ 🔵 Suggestions (3)    │
├─────────────────────────┤
│ 📊 DASHBOARD            │
├─────────────────────────┤
│ Health     ████░░ 85    │
│ Accepted   ██████░ 72%  │
│ Reviews    5 today      │
│                         │
│ ⚡ Llama 3.3 • Connected │
│                         │
│ [🔄 Reset] [⚙️ Config]  │
└─────────────────────────┘
```

---

## Next Steps

1. Reply **"go"** to start Phase 1 (Issues TreeView)
2. Or modify this plan as needed
