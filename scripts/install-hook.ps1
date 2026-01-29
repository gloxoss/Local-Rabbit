# LOCAL CODERABBIT - INSTALL PRE-COMMIT HOOK
# Installs the AI code review pre-commit hook into a git repository

param(
    [Parameter(Position=0)]
    [string]$RepoPath = "."
)

$RepoPath = Resolve-Path $RepoPath -ErrorAction Stop
$GitDir = Join-Path $RepoPath ".git"
$HooksDir = Join-Path $GitDir "hooks"

if (-not (Test-Path $GitDir)) {
    Write-Host "[ERROR] Not a git repository: $RepoPath" -ForegroundColor Red
    exit 1
}

# Create hooks directory if it doesn't exist
if (-not (Test-Path $HooksDir)) {
    New-Item -ItemType Directory -Path $HooksDir | Out-Null
}

# Create the pre-commit hook
$HookScript = @'
#!/bin/sh
# Local CodeRabbit Pre-Commit Hook
# Requires: pip install openai

# Check if we have API access configured
if [ -z "$ZAI_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ No AI API key configured, skipping review"
    exit 0
fi

# Run the Python pre-commit script
python "$(dirname "$0")/../../scripts/pre-commit.py"
exit $?
'@

$HookPath = Join-Path $HooksDir "pre-commit"
$HookScript | Out-File -FilePath $HookPath -Encoding utf8 -NoNewline

# Copy our pre-commit.py to the repo's scripts folder
$ScriptsDir = Join-Path $RepoPath "scripts"
if (-not (Test-Path $ScriptsDir)) {
    New-Item -ItemType Directory -Path $ScriptsDir | Out-Null
}

$SourceScript = Join-Path $PSScriptRoot "pre-commit.py"
$DestScript = Join-Path $ScriptsDir "pre-commit.py"

if (Test-Path $SourceScript) {
    Copy-Item $SourceScript $DestScript -Force
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Pre-Commit Hook Installed!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[HOOK]   $HookPath" -ForegroundColor Gray
Write-Host "[SCRIPT] $DestScript" -ForegroundColor Gray
Write-Host ""
Write-Host "The hook will run on every commit and:" -ForegroundColor Green
Write-Host "  • Review staged code files" -ForegroundColor White
Write-Host "  • Block commits with critical issues" -ForegroundColor White
Write-Host ""
Write-Host "To skip temporarily: git commit --no-verify" -ForegroundColor Yellow
Write-Host ""

# Ensure the hook is executable (for WSL/Git Bash)
try {
    icacls $HookPath /grant "Everyone:(RX)" 2>$null | Out-Null
} catch {}

Write-Host "✅ Done!" -ForegroundColor Green
