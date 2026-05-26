#!/usr/bin/env python3
"""
Local CodeRabbit - Report Generator
Generates scheduled reports for email/Slack delivery.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class ReportConfig:
    """Report configuration"""
    schedule: str  # daily, weekly, sprint
    format: str  # standup, detailed, executive
    channels: list[str]  # email, slack, discord
    include_trends: bool
    include_top_issues: bool
    include_recommendations: bool


def load_stats(reviews_dir: Path) -> dict:
    """Load stats from stats.json"""
    stats_file = reviews_dir / "stats.json"
    if stats_file.exists():
        return json.loads(stats_file.read_text())
    return {"totals": {}, "recent": [], "daily": {}}


def calculate_trends(stats: dict, days: int = 7) -> dict:
    """Calculate trends over time period"""
    daily = stats.get("daily", {})
    
    if not daily:
        return {"trend": "neutral", "change": 0}
    
    # Sort by date and get last N days
    sorted_days = sorted(daily.items())[-days:]
    
    if len(sorted_days) < 2:
        return {"trend": "neutral", "change": 0}
    
    # Calculate issue counts for first and second half
    mid = len(sorted_days) // 2
    first_half = sum(d[1].get("critical", 0) + d[1].get("warning", 0) for d in sorted_days[:mid])
    second_half = sum(d[1].get("critical", 0) + d[1].get("warning", 0) for d in sorted_days[mid:])
    
    if first_half == 0:
        change = 100 if second_half > 0 else 0
    else:
        change = ((second_half - first_half) / first_half) * 100
    
    trend = "improving" if change < -10 else "declining" if change > 10 else "stable"
    
    return {
        "trend": trend,
        "change": round(change, 1),
        "first_period_issues": first_half,
        "second_period_issues": second_half
    }


def get_top_issues(reviews_dir: Path, limit: int = 5) -> list[dict]:
    """Get top recurring issues from history"""
    history_dir = reviews_dir / "history"
    if not history_dir.exists():
        return []
    
    issue_counts = {}
    
    for file in history_dir.glob("*.json"):
        try:
            data = json.loads(file.read_text())
            for severity in ["critical", "warning"]:
                for issue in data.get("issues", {}).get(severity, []):
                    # Normalize issue text
                    issue_key = issue[:50]  # First 50 chars as key
                    if issue_key not in issue_counts:
                        issue_counts[issue_key] = {"text": issue, "count": 0, "severity": severity}
                    issue_counts[issue_key]["count"] += 1
        except Exception:
            continue
    
    # Sort by count
    sorted_issues = sorted(issue_counts.values(), key=lambda x: x["count"], reverse=True)
    return sorted_issues[:limit]


def generate_standup_report(stats: dict, trends: dict, top_issues: list) -> str:
    """Generate daily standup format report"""
    today = datetime.now().strftime("%A, %B %d, %Y")
    
    output = []
    output.append("=" * 50)
    output.append(f"📊 DAILY STANDUP - {today}")
    output.append("=" * 50)
    output.append("")
    
    # Yesterday's numbers
    totals = stats.get("totals", {})
    output.append("📈 Current State:")
    output.append(f"  • Critical issues: {totals.get('critical', 0)}")
    output.append(f"  • Warnings: {totals.get('warning', 0)}")
    output.append(f"  • Files reviewed: {totals.get('files', 0)}")
    output.append("")
    
    # Trend
    output.append("📉 Trend:")
    trend_emoji = "📈" if trends["trend"] == "declining" else "📉" if trends["trend"] == "improving" else "➡️"
    output.append(f"  {trend_emoji} Issues are {trends['trend']} ({trends['change']:+.1f}% vs previous period)")
    output.append("")
    
    # Recent activity
    recent = stats.get("recent", [])[:3]
    if recent:
        output.append("🔍 Recent Reviews:")
        for r in recent:
            status_emoji = "🔴" if r.get("status") == "critical" else "🟡" if r.get("status") == "warning" else "✅"
            output.append(f"  {status_emoji} {r.get('file')} at {r.get('time')}")
    output.append("")
    
    # Today's focus
    if top_issues:
        output.append("🎯 Focus Areas:")
        for issue in top_issues[:3]:
            output.append(f"  • {issue['text'][:60]}... ({issue['count']}x)")
    
    return "\n".join(output)


def generate_detailed_report(stats: dict, trends: dict, top_issues: list) -> str:
    """Generate detailed report"""
    output = []
    output.append("=" * 60)
    output.append("  LOCAL CODERABBIT - DETAILED REPORT")
    output.append(f"  Generated: {datetime.now().isoformat()}")
    output.append("=" * 60)
    output.append("")
    
    # Summary stats
    totals = stats.get("totals", {})
    output.append("📊 SUMMARY")
    output.append("-" * 40)
    output.append(f"  Total files reviewed: {totals.get('files', 0)}")
    output.append(f"  Critical issues:      {totals.get('critical', 0)}")
    output.append(f"  Warnings:             {totals.get('warning', 0)}")
    output.append(f"  Suggestions:          {totals.get('suggestion', 0)}")
    output.append("")
    
    # Trend analysis
    output.append("📈 TREND ANALYSIS")
    output.append("-" * 40)
    output.append(f"  Trend: {trends['trend'].upper()}")
    output.append(f"  Change: {trends['change']:+.1f}%")
    output.append(f"  Previous period issues: {trends.get('first_period_issues', 0)}")
    output.append(f"  Current period issues: {trends.get('second_period_issues', 0)}")
    output.append("")
    
    # Daily breakdown
    daily = stats.get("daily", {})
    if daily:
        output.append("📅 DAILY BREAKDOWN (Last 7 days)")
        output.append("-" * 40)
        for date, data in sorted(daily.items())[-7:]:
            day = data.get('day', date)
            c = data.get('critical', 0)
            w = data.get('warning', 0)
            s = data.get('suggestion', 0)
            output.append(f"  {day}: {c} critical, {w} warnings, {s} suggestions")
        output.append("")
    
    # Top issues
    if top_issues:
        output.append("🔥 TOP RECURRING ISSUES")
        output.append("-" * 40)
        for i, issue in enumerate(top_issues, 1):
            sev_emoji = "🔴" if issue['severity'] == 'critical' else "🟡"
            output.append(f"  {i}. {sev_emoji} {issue['text'][:70]}")
            output.append(f"     Occurrences: {issue['count']}")
        output.append("")
    
    # Recent activity
    recent = stats.get("recent", [])[:10]
    if recent:
        output.append("🕒 RECENT ACTIVITY")
        output.append("-" * 40)
        for r in recent:
            status = r.get("status", "unknown")
            status_emoji = "🔴" if status == "critical" else "🟡" if status == "warning" else "✅"
            author = r.get("author", "Unknown")
            output.append(f"  {status_emoji} {r.get('file')}")
            output.append(f"     {r.get('time')} by {author}")
        output.append("")
    
    return "\n".join(output)


def generate_executive_report(stats: dict, trends: dict, top_issues: list) -> str:
    """Generate executive summary report"""
    output = []
    output.append("═" * 50)
    output.append("  EXECUTIVE SUMMARY")
    output.append("═" * 50)
    output.append("")
    
    totals = stats.get("totals", {})
    total_issues = totals.get("critical", 0) + totals.get("warning", 0)
    
    # Health status
    if totals.get("critical", 0) == 0 and trends["trend"] != "declining":
        status = "🟢 HEALTHY"
    elif totals.get("critical", 0) <= 2 and trends["trend"] != "declining":
        status = "🟡 NEEDS ATTENTION"
    else:
        status = "🔴 ACTION REQUIRED"
    
    output.append(f"Code Quality Status: {status}")
    output.append("")
    output.append("Key Metrics:")
    output.append(f"  • {totals.get('files', 0)} files reviewed")
    output.append(f"  • {total_issues} issues identified")
    output.append(f"  • Trend: {trends['trend'].capitalize()} ({trends['change']:+.1f}%)")
    output.append("")
    
    # Recommendations
    output.append("Recommendations:")
    if totals.get("critical", 0) > 0:
        output.append(f"  ⚠️ Address {totals.get('critical', 0)} critical issues immediately")
    if trends["trend"] == "declining":
        output.append("  ⚠️ Issue count increasing - review development practices")
    if totals.get("warning", 0) > 10:
        output.append("  📋 Schedule time to address accumulated warnings")
    if total_issues == 0:
        output.append("  ✅ Excellent! Maintain current quality standards")
    
    return "\n".join(output)


def generate_report(
    reviews_dir: Path,
    format: str = "standup",
    output_format: str = "text"
) -> str:
    """Generate report based on format"""
    stats = load_stats(reviews_dir)
    trends = calculate_trends(stats)
    top_issues = get_top_issues(reviews_dir)
    
    if output_format == "json":
        return json.dumps({
            "generatedAt": datetime.now().isoformat(),
            "format": format,
            "stats": stats.get("totals", {}),
            "trends": trends,
            "topIssues": top_issues,
            "recentActivity": stats.get("recent", [])[:10]
        }, indent=2)
    
    if format == "standup":
        return generate_standup_report(stats, trends, top_issues)
    elif format == "detailed":
        return generate_detailed_report(stats, trends, top_issues)
    elif format == "executive":
        return generate_executive_report(stats, trends, top_issues)
    else:
        return generate_standup_report(stats, trends, top_issues)


def send_to_slack(webhook_url: str, report: str) -> bool:
    """Send report to Slack"""
    import urllib.request
    
    payload = json.dumps({
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{report}```"}
            }
        ]
    }).encode()
    
    try:
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


def send_to_discord(webhook_url: str, report: str) -> bool:
    """Send report to Discord"""
    import urllib.request
    
    payload = json.dumps({
        "content": f"```\n{report}\n```"
    }).encode()
    
    try:
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    report_format = sys.argv[2] if len(sys.argv) > 2 else "standup"
    output_format = sys.argv[3] if len(sys.argv) > 3 else "text"
    
    reviews_dir = root / "reviews"
    
    if not reviews_dir.exists():
        print("No reviews directory found. Run the watcher first to generate data.")
        sys.exit(1)
    
    report = generate_report(reviews_dir, report_format, output_format)
    print(report)
