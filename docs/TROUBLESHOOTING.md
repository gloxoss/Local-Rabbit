# Troubleshooting Guide

## Common Issues

### "Ollama connection refused"
```powershell
docker-compose ps                    # Check status
docker-compose restart ollama        # Restart
docker-compose logs ollama           # View logs
curl http://localhost:11434/api/tags # Test endpoint
```

### "Model not found"
```powershell
docker exec local-coderabbit-ollama ollama list                  # List models
docker exec local-coderabbit-ollama ollama pull deepseek-coder-v2 # Pull model
docker-compose restart pr-agent                                   # Restart
```

### "Review not posting to GitHub"
```powershell
docker-compose logs pr-agent | Select-Object -Last 50    # Check logs

# Verify token works
$token = (Get-Content .env | Select-String "GITHUB_TOKEN=").ToString().Split("=")[1]
Invoke-WebRequest -Uri "https://api.github.com/user" -Headers @{Authorization="token $token"}

# Test manual trigger
.\scripts\test-review.ps1 myuser/myrepo 1
```

### "PR-Agent not starting"
```powershell
docker-compose logs pr-agent         # Check errors
docker-compose down                  # Stop all
docker-compose up -d                 # Restart
```

### "Out of memory"
Reduce model size in `.env`:
```
OLLAMA_MODEL=qwen2.5-coder   # 7B model, uses ~5GB RAM
```

## Health Check Commands
```powershell
# System status
docker-compose ps

# Ollama API
Invoke-WebRequest http://localhost:11434/api/tags

# PR-Agent
Invoke-WebRequest http://localhost:3000/

# Resource usage
docker stats --no-stream
```
