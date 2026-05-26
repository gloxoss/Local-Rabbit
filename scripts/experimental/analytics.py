import re

def calculate_complexity(code):
    """
    Calculate a simple complexity score based on indentation and length.
    Heuristic: deeper indentation = more complex logic.
    """
    if not code:
        return 0
        
    lines = code.split('\n')
    score = 0
    max_depth = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '//', '/*', '*')):
            continue
            
        # Count leading spaces (assuming 4 spaces per indent)
        indent = len(line) - len(line.lstrip())
        depth = indent // 4
        
        # Add to score: 1 point per line, + depth^1.5 penalty
        score += 1 + (depth ** 1.5)
        max_depth = max(max_depth, depth)
        
    # Normalized score relative to file length (average complexity per line * 10)
    # This prevents long simple files from having huge scores
    if len(lines) > 0:
        normalized = (score / len(lines)) * 10
    else:
        normalized = 0
        
    return round(normalized, 1)

def calculate_health_score(issues, complexity):
    """
    Calculate health score (0-100).
    Start at 100. Deduct for issues and high complexity.
    """
    score = 100
    
    # Penalties
    critical_penalty = len(issues.get("critical", [])) * 15
    warning_penalty = len(issues.get("warning", [])) * 5
    suggestion_penalty = len(issues.get("suggestion", [])) * 1
    
    # Complexity penalty: significant only if > 5.0
    complexity_penalty = max(0, (complexity - 5) * 5)
    
    deductions = critical_penalty + warning_penalty + suggestion_penalty + complexity_penalty
    
    final_score = max(0, score - deductions)
    return round(final_score)

def get_hotspot_status(health_score):
    if health_score >= 80:
        return "healthy"
    elif health_score >= 50:
        return "warning"
    else:
        return "critical"
