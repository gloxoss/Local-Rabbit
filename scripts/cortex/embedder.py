"""
Embedder Service for Cortex
Uses Ollama's local API to generate embeddings for code chunks.
"""

import os
import requests
import time
from typing import List

# Default to a high-quality efficient model
# Ensure you have run: `ollama pull nomic-embed-text`
DEFAULT_MODEL = 'nomic-embed-text'
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

class Embedder:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
            cls._instance.model = os.environ.get("OLLAMA_EMBEDDING_MODEL", DEFAULT_MODEL)
            cls._instance.base_url = OLLAMA_BASE_URL
            print(f"🧠 Cortex: Using embedding model '{cls._instance.model}' at {cls._instance.base_url}")
        return cls._instance
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text strings using Ollama."""
        if not texts:
            return []
            
        embeddings = []
        # Ollama API doesn't support batching in all versions yet, so we loop.
        # Future optimization: parallelize or use batch endpoint if available.
        for text in texts:
            try:
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text,
                        "options": {"temperature": 0} # Deterministic
                    }
                )
                if response.status_code == 200:
                    embeddings.append(response.json()["embedding"])
                else:
                    print(f"❌ Cortex: Embedding failed: {response.text}")
                    # Fallback or empty? Appending empty list to keep index valid
                    embeddings.append([]) 
            except Exception as e:
                print(f"❌ Cortex: Connection error to Ollama: {e}")
                embeddings.append([])
                
        return embeddings

def get_embedder():
    return Embedder()
