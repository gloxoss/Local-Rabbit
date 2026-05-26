"""
Context Retrieval Service
Orchestrates context fetching for RAG.
"""

from typing import List, Dict, Optional
import os
from .indexer import get_indexer

class ContextRetriever:
    def __init__(self):
        self.indexer = get_indexer()

    def retrieve_context(self, query: str, current_file: str = "", n_results: int = 5) -> str:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: The search query (diff or question)
            current_file: The file currently being reviewed (to prioritize local context or exclude self)
            n_results: Number of chunks to retrieve
            
        Returns:
            Formatted string of context chunks ready for LLM prompt.
        """
        if not query:
            return ""
            
        # Get raw results from vector DB
        results = self.indexer.query(query, n_results=n_results)
        
        if not results:
            return ""
            
        formatted_chunks = []
        for res in results:
            path = res['metadata']['path']
            
            # Simple re-ranking or filtering logic can go here
            # For now, just skip if it's the exact same chunk from the same file (approximate check)
            # if path == current_file: continue 
            
            formatted_chunks.append(
                f"--- [Reference: {path}] ---\n{res['text']}\n"
            )
            
        return "\n".join(formatted_chunks)

def get_retriever():
    return ContextRetriever()
