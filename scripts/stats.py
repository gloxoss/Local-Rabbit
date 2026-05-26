"""
Local CodeRabbit — Dashboard Stats Module (SRP)
Manages JSON stats file for dashboard consumption.
"""

import json
from pathlib import Path
from datetime import datetime


try:
    from experimental.analytics import calculate_complexity, calculate_health_score
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

try:
    from git_blame import get_file_last_author
except ImportError:
    get_file_last_author = None


_DEFAULT_STATS = {
    "totals": {"critical": 0, "warning": 0, "suggestion": 0, "files": 0},
    "recent": [],
    "daily": {}
}


def _load_stats(stats_file):
    """Load existing stats or create fresh."""
    if stats_file.exists():
        try:
            with open(stats_file) as f:
                return json.load(f)
        except Exception:
            pass
    import copy
    return {**copy.deepcopy(_DEFAULT_STATS), "hotspots": [], "health_score": 100}


def update_dashboard_stats(root_dir, config, filepath, issues):
    """Update JSON stats file for dashboard consumption."""
    history_folder = Path(root_dir) / config["history"]["folder"]
    stats_file = history_folder / "stats.json"
    stats = _load_stats(stats_file)

    ext = Path(filepath).suffix.lstrip('.')
    file_type = {'ts': 'ts', 'tsx': 'ts', 'js': 'js', 'jsx': 'js', 'py': 'py'}.get(ext, ext)

    critical = len(issues["critical"])
    warning = len(issues["warning"])
    suggestion = len(issues["suggestion"])
    total_issues = critical + warning + suggestion

    # Analytics (optional)
    complexity, health_score = 0, 100
    if ANALYTICS_AVAILABLE:
        try:
            full_path = Path(root_dir) / filepath
            if full_path.exists():
                code = full_path.read_text(encoding='utf-8', errors='ignore')
                complexity = calculate_complexity(code)
                health_score = calculate_health_score(issues, complexity)
        except Exception as e:
            print(f"⚠️ Analytics Error: {e}")

    # Totals
    stats["totals"]["critical"] += critical
    stats["totals"]["warning"] += warning
    stats["totals"]["suggestion"] += suggestion
    stats["totals"]["files"] += 1

    # Health score (running average)
    current_health = stats.get("health_score", 100)
    stats["health_score"] = round(current_health * 0.9 + health_score * 0.1)

    # Hotspots
    stats.setdefault("hotspots", [])
    stats["hotspots"] = [h for h in stats["hotspots"] if h["file"] != filepath]
    if total_issues > 0:
        stats["hotspots"].append({
            "file": filepath,
            "score": total_issues * 10 + critical * 20,
            "issues": total_issues,
            "critical": critical
        })
    stats["hotspots"].sort(key=lambda x: x["score"], reverse=True)
    stats["hotspots"] = stats["hotspots"][:5]

    # Recent (keep last 10)
    recent_entry = {
        "file": filepath,
        "abs_path": str((Path(root_dir) / filepath).resolve()),
        "type": file_type,
        "time": datetime.now().strftime("%H:%M"),
        "critical": critical, "warning": warning, "suggestion": suggestion,
        "status": "critical" if critical > 0 else "warning" if warning > 0 else "clean",
        "health": health_score,
        "complexity": complexity,
        "issues": issues
    }

    if get_file_last_author:
        try:
            blame_info = get_file_last_author(str(Path(root_dir) / filepath))
            if blame_info:
                recent_entry["author"] = blame_info.get("author", "")
                recent_entry["author_date"] = blame_info.get("relative_date", "")
                recent_entry["commit_msg"] = blame_info.get("commit_message", "")[:40]
        except Exception:
            pass

    stats["recent"].insert(0, recent_entry)
    stats["recent"] = stats["recent"][:10]

    # Daily breakdown (keep 7 days)
    today = datetime.now().strftime("%Y-%m-%d")
    day_name = datetime.now().strftime("%a")
    if today not in stats.setdefault("daily", {}):
        stats["daily"][today] = {"day": day_name, "critical": 0, "warning": 0, "suggestion": 0}
    stats["daily"][today]["critical"] += critical
    stats["daily"][today]["warning"] += warning
    stats["daily"][today]["suggestion"] += suggestion

    if len(stats["daily"]) > 7:
        for old_day in sorted(stats["daily"].keys())[:-7]:
            del stats["daily"][old_day]

    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=2)
