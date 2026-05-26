"""
Local CodeRabbit — Shared Pydantic Models
Request/response schemas used by the API server.
"""

from typing import Optional
from pydantic import BaseModel


class ReviewRequest(BaseModel):
    code: str
    filename: str
    language: Optional[str] = None
    project_root: Optional[str] = None


class Issue(BaseModel):
    line: int
    severity: str
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
    action: str
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
