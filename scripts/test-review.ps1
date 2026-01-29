# LOCAL CODERABBIT - TEST REVIEW SCRIPT
# Usage: .\scripts\test-review.ps1 username/repo 42

param(
    [Parameter(Mandatory=$true, Position=0)][string]$Repo,
    [Parameter(Mandatory=$true, Position=1)][int]$PrNumber,
    [Parameter(Position=2)][ValidateSet("review","describe","improve")][string]$Action = "review"
)

Write-Host "[TEST] Running PR-Agent $Action on $Repo #$PrNumber..." -ForegroundColor Cyan

# Check if container is running
$container = docker ps --filter "name=local-coderabbit-pr-agent" --format "{{.Names}}" 2>$null
if (-not $container) {
    Write-Host "[ERROR] PR-Agent container not running. Run: docker compose up -d" -ForegroundColor Red
    exit 1
}

# Run PR-Agent CLI review
Write-Host "[RUN] Triggering $Action..." -ForegroundColor Yellow
$prUrl = "https://github.com/$Repo/pull/$PrNumber"

docker exec local-coderabbit-pr-agent python -m pr_agent.cli --pr_url=$prUrl $Action

Write-Host "`n[DONE] Check PR: $prUrl" -ForegroundColor Green
