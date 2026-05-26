#!/usr/bin/env python3
"""
Local CodeRabbit - Review Queue
Interactive review queue for managing pending reviews.
"""

import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class ReviewStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    DEFERRED = "deferred"


@dataclass
class ReviewItem:
    """Item in the review queue"""
    id: str
    file: str
    line: int
    severity: str  # critical, warning, suggestion
    message: str
    status: ReviewStatus
    assignee: Optional[str]
    created_at: str
    resolved_at: Optional[str]
    notes: Optional[str]


class ReviewQueue:
    """Manages the review queue"""
    
    def __init__(self, queue_path: Path = None):
        self.queue_path = queue_path or Path("reviews") / "queue.json"
        self.items: dict[str, ReviewItem] = {}
        self._load_queue()
    
    def _load_queue(self):
        """Load queue from file"""
        if self.queue_path.exists():
            try:
                data = json.loads(self.queue_path.read_text())
                
                for item in data.get("items", []):
                    review = ReviewItem(
                        id=item["id"],
                        file=item["file"],
                        line=item.get("line", 0),
                        severity=item["severity"],
                        message=item["message"],
                        status=ReviewStatus(item.get("status", "pending")),
                        assignee=item.get("assignee"),
                        created_at=item["created_at"],
                        resolved_at=item.get("resolved_at"),
                        notes=item.get("notes")
                    )
                    self.items[item["id"]] = review
                    
            except Exception as e:
                print(f"Warning: Could not load queue: {e}")
    
    def _save_queue(self):
        """Save queue to file"""
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "updated_at": datetime.now().isoformat(),
            "items": [
                {
                    "id": item.id,
                    "file": item.file,
                    "line": item.line,
                    "severity": item.severity,
                    "message": item.message,
                    "status": item.status.value,
                    "assignee": item.assignee,
                    "created_at": item.created_at,
                    "resolved_at": item.resolved_at,
                    "notes": item.notes
                }
                for item in self.items.values()
            ]
        }
        
        self.queue_path.write_text(json.dumps(data, indent=2))
    
    def add_item(self, file: str, line: int, severity: str, message: str, assignee: str = None) -> ReviewItem:
        """Add an item to the queue"""
        # Generate unique ID
        import hashlib
        content = f"{file}:{line}:{message}"
        item_id = hashlib.md5(content.encode()).hexdigest()[:8]
        
        # Check if already exists
        if item_id in self.items:
            return self.items[item_id]
        
        item = ReviewItem(
            id=item_id,
            file=file,
            line=line,
            severity=severity,
            message=message,
            status=ReviewStatus.PENDING,
            assignee=assignee,
            created_at=datetime.now().isoformat(),
            resolved_at=None,
            notes=None
        )
        
        self.items[item_id] = item
        self._save_queue()
        
        return item
    
    def add_from_review(self, file: str, issues: dict, assignee: str = None):
        """Add items from a review result"""
        for severity in ["critical", "warning", "suggestion"]:
            for issue in issues.get(severity, []):
                # Extract line number from issue if present
                import re
                match = re.search(r'line\s*(\d+)', issue, re.IGNORECASE)
                line = int(match.group(1)) if match else 0
                
                self.add_item(file, line, severity, issue, assignee)
    
    def update_status(self, item_id: str, status: ReviewStatus, notes: str = None) -> bool:
        """Update item status"""
        if item_id in self.items:
            item = self.items[item_id]
            item.status = status
            
            if status == ReviewStatus.RESOLVED:
                item.resolved_at = datetime.now().isoformat()
            
            if notes:
                item.notes = notes
            
            self._save_queue()
            return True
        
        return False
    
    def assign(self, item_id: str, assignee: str) -> bool:
        """Assign item to team member"""
        if item_id in self.items:
            self.items[item_id].assignee = assignee
            self.items[item_id].status = ReviewStatus.IN_PROGRESS
            self._save_queue()
            return True
        return False
    
    def get_pending(self, severity: str = None, assignee: str = None) -> list[ReviewItem]:
        """Get pending items, optionally filtered"""
        items = [i for i in self.items.values() if i.status == ReviewStatus.PENDING]
        
        if severity:
            items = [i for i in items if i.severity == severity]
        
        if assignee:
            items = [i for i in items if i.assignee == assignee]
        
        # Sort by severity (critical first)
        severity_order = {"critical": 0, "warning": 1, "suggestion": 2}
        items.sort(key=lambda x: severity_order.get(x.severity, 3))
        
        return items
    
    def get_by_file(self, file: str) -> list[ReviewItem]:
        """Get all items for a file"""
        return [i for i in self.items.values() if i.file == file]
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        total = len(self.items)
        pending = len([i for i in self.items.values() if i.status == ReviewStatus.PENDING])
        in_progress = len([i for i in self.items.values() if i.status == ReviewStatus.IN_PROGRESS])
        resolved = len([i for i in self.items.values() if i.status == ReviewStatus.RESOLVED])
        
        critical = len([i for i in self.items.values() if i.severity == "critical" and i.status == ReviewStatus.PENDING])
        warning = len([i for i in self.items.values() if i.severity == "warning" and i.status == ReviewStatus.PENDING])
        
        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved,
            "critical_pending": critical,
            "warning_pending": warning
        }
    
    def cleanup_resolved(self, older_than_days: int = 30) -> int:
        """Remove resolved items older than N days"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=older_than_days)
        removed = 0
        
        to_remove = []
        for item_id, item in self.items.items():
            if item.status == ReviewStatus.RESOLVED and item.resolved_at:
                resolved_date = datetime.fromisoformat(item.resolved_at)
                if resolved_date < cutoff:
                    to_remove.append(item_id)
        
        for item_id in to_remove:
            del self.items[item_id]
            removed += 1
        
        if removed:
            self._save_queue()
        
        return removed


def print_queue_table(items: list[ReviewItem]):
    """Print queue items as formatted table"""
    if not items:
        print("No items in queue")
        return
    
    print(f"{'ID':<10} {'SEV':<10} {'FILE':<30} {'STATUS':<12}")
    print("=" * 70)
    
    for item in items:
        sev_color = "\033[31m" if item.severity == "critical" else "\033[33m" if item.severity == "warning" else "\033[34m"
        reset = "\033[0m"
        
        file_short = item.file[-28:] if len(item.file) > 28 else item.file
        status = item.status.value.upper()[:10]
        
        print(f"{item.id:<10} {sev_color}{item.severity:<10}{reset} {file_short:<30} {status:<12}")


if __name__ == "__main__":
    import sys
    
    queue = ReviewQueue()
    
    if len(sys.argv) < 2:
        print("Usage: python review_queue.py <command> [args]")
        print("\nCommands:")
        print("  list [severity]          - List pending items")
        print("  stats                    - Show queue statistics")
        print("  resolve <id> [notes]     - Mark item as resolved")
        print("  assign <id> <assignee>   - Assign item to team member")
        print("  ignore <id>              - Ignore an item")
        print("  defer <id>               - Defer an item for later")
        print("  cleanup [days]           - Remove old resolved items")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        severity = sys.argv[2] if len(sys.argv) > 2 else None
        items = queue.get_pending(severity=severity)
        print_queue_table(items)
    
    elif command == "stats":
        stats = queue.get_stats()
        print(f"Total items: {stats['total']}")
        print(f"  Pending: {stats['pending']} ({stats['critical_pending']} critical, {stats['warning_pending']} warnings)")
        print(f"  In Progress: {stats['in_progress']}")
        print(f"  Resolved: {stats['resolved']}")
    
    elif command == "resolve" and len(sys.argv) >= 3:
        item_id = sys.argv[2]
        notes = sys.argv[3] if len(sys.argv) > 3 else None
        if queue.update_status(item_id, ReviewStatus.RESOLVED, notes):
            print(f"Resolved: {item_id}")
        else:
            print(f"Item not found: {item_id}")
    
    elif command == "assign" and len(sys.argv) >= 4:
        item_id = sys.argv[2]
        assignee = sys.argv[3]
        if queue.assign(item_id, assignee):
            print(f"Assigned {item_id} to {assignee}")
        else:
            print(f"Item not found: {item_id}")
    
    elif command == "ignore" and len(sys.argv) >= 3:
        item_id = sys.argv[2]
        if queue.update_status(item_id, ReviewStatus.IGNORED):
            print(f"Ignored: {item_id}")
        else:
            print(f"Item not found: {item_id}")
    
    elif command == "defer" and len(sys.argv) >= 3:
        item_id = sys.argv[2]
        if queue.update_status(item_id, ReviewStatus.DEFERRED):
            print(f"Deferred: {item_id}")
        else:
            print(f"Item not found: {item_id}")
    
    elif command == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        removed = queue.cleanup_resolved(days)
        print(f"Removed {removed} resolved items older than {days} days")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
