#!/usr/bin/env python3
"""
Pytest suite for the SOLID modules extracted from watcher.py.
Tests config.py, client.py, stats.py, and models.py in isolation.
No AI calls, no network — pure unit tests.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from config import (
    DEFAULT_CONFIG, BASE_PROMPT, AGENT_CONTEXT_FILES,
    load_config, load_custom_prompt, load_agent_context
)
from client import get_client, get_model_name
from stats import update_dashboard_stats
from models import (
    ReviewRequest, Issue, ReviewResponse,
    FeedbackRequest, QueryRequest,
    ChatContext, ChatRequest,
    HealthResponse, FeedbackStatsResponse
)


# =============================================================================
# config.py tests
# =============================================================================

class TestLoadConfig:
    """Tests for load_config()."""

    def test_returns_defaults_when_no_config_file(self, tmp_path):
        result = load_config(str(tmp_path))
        assert result == DEFAULT_CONFIG

    def test_merges_user_config(self, tmp_path):
        user_config = {"min_severity": "warning", "custom_key": "value"}
        (tmp_path / "config.json").write_text(json.dumps(user_config))
        result = load_config(str(tmp_path))
        assert result["min_severity"] == "warning"
        assert result["custom_key"] == "value"
        # Defaults still present for unset keys
        assert result["debounce_seconds"] == DEFAULT_CONFIG["debounce_seconds"]

    def test_handles_invalid_json_gracefully(self, tmp_path):
        (tmp_path / "config.json").write_text("{invalid json")
        result = load_config(str(tmp_path))
        assert result == DEFAULT_CONFIG

    def test_default_config_has_required_keys(self):
        required = ["min_severity", "severity_levels", "history", "notifications",
                     "debounce_seconds", "watch_extensions", "ignore_dirs"]
        for key in required:
            assert key in DEFAULT_CONFIG, f"Missing key: {key}"


class TestLoadCustomPrompt:
    """Tests for load_custom_prompt()."""

    def test_returns_base_prompt_when_no_file(self, tmp_path):
        result = load_custom_prompt(str(tmp_path))
        assert result == BASE_PROMPT

    def test_loads_custom_review_prompt(self, tmp_path):
        custom = {"review_prompt": "Custom review rules here"}
        (tmp_path / "prompts.json").write_text(json.dumps(custom))
        result = load_custom_prompt(str(tmp_path))
        assert result == "Custom review rules here"

    def test_falls_back_to_base_if_key_missing(self, tmp_path):
        (tmp_path / "prompts.json").write_text(json.dumps({"other_key": "value"}))
        result = load_custom_prompt(str(tmp_path))
        assert result == BASE_PROMPT

    def test_handles_corrupt_json(self, tmp_path):
        (tmp_path / "prompts.json").write_text("not json")
        result = load_custom_prompt(str(tmp_path))
        assert result == BASE_PROMPT


class TestLoadAgentContext:
    """Tests for load_agent_context()."""

    def test_returns_empty_when_no_agent_files(self, tmp_path):
        result = load_agent_context(str(tmp_path))
        assert result == ""

    def test_loads_agent_file_and_strips_frontmatter(self, tmp_path):
        agent_dir = tmp_path / ".agent"
        agent_dir.mkdir()
        gemini_file = tmp_path / "GEMINI.md"
        gemini_file.write_text("---\ntrigger: always\n---\n# Rules\nBe concise.", encoding="utf-8")
        result = load_agent_context(str(tmp_path))
        assert "Rules" in result
        assert "trigger:" not in result

    def test_base_prompt_contains_severity_markers(self):
        assert "[CRITICAL]" in BASE_PROMPT
        assert "[WARNING]" in BASE_PROMPT
        assert "[SUGGESTION]" in BASE_PROMPT


# =============================================================================
# client.py tests
# =============================================================================

class TestGetClient:
    """Tests for get_client() — verifies provider routing via env vars."""

    @patch.dict(os.environ, {"USE_OLLAMA": "true", "OLLAMA_HOST": "http://test:11434"}, clear=False)
    def test_ollama_client(self):
        client = get_client()
        assert client is not None
        assert "test:11434" in str(client.base_url)

    @patch.dict(os.environ, {"USE_OLLAMA": "false", "USE_GROQ": "true", "GROQ_API_KEY": "test-key"}, clear=False)
    def test_groq_client(self):
        client = get_client()
        assert client is not None
        assert "groq.com" in str(client.base_url)

    @patch.dict(os.environ, {"USE_OLLAMA": "false", "USE_GROQ": "false", "ZAI_API_KEY": "test"}, clear=False)
    def test_default_zai_client(self):
        client = get_client()
        assert client is not None
        assert "z.ai" in str(client.base_url)


class TestGetModelName:
    """Tests for get_model_name()."""

    @patch.dict(os.environ, {"USE_OLLAMA": "true", "OLLAMA_MODEL": "llama3"}, clear=False)
    def test_ollama_model(self):
        assert get_model_name() == "llama3"

    @patch.dict(os.environ, {"USE_OLLAMA": "false", "USE_GROQ": "true", "GROQ_MODEL": "mixtral-8x7b"}, clear=False)
    def test_groq_model(self):
        assert get_model_name() == "mixtral-8x7b"

    @patch.dict(os.environ, {"USE_OLLAMA": "false", "USE_GROQ": "false", "ZAI_MODEL": "glm-4-plus"}, clear=False)
    def test_zai_model(self):
        assert get_model_name() == "glm-4-plus"

    @patch.dict(os.environ, {"USE_OLLAMA": "true"}, clear=False)
    def test_ollama_default_model(self):
        os.environ.pop("OLLAMA_MODEL", None)
        assert get_model_name() == "qwen2.5-coder:7b"


# =============================================================================
# stats.py tests
# =============================================================================

class TestUpdateDashboardStats:
    """Tests for update_dashboard_stats()."""

    def _make_config(self, tmp_path):
        reviews_dir = tmp_path / "reviews"
        reviews_dir.mkdir()
        return {"history": {"folder": "reviews"}}

    def test_creates_stats_file(self, tmp_path):
        config = self._make_config(tmp_path)
        issues = {"critical": ["issue1"], "warning": [], "suggestion": ["sug1"]}
        update_dashboard_stats(str(tmp_path), config, "test.py", issues)

        stats_file = tmp_path / "reviews" / "stats.json"
        assert stats_file.exists()
        stats = json.loads(stats_file.read_text())
        assert stats["totals"]["critical"] == 1
        assert stats["totals"]["suggestion"] == 1
        assert stats["totals"]["files"] == 1

    def test_accumulates_totals(self, tmp_path):
        config = self._make_config(tmp_path)
        issues1 = {"critical": ["c1"], "warning": ["w1"], "suggestion": []}
        issues2 = {"critical": [], "warning": ["w2", "w3"], "suggestion": ["s1"]}
        update_dashboard_stats(str(tmp_path), config, "a.py", issues1)
        update_dashboard_stats(str(tmp_path), config, "b.py", issues2)

        stats = json.loads((tmp_path / "reviews" / "stats.json").read_text())
        assert stats["totals"]["critical"] == 1
        assert stats["totals"]["warning"] == 3
        assert stats["totals"]["files"] == 2

    def test_keeps_recent_capped_at_10(self, tmp_path):
        config = self._make_config(tmp_path)
        issues = {"critical": [], "warning": [], "suggestion": []}
        for i in range(15):
            update_dashboard_stats(str(tmp_path), config, f"file{i}.py", issues)

        stats = json.loads((tmp_path / "reviews" / "stats.json").read_text())
        assert len(stats["recent"]) == 10

    def test_hotspots_sorted_by_score(self, tmp_path):
        config = self._make_config(tmp_path)
        update_dashboard_stats(str(tmp_path), config, "low.py",
                               {"critical": [], "warning": ["w"], "suggestion": []})
        update_dashboard_stats(str(tmp_path), config, "high.py",
                               {"critical": ["c1", "c2"], "warning": ["w"], "suggestion": []})

        stats = json.loads((tmp_path / "reviews" / "stats.json").read_text())
        assert stats["hotspots"][0]["file"] == "high.py"

    def test_daily_breakdown_keeps_7_days(self, tmp_path):
        config = self._make_config(tmp_path)
        # Pre-seed with 8 days of data
        reviews_dir = tmp_path / "reviews"
        old_stats = {
            "totals": {"critical": 0, "warning": 0, "suggestion": 0, "files": 0},
            "recent": [], "hotspots": [], "health_score": 100,
            "daily": {f"2025-01-{10+i:02d}": {"day": "Mon", "critical": 0, "warning": 0, "suggestion": 0} for i in range(8)}
        }
        (reviews_dir / "stats.json").write_text(json.dumps(old_stats))

        issues = {"critical": [], "warning": [], "suggestion": []}
        update_dashboard_stats(str(tmp_path), config, "x.py", issues)

        stats = json.loads((reviews_dir / "stats.json").read_text())
        assert len(stats["daily"]) <= 7


# =============================================================================
# models.py tests
# =============================================================================

class TestPydanticModels:
    """Tests for shared Pydantic models."""

    def test_review_request_valid(self):
        req = ReviewRequest(code="print('hello')", filename="test.py")
        assert req.code == "print('hello')"
        assert req.language is None

    def test_review_request_with_language(self):
        req = ReviewRequest(code="x", filename="t.py", language="python")
        assert req.language == "python"

    def test_issue_model(self):
        issue = Issue(line=10, severity="critical", message="SQL injection")
        assert issue.line == 10
        assert issue.fixCode is None

    def test_issue_with_fix(self):
        issue = Issue(line=5, severity="warning", message="bad", fixCode="good")
        assert issue.fixCode == "good"

    def test_review_response(self):
        resp = ReviewResponse(issues=[], raw="[CLEAN]", model="gpt-4")
        assert resp.provider == "unknown"
        assert resp.context_used is False

    def test_chat_request(self):
        ctx = ChatContext(file="main.py", line=42)
        req = ChatRequest(query="explain this", context=ctx)
        assert req.context.file == "main.py"

    def test_health_response(self):
        resp = HealthResponse(status="ok", model="test", provider="ollama")
        assert resp.status == "ok"

    def test_feedback_stats(self):
        stats = FeedbackStatsResponse(
            total_feedback=100, accepted=80, rejected=20,
            acceptance_rate=0.8, learning_active=True
        )
        assert stats.acceptance_rate == 0.8

    def test_review_request_rejects_missing_required(self):
        with pytest.raises(Exception):
            ReviewRequest(filename="test.py")  # missing 'code'

    def test_query_request_defaults(self):
        req = QueryRequest(query="search this")
        assert req.n_results == 5
