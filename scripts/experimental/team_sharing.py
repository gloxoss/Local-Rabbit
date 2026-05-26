#!/usr/bin/env python3
"""
Local CodeRabbit - Team Sharing
Sends notifications to Slack/Discord/Telegram.
"""

import os
import json
import urllib.request
from datetime import datetime

def send_discord(webhook_url, title, message, severity="info", file_path=None):
    """Send notification to Discord webhook."""
    colors = {
        "critical": 15158332,  # Red
        "warning": 15844367,   # Orange/Yellow
        "suggestion": 3447003,  # Blue
        "info": 5763719        # Green
    }
    
    embed = {
        "title": f"🐰 {title}",
        "description": message[:2000],
        "color": colors.get(severity, colors["info"]),
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Local CodeRabbit"}
    }
    
    if file_path:
        embed["fields"] = [{"name": "File", "value": f"`{file_path}`", "inline": True}]
    
    payload = json.dumps({"embeds": [embed]}).encode('utf-8')
    
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"Discord error: {e}")
        return False

def send_slack(webhook_url, title, message, severity="info", file_path=None):
    """Send notification to Slack webhook."""
    colors = {
        "critical": "#ef4444",
        "warning": "#f59e0b",
        "suggestion": "#3b82f6",
        "info": "#10b981"
    }
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🐰 {title}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message[:2000]}
        }
    ]
    
    if file_path:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📁 `{file_path}`"}]
        })
    
    payload = json.dumps({
        "attachments": [{
            "color": colors.get(severity, colors["info"]),
            "blocks": blocks
        }]
    }).encode('utf-8')
    
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"Slack error: {e}")
        return False

def send_telegram(bot_token, chat_id, title, message, severity="info", file_path=None):
    """Send notification to Telegram."""
    emoji = {
        "critical": "🔴",
        "warning": "🟡",
        "suggestion": "🔵",
        "info": "✅"
    }
    
    text = f"{emoji.get(severity, '🐰')} *{title}*\n\n{message[:3000]}"
    if file_path:
        text += f"\n\n📁 `{file_path}`"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

class TeamNotifier:
    """Manages team notifications across platforms."""
    
    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
    
    def _load_config(self, config_path):
        """Load notification config from file or environment."""
        config = {
            "discord_webhook": os.environ.get("DISCORD_WEBHOOK"),
            "slack_webhook": os.environ.get("SLACK_WEBHOOK"),
            "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
            "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID"),
            "notify_on": ["critical"]  # Only critical by default
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    file_config = json.load(f)
                    config.update(file_config.get("team_sharing", {}))
            except Exception:
                pass
        
        return config
    
    def notify(self, title, message, severity="info", file_path=None):
        """Send notification to all configured platforms."""
        if severity not in self.config.get("notify_on", ["critical"]):
            return
        
        results = []
        
        if self.config.get("discord_webhook"):
            results.append(("Discord", send_discord(
                self.config["discord_webhook"], title, message, severity, file_path
            )))
        
        if self.config.get("slack_webhook"):
            results.append(("Slack", send_slack(
                self.config["slack_webhook"], title, message, severity, file_path
            )))
        
        if self.config.get("telegram_bot_token") and self.config.get("telegram_chat_id"):
            results.append(("Telegram", send_telegram(
                self.config["telegram_bot_token"],
                self.config["telegram_chat_id"],
                title, message, severity, file_path
            )))
        
        return results

def test_notifications():
    """Test all configured notification channels."""
    notifier = TeamNotifier()
    
    print("🔔 Testing Team Notifications\n")
    
    results = notifier.notify(
        "Test Notification",
        "This is a test message from Local CodeRabbit 🐰\n\n🔴 CRITICAL: Example critical issue\n🟡 WARNING: Example warning",
        severity="critical",
        file_path="test/example.ts"
    )
    
    if not results:
        print("❌ No notification channels configured")
        print("\nSet environment variables:")
        print("  - DISCORD_WEBHOOK")
        print("  - SLACK_WEBHOOK")
        print("  - TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID")
    else:
        for name, success in results:
            print(f"{'✅' if success else '❌'} {name}")

if __name__ == '__main__':
    test_notifications()
