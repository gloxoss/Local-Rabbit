# LOCAL CODERABBIT - SETUP OFFLINE MODE (OLLAMA)
# Pulls the recommended model and configures for offline use

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setting Up Offline Mode (Ollama)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Ollama container with offline profile
Write-Host "[1/3] Starting Ollama container..." -ForegroundColor Yellow
docker compose --profile offline up -d ollama

# Wait for Ollama to be ready
Write-Host "[2/3] Waiting for Ollama to start..." -ForegroundColor Yellow
$maxWait = 30
$waited = 0
do {
    Start-Sleep -Seconds 2
    $waited += 2
    $health = docker exec local-coderabbit-ollama ollama list 2>$null
} while (-not $health -and $waited -lt $maxWait)

if ($waited -ge $maxWait) {
    Write-Host "[ERROR] Ollama failed to start" -ForegroundColor Red
    exit 1
}

# Pull recommended model
Write-Host "[3/3] Pulling qwen2.5-coder model (this may take a few minutes)..." -ForegroundColor Yellow
docker exec -it local-coderabbit-ollama ollama pull qwen2.5-coder

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Offline Mode Ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Ollama is running at: http://localhost:11434" -ForegroundColor Gray
Write-Host ""
Write-Host "To use offline mode, set these environment variables:" -ForegroundColor Yellow
Write-Host '  $env:OPENAI_API_BASE = "http://localhost:11434/v1"' -ForegroundColor White
Write-Host '  $env:OPENAI_API_KEY = "ollama"' -ForegroundColor White
Write-Host '  $env:ZAI_MODEL = "qwen2.5-coder"' -ForegroundColor White
Write-Host ""
Write-Host "Or the watcher will automatically fallback to Ollama if Z.AI fails." -ForegroundColor Gray
