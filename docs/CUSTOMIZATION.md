# Customization Guide

## Changing Models

Edit `.env`:
```bash
# Options (in order of quality → speed)
OLLAMA_MODEL=deepseek-coder-v2   # Best quality, 16B, ~12GB RAM
OLLAMA_MODEL=qwen2.5-coder       # Fast, 7B, ~5GB RAM  
OLLAMA_MODEL=llama3.1            # General reasoning, 8B
OLLAMA_MODEL=mistral             # Fastest, 7B, ~4GB RAM
```

Then restart:
```powershell
docker-compose restart pr-agent
```

## Custom Review Prompts

Edit `pr-agent/settings/pr_reviewer_prompts.toml`.

### Security-First Example
```toml
[system_prompts]
main_prompt = """
SECURITY-FIRST CODE REVIEW

Check for:
1. SQL Injection (use parameterized queries)
2. XSS vectors (escape HTML)
3. Auth bypass risks
4. Secrets in code
5. Input validation

REJECT PRs with security issues.
"""
```

### Performance-Focused Example
```toml
[system_prompts]
main_prompt = """
PERFORMANCE REVIEW

Analyze:
1. N+1 database queries
2. Unnecessary React re-renders
3. Bundle size impact
4. Missing caching
5. Memory leaks

Suggest optimizations with impact metrics.
"""
```

## File Skip Patterns

Edit `pr-agent/settings/configuration.toml`:
```toml
[pr_reviewer]
skip_files = [
    "*.md",
    "*.lock",
    "*.min.js",
    "tests/**"
]
```

## Adjusting Timeout

For slower machines, increase in `configuration.toml`:
```toml
[performance]
llm_timeout = 300  # 5 minutes
```
