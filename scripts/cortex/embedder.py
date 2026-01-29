"""
Embedder Service for Cortex
Wraps sentence-transformers to generate vector embeddings for code chunks.
"""

import os
from typing import List
from sentence_transformers import SentenceTransformer

# Use a small, fast model suitable for code/text hybrid
# 'all-MiniLM-L6-v2' is a good balance of speed and performance
# 'multi-qa-MiniLM-L6-cos-v1' is also good for QA
MODEL_NAME = 'all-MiniLM-L6-v2'

class Embedder:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
            print(f"🧠 Cortex: Loading embedding model {MODEL_NAME}...")
            cls._instance.model = SentenceTransformer(MODEL_NAME)
            print("🧠 Cortex: Model loaded.")
        return cls._instance
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text strings."""
        if not texts:
            return []
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

def get_embedder():
    return Embedder()
