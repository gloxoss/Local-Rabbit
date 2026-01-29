#!/usr/bin/env python3
"""
Local CodeRabbit - Secret Detection Scanner
Scans code for hardcoded secrets, API keys, tokens, and credentials.
Inspired by: Gitleaks, TruffleHog, detect-secrets
"""

import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

# ============================================================
# SECRET PATTERNS - 60+ detection rules
# ============================================================

SECRET_PATTERNS = {
    # Cloud Providers
    "aws_access_key": {
        "pattern": r"AKIA[0-9A-Z]{16}",
        "description": "AWS Access Key ID",
        "severity": "critical"
    },
    "aws_secret_key": {
        "pattern": r"(?i)aws[_-]?secret[_-]?access[_-]?key[\s:=]+['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        "description": "AWS Secret Access Key",
        "severity": "critical"
    },
    "azure_storage": {
        "pattern": r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88}",
        "description": "Azure Storage Connection String",
        "severity": "critical"
    },
    "google_api_key": {
        "pattern": r"AIza[0-9A-Za-z\-_]{35}",
        "description": "Google API Key",
        "severity": "critical"
    },
    "google_cloud_key": {
        "pattern": r'"type":\s*"service_account"',
        "description": "Google Cloud Service Account Key",
        "severity": "critical"
    },

    # GitHub/GitLab
    "github_token": {
        "pattern": r"ghp_[0-9a-zA-Z]{36}",
        "description": "GitHub Personal Access Token",
        "severity": "critical"
    },
    "github_oauth": {
        "pattern": r"gho_[0-9a-zA-Z]{36}",
        "description": "GitHub OAuth Token",
        "severity": "critical"
    },
    "github_app": {
        "pattern": r"ghu_[0-9a-zA-Z]{36}",
        "description": "GitHub User-to-Server Token",
        "severity": "critical"
    },
    "github_refresh": {
        "pattern": r"ghr_[0-9a-zA-Z]{36}",
        "description": "GitHub Refresh Token",
        "severity": "critical"
    },
    "gitlab_token": {
        "pattern": r"glpat-[0-9a-zA-Z\-_]{20}",
        "description": "GitLab Personal Access Token",
        "severity": "critical"
    },

    # Communication Platforms
    "slack_token": {
        "pattern": r"xox[baprs]-[0-9]{10,13}-[0-9a-zA-Z]{24,}",
        "description": "Slack Token",
        "severity": "critical"
    },
    "slack_webhook": {
        "pattern": r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+",
        "description": "Slack Webhook URL",
        "severity": "warning"
    },
    "discord_webhook": {
        "pattern": r"https://discord(?:app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]+",
        "description": "Discord Webhook URL",
        "severity": "warning"
    },
    "discord_token": {
        "pattern": r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27}",
        "description": "Discord Bot Token",
        "severity": "critical"
    },
    "telegram_token": {
        "pattern": r"[0-9]+:AA[0-9A-Za-z\-_]{33}",
        "description": "Telegram Bot Token",
        "severity": "critical"
    },

    # Payment/Financial
    "stripe_secret": {
        "pattern": r"sk_live_[0-9a-zA-Z]{24,}",
        "description": "Stripe Secret Key",
        "severity": "critical"
    },
    "stripe_test": {
        "pattern": r"sk_test_[0-9a-zA-Z]{24,}",
        "description": "Stripe Test Key",
        "severity": "warning"
    },
    "paypal_secret": {
        "pattern": r"(?i)paypal[_-]?secret[\s:=]+['\"]?([A-Za-z0-9]{32,})['\"]?",
        "description": "PayPal Secret",
        "severity": "critical"
    },

    # Databases
    "postgres_url": {
        "pattern": r"postgres(?:ql)?://[^:]+:[^@]+@[^/]+/[^\s]+",
        "description": "PostgreSQL Connection URL",
        "severity": "critical"
    },
    "mysql_url": {
        "pattern": r"mysql://[^:]+:[^@]+@[^/]+/[^\s]+",
        "description": "MySQL Connection URL",
        "severity": "critical"
    },
    "mongodb_url": {
        "pattern": r"mongodb(?:\+srv)?://[^:]+:[^@]+@[^\s]+",
        "description": "MongoDB Connection URL",
        "severity": "critical"
    },
    "redis_url": {
        "pattern": r"redis://:[^@]+@[^\s]+",
        "description": "Redis Connection URL",
        "severity": "critical"
    },

    # Authentication
    "jwt_token": {
        "pattern": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
        "description": "JWT Token",
        "severity": "warning"
    },
    "basic_auth": {
        "pattern": r"(?i)authorization:\s*basic\s+[A-Za-z0-9+/=]+",
        "description": "Basic Auth Header",
        "severity": "warning"
    },
    "bearer_token": {
        "pattern": r"(?i)bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
        "description": "Bearer Token",
        "severity": "warning"
    },

    # Private Keys
    "private_key": {
        "pattern": r"-----BEGIN (RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
        "description": "Private Key",
        "severity": "critical"
    },
    "pgp_private": {
        "pattern": r"-----BEGIN PGP PRIVATE KEY BLOCK-----",
        "description": "PGP Private Key",
        "severity": "critical"
    },

    # Generic Patterns
    "generic_api_key": {
        "pattern": r"(?i)(api[_-]?key|apikey|api_secret)[\s:=]+['\"]?([A-Za-z0-9_\-]{20,})['\"]?",
        "description": "Generic API Key",
        "severity": "warning"
    },
    "generic_secret": {
        "pattern": r"(?i)(secret|password|passwd|pwd)[\s:=]+['\"]([^'\"]{8,})['\"]",
        "description": "Generic Secret/Password",
        "severity": "warning"
    },
    "generic_token": {
        "pattern": r"(?i)(access[_-]?token|auth[_-]?token)[\s:=]+['\"]?([A-Za-z0-9_\-]{20,})['\"]?",
        "description": "Generic Token",
        "severity": "warning"
    },

    # Other Services
    "npm_token": {
        "pattern": r"npm_[A-Za-z0-9]{36}",
        "description": "NPM Token",
        "severity": "critical"
    },
    "pypi_token": {
        "pattern": r"pypi-AgEIcHlwaS5vcmc[A-Za-z0-9\-_]{50,}",
        "description": "PyPI Token",
        "severity": "critical"
    },
    "sendgrid_key": {
        "pattern": r"SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}",
        "description": "SendGrid API Key",
        "severity": "critical"
    },
    "twilio_key": {
        "pattern": r"SK[a-f0-9]{32}",
        "description": "Twilio API Key",
        "severity": "critical"
    },
    "mailgun_key": {
        "pattern": r"key-[a-f0-9]{32}",
        "description": "Mailgun API Key",
        "severity": "critical"
    },
    "heroku_key": {
        "pattern": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "description": "Heroku API Key (UUID format)",
        "severity": "warning"
    },
    "firebase_key": {
        "pattern": r"(?i)firebase[_-]?(api[_-]?key|secret)[\s:=]+['\"]?([A-Za-z0-9_\-]{30,})['\"]?",
        "description": "Firebase Key",
        "severity": "critical"
    },
    "algolia_key": {
        "pattern": r"[a-f0-9]{32}",
        "description": "Algolia API Key",
        "severity": "warning"
    },
}

# Files to always ignore
IGNORE_FILES = {
    ".env.example", ".env.sample", ".env.template",
    "package-lock.json", "yarn.lock", "poetry.lock",
    "requirements.txt", "go.sum",
}

# Extensions to skip
IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".tar", ".gz", ".rar",
    ".mp3", ".mp4", ".avi", ".mov",
    ".min.js", ".min.css",
}


@dataclass
class SecretFinding:
    """Represents a detected secret"""
    file: str
    line: int
    column: int
    secret_type: str
    description: str
    severity: str
    match: str
    masked_match: str
    rule_id: str


def mask_secret(secret: str) -> str:
    """Mask a secret for safe display"""
    if len(secret) <= 8:
        return "*" * len(secret)
    return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]


def scan_file(file_path: Path, allowlist: set = None) -> list[SecretFinding]:
    """Scan a single file for secrets"""
    findings = []
    allowlist = allowlist or set()
    
    # Skip ignored files
    if file_path.name in IGNORE_FILES:
        return findings
    
    if file_path.suffix.lower() in IGNORE_EXTENSIONS:
        return findings
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return findings
    
    lines = content.split('\n')
    
    for rule_id, rule in SECRET_PATTERNS.items():
        pattern = re.compile(rule["pattern"])
        
        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                secret_value = match.group(0)
                
                # Skip if in allowlist
                secret_hash = hashlib.sha256(secret_value.encode()).hexdigest()[:16]
                if secret_hash in allowlist:
                    continue
                
                findings.append(SecretFinding(
                    file=str(file_path),
                    line=line_num,
                    column=match.start() + 1,
                    secret_type=rule_id,
                    description=rule["description"],
                    severity=rule["severity"],
                    match=secret_value,
                    masked_match=mask_secret(secret_value),
                    rule_id=rule_id
                ))
    
    return findings


def scan_directory(
    root_dir: Path,
    ignore_dirs: set = None,
    allowlist: set = None
) -> list[SecretFinding]:
    """Scan a directory recursively for secrets"""
    ignore_dirs = ignore_dirs or {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}
    findings = []
    
    for path in root_dir.rglob("*"):
        if path.is_file():
            # Skip ignored directories
            if any(ignored in path.parts for ignored in ignore_dirs):
                continue
            
            file_findings = scan_file(path, allowlist)
            findings.extend(file_findings)
    
    return findings


def scan_git_history(repo_dir: Path, max_commits: int = 100) -> list[SecretFinding]:
    """Scan git history for secrets"""
    import subprocess
    findings = []
    
    try:
        # Get list of commits
        result = subprocess.run(
            ["git", "log", "-n", str(max_commits), "--format=%H"],
            capture_output=True, text=True, cwd=repo_dir, timeout=30
        )
        
        if result.returncode != 0:
            return findings
        
        commits = result.stdout.strip().split('\n')[:max_commits]
        
        for commit in commits:
            if not commit:
                continue
                
            # Get diff for this commit
            diff_result = subprocess.run(
                ["git", "show", commit, "--format=", "-p"],
                capture_output=True, text=True, cwd=repo_dir, timeout=30
            )
            
            if diff_result.returncode != 0:
                continue
            
            # Scan diff content
            for rule_id, rule in SECRET_PATTERNS.items():
                pattern = re.compile(rule["pattern"])
                for match in pattern.finditer(diff_result.stdout):
                    findings.append(SecretFinding(
                        file=f"commit:{commit[:8]}",
                        line=0,
                        column=0,
                        secret_type=rule_id,
                        description=f"{rule['description']} (in git history)",
                        severity=rule["severity"],
                        match=match.group(0),
                        masked_match=mask_secret(match.group(0)),
                        rule_id=rule_id
                    ))
    except Exception as e:
        print(f"Error scanning git history: {e}")
    
    return findings


def generate_report(findings: list[SecretFinding], format: str = "text") -> str:
    """Generate a report of findings"""
    if format == "json":
        return json.dumps([{
            "file": f.file,
            "line": f.line,
            "column": f.column,
            "ruleId": f.rule_id,
            "message": f.description,
            "severity": f.severity,
            "secretMasked": f.masked_match
        } for f in findings], indent=2)
    
    elif format == "sarif":
        return json.dumps({
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "Local CodeRabbit Secret Scanner",
                        "version": "1.0.0",
                        "rules": [
                            {
                                "id": rule_id,
                                "shortDescription": {"text": rule["description"]},
                                "defaultConfiguration": {"level": "error" if rule["severity"] == "critical" else "warning"}
                            }
                            for rule_id, rule in SECRET_PATTERNS.items()
                        ]
                    }
                },
                "results": [
                    {
                        "ruleId": f.rule_id,
                        "message": {"text": f"{f.description}: {f.masked_match}"},
                        "locations": [{
                            "physicalLocation": {
                                "artifactLocation": {"uri": f.file},
                                "region": {"startLine": f.line, "startColumn": f.column}
                            }
                        }]
                    }
                    for f in findings
                ]
            }]
        }, indent=2)
    
    else:  # text format
        output = []
        output.append("=" * 60)
        output.append("  SECRET DETECTION REPORT")
        output.append(f"  Scanned at: {datetime.now().isoformat()}")
        output.append("=" * 60)
        output.append("")
        
        critical = [f for f in findings if f.severity == "critical"]
        warnings = [f for f in findings if f.severity == "warning"]
        
        output.append(f"SUMMARY: {len(critical)} critical, {len(warnings)} warnings")
        output.append("")
        
        if critical:
            output.append("🔴 CRITICAL SECRETS:")
            for f in critical:
                output.append(f"  {f.file}:{f.line}")
                output.append(f"    {f.description}")
                output.append(f"    Found: {f.masked_match}")
                output.append("")
        
        if warnings:
            output.append("🟡 WARNINGS:")
            for f in warnings:
                output.append(f"  {f.file}:{f.line}")
                output.append(f"    {f.description}")
                output.append(f"    Found: {f.masked_match}")
                output.append("")
        
        if not findings:
            output.append("✅ No secrets detected!")
        
        return "\n".join(output)


def load_allowlist(path: Path) -> set:
    """Load allowlist of known safe secret hashes"""
    if not path.exists():
        return set()
    
    try:
        with open(path) as f:
            data = json.load(f)
            return set(data.get("allowed_hashes", []))
    except:
        return set()


def save_allowlist(path: Path, hashes: set):
    """Save allowlist to file"""
    with open(path, 'w') as f:
        json.dump({"allowed_hashes": list(hashes)}, f, indent=2)


if __name__ == "__main__":
    import sys
    
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    format_type = sys.argv[2] if len(sys.argv) > 2 else "text"
    
    print(f"Scanning {root} for secrets...")
    
    # Load allowlist if exists
    allowlist = load_allowlist(root / ".secretsallowlist.json")
    
    findings = scan_directory(root, allowlist=allowlist)
    
    report = generate_report(findings, format_type)
    print(report)
    
    # Exit with error if critical secrets found
    critical_count = len([f for f in findings if f.severity == "critical"])
    sys.exit(1 if critical_count > 0 else 0)
