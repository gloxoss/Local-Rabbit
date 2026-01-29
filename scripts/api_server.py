"""
Local CodeRabbit - API Server
FastAPI server that provides HTTP API for code reviews.
Runs in Docker and accepts review requests from any VS Code workspace.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.watcher import (
    get_client, 
    load_agent_context, 
    load_custom_prompt, 
    parse_severity,
    BASE_PROMPT
)
from scripts.context_loader import load_project_context, ContextLoader
from scripts.model_router import get_router, select_model, ModelProvider, MODELS
from scripts.feedback_store import (
    get_feedback_store, 
    record_feedback, 
    get_prompt_adjustments,
    FeedbackEntry
)
from scripts.cortex.indexer import get_indexer
from scripts.watcher_daemon import WatcherDaemon
from scripts.memory.journal import get_journal

app = FastAPI(
    title="Local CodeRabbit API",
    description="AI-powered code review API",
    version="1.0.0"
)

# Enable CORS for VS Code extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global client (initialized once)
client = None
agent_context = ""
custom_prompt = BASE_PROMPT


class ReviewRequest(BaseModel):
    code: str
    filename: str
    language: Optional[str] = None
    project_root: Optional[str] = None  # For context loading


class Issue(BaseModel):
    line: int
    severity: str  # critical, warning, suggestion
    message: str
    fixCode: Optional[str] = None


class ReviewResponse(BaseModel):
    issues: list[Issue]
    raw: str
    model: str
    provider: str = "unknown"
    context_used: bool = False
    routing_reason: Optional[str] = None


class FeedbackRequest(BaseModel):
    issue_type: str
    severity: str
    action: str  # accepted, rejected
    filename: Optional[str] = None
    language: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    n_results: int = 5


class ChatContext(BaseModel):
    file: Optional[str] = None
    selection: Optional[str] = None
    line: Optional[int] = None
    project_root: Optional[str] = None


class ChatRequest(BaseModel):
    query: str
    context: Optional[ChatContext] = None


class HealthResponse(BaseModel):
    status: str
    model: str
    provider: str


class FeedbackStatsResponse(BaseModel):
    total_feedback: int
    accepted: int
    rejected: int
    acceptance_rate: float
    learning_active: bool


@app.post("/api/query")
async def query_codebase(request: QueryRequest):
    """Query the codebase using Cortex (RAG)."""
    try:
        indexer = get_indexer()
        results = indexer.query(request.query, request.n_results)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_chat_history(session_id: str = "default"):
    """Get chat history from memory."""
    try:
        journal = get_journal()
        return {"history": journal.get_history(session_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/history")
async def clear_chat_history(session_id: str = "default"):
    """Clear chat history."""
    try:
        journal = get_journal()
        journal.clear(session_id)
        return {"success": True}
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response with context."""
    return StreamingResponse(stream_chat(request), media_type="text/event-stream")

async def stream_chat(request: ChatRequest):
    """Generator for streaming chat responses."""
    yield f"data: {json.dumps({'type': 'status', 'content': 'Thinking...'})}\n\n"
    
    # Init Journal
    journal = get_journal()
    session_id = "default"  # Use a single session for MVP
    
    # Save User Message
    journal.add_message(session_id, "user", request.query, request.context.dict() if request.context else {})
    
    # 1. Retrieve Context (RAG)
    rag_context = ""
    try:
        indexer = get_indexer()
        # Only query RAG if we have a project root
        if request.context and request.context.project_root:
            results = indexer.query(request.query, n_results=3)
            if results:
                # Format RAG results as context
                rag_context = "\n\nRelevant Project Files:\n" + "\n".join(
                    [f"- {r['metadata']['path']}: {r['text'][:200]}..." for r in results]
                )
                yield f"data: {json.dumps({'type': 'status', 'content': 'Searching knowledge base...'})}\n\n"
    except Exception as e:
        print(f"RAG Error: {e}")

    # 2. Build Prompt
    system_prompt = BASE_PROMPT
    if rag_context:
        system_prompt += f"\n\n<context>\n{rag_context}\n</context>\n"
    
    if request.context:
         file_info = f"\nCurrent File: {request.context.file}" if request.context.file else ""
         selection_info = f"\nSelected Code:\n{request.context.selection}" if request.context.selection else ""
         system_prompt += f"\nUSER CONTEXT:{file_info}{selection_info}"

    # 3. Select Model (Router)
    router = get_router()
    default_model = MODELS.get(router.default_model)
    model = default_model.model_name
    provider = default_model.provider.value
    
    yield f"data: {json.dumps({'type': 'status', 'content': f'Using {model}'})}\n\n"

    # 4. Stream Response
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': request.query}
            ],
            stream=True
        )

        full_response = ""
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        
        # Save AI Message
        journal.add_message(session_id, "assistant", full_response, {"model": model})
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response with context."""
    return StreamingResponse(stream_chat(request), media_type="text/event-stream")


@app.on_event("startup")
async def startup():
    """Initialize AI client on startup."""
    global client, agent_context, custom_prompt
    
    print("🚀 Starting Local CodeRabbit API Server...")
    
    # Load .env if exists
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        print(f"📋 Loading .env from {env_path}")
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ[key.strip()] = val.strip()
    
    # Initialize client
    client = get_client()
    
    # Load context
    root_dir = str(Path(__file__).parent.parent)
    agent_context = load_agent_context(root_dir)
    custom_prompt = load_custom_prompt(root_dir)
    
    # Determine provider
    use_groq = os.environ.get('USE_GROQ', 'false').lower() == 'true'
    use_ollama = os.environ.get('USE_OLLAMA', 'false').lower() == 'true'
    provider = "groq" if use_groq else ("ollama" if use_ollama else "z.ai")
    
    # Start Watcher Daemon (Phase 0)
    print(f"👀 Starting Watcher Daemon for {root_dir}")
    watcher = WatcherDaemon(root_dir)
    watcher.start()
    
    # Initialize Memory Journal (Phase 3)
    print(f"🧠 Initializing Memory Journal at {root_dir}")
    get_journal(root_dir)
    
    print(f"✅ API Server ready!")
    print(f"   Provider: {provider}")
    print(f"   Model: {os.environ.get('GROQ_MODEL', os.environ.get('OLLAMA_MODEL', os.environ.get('ZAI_MODEL', 'unknown')))}")


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    router = get_router()
    available = router.get_available_models()
    default_model = MODELS.get(router.default_model)
    
    return HealthResponse(
        status="ok", 
        model=default_model.model_name if default_model else "unknown", 
        provider=default_model.provider.value if default_model else "unknown"
    )


@app.get("/api/models")
async def list_models():
    """List available models and their status."""
    router = get_router()
    available = router.get_available_models()
    
    models = []
    for key, model in MODELS.items():
        models.append({
            "key": key,
            "name": model.model_name,
            "provider": model.provider.value,
            "available": model.is_available,
            "is_default": key == router.default_model
        })
    
    return {"models": models, "available_count": len(available)}


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Record user feedback on an issue."""
    try:
        entry_id = record_feedback(
            issue_type=request.issue_type,
            severity=request.severity,
            action=request.action,
            filename=request.filename or "",
            language=request.language or ""
        )
        
        # Log feedback
        print(f"📝 Feedback recorded: {request.action} - {request.issue_type} ({request.severity})")
        
        return {
            "success": True,
            "id": entry_id,
            "message": f"Feedback recorded: {request.action}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback/stats", response_model=FeedbackStatsResponse)
async def feedback_stats():
    """Get feedback statistics and learning status."""
    store = get_feedback_store()
    stats = store.get_stats()
    
    return FeedbackStatsResponse(
        total_feedback=stats["total_feedback"],
        accepted=stats["accepted"],
        rejected=stats["rejected"],
        acceptance_rate=stats["acceptance_rate"],
        learning_active=stats["total_feedback"] >= 5  # Need at least 5 feedback entries
    )


@app.get("/api/feedback/preferences")
async def get_preferences():
    """Get current user preferences based on feedback."""
    store = get_feedback_store()
    prefs = store.get_preferences()
    prompt_adjustments = prefs.get_prompt_adjustments()
    
    return {
        "accepted_patterns": prefs.accepted_patterns,
        "rejected_patterns": prefs.rejected_patterns,
        "severity_preferences": prefs.severity_preferences,
        "prompt_adjustments": prompt_adjustments,
        "learning_active": bool(prompt_adjustments)
    }


@app.delete("/api/feedback/reset")
async def reset_feedback():
    """Reset all feedback data (start fresh)."""
    store = get_feedback_store()
    store.reset()
    return {"success": True, "message": "Feedback data reset"}

@app.post("/api/review", response_model=ReviewResponse)
async def review(request: ReviewRequest):
    """Review code and return issues."""
    global client
    
    if not client:
        raise HTTPException(status_code=503, detail="AI client not initialized")
    
    if len(request.code) < 10:
        return ReviewResponse(issues=[], raw="[CLEAN] Code too short to review", model="")
    
    # Build messages with context
    system_content = custom_prompt
    if agent_context:
        system_content += f"\n\nCONTEXT RULES:\n{agent_context}"
    
    # Build system prompt
    system_content = BASE_PROMPT
    
    # 1. Add User Preferences (Phase 3)
    prompt_adjustments = get_prompt_adjustments()
    if prompt_adjustments:
        system_content += f"\n\n{prompt_adjustments}"
        
    # 2. Load Project Context (Phase 1)
    context_used = False
    if request.project_root:
        try:
            project_context = load_project_context(request.project_root)
            if project_context:
                system_content += f"\n\nPROJECT CONTEXT:\n{project_context}"
                context_used = True
        except Exception as e:
            print(f"Warning: Could not load project context: {e}")
    
    # Add file-specific hints
    loader = ContextLoader(request.project_root or str(Path(__file__).parent.parent))
    file_hints = loader.get_file_context(request.filename)
    if file_hints:
        system_content += f"\n\n{file_hints}"
    
    user_content = f"Please review this code ({request.filename}):\n```{request.language or ''}\n{request.code[:4000]}\n```\n\nREMINDER: OUTPUT ONLY [CRITICAL], [WARNING], [SUGGESTION] ENTRIES. DO NOT ADD SUMMARIES."
    
    # Use model router to select best model
    router = get_router()
    model_config = select_model(request.filename, request.code)
    routing_reason = router.explain_selection(request.filename, request.code)
    
    print(f"🧠 {routing_reason}")
    
    # Get or create client for the selected provider
    model = model_config.model_name
    provider_name = model_config.provider.value
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_content},
                {'role': 'user', 'content': user_content}
            ],
            max_tokens=1000
        )
        
        content = response.choices[0].message.content or ""
        
        # Parse issues
        parsed = parse_severity(content)
        
        issues = []
        for severity in ['critical', 'warning', 'suggestion']:
            for item in parsed.get(severity, []):
                # Extract line number from the issue text
                line = 1
                message = item
                
                # Try to extract "Line N:" pattern
                import re
                match = re.search(r'[Ll]ine\s*(\d+)', item)
                if match:
                    line = int(match.group(1))
                
                issues.append(Issue(
                    line=line,
                    severity=severity,
                    message=message
                ))
        
        return ReviewResponse(
            issues=issues, 
            raw=content, 
            model=model, 
            provider=provider_name,
            context_used=context_used,
            routing_reason=routing_reason
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    uvicorn.run(app, host="0.0.0.0", port=port)
