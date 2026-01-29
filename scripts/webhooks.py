#!/usr/bin/env python3
"""
Local CodeRabbit - Webhook Notifications
Sends review alerts to Slack, Discord, or custom webhooks.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


def send_slack_webhook(url: str, file_path: str, issues: dict, code_snippet: str = None):
    """Send a formatted message to Slack webhook."""
    critical = len(issues.get("critical", []))
    warning = len(issues.get("warning", []))
    suggestion = len(issues.get("suggestion", []))
    
    # Determine color based on severity
    if critical > 0:
        color = "#ef4444"  # red
        icon = ":red_circle:"
    elif warning > 0:
        color = "#eab308"  # yellow
        icon = ":large_yellow_circle:"
    else:
        color = "#22c55e"  # green
        icon = ":large_green_circle:"
    
    # Build issue list
    issue_lines = []
    for severity, items in issues.items():
        for item in items[:3]:  # Limit to 3 per severity
            issue_lines.append(f"• {item}")
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{icon} Code Review Alert",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*File:*\n`{file_path}`"},
                {"type": "mrkdwn", "text": f"*Time:*\n{datetime.now().strftime('%H:%M:%S')}"}
            ]
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Critical:* {critical}"},
                {"type": "mrkdwn", "text": f"*Warnings:* {warning}"},
                {"type": "mrkdwn", "text": f"*Suggestions:* {suggestion}"}
            ]
        }
    ]
    
    if issue_lines:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Issues:*\n" + "\n".join(issue_lines[:5])
            }
        })
    
    if code_snippet:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{code_snippet[:500]}```"
            }
        })
    
    payload = {
        "blocks": blocks,
        "attachments": [{
            "color": color
        }]
    }
    
    return _send_webhook(url, payload)


def send_discord_webhook(url: str, file_path: str, issues: dict, code_snippet: str = None):
    """Send a formatted message to Discord webhook."""
    critical = len(issues.get("critical", []))
    warning = len(issues.get("warning", []))
    suggestion = len(issues.get("suggestion", []))
    
    # Determine color based on severity (Discord uses decimal)
    if critical > 0:
        color = 15548997  # red
        title = "🔴 Critical Issue Found"
    elif warning > 0:
        color = 15395562  # yellow
        title = "🟡 Warning Detected"
    else:
        color = 5763719   # green
        title = "🔵 Suggestion Available"
    
    # Build issue list
    issue_text = ""
    for severity, items in issues.items():
        for item in items[:3]:
            issue_text += f"• {item}\n"
    
    embed = {
        "title": title,
        "color": color,
        "fields": [
            {"name": "📄 File", "value": f"`{file_path}`", "inline": True},
            {"name": "⏰ Time", "value": datetime.now().strftime('%H:%M:%S'), "inline": True},
            {"name": "📊 Summary", "value": f"Critical: {critical} | Warnings: {warning} | Suggestions: {suggestion}", "inline": False}
        ],
        "footer": {"text": "Local CodeRabbit"},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if issue_text:
        embed["description"] = issue_text[:1024]
    
    if code_snippet:
        embed["fields"].append({
            "name": "📝 Code Snippet",
            "value": f"```\n{code_snippet[:500]}\n```",
            "inline": False
        })
    
    payload = {"embeds": [embed]}
    
    return _send_webhook(url, payload)


def _send_webhook(url: str, payload: dict) -> bool:
    """Send JSON payload to webhook URL."""
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status in (200, 204)
    except urllib.error.URLError as e:
        print(f"   [WEBHOOK] Error: {e}")
        return False
    except Exception as e:
        print(f"   [WEBHOOK] Unexpected error: {e}")
        return False


def notify_webhooks(config: dict, file_path: str, issues: dict, code_snippet: str = None):
    """Send notifications to all configured webhooks."""
    webhook_config = config.get("webhooks", {})
    
    if not webhook_config.get("enabled", False):
        return
    
    # Check if this severity level should trigger notification
    notify_on = webhook_config.get("notify_on", ["critical"])
    should_notify = False
    
    if "critical" in notify_on and issues.get("critical"):
        should_notify = True
    if "warning" in notify_on and issues.get("warning"):
        should_notify = True
    if "suggestion" in notify_on and issues.get("suggestion"):
        should_notify = True
    
    if not should_notify:
        return
    
    # Don't include code snippet if disabled
    if not webhook_config.get("include_code_snippet", True):
        code_snippet = None
    
    # Send to Slack
    slack_url = webhook_config.get("slack_url", "")
    if slack_url:
        if send_slack_webhook(slack_url, file_path, issues, code_snippet):
            print(f"   [WEBHOOK] Sent to Slack")
        else:
            print(f"   [WEBHOOK] Slack failed")
    
    # Send to Discord
    discord_url = webhook_config.get("discord_url", "")
    if discord_url:
        if send_discord_webhook(discord_url, file_path, issues, code_snippet):
            print(f"   [WEBHOOK] Sent to Discord")
        else:
            print(f"   [WEBHOOK] Discord failed")


if __name__ == "__main__":
    # Test mode
    print("Testing webhook module...")
    
    test_issues = {
        "critical": ["SQL injection in user input"],
        "warning": ["Missing error handling", "Unused variable"],
        "suggestion": []
    }
    
    # Dry run
    print("\nSlack payload preview:")
    print(json.dumps({
        "file": "test.py",
        "issues": test_issues
    }, indent=2))
