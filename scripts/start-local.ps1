# LOCAL CODERABBIT - START WATCHER (LOCAL MODE)
# Runs watcher directly on your machine without Docker

param(
    [Parameter(Position=0)]
    [string]$WatchPath = "."
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LOCAL CODERABBIT v3.0 - Local Mode" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Resolve to absolute path
$AbsPath = Resolve-Path $WatchPath -ErrorAction SilentlyContinue
if (-not $AbsPath) {
    Write-Host "[ERROR] Path not found: $WatchPath" -ForegroundColor Red
    exit 1
}
Write-Host "[TARGET] $AbsPath" -ForegroundColor Gray

# Check for .agent folder
$AgentPath = Join-Path $AbsPath ".agent"
if (Test-Path $AgentPath) {
    Write-Host "[AGENT]  Found .agent folder - rules will be loaded" -ForegroundColor Green
} else {
    Write-Host "[AGENT]  No .agent folder - using default rules" -ForegroundColor Yellow
}

# Check for custom prompts
$PromptsPath = Join-Path $AbsPath "prompts.json"
if (Test-Path $PromptsPath) {
    Write-Host "[PROMPT] Custom prompts.json found" -ForegroundColor Green
} else {
    Write-Host "[PROMPT] Using default prompts" -ForegroundColor Yellow
}

# Check for config
$ConfigPath = Join-Path $AbsPath "config.json"
if (Test-Path $ConfigPath) {
    Write-Host "[CONFIG] config.json found" -ForegroundColor Green
} else {
    Write-Host "[CONFIG] Using default configuration" -ForegroundColor Yellow
}

# Load .env file if exists
$EnvPath = Join-Path $AbsPath ".env"
if (Test-Path $EnvPath) {
    Write-Host "[ENV] Loading .env file..." -ForegroundColor Green
    Get-Content $EnvPath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $Matches[1].Trim()
            $value = $Matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Host "[ENV] No .env file found" -ForegroundColor Yellow
}

Write-Host ""

# Set encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check if openai package is installed
Write-Host "[SETUP] Checking dependencies..." -ForegroundColor Gray
$hasOpenAI = python -c "import openai" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[SETUP] Installing openai package..." -ForegroundColor Yellow
    pip install openai -q
}

# Check Z.AI API key
if (-not $env:ZAI_API_KEY) {
    Write-Host "[WARN] ZAI_API_KEY not set in environment" -ForegroundColor Yellow
    Write-Host "       Set it with: `$env:ZAI_API_KEY = 'your-key'" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[OK] Starting watcher with Z.AI..." -ForegroundColor Green
Write-Host "     Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ("-" * 50) -ForegroundColor Gray
Write-Host ""

# Set environment for Z.AI (Force update)
$env:OPENAI_API_KEY = $env:ZAI_API_KEY
if ($env:ZAI_API_BASE) {
    $env:OPENAI_API_BASE = $env:ZAI_API_BASE
} else {
    $env:OPENAI_API_BASE = "https://open.bigmodel.cn/api/paas/v4/"
}

# Start Dashboard Server (Background Process)
Write-Host "[SETUP] Starting Dashboard Server..." -ForegroundColor Gray
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue
Start-Process python -ArgumentList "scripts/server.py" -WorkingDirectory $AbsPath -WindowStyle Hidden

# Run watcher directly
Set-Location $AbsPath
python -u scripts/watcher.py . > watcher.log 2>&1
