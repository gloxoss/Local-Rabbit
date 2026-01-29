# 🐰 Super Rabbit - Intelligence & Memory Upgrade

> **Goal**: Transform Local CodeRabbit from a reactive reviewer into a **proactive, knowledgeable companion** that remembers project history, indexes the entire codebase, and performs deep analysis.

---

## Architecture: The "Rabbit Brain" 🧠

We will introduce a new subsystem called **Cortex**.

```
┌──────────────────────────────────────────┐
│              Cortex (Python)             │
├─────────────┬─────────────┬──────────────┤
│  Indexing   │  Long-Term  │  Deep Scan   │
│  Engine     │  Memory     │  Agent       │
│  (ChromaDB) │  (SQLite)   │  (LLM Loop)  │
└──────▲──────┴──────▲──────┴──────▲───────┘
       │             │             │
       └─────────────┼─────────────┘
                     ▼
              API Server (/api/chat, /api/scan)
                     ▲       ▲
                     │       │
              VS Code Sidebar  File Watcher
           (Chat UI + Scan Tab) (Continuous)
```

---

## Phase 0️⃣: The Watcher (Always-On Daemon)
**Effort:** Medium | **ETA:** 2-3 hours

### Goal
Ensure the Rabbit "follows" you.
1. **Initial Full Scan**: On startup, read **every** file in the project.
2. **Incremental Watch**: When you add/edit a file, immediately re-index and re-scan it.

### Implementation
- **Backend Watcher**: Python `watchdog` to monitor filesystem.
- **Queue System**: Files to process are added to a background queue.
- **Status API**: `GET /api/status` to show "Indexing 45/100 files...".


---

## Phase 1️⃣: The Cortex (Indexing & RAG)
**Effort:** High | **ETA:** 4-6 hours

### Goal
Enable "Ask about anything" by indexing the codebase into a vector database.

### Implementation
1. **Full Scan Strategy**:
   - Iterate recursively through `project_root`.
   - Skip `.git`, `node_modules`, `venv`.
   - Chunk and embed every file.
2. **Vector Store**: Use `chromadb` (runs locally, no setup needed).
3. **Embeddings**: Use `sentence-transformers/all-MiniLM-L6-v2` (fast, local CPU).
3. **Indexer**:
   - Walks file tree.
   - Chunks code (function/class level).
   - Stores embeddings + metadata (filepath, start_line).
4. **Search API**:
   - `POST /api/query`: Retrieves relevant code chunks.
   - Reranks results using LLM for relevance.

### Deliverables
- [ ] `scripts/cortex/indexer.py`
- [ ] `scripts/cortex/retriever.py`
- [ ] `/api/chat` endpoint

---

## Phase 2️⃣: Deep Scan Agent (The Hunter)
**Effort:** High | **ETA:** 5-7 hours

### Goal
Proactively find "bad code", security holes, and logic errors that single-file reviews miss.

### Implementation
1. **Analysis Pipeline**:
   - **Static Check**: Run `bandit` (security) and `pylint`/`eslint` (quality).
   - **Duplication Hunter**: Use AST hashing to find repeated logic.
   - **Logic Analyzer (LLM)**: Feed critical paths (e.g., auth flows) to "Thinker" model (like DeepSeek-R1 or Claude 3.5).
2. **Report Generator**:
   - Aggregates findings.
   - Auto-generates fix suggestions.
   - Stores in `issues.db`.

### Deliverables
- [ ] `scripts/tools/scanner.py`
- [ ] `scripts/tools/duplication.py`
- [ ] `/api/scan` endpoint

---

## Phase 3️⃣: Persistent Memory (The Journal)
**Effort:** Medium | **ETA:** 3-4 hours

### Goal
"Remember context and continue on it." The AI should know what happened yesterday.

### Implementation
1. **Event Log (`data/memory.db`)**:
   - Logs: `User asked about X`, `Refactored Y`, `Fix failed for Z`.
2. **Context Synthesis**:
   - When user asks "Continue what we did yesterday", Cortex retrieves the last 5 session summaries.
3. **Memory API**:
   - `POST /api/memory/log`
   - `GET /api/memory/context`

### Deliverables
- [ ] `scripts/memory/journal.py`
- [ ] Integration with `api_server.py` to auto-log actions.

---

## Phase 4️⃣: Chat UI
**Effort:** Medium | **ETA:** 3-4 hours

### Goal
A "Chat" tab in the sidebar to interact with the Brain.

### Implementation
1. **Sidebar Tab**: Add "Chat" tab next to "Issues" and "Dashboard".
2. **Chat Interface**:
   - User input area.
   - Markdown rendering for AI responses.
   - "Cite" sources (file links).
3. **Context Menu**: "Ask Rabbit about this" in editor context menu.

### Deliverables
- [ ] `src/chatWebView.ts`
- [ ] `package.json` Chat View updates.

---

## Recommended Tech Stack (Local-First)
- **Vector DB**: ChromaDB
- **Embeddings**: HuggingFace (Local)
- **Thinker Model**: DeepSeek-R1-Distill (via Ollama/Groq) for logic analysis
- **Chat Model**: Llama 3 for fast interaction

---

---

## Next Steps
Reply **"Activate Cortex"** to start!
We will begin by creating the **File Watcher** and **Initial Scanner**.
