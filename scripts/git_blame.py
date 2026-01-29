#!/usr/bin/env python3
"""
Local CodeRabbit - Git Blame Integration
Provides author context for code issues.
"""

import subprocess
import re
from pathlib import Path
from datetime import datetime


def get_git_blame(file_path: str, line_number: int = None) -> dict:
    """
    Get git blame information for a file or specific line.
    
    Returns:
        dict with keys: author, email, date, commit_hash, commit_message
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return None
        
        # Build blame command
        cmd = ["git", "blame", "--porcelain"]
        if line_number:
            cmd.extend(["-L", f"{line_number},{line_number}"])
        cmd.append(str(file_path))
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=file_path.parent,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        return _parse_blame_output(result.stdout)
    
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        return None


def _parse_blame_output(output: str) -> dict:
    """Parse git blame --porcelain output."""
    info = {}
    lines = output.strip().split('\n')
    
    for line in lines:
        if line.startswith('author '):
            info['author'] = line[7:]
        elif line.startswith('author-mail '):
            info['email'] = line[12:].strip('<>')
        elif line.startswith('author-time '):
            timestamp = int(line[12:])
            info['date'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            info['relative_date'] = _relative_time(timestamp)
        elif line.startswith('summary '):
            info['commit_message'] = line[8:]
        elif len(line) == 40 and all(c in '0123456789abcdef' for c in line[:40]):
            info['commit_hash'] = line[:8]  # Short hash
    
    return info if info else None


def _relative_time(timestamp: int) -> str:
    """Convert timestamp to relative time string."""
    now = datetime.now().timestamp()
    diff = now - timestamp
    
    if diff < 60:
        return "just now"
    elif diff < 3600:
        mins = int(diff / 60)
        return f"{mins} min{'s' if mins > 1 else ''} ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < 604800:
        days = int(diff / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif diff < 2592000:
        weeks = int(diff / 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    else:
        months = int(diff / 2592000)
        return f"{months} month{'s' if months > 1 else ''} ago"


def get_file_last_author(file_path: str) -> dict:
    """Get the most recent author of a file."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%an|%ae|%ar|%s", str(file_path)],
            capture_output=True,
            text=True,
            cwd=Path(file_path).parent,
            timeout=5
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            return None
        
        parts = result.stdout.strip().split('|')
        if len(parts) >= 4:
            return {
                'author': parts[0],
                'email': parts[1],
                'relative_date': parts[2],
                'commit_message': parts[3]
            }
        return None
    except:
        return None


def format_blame_for_display(blame_info: dict) -> str:
    """Format blame info for terminal/webhook display."""
    if not blame_info:
        return ""
    
    author = blame_info.get('author', 'Unknown')
    date = blame_info.get('relative_date', blame_info.get('date', ''))
    message = blame_info.get('commit_message', '')[:50]
    
    return f"{author} ({date}): \"{message}\""


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        line = int(sys.argv[2]) if len(sys.argv) > 2 else None
        
        print(f"Getting blame for: {file_path}")
        if line:
            print(f"Line: {line}")
        
        blame = get_git_blame(file_path, line)
        if blame:
            print("\nBlame info:")
            for key, value in blame.items():
                print(f"  {key}: {value}")
            print(f"\nFormatted: {format_blame_for_display(blame)}")
        else:
            print("No blame info available (not in git repo or uncommitted)")
    else:
        print("Usage: python git_blame.py <file_path> [line_number]")
