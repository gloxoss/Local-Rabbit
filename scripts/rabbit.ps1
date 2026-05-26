<#
.SYNOPSIS
Unified CLI for Local CodeRabbit
Controls setup, startup, and utilities.

.EXAMPLE
.\scripts\rabbit.ps1 start
.\scripts\rabbit.ps1 setup
.\scripts\rabbit.ps1 audit
#>

param(
    [Parameter(Mandatory=$false, Position=0)]
    [ValidateSet("start", "setup", "audit", "stop", "help")]
    [string]$Command = "help",

    [Parameter(Mandatory=$false, Position=1)]
    [string]$Target = "."
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$PythonCmd = "python"

function Show-Logo {
    Write-Host ""
    Write-Host "  🐰 LOCAL CODERABBIT CLI" -ForegroundColor Cyan
    Write-Host "  =======================" -ForegroundColor Cyan
    Write-Host ""
}

function Run-Setup {
    Write-Host "[CLI] Running Setup..." -ForegroundColor Cyan
    & "$ScriptDir\setup.ps1"
}

function Load-Env {
    $EnvPath = Join-Path $RootDir ".env"
    if (Test-Path $EnvPath) {
        Write-Host "[Env] Loading .env..." -ForegroundColor Gray
        Get-Content $EnvPath | ForEach-Object {
            if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
                $name = $Matches[1].Trim()
                $value = $Matches[2].Trim()
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
}

function Run-Start {
    param($Path)
    Load-Env
    Write-Host "[CLI] Starting Local CodeRabbit..." -ForegroundColor Cyan
    
    # Check if Docker is needed/running (optional for local mode but good check)
    if (Test-Path "$RootDir\docker-compose.yml") {
        # Optional: Check docker status if we rely on it
    }

    # Start Dashboard Server in background
    Write-Host "[CLI] Starting Dashboard (Background)..." -ForegroundColor Gray
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Process $PythonCmd -ArgumentList "scripts/server.py" -WorkingDirectory $RootDir -WindowStyle Hidden

    # run watcher
    Write-Host "[CLI] Launching Watcher..." -ForegroundColor Green
    Set-Location $RootDir
    & $PythonCmd -u scripts/watcher.py $Path
}

function Run-Audit {
    Write-Host "[CLI] Running Codebase Audit..." -ForegroundColor Cyan
    Write-Host "TODO: Implement audit runner logic here or call audit script if exists." -ForegroundColor Yellow
    # For now, just list files
    Get-ChildItem $RootDir -Recurse | Measure-Object | ForEach-Object { Write-Host "Files: $($_.Count)" }
}

function Stop-All {
    Write-Host "[CLI] Stopping all services..." -ForegroundColor Yellow
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "[CLI] Stopped." -ForegroundColor Green
}

function Show-Help {
    Show-Logo
    Write-Host "Usage: .\scripts\rabbit.ps1 [command] [target]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start   - Start the dashboard and watcher (default target: current dir)"
    Write-Host "  setup   - Run the initial setup script"
    Write-Host "  audit   - Run usage/health audit"
    Write-Host "  stop    - Stop background services (Dashboard)"
    Write-Host "  help    - Show this message"
    Write-Host ""
}

# Main Dispatch
switch ($Command) {
    "start" { Run-Start -Path $Target }
    "setup" { Run-Setup }
    "audit" { Run-Audit }
    "stop"  { Stop-All }
    "help"  { Show-Help }
    Default { Show-Help }
}
