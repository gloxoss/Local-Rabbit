#!/usr/bin/env python3
"""
Local CodeRabbit - Pre-Commit Hook
Blocks commits if critical issues are found.
"""

import os
import sys
import subprocess
from pathlib import Path

# SOLID module imports
sys.path.insert(0, str(Path(__file__).parent))
from client import get_client, get_model_name


def get_staged_files():
    """Get list of staged files that match our extensions."""
    extensions = {'.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs', '.vue', '.svelte'}
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True, text=True
    )
    files = []
    for f in result.stdout.strip().split('\n'):
        if f and Path(f).suffix in extensions:
            files.append(f)
    return files

def review_file(client, filepath):
    """Quick review for critical issues only."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        if len(code) < 10:
            return []
        
        prompt = """You are a code reviewer. Check ONLY for CRITICAL issues:
- Security vulnerabilities
- Obvious bugs
- Type errors
- Missing error handling

Respond with ONLY the issues, one per line starting with "🔴 CRITICAL:".
If no critical issues, respond with just "✅".

CODE:
```
""" + code[:3000] + "\n```"
        
        response = client.chat.completions.create(
            model=get_model_name(),
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        issues = [line.strip() for line in result.split('\n') 
                  if '🔴' in line or 'CRITICAL' in line.upper()]
        return issues
        
    except Exception as e:
        print(f"⚠️ Error reviewing {filepath}: {e}")
        return []  # Don't block on errors

def main():
    print("\n🐰 Local CodeRabbit - Pre-Commit Check")
    print("-" * 40)
    
    files = get_staged_files()
    if not files:
        print("✅ No staged code files to review")
        sys.exit(0)
    
    print(f"📄 Checking {len(files)} file(s)...")
    
    try:
        client = get_client()
    except Exception as e:
        print(f"⚠️ Could not connect to AI: {e}")
        print("   Skipping pre-commit review")
        sys.exit(0)  # Don't block if no API access
    
    all_issues = {}
    
    for filepath in files:
        print(f"   • {filepath}", end=" ")
        issues = review_file(client, filepath)
        if issues:
            print("🔴")
            all_issues[filepath] = issues
        else:
            print("✅")
    
    if all_issues:
        print("\n" + "=" * 40)
        print("❌ COMMIT BLOCKED - Critical issues found:")
        print("=" * 40)
        
        for filepath, issues in all_issues.items():
            print(f"\n📁 {filepath}")
            for issue in issues:
                print(f"   {issue}")
        
        print("\n💡 Fix these issues or use --no-verify to skip")
        sys.exit(1)
    
    print("\n✅ All files passed review!")
    sys.exit(0)

if __name__ == '__main__':
    main()
