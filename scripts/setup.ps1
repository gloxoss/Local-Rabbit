# LOCAL CODERABBIT - SETUP SCRIPT
$ErrorActionPreference = "Stop"

Write-Host "[SETUP] Initializing Z.AI CodeRabbit System..." -ForegroundColor Cyan

# Check Docker
Write-Host "`n[CHECK] Prerequisites..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    Write-Host "  [OK] Docker installed" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Docker not installed" -ForegroundColor Red
    exit 1
}

# Check if Docker daemon is running
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker not running" }
    Write-Host "  [OK] Docker daemon running" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Docker Desktop is not running!" -ForegroundColor Red
    Write-Host "         Start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

try {
    docker compose version | Out-Null
    Write-Host "  [OK] Docker Compose installed" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Docker Compose not installed" -ForegroundColor Red
    exit 1
}

# Check .env
Write-Host "`n[CHECK] Configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "  [WARN] .env not found, copying template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

$envContent = Get-Content ".env" -Raw
$missingKeys = @()

if ($envContent -match "ghp_REPLACE|ghp_YOUR") { $missingKeys += "GITHUB_TOKEN" }
if ($envContent -match "z-ai-REPLACE") { $missingKeys += "ZAI_API_KEY" }

if ($missingKeys.Count -gt 0) {
    Write-Host "  [ERROR] Missing API keys in .env:" -ForegroundColor Red
    $missingKeys | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
    exit 1
}
Write-Host "  [OK] API keys configured" -ForegroundColor Green

# Create secrets file
Write-Host "`n[SETUP] Generating PR-Agent secrets..." -ForegroundColor Yellow

$githubToken = ""
$webhookSecret = ""
$zaiKey = ""
$zaiBase = ""

Get-Content ".env" | ForEach-Object {
    if ($_ -match "^GITHUB_TOKEN=(.+)$") { $githubToken = $matches[1] }
    if ($_ -match "^GITHUB_WEBHOOK_SECRET=(.+)$") { $webhookSecret = $matches[1] }
    if ($_ -match "^ZAI_API_KEY=(.+)$") { $zaiKey = $matches[1] }
    if ($_ -match "^ZAI_API_BASE=(.+)$") { $zaiBase = $matches[1] }
}

$secretsContent = @"
[github]
user_token = "$githubToken"
webhook_secret = "$webhookSecret"

[openai]
key = "$zaiKey"
api_base = "$zaiBase"
api_type = "openai"
"@

Set-Content -Path "pr-agent\.secrets.toml" -Value $secretsContent -Encoding UTF8
Write-Host "  [OK] Created pr-agent/.secrets.toml" -ForegroundColor Green

# Docker setup
Write-Host "`n[SETUP] Docker infrastructure..." -ForegroundColor Yellow
docker network create local-coderabbit-network 2>$null
Write-Host "  [OK] Network ready" -ForegroundColor Green

# Pull images
Write-Host "`n[SETUP] Pulling Docker images..." -ForegroundColor Yellow
docker compose pull
Write-Host "  [OK] Images pulled" -ForegroundColor Green

Write-Host "`n[DONE] Setup complete!" -ForegroundColor Green
Write-Host "Next: .\scripts\start.ps1" -ForegroundColor Cyan
