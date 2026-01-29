"""
Feedback Store for Local CodeRabbit
Tracks user feedback on AI suggestions to personalize future reviews.

Phase 3 of Smart Reviews - learning from user feedback.
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class FeedbackEntry:
    """A single feedback record."""
    id: Optional[int] = None
    issue_type: str = ""  # e.g., "unused-variable", "error-handling", "type-safety"
    severity: str = ""  # critical, warning, suggestion
    action: str = ""  # accepted, rejected, ignored
    filename: str = ""
    language: str = ""
    timestamp: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UserPreferences:
    """Aggregated user preferences based on feedback history."""
    accepted_patterns: Dict[str, int] = None  # issue_type -> count
    rejected_patterns: Dict[str, int] = None
    severity_preferences: Dict[str, int] = None  # severity -> adjustment (-2 to +2)
    language_preferences: Dict[str, bool] = None  # language -> enabled
    
    def __post_init__(self):
        self.accepted_patterns = self.accepted_patterns or {}
        self.rejected_patterns = self.rejected_patterns or {}
        self.severity_preferences = self.severity_preferences or {}
        self.language_preferences = self.language_preferences or {}
    
    def get_prompt_adjustments(self) -> str:
        """Generate prompt adjustments based on preferences."""
        adjustments = []
        
        # Top 3 accepted patterns - emphasize these
        top_accepted = sorted(
            self.accepted_patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        for pattern, count in top_accepted:
            if count >= 3:  # Threshold for emphasis
                adjustments.append(f"- EMPHASIZE: {pattern} (user appreciates this)")
        
        # Top 3 rejected patterns - de-emphasize these
        top_rejected = sorted(
            self.rejected_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        for pattern, count in top_rejected:
            if count >= 3:  # Threshold for de-emphasis
                adjustments.append(f"- AVOID: {pattern} (user dismisses this)")
        
        if adjustments:
            return "USER PREFERENCES:\n" + "\n".join(adjustments)
        return ""


class FeedbackStore:
    """SQLite-based storage for user feedback."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to data directory in project
            db_path = Path(__file__).parent.parent / "data" / "feedback.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    action TEXT NOT NULL,
                    filename TEXT,
                    language TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_issue_type ON feedback(issue_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_action ON feedback(action)
            """)
            conn.commit()
    
    def record_feedback(self, entry: FeedbackEntry) -> int:
        """Record a new feedback entry. Returns the entry ID."""
        entry.timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO feedback (issue_type, severity, action, filename, language, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.issue_type,
                entry.severity,
                entry.action,
                entry.filename,
                entry.language,
                entry.timestamp
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_preferences(self) -> UserPreferences:
        """Calculate user preferences from feedback history."""
        prefs = UserPreferences()
        
        with sqlite3.connect(self.db_path) as conn:
            # Get accepted patterns
            for row in conn.execute("""
                SELECT issue_type, COUNT(*) as cnt
                FROM feedback WHERE action = 'accepted'
                GROUP BY issue_type
            """):
                prefs.accepted_patterns[row[0]] = row[1]
            
            # Get rejected patterns
            for row in conn.execute("""
                SELECT issue_type, COUNT(*) as cnt
                FROM feedback WHERE action = 'rejected'
                GROUP BY issue_type
            """):
                prefs.rejected_patterns[row[0]] = row[1]
            
            # Calculate severity preferences
            for severity in ['critical', 'warning', 'suggestion']:
                accepted = sum(1 for r in conn.execute("""
                    SELECT 1 FROM feedback 
                    WHERE severity = ? AND action = 'accepted'
                """, (severity,)))
                rejected = sum(1 for r in conn.execute("""
                    SELECT 1 FROM feedback 
                    WHERE severity = ? AND action = 'rejected'
                """, (severity,)))
                
                if accepted + rejected > 0:
                    # Range: -2 to +2
                    ratio = (accepted - rejected) / (accepted + rejected)
                    prefs.severity_preferences[severity] = int(ratio * 2)
        
        return prefs
    
    def get_recent_feedback(self, limit: int = 50) -> List[FeedbackEntry]:
        """Get recent feedback entries."""
        entries = []
        with sqlite3.connect(self.db_path) as conn:
            for row in conn.execute("""
                SELECT id, issue_type, severity, action, filename, language, timestamp
                FROM feedback
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)):
                entries.append(FeedbackEntry(
                    id=row[0],
                    issue_type=row[1],
                    severity=row[2],
                    action=row[3],
                    filename=row[4],
                    language=row[5],
                    timestamp=row[6]
                ))
        return entries
    
    def get_stats(self) -> dict:
        """Get overall feedback statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            accepted = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE action = 'accepted'"
            ).fetchone()[0]
            rejected = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE action = 'rejected'"
            ).fetchone()[0]
            
            return {
                "total_feedback": total,
                "accepted": accepted,
                "rejected": rejected,
                "acceptance_rate": accepted / total if total > 0 else 0,
                "top_accepted": self._get_top_patterns('accepted'),
                "top_rejected": self._get_top_patterns('rejected')
            }
    
    def _get_top_patterns(self, action: str, limit: int = 5) -> List[dict]:
        """Get top issue patterns for an action."""
        patterns = []
        with sqlite3.connect(self.db_path) as conn:
            for row in conn.execute("""
                SELECT issue_type, COUNT(*) as cnt
                FROM feedback WHERE action = ?
                GROUP BY issue_type
                ORDER BY cnt DESC
                LIMIT ?
            """, (action, limit)):
                patterns.append({"type": row[0], "count": row[1]})
        return patterns
    
    def reset(self):
        """Reset all feedback data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM feedback")
            conn.commit()


# Singleton instance
_store: Optional[FeedbackStore] = None


def get_feedback_store(db_path: Optional[str] = None) -> FeedbackStore:
    """Get or create the feedback store."""
    global _store
    if _store is None or db_path:
        _store = FeedbackStore(db_path)
    return _store


def record_feedback(
    issue_type: str,
    severity: str,
    action: str,
    filename: str = "",
    language: str = ""
) -> int:
    """Convenience function to record feedback."""
    store = get_feedback_store()
    entry = FeedbackEntry(
        issue_type=issue_type,
        severity=severity,
        action=action,
        filename=filename,
        language=language
    )
    return store.record_feedback(entry)


def get_prompt_adjustments() -> str:
    """Get prompt adjustments based on user preferences."""
    store = get_feedback_store()
    prefs = store.get_preferences()
    return prefs.get_prompt_adjustments()
