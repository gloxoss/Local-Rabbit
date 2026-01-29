"""
Indexer Service for Cortex
Manages ChromaDB vector store and indexing of codebase files.
"""

import threading
import time
import os
import glob
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

from .embedder import get_embedder

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cortex_db")
COLLECTION_NAME = "codebase"

class Indexer:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Indexer, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance
    
    def _init_db(self):
        """Initialize ChromaDB client."""
        # Ensure data directory exists
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        
        print(f"🧠 Cortex: Connecting to Vector DB at {DB_PATH}")
        self.client = chromadb.PersistentClient(path=DB_PATH)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)
        self.embedder = get_embedder()
        print("🧠 Cortex: Indexer ready.")

    def index_file(self, filepath: str, project_root: str):
        """Index a single file."""
        try:
            rel_path = os.path.relpath(filepath, project_root)
            
            # Skip non-code files
            if should_ignore(rel_path):
                return
                
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            if not content.strip():
                return
                
            # Chunking logic (simple sliding window for now)
            # Todo: AST-based chunking for better semantic understanding
            chunks = self._chunk_content(content)
            
            if not chunks:
                return
                
            # Prepare data for Chroma
            ids = [f"{rel_path}_{i}" for i in range(len(chunks))]
            documents = [chunk['text'] for chunk in chunks]
            metadatas = [{'path': rel_path, 'line': chunk['line']} for chunk in chunks]
            
            # Get embeddings
            embeddings = self.embedder.embed(documents)
            
            # Upsert (overwrite existing)
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            print(f"🧠 Cortex: Indexed {rel_path} ({len(chunks)} chunks)")
            
        except Exception as e:
            print(f"❌ Cortex: Failed to index {filepath}: {e}")

    def _chunk_content(self, content: str, chunk_size: int = 50, overlap: int = 10) -> List[Dict]:
        """Split content into chunks of lines."""
        lines = content.splitlines()
        chunks = []
        
        if len(lines) <= chunk_size:
            return [{'text': content, 'line': 1}]
            
        for i in range(0, len(lines), chunk_size - overlap):
            chunk_lines = lines[i:i + chunk_size]
            chunk_text = "\n".join(chunk_lines)
            chunks.append({
                'text': chunk_text,
                'line': i + 1
            })
            
        return chunks

    def query(self, query_text: str, n_results: int = 5) -> List[Dict]:
        """Query the codebase."""
        query_embedding = self.embedder.embed([query_text])[0]
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Flatten results structure
        output = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                output.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else 0
                })
        
        return output
        
    def full_scan(self, project_root: str):
        """Scan and index entire project."""
        print(f"🧠 Cortex: Starting full scan of {project_root}...")
        count = 0
        for root, dirs, files in os.walk(project_root):
            # Ignore directories
            dirs[:] = [d for d in dirs if not should_ignore(d)]
            
            for file in files:
                filepath = os.path.join(root, file)
                self.index_file(filepath, project_root)
                count += 1
                # Yield GIL to allow API server to breathe
                time.sleep(0.05)
                
        print(f"🧠 Cortex: Full scan complete. Indexed {count} files.")

def should_ignore(path_str: str) -> bool:
    """Check if file should be ignored."""
    ignore_patterns = [
        '.git', '__pycache__', 'node_modules', 'dist', 'build', '.env', 
        '.DS_Store', '*.pyc', '*.o', 'cortex_db', '*.db', '*.sqlite*', '*-journal',
        'package-lock.json', 'yarn.lock'
    ]
    path_name = Path(path_str).name
    # Simple check (expand with glob matching if needed)
    for pattern in ignore_patterns:
        if pattern.startswith('*'):
            if path_name.endswith(pattern[1:]): return True
        elif pattern in path_str:
            return True
    return False

def get_indexer():
    return Indexer()
