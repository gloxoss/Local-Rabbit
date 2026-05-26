"""
Local CodeRabbit — AI Client Factory (SRP)
Creates OpenAI-compatible clients for different providers.
"""

import os
from openai import OpenAI


def get_client():
    """Get OpenAI-compatible client based on environment config."""
    use_ollama = os.environ.get('USE_OLLAMA', 'false').lower() == 'true'
    use_groq = os.environ.get('USE_GROQ', 'false').lower() == 'true'

    if use_ollama:
        ollama_host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        return OpenAI(api_key='ollama', base_url=f"{ollama_host}/v1")
    elif use_groq:
        return OpenAI(
            api_key=os.environ.get('GROQ_API_KEY'),
            base_url="https://api.groq.com/openai/v1"
        )
    else:
        return OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY', os.environ.get('ZAI_API_KEY')),
            base_url=os.environ.get('OPENAI_API_BASE', os.environ.get('ZAI_API_BASE', 'https://api.z.ai/v1'))
        )


def get_model_name():
    """Get the active model name based on provider."""
    use_ollama = os.environ.get('USE_OLLAMA', 'false').lower() == 'true'
    use_groq = os.environ.get('USE_GROQ', 'false').lower() == 'true'

    if use_ollama:
        return os.environ.get('OLLAMA_MODEL', 'qwen2.5-coder:7b')
    elif use_groq:
        return os.environ.get('GROQ_MODEL', 'llama3-70b-8192')
    else:
        return os.environ.get('ZAI_MODEL', 'glm-4')
