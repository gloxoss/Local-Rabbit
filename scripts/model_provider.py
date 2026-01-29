#!/usr/bin/env python3
"""
Multi-Model Provider for Local CodeRabbit
Supports: Z.AI, Ollama, any OpenAI-compatible API
"""

import os
import json
from pathlib import Path
from openai import OpenAI

class ModelProvider:
    """Manages multiple LLM backends with fallback support."""
    
    def __init__(self, config_path=None):
        self.providers = []
        self._load_providers(config_path)
    
    def _load_providers(self, config_path):
        """Load provider configuration."""
        # Default providers in priority order
        default_providers = [
            {
                "name": "zai",
                "type": "openai",
                "base_url": os.environ.get('ZAI_API_BASE', 'https://api.z.ai/v1'),
                "api_key": os.environ.get('ZAI_API_KEY', os.environ.get('OPENAI_API_KEY')),
                "model": os.environ.get('ZAI_MODEL', 'glm-4'),
                "priority": 1
            },
            {
                "name": "ollama",
                "type": "openai",
                "base_url": os.environ.get('OLLAMA_BASE_URL', 'http://ollama:11434/v1'),
                "api_key": "ollama",  # Ollama doesn't need a real key
                "model": os.environ.get('OLLAMA_MODEL', 'qwen2.5-coder'),
                "priority": 2
            }
        ]
        
        # Try to load from config file
        if config_path and Path(config_path).exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    if 'providers' in config:
                        default_providers = config['providers']
            except:
                pass
        
        # Filter out providers without API keys (except Ollama)
        for p in default_providers:
            if p.get('api_key') or p.get('name') == 'ollama':
                self.providers.append(p)
        
        # Sort by priority
        self.providers.sort(key=lambda x: x.get('priority', 99))
    
    def get_client(self, provider_name=None):
        """Get an OpenAI client for the specified or first available provider."""
        for p in self.providers:
            if provider_name and p['name'] != provider_name:
                continue
            try:
                client = OpenAI(
                    api_key=p.get('api_key', 'dummy'),
                    base_url=p['base_url']
                )
                return client, p['model'], p['name']
            except:
                continue
        
        raise Exception("No available model providers")
    
    def chat(self, messages, max_tokens=1000, provider_name=None):
        """Send chat completion with automatic fallback."""
        errors = []
        
        for p in self.providers:
            if provider_name and p['name'] != provider_name:
                continue
            
            try:
                client = OpenAI(
                    api_key=p.get('api_key', 'dummy'),
                    base_url=p['base_url'],
                    timeout=30
                )
                
                response = client.chat.completions.create(
                    model=p['model'],
                    messages=messages,
                    max_tokens=max_tokens
                )
                
                return {
                    "content": response.choices[0].message.content,
                    "provider": p['name'],
                    "model": p['model']
                }
            except Exception as e:
                errors.append(f"{p['name']}: {str(e)}")
                continue
        
        raise Exception(f"All providers failed: {'; '.join(errors)}")


def test_providers():
    """Test which providers are available."""
    print("🔍 Testing model providers...\n")
    
    provider = ModelProvider()
    
    for p in provider.providers:
        print(f"📡 {p['name'].upper()}")
        print(f"   URL: {p['base_url']}")
        print(f"   Model: {p['model']}")
        
        try:
            client = OpenAI(
                api_key=p.get('api_key', 'dummy'),
                base_url=p['base_url'],
                timeout=5
            )
            # Quick test
            models = client.models.list()
            print(f"   Status: ✅ Connected")
        except Exception as e:
            print(f"   Status: ❌ {str(e)[:50]}")
        print()


if __name__ == '__main__':
    test_providers()
