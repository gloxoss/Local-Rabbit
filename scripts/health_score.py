#!/usr/bin/env python3
"""
Local CodeRabbit - Code Health Score Calculator
Analyzes codebase for complexity, maintainability, security, and test coverage.
"""

import re
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FileMetrics:
    """Metrics for a single file"""
    path: str
    language: str
    lines_of_code: int
    blank_lines: int
    comment_lines: int
    functions: int
    classes: int
    cyclomatic_complexity: float
    max_function_length: int
    todo_fixme_count: int
    has_tests: bool


@dataclass
class HealthScore:
    """Overall health score breakdown"""
    total_score: int  # 0-100
    complexity_score: int
    maintainability_score: int
    security_score: int
    test_coverage_score: int
    documentation_score: int
    details: dict


def count_lines(content: str) -> tuple[int, int, int]:
    """Count code lines, blank lines, and comment lines"""
    lines = content.split('\n')
    blank = 0
    comment = 0
    code = 0
    
    in_multiline_comment = False
    
    for line in lines:
        stripped = line.strip()
        
        # Check for multiline comments
        if '"""' in stripped or "'''" in stripped:
            comment += 1
            in_multiline_comment = not in_multiline_comment
            continue
        if '/*' in stripped:
            comment += 1
            if '*/' not in stripped:
                in_multiline_comment = True
            continue
        if '*/' in stripped:
            comment += 1
            in_multiline_comment = False
            continue
        
        if in_multiline_comment:
            comment += 1
        elif not stripped:
            blank += 1
        elif stripped.startswith(('#', '//', '*')):
            comment += 1
        else:
            code += 1
    
    return code, blank, comment


def count_functions_classes(content: str, language: str) -> tuple[int, int]:
    """Count functions and classes in file"""
    functions = 0
    classes = 0
    
    if language == "python":
        functions = len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
        classes = len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
    elif language in ["javascript", "typescript"]:
        # Function declarations and arrow functions
        functions = len(re.findall(r'(function\s+\w+|const\s+\w+\s*=\s*(async\s*)?\([^)]*\)\s*=>|^\s*\w+\s*\([^)]*\)\s*{)', content, re.MULTILINE))
        classes = len(re.findall(r'class\s+\w+', content))
    
    return functions, classes


def calculate_cyclomatic_complexity(content: str, language: str) -> float:
    """Estimate cyclomatic complexity"""
    decision_points = 0
    
    # Count decision points
    patterns = [
        r'\bif\b', r'\belif\b', r'\belse\b',
        r'\bfor\b', r'\bwhile\b',
        r'\bcase\b', r'\bcatch\b',
        r'\band\b', r'\bor\b', r'&&', r'\|\|',
        r'\?'  # Ternary operator
    ]
    
    for pattern in patterns:
        decision_points += len(re.findall(pattern, content))
    
    # Basic CC formula: 1 + decision points / number of functions
    functions, _ = count_functions_classes(content, language)
    if functions == 0:
        functions = 1
    
    return 1 + (decision_points / functions)


def get_max_function_length(content: str, language: str) -> int:
    """Get maximum function length in lines"""
    max_length = 0
    
    if language == "python":
        # Simple heuristic: count lines between def and next def/class/end
        in_function = False
        current_length = 0
        base_indent = 0
        
        for line in content.split('\n'):
            if re.match(r'^\s*def\s+', line):
                if in_function:
                    max_length = max(max_length, current_length)
                in_function = True
                current_length = 1
                base_indent = len(line) - len(line.lstrip())
            elif in_function:
                if line.strip() and not line.startswith(' ' * (base_indent + 1)):
                    # Function ended (different or lower indent)
                    if not line.strip().startswith('@'):  # Not a decorator
                        max_length = max(max_length, current_length)
                        in_function = False
                else:
                    current_length += 1
        
        if in_function:
            max_length = max(max_length, current_length)
    
    return max_length


def count_todos(content: str) -> int:
    """Count TODO and FIXME comments"""
    return len(re.findall(r'\b(TODO|FIXME|HACK|XXX)\b', content, re.IGNORECASE))


def analyze_file(file_path: Path) -> Optional[FileMetrics]:
    """Analyze a single file"""
    ext_to_lang = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.go': 'go',
        '.rs': 'rust'
    }
    
    language = ext_to_lang.get(file_path.suffix.lower())
    if not language:
        return None
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return None
    
    code, blank, comment = count_lines(content)
    functions, classes = count_functions_classes(content, language)
    cc = calculate_cyclomatic_complexity(content, language)
    max_func_len = get_max_function_length(content, language)
    todos = count_todos(content)
    
    # Check if it's a test file
    is_test = 'test' in file_path.name.lower() or '_test.' in file_path.name.lower()
    
    return FileMetrics(
        path=str(file_path),
        language=language,
        lines_of_code=code,
        blank_lines=blank,
        comment_lines=comment,
        functions=functions,
        classes=classes,
        cyclomatic_complexity=cc,
        max_function_length=max_func_len,
        todo_fixme_count=todos,
        has_tests=is_test
    )


def analyze_directory(root: Path, ignore_dirs: set = None) -> list[FileMetrics]:
    """Analyze all files in directory"""
    ignore_dirs = ignore_dirs or {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}
    
    metrics = []
    for path in root.rglob("*"):
        if path.is_file():
            if any(ignored in path.parts for ignored in ignore_dirs):
                continue
            
            file_metrics = analyze_file(path)
            if file_metrics:
                metrics.append(file_metrics)
    
    return metrics


def calculate_health_score(metrics: list[FileMetrics], security_findings: int = 0) -> HealthScore:
    """Calculate overall health score"""
    if not metrics:
        return HealthScore(
            total_score=100,
            complexity_score=100,
            maintainability_score=100,
            security_score=100,
            test_coverage_score=0,
            documentation_score=100,
            details={}
        )
    
    total_loc = sum(m.lines_of_code for m in metrics)
    total_comments = sum(m.comment_lines for m in metrics)
    total_functions = sum(m.functions for m in metrics)
    total_todos = sum(m.todo_fixme_count for m in metrics)
    avg_cc = sum(m.cyclomatic_complexity for m in metrics) / len(metrics)
    max_func_lengths = [m.max_function_length for m in metrics if m.max_function_length > 0]
    avg_max_func_length = sum(max_func_lengths) / len(max_func_lengths) if max_func_lengths else 0
    
    test_files = sum(1 for m in metrics if m.has_tests)
    src_files = len(metrics) - test_files
    
    # Complexity Score (0-100)
    # Lower complexity is better
    complexity_score = 100
    if avg_cc > 5:
        complexity_score -= (avg_cc - 5) * 5  # -5 points per CC above 5
    if avg_max_func_length > 50:
        complexity_score -= (avg_max_func_length - 50) * 0.5
    complexity_score = max(0, min(100, complexity_score))
    
    # Maintainability Score (0-100)
    maintainability_score = 100
    # Penalize for TODOs
    maintainability_score -= min(20, total_todos * 2)
    # Bonus for comments
    comment_ratio = total_comments / total_loc if total_loc > 0 else 0
    if comment_ratio < 0.1:
        maintainability_score -= 10
    elif comment_ratio > 0.3:
        maintainability_score += 5
    maintainability_score = max(0, min(100, maintainability_score))
    
    # Security Score (0-100)
    security_score = 100 - min(100, security_findings * 10)
    
    # Test Coverage Score (0-100)
    # Estimate based on presence of test files
    test_ratio = test_files / src_files if src_files > 0 else 0
    test_coverage_score = min(100, int(test_ratio * 200))  # 50% test files = 100%
    
    # Documentation Score (0-100)
    documentation_score = 100
    if comment_ratio < 0.05:
        documentation_score = 30
    elif comment_ratio < 0.1:
        documentation_score = 60
    elif comment_ratio < 0.2:
        documentation_score = 80
    
    # Total Score (weighted average)
    total_score = int(
        complexity_score * 0.25 +
        maintainability_score * 0.25 +
        security_score * 0.25 +
        test_coverage_score * 0.15 +
        documentation_score * 0.10
    )
    
    return HealthScore(
        total_score=total_score,
        complexity_score=int(complexity_score),
        maintainability_score=int(maintainability_score),
        security_score=int(security_score),
        test_coverage_score=int(test_coverage_score),
        documentation_score=int(documentation_score),
        details={
            "total_files": len(metrics),
            "total_loc": total_loc,
            "total_functions": total_functions,
            "avg_cyclomatic_complexity": round(avg_cc, 2),
            "avg_max_function_length": round(avg_max_func_length, 2),
            "todo_count": total_todos,
            "comment_ratio": round(comment_ratio, 3),
            "test_files": test_files,
            "src_files": src_files
        }
    )


def generate_health_report(score: HealthScore, format: str = "text") -> str:
    """Generate health report"""
    if format == "json":
        return json.dumps({
            "totalScore": score.total_score,
            "breakdown": {
                "complexity": score.complexity_score,
                "maintainability": score.maintainability_score,
                "security": score.security_score,
                "testCoverage": score.test_coverage_score,
                "documentation": score.documentation_score
            },
            "details": score.details,
            "generatedAt": datetime.now().isoformat()
        }, indent=2)
    
    else:  # text
        def bar(value, width=20):
            filled = int(value / 100 * width)
            return "█" * filled + "░" * (width - filled)
        
        grade = "A" if score.total_score >= 90 else "B" if score.total_score >= 80 else "C" if score.total_score >= 70 else "D" if score.total_score >= 60 else "F"
        
        output = []
        output.append("=" * 50)
        output.append("  CODE HEALTH SCORE")
        output.append("=" * 50)
        output.append("")
        output.append(f"  ┌{'─' * 30}┐")
        output.append(f"  │ OVERALL: {score.total_score:3d}/100  Grade: {grade}   │")
        output.append(f"  └{'─' * 30}┘")
        output.append("")
        output.append("BREAKDOWN:")
        output.append(f"  Complexity      {bar(score.complexity_score)} {score.complexity_score:3d}%")
        output.append(f"  Maintainability {bar(score.maintainability_score)} {score.maintainability_score:3d}%")
        output.append(f"  Security        {bar(score.security_score)} {score.security_score:3d}%")
        output.append(f"  Test Coverage   {bar(score.test_coverage_score)} {score.test_coverage_score:3d}%")
        output.append(f"  Documentation   {bar(score.documentation_score)} {score.documentation_score:3d}%")
        output.append("")
        output.append("DETAILS:")
        output.append(f"  Files analyzed:          {score.details.get('total_files', 0)}")
        output.append(f"  Lines of code:           {score.details.get('total_loc', 0)}")
        output.append(f"  Functions:               {score.details.get('total_functions', 0)}")
        output.append(f"  Avg complexity (CC):     {score.details.get('avg_cyclomatic_complexity', 0)}")
        output.append(f"  Comment ratio:           {score.details.get('comment_ratio', 0):.1%}")
        output.append(f"  TODO/FIXME count:        {score.details.get('todo_count', 0)}")
        output.append(f"  Test files:              {score.details.get('test_files', 0)}")
        output.append("")
        
        # Recommendations
        output.append("RECOMMENDATIONS:")
        if score.complexity_score < 70:
            output.append("  🔴 Reduce complexity: Break down large functions")
        if score.maintainability_score < 70:
            output.append("  🟡 Address TODOs and improve code organization")
        if score.security_score < 70:
            output.append("  🔴 Fix security issues before deployment")
        if score.test_coverage_score < 50:
            output.append("  🟡 Increase test coverage")
        if score.documentation_score < 50:
            output.append("  🔵 Add more code comments/documentation")
        if score.total_score >= 80:
            output.append("  ✅ Code health is good!")
        
        return "\n".join(output)


if __name__ == "__main__":
    import sys
    
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    format_type = sys.argv[2] if len(sys.argv) > 2 else "text"
    
    print(f"Analyzing {root}...")
    metrics = analyze_directory(root)
    print(f"Found {len(metrics)} files to analyze")
    print()
    
    score = calculate_health_score(metrics)
    report = generate_health_report(score, format_type)
    print(report)
