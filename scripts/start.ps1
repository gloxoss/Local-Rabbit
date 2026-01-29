# LOCAL CODERABBIT - START SCRIPT
$ErrorActionPreference = "Stop"

Write-Host "[START] Starting Z.AI CodeRabbit System..." -ForegroundColor Cyan

# Validate
if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] .env not found. Run .\scripts\setup.ps1 first" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "pr-agent\.secrets.toml")) {
    Write-Host "[ERROR] secrets.toml not found. Run .\scripts\setup.ps1 first" -ForegroundColor Red
    exit 1
}

# Start services
Write-Host "`n[START] Docker Compose services..." -ForegroundColor Yellow
docker compose up -d

# Quick status check
Write-Host "`n[CHECK] Container status..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$prAgent = docker ps --filter "name=local-coderabbit-pr-agent" --format "{{.Status}}" 2>$null
$zaiCli = docker ps --filter "name=local-coderabbit-zai-cli" --format "{{.Status}}" 2>$null

if ($prAgent) {
    Write-Host "  [OK] PR-Agent: $prAgent" -ForegroundColor Green
} else {
    Write-Host "  [WARN] PR-Agent not running" -ForegroundColor Yellow
}

if ($zaiCli) {
    Write-Host "  [OK] Z.AI CLI: $zaiCli" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Z.AI CLI not running" -ForegroundColor Yellow
}

# Summary
Write-Host "`n[DONE] System Started!" -ForegroundColor Green
Write-Host "`nAgents:" -ForegroundColor White
Write-Host "  PR-Agent:  http://localhost:3000" -ForegroundColor Gray
Write-Host "  Z.AI CLI:  docker exec -it local-coderabbit-zai-cli sh" -ForegroundColor Gray

Write-Host "`nLogs:" -ForegroundColor White
Write-Host "  docker compose logs -f pr-agent" -ForegroundColor Gray
Write-Host "  docker compose logs -f zai-cli" -ForegroundColor Gray
