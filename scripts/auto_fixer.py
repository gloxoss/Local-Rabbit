#!/usr/bin/env python3
"""
Local CodeRabbit - Auto-Fix Generator
Generate AI-powered fixes for detected issues with diff preview.
"""

import json
import os
import re
import difflib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import urllib.request


@dataclass
class Fix:
    """Represents a proposed fix"""
    file: str
    line_start: int
    line_end: int
    original_code: str
    fixed_code: str
    description: str
    confidence: float  # 0.0 - 1.0
    issue_type: str


@dataclass
class DiffChunk:
    """A chunk in a unified diff"""
    original_start: int
    original_count: int
    new_start: int
    new_count: int
    lines: list[str]


class AutoFixer:
    """Generates AI-powered fixes for code issues"""
    
    def __init__(self, ollama_url: str = None, model: str = None):
        self.ollama_url = ollama_url or os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        self.model = model or os.environ.get('OLLAMA_MODEL', 'qwen2.5-coder')
    
    def generate_fix(self, code: str, issue: str, context: str = "") -> Optional[Fix]:
        """Generate a fix for a single issue"""
        prompt = f"""Fix the following code issue:

ISSUE: {issue}

ORIGINAL CODE:
```
{code}
```

{f"CONTEXT: {context}" if context else ""}

Provide ONLY the fixed code, no explanations. Output the complete fixed code block."""

        try:
            response = self._query_ollama(prompt)
            
            # Extract code from response
            fixed_code = self._extract_code_block(response)
            if not fixed_code:
                fixed_code = response.strip()
            
            # Calculate confidence based on response quality
            confidence = self._calculate_confidence(code, fixed_code, issue)
            
            return Fix(
                file="",
                line_start=1,
                line_end=len(code.split('\n')),
                original_code=code,
                fixed_code=fixed_code,
                description=f"Fix for: {issue[:100]}",
                confidence=confidence,
                issue_type=self._detect_issue_type(issue)
            )
        
        except Exception as e:
            print(f"Error generating fix: {e}")
            return None
    
    def generate_fixes_for_file(self, file_path: Path, issues: list[dict]) -> list[Fix]:
        """Generate fixes for all issues in a file"""
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return []
        
        lines = content.split('\n')
        fixes = []
        
        for issue in issues:
            line_num = issue.get("line", 1)
            message = issue.get("message", "")
            
            # Get context (5 lines before and after)
            start = max(0, line_num - 5)
            end = min(len(lines), line_num + 5)
            code_chunk = '\n'.join(lines[start:end])
            
            fix = self.generate_fix(code_chunk, message)
            if fix:
                fix.file = str(file_path)
                fix.line_start = start + 1
                fix.line_end = end
                fixes.append(fix)
        
        return fixes
    
    def generate_diff(self, fix: Fix) -> str:
        """Generate unified diff for a fix"""
        original_lines = fix.original_code.split('\n')
        fixed_lines = fix.fixed_code.split('\n')
        
        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{Path(fix.file).name}",
            tofile=f"b/{Path(fix.file).name}",
            lineterm=''
        )
        
        return '\n'.join(diff)
    
    def generate_colored_diff(self, fix: Fix) -> str:
        """Generate colored diff for terminal display"""
        diff = self.generate_diff(fix)
        lines = diff.split('\n')
        colored = []
        
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                colored.append(f"\033[32m{line}\033[0m")  # Green
            elif line.startswith('-') and not line.startswith('---'):
                colored.append(f"\033[31m{line}\033[0m")  # Red
            elif line.startswith('@@'):
                colored.append(f"\033[36m{line}\033[0m")  # Cyan
            else:
                colored.append(line)
        
        return '\n'.join(colored)
    
    def apply_fix(self, fix: Fix) -> bool:
        """Apply a fix to the file"""
        try:
            file_path = Path(fix.file)
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Replace the lines
            new_lines = (
                lines[:fix.line_start - 1] +
                fix.fixed_code.split('\n') +
                lines[fix.line_end:]
            )
            
            file_path.write_text('\n'.join(new_lines), encoding='utf-8')
            return True
        
        except Exception as e:
            print(f"Error applying fix: {e}")
            return False
    
    def _query_ollama(self, prompt: str) -> str:
        """Query Ollama API"""
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,  # Deterministic for fixes
                "num_predict": 1024
            }
        }).encode()
        
        req = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.load(response)
            return data.get("response", "")
    
    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract code from markdown code block"""
        patterns = [
            r'```(?:\w+)?\n(.*?)```',  # ```lang\ncode```
            r'```(.*?)```',  # ```code```
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _calculate_confidence(self, original: str, fixed: str, issue: str) -> float:
        """Estimate confidence in the fix"""
        # Basic heuristics
        confidence = 0.5
        
        # Penalize if fix is empty or same as original
        if not fixed or fixed == original:
            return 0.0
        
        # Penalize very different fixes (might be wrong)
        similarity = difflib.SequenceMatcher(None, original, fixed).ratio()
        if similarity < 0.3:
            confidence -= 0.2
        elif similarity > 0.9:
            confidence += 0.2
        
        # Boost if fix addresses specific patterns
        if "sql" in issue.lower() and "parameterized" in fixed.lower():
            confidence += 0.2
        if "xss" in issue.lower() and "sanitize" in fixed.lower():
            confidence += 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def _detect_issue_type(self, issue: str) -> str:
        """Detect the type of issue"""
        issue_lower = issue.lower()
        
        if any(w in issue_lower for w in ["sql", "injection"]):
            return "sql_injection"
        if any(w in issue_lower for w in ["xss", "innerhtml"]):
            return "xss"
        if any(w in issue_lower for w in ["password", "secret", "key"]):
            return "secrets"
        if any(w in issue_lower for w in ["complexity", "too long", "refactor"]):
            return "complexity"
        
        return "general"


def generate_batch_report(fixes: list[Fix]) -> str:
    """Generate a report of all proposed fixes"""
    output = []
    output.append("=" * 60)
    output.append("  AUTO-FIX PROPOSAL REPORT")
    output.append("=" * 60)
    output.append("")
    
    for i, fix in enumerate(fixes, 1):
        output.append(f"Fix #{i}: {fix.description}")
        output.append(f"  File: {fix.file}:{fix.line_start}-{fix.line_end}")
        output.append(f"  Type: {fix.issue_type}")
        output.append(f"  Confidence: {fix.confidence:.0%}")
        output.append("")
        output.append("  Diff:")
        
        # Generate inline diff
        fixer = AutoFixer()
        diff = fixer.generate_diff(fix)
        for line in diff.split('\n')[:15]:  # Show first 15 lines
            output.append(f"    {line}")
        
        output.append("")
        output.append("-" * 40)
        output.append("")
    
    output.append(f"Total fixes proposed: {len(fixes)}")
    high_conf = len([f for f in fixes if f.confidence >= 0.7])
    output.append(f"High confidence fixes: {high_conf}")
    
    return "\n".join(output)


if __name__ == "__main__":
    import sys
    
    # Example usage
    fixer = AutoFixer()
    
    # Test fix generation
    test_code = """
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()
"""
    
    issue = "SQL injection vulnerability - use parameterized queries instead of f-strings"
    
    print("Generating fix for SQL injection...")
    print()
    
    fix = fixer.generate_fix(test_code, issue)
    
    if fix:
        print("Original code:")
        print(test_code)
        print()
        print("Proposed fix:")
        print(fix.fixed_code)
        print()
        print(f"Confidence: {fix.confidence:.0%}")
        print()
        print("Diff:")
        print(fixer.generate_colored_diff(fix))
    else:
        print("Could not generate fix")
