"""
Multi-Model Router for Local CodeRabbit
Automatically selects the best AI model based on file type, complexity, and cost.

Phase 2 of Smart Reviews - intelligent model routing.
"""

import os
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class ModelProvider(Enum):
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


@dataclass
class ModelConfig:
    provider: ModelProvider
    model_name: str
    base_url: str
    api_key_env: str
    max_tokens: int = 1000
    temperature: float = 0.2
    
    @property
    def api_key(self) -> Optional[str]:
        return os.environ.get(self.api_key_env)
    
    @property
    def is_available(self) -> bool:
        if self.provider == ModelProvider.OLLAMA:
            return True  # Ollama doesn't need API key
        return bool(self.api_key)


# Model definitions
MODELS = {
    # Fast & cheap - for simple files
    "groq-llama-8b": ModelConfig(
        provider=ModelProvider.GROQ,
        model_name="llama-3.1-8b-instant",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        max_tokens=500
    ),
    
    # Balanced - default
    "groq-llama-70b": ModelConfig(
        provider=ModelProvider.GROQ,
        model_name="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY"
    ),
    
    # Thorough - for security-sensitive files
    "openai-gpt4": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4-turbo-preview",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        max_tokens=1500
    ),
    
    # Large context - for complex files
    "anthropic-claude": ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-5-sonnet-20241022",
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=2000
    ),
    
    # Local/Offline
    "ollama-qwen": ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_name="qwen2.5-coder:7b",
        base_url="http://localhost:11434/v1",
        api_key_env="OLLAMA_API_KEY"
    ),
}

# Security-sensitive file patterns
SECURITY_PATTERNS = [
    r'auth', r'login', r'crypt', r'password', r'secret', 
    r'token', r'session', r'oauth', r'jwt', r'api.?key',
    r'credential', r'permission', r'rbac', r'acl'
]

# Complex file patterns (framework/architecture)
COMPLEX_PATTERNS = [
    r'middleware', r'router', r'controller', r'provider',
    r'context', r'store', r'reducer', r'saga'
]


class ModelRouter:
    """Routes code review requests to the best available model."""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.default_model = self.config.get("default_model", "groq-llama-70b")
        self.enable_routing = self.config.get("enable_routing", True)
    
    def select_model(
        self, 
        filename: str, 
        code: str, 
        force_model: Optional[str] = None
    ) -> ModelConfig:
        """
        Select the best model for reviewing the given code.
        
        Priority:
        1. Forced model (if specified and available)
        2. Security-sensitive files → GPT-4 (if available)
        3. Complex/large files → Claude (if available)
        4. Simple files → Llama 8B
        5. Default → Llama 70B
        """
        # If routing is disabled or model is forced
        if force_model and force_model in MODELS:
            model = MODELS[force_model]
            if model.is_available:
                return model
        
        if not self.enable_routing:
            return self._get_default_model()
        
        # Analyze the file
        analysis = self._analyze_file(filename, code)
        
        # Security-sensitive → GPT-4
        if analysis["is_security_sensitive"]:
            if MODELS["openai-gpt4"].is_available:
                return MODELS["openai-gpt4"]
        
        # Complex or large → Claude
        if analysis["is_complex"] or analysis["line_count"] > 500:
            if MODELS["anthropic-claude"].is_available:
                return MODELS["anthropic-claude"]
        
        # Simple and short → Llama 8B (fast)
        if analysis["line_count"] < 100 and not analysis["is_complex"]:
            if MODELS["groq-llama-8b"].is_available:
                return MODELS["groq-llama-8b"]
        
        # Default
        return self._get_default_model()
    
    def _analyze_file(self, filename: str, code: str) -> dict:
        """Analyze file characteristics for routing decisions."""
        filename_lower = filename.lower()
        code_lower = code.lower()
        lines = code.split('\n')
        
        # Check for security-sensitive patterns
        is_security = any(
            re.search(pattern, filename_lower) or re.search(pattern, code_lower[:1000])
            for pattern in SECURITY_PATTERNS
        )
        
        # Check for complex patterns
        is_complex = any(
            re.search(pattern, filename_lower)
            for pattern in COMPLEX_PATTERNS
        )
        
        # Also check for complexity indicators in code
        complexity_indicators = [
            len(re.findall(r'\bclass\b', code)) > 3,  # Multiple classes
            len(re.findall(r'\bdef\b|\bfunction\b', code)) > 10,  # Many functions
            len(re.findall(r'\bimport\b|\bfrom\b', code)) > 15,  # Many imports
            len(re.findall(r'\btry\b|\bcatch\b|\bexcept\b', code)) > 5  # Error handling
        ]
        is_complex = is_complex or sum(complexity_indicators) >= 2
        
        return {
            "filename": filename,
            "line_count": len(lines),
            "is_security_sensitive": is_security,
            "is_complex": is_complex,
            "extension": Path(filename).suffix.lower()
        }
    
    def _get_default_model(self) -> ModelConfig:
        """Get the default model, falling back if unavailable."""
        # Try default
        if self.default_model in MODELS and MODELS[self.default_model].is_available:
            return MODELS[self.default_model]
        
        # Fallback order
        fallback_order = [
            "groq-llama-70b",
            "groq-llama-8b",
            "ollama-qwen",
            "openai-gpt4",
            "anthropic-claude"
        ]
        
        for model_key in fallback_order:
            if model_key in MODELS and MODELS[model_key].is_available:
                return MODELS[model_key]
        
        # Last resort - return default even if unavailable
        return MODELS[self.default_model]
    
    def get_available_models(self) -> list[str]:
        """Return list of available model keys."""
        return [key for key, model in MODELS.items() if model.is_available]
    
    def explain_selection(self, filename: str, code: str) -> str:
        """Explain why a particular model was selected."""
        analysis = self._analyze_file(filename, code)
        model = self.select_model(filename, code)
        
        reasons = []
        if analysis["is_security_sensitive"]:
            reasons.append("🔒 Security-sensitive file detected")
        if analysis["is_complex"]:
            reasons.append("🧩 Complex file structure")
        if analysis["line_count"] > 500:
            reasons.append(f"📏 Large file ({analysis['line_count']} lines)")
        if analysis["line_count"] < 100:
            reasons.append(f"📄 Small file ({analysis['line_count']} lines)")
        
        reason_text = ", ".join(reasons) if reasons else "Default routing"
        return f"Selected {model.model_name} ({model.provider.value}) - {reason_text}"


# Singleton router instance
_router: Optional[ModelRouter] = None


def get_router(config: Optional[dict] = None) -> ModelRouter:
    """Get or create the model router."""
    global _router
    if _router is None or config:
        _router = ModelRouter(config)
    return _router


def select_model(filename: str, code: str, force_model: Optional[str] = None) -> ModelConfig:
    """Convenience function to select a model."""
    router = get_router()
    return router.select_model(filename, code, force_model)
