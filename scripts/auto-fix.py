#!/usr/bin/env python3
"""
Local CodeRabbit - Auto-Fix Generator
Generates git patches for common issues.
"""

import os
import sys
import json
import difflib
from pathlib import Path
from datetime import datetime
from openai import OpenAI

FIX_PROMPT = """You are a code fixer. Given the issue and code, provide ONLY the corrected code.

ISSUE: {issue}

ORIGINAL CODE:
```
{code}
```

Rules:
1. Return ONLY the fixed code, no explanations
2. Preserve all unchanged lines exactly
3. Fix the specific issue mentioned
4. Keep the same formatting style

FIXED CODE:
```
"""

def get_client():
    return OpenAI(
        api_key=os.environ.get('OPENAI_API_KEY', os.environ.get('ZAI_API_KEY')),
        base_url=os.environ.get('OPENAI_API_BASE', os.environ.get('ZAI_API_BASE', 'https://api.z.ai/v1'))
    )

def generate_fix(client, code, issue):
    """Generate fixed code using AI."""
    try:
        prompt = FIX_PROMPT.format(issue=issue, code=code)
        
        response = client.chat.completions.create(
            model=os.environ.get('ZAI_MODEL', 'glm-4'),
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=2000
        )
        
        result = response.choices[0].message.content
        
        # Extract code from response
        if '```' in result:
            parts = result.split('```')
            if len(parts) >= 2:
                code_part = parts[1]
                # Remove language identifier if present
                lines = code_part.split('\n')
                if lines[0].strip() in ['typescript', 'javascript', 'python', 'tsx', 'jsx', '']:
                    code_part = '\n'.join(lines[1:])
                return code_part.strip()
        
        return result.strip()
    except Exception as e:
        return None

def create_patch(original, fixed, filepath):
    """Create a unified diff patch."""
    original_lines = original.splitlines(keepends=True)
    fixed_lines = fixed.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        fixed_lines,
        fromfile=f'a/{filepath}',
        tofile=f'b/{filepath}',
        lineterm=''
    )
    
    return ''.join(diff)

def save_patch(patch, filepath, patches_dir):
    """Save patch to file."""
    patches_dir = Path(patches_dir)
    patches_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    basename = Path(filepath).stem
    patch_name = f"{basename}_{timestamp}.patch"
    patch_path = patches_dir / patch_name
    
    with open(patch_path, 'w', encoding='utf-8') as f:
        f.write(patch)
    
    return patch_path

def apply_fix_interactive(filepath, original, fixed, issue):
    """Show diff and ask user to apply."""
    print(f"\n{'=' * 60}")
    print(f"📁 {filepath}")
    print(f"🔧 Issue: {issue[:100]}")
    print(f"{'=' * 60}\n")
    
    # Show colorized diff
    original_lines = original.splitlines()
    fixed_lines = fixed.splitlines()
    
    diff = list(difflib.unified_diff(original_lines, fixed_lines, lineterm=''))
    
    for line in diff[2:]:  # Skip headers
        if line.startswith('+'):
            print(f"\033[92m{line}\033[0m")  # Green for additions
        elif line.startswith('-'):
            print(f"\033[91m{line}\033[0m")  # Red for deletions
        elif line.startswith('@'):
            print(f"\033[96m{line}\033[0m")  # Cyan for line numbers
        else:
            print(line)
    
    print(f"\n{'=' * 60}")
    response = input("Apply this fix? [y/N/s(save patch)]: ").strip().lower()
    
    return response

def auto_fix_file(filepath, issues):
    """Attempt to auto-fix issues in a file."""
    print(f"\n🔧 Auto-Fix Generator")
    print(f"📁 File: {filepath}")
    print(f"🐛 Issues: {len(issues)}")
    print("-" * 40)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception as e:
        print(f"❌ Cannot read file: {e}")
        return
    
    client = get_client()
    patches_dir = Path(filepath).parent / '.patches'
    
    fixed_code = original
    
    for i, issue in enumerate(issues, 1):
        print(f"\n[{i}/{len(issues)}] {issue[:80]}...")
        
        fixed = generate_fix(client, fixed_code, issue)
        
        if fixed and fixed != fixed_code:
            response = apply_fix_interactive(filepath, fixed_code, fixed, issue)
            
            if response == 'y':
                fixed_code = fixed
                print("✅ Fix applied in memory")
            elif response == 's':
                patch = create_patch(fixed_code, fixed, filepath)
                patch_path = save_patch(patch, filepath, patches_dir)
                print(f"💾 Patch saved: {patch_path}")
            else:
                print("⏭️ Skipped")
        else:
            print("⚠️ Could not generate fix")
    
    # Write final result if changes were made
    if fixed_code != original:
        print(f"\n📝 Writing changes to {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_code)
        print("✅ File updated!")
    else:
        print("\n ℹ️ No changes applied")

def main():
    if len(sys.argv) < 2:
        print("Usage: auto-fix.py <filepath> [issue1] [issue2] ...")
        print("       auto-fix.py <filepath>  # Will prompt for issues")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if len(sys.argv) > 2:
        issues = sys.argv[2:]
    else:
        print("Enter issues to fix (one per line, empty line to finish):")
        issues = []
        while True:
            line = input().strip()
            if not line:
                break
            issues.append(line)
    
    if not issues:
        print("❌ No issues provided")
        sys.exit(1)
    
    auto_fix_file(filepath, issues)

if __name__ == '__main__':
    main()
