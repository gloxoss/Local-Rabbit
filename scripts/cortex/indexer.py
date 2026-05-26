"""
Indexer Service for Cortex
Manages ChromaDB vector store and indexing of codebase files.
"""

import threading
import time
import os
import hashlib
import glob
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

from .embedder import get_embedder

import json

# Configuration Defaults
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cortex_db")
DEFAULT_COLLECTION = "cortex_codebase_v2"

def load_cortex_config():
    """Load config.json relative to script root."""
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_path = os.path.join(root_dir, "config.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config.get("cortex", {})
    except Exception:
        return {}

cortex_config = load_cortex_config()
DB_PATH = cortex_config.get("db_path", DEFAULT_DB_PATH)
COLLECTION_NAME = cortex_config.get("collection_name", DEFAULT_COLLECTION)


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
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self.embedder = get_embedder()
        print("🧠 Cortex: Indexer ready.")

    def _calculate_hash(self, content: str) -> str:
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def index_file(self, filepath: str, project_root: str, force: bool = False):
        """Index a single file with incremental check."""
        try:
            rel_path = os.path.relpath(filepath, project_root)
            
            # Skip non-code files
            if should_ignore(rel_path):
                return
                
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except IOError:
                return # File might have been deleted

            if not content.strip():
                return
            
            current_hash = self._calculate_hash(content)
            
            # Check if file needs re-indexing using simple metadata query
            if not force:
                existing = self.collection.get(
                    where={"path": rel_path},
                    include=['metadatas']
                )
                if existing['ids'] and existing['metadatas']:
                    # Check the hash of the first chunk (assuming uniform file hash stored in all chunks)
                    stored_hash = existing['metadatas'][0].get('file_hash')
                    if stored_hash == current_hash:
                        # print(f"🧠 Cortex: Skipping {rel_path} (unchanged)")
                        return

            # Clean up old chunks for this file
            self.collection.delete(where={"path": rel_path})

            # Chunking logic
            chunks = self._chunk_content(content)
            
            if not chunks:
                return
                
            # Prepare data for Chroma
            ids = [f"{rel_path}_{i}" for i in range(len(chunks))]
            documents = [chunk['text'] for chunk in chunks]
            metadatas = [{
                'path': rel_path, 
                'line': chunk['line'],
                'file_hash': current_hash
            } for chunk in chunks]
            
            # Get embeddings
            embeddings = self.embedder.embed(documents)
            
            # Filter out failed embeddings
            valid_ids = []
            valid_docs = []
            valid_embs = []
            valid_metas = []
            
            for i, emb in enumerate(embeddings):
                if emb: # Check if not empty
                    valid_ids.append(ids[i])
                    valid_docs.append(documents[i])
                    valid_embs.append(emb)
                    valid_metas.append(metadatas[i])
            
            if valid_ids:
                self.collection.upsert(
                    ids=valid_ids,
                    documents=valid_docs,
                    embeddings=valid_embs,
                    metadatas=valid_metas
                )
                print(f"🧠 Cortex: Indexed {rel_path} ({len(valid_ids)} chunks)")
            
        except Exception as e:
            print(f"❌ Cortex: Failed to index {filepath}: {e}")

    def _chunk_content(self, content: str, chunk_size: int = 50, overlap: int = 15) -> List[Dict]:
        """Split content into semi-smart chunks."""
        # TODO: Implement proper AST chunking (TreeSitter)
        # For now, improved line-based chunking with paragraph preservation
        lines = content.splitlines()
        chunks = []
        
        if len(lines) <= chunk_size:
            return [{'text': content, 'line': 1}]
            
        for i in range(0, len(lines), chunk_size - overlap):
            chunk_lines = lines[i:i + chunk_size]
            # Add file context header to improves semantic retrieval
            # chunk_text = f"... {i+1} ...\n" + "\n".join(chunk_lines)
            chunk_text = "\n".join(chunk_lines)
            chunks.append({
                'text': chunk_text,
                'line': i + 1
            })
            
        return chunks

    def query(self, query_text: str, n_results: int = 5) -> List[Dict]:
        """Query the codebase."""
        # self.embedder.embed returns a list of embeddings
        query_embeddings = self.embedder.embed([query_text])
        if not query_embeddings or not query_embeddings[0]:
            print("❌ Cortex: Failed to generate query embedding")
            return []
            
        results = self.collection.query(
            query_embeddings=query_embeddings,
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
                
        print(f"🧠 Cortex: Full scan complete. Scanned {count} files.")

def should_ignore(path_str: str) -> bool:
    """Check if file should be ignored."""
    ignore_patterns = [
        '.git', '__pycache__', 'node_modules', 'dist', 'build', '.env', 
        '.DS_Store', '*.pyc', '*.o', 'cortex_db', '*.db', '*.sqlite*', '*-journal',
        'package-lock.json', 'yarn.lock', '.vscode', '.idea'
    ]
    path_name = Path(path_str).name
    
    # 1. Exact Name/Dir Match
    if path_name in ignore_patterns or path_str in ignore_patterns:
        return True
        
    # 2. Pattern Match
    for pattern in ignore_patterns:
        if pattern.startswith('*') and path_name.endswith(pattern[1:]):
            return True
        elif pattern in path_str:
            return True
            
    return False

def get_indexer():
    return Indexer()
