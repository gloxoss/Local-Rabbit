"""
Rabbit Journal - Memory Subsystem
Handles persistence of chat history and context using SQLite.
"""
import sqlite3
import json
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

class Journal:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.data_dir = self.root_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "memory.db"
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Sessions table
        c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at REAL,
            updated_at REAL
        )
        ''')
        
        # Messages table
        c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp REAL,
            metadata TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to the journal."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Ensure session exists
        c.execute("INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                  (session_id, "New Chat", time.time(), time.time()))
        
        # Update session timestamp
        c.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (time.time(), session_id))
        
        # Insert message
        c.execute('''
        INSERT INTO messages (session_id, role, content, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?)
        ''', (session_id, role, content, time.time(), json.dumps(metadata or {})))
        
        conn.commit()
        conn.close()

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get message history for a session."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''
        SELECT role, content, timestamp, metadata 
        FROM messages 
        WHERE session_id = ? 
        ORDER BY id ASC 
        LIMIT ?
        ''', (session_id, limit))
        
        rows = c.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            })
            
        return history

    def clear(self, session_id: str):
        """Clear history for a session."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()

# Singleton accessor
_journal: Optional[Journal] = None

def get_journal(root_dir: str = None) -> Journal:
    global _journal
    if _journal is None:
        if root_dir is None:
             raise ValueError("Journal not initialized. Provide root_dir first.")
        _journal = Journal(root_dir)
    return _journal
