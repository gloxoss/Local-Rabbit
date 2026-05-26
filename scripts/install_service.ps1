# =====================================================
# Local Rabbit Orchestrator - Windows Service Installer
# =====================================================
#
# Usage:
#   .\scripts\install_service.ps1 -Install      # Register as Scheduled Task
#   .\scripts\install_service.ps1 -Uninstall     # Remove Scheduled Task
#   .\scripts\install_service.ps1 -Status        # Check if running
#   .\scripts\install_service.ps1 -Start         # Start the orchestrator
#   .\scripts\install_service.ps1 -Stop          # Stop the orchestrator
#

param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Status,
    [switch]$Start,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$TaskName = "LocalRabbit-Orchestrator"
$ProjectRoot = (Get-Item $PSScriptRoot).Parent.FullName
$PythonScript = Join-Path $ProjectRoot "scripts\orchestrator.py"
$LogFile = Join-Path $ProjectRoot "data\orchestrator.log"

# Find Python
$Python = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $Python) {
    $Python = Get-Command python3 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}
if (-not $Python) {
    Write-Host "Error: Python not found in PATH" -ForegroundColor Red
    exit 1
}

function Show-Banner {
    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host "  LOCAL RABBIT - Service Manager" -ForegroundColor White
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Install-OrchestratorTask {
    Show-Banner
    Write-Host "Installing $TaskName as Scheduled Task..." -ForegroundColor Yellow

    # Check if task already exists
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "  Task already exists. Updating..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    try {
        # Create the action (run orchestrator.py)
        $action = New-ScheduledTaskAction `
            -Execute $Python `
            -Argument "`"$PythonScript`"" `
            -WorkingDirectory $ProjectRoot

        # Trigger: at logon
        $trigger = New-ScheduledTaskTrigger -AtLogon

        # Settings: restart on failure, don't stop on idle
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 1) `
            -StartWhenAvailable `
            -ExecutionTimeLimit (New-TimeSpan -Days 365)

        # Register
        Register-ScheduledTask `
            -TaskName $TaskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Description "Local Rabbit 24/7 AI Code Auditor" `
            -RunLevel Highest

        Write-Host ""
        Write-Host "  Installed successfully!" -ForegroundColor Green
        Write-Host "  Task Name:  $TaskName" -ForegroundColor White
        Write-Host "  Python:     $Python" -ForegroundColor Gray
        Write-Host "  Script:     $PythonScript" -ForegroundColor Gray
        Write-Host "  Log File:   $LogFile" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  The orchestrator will start automatically on next login." -ForegroundColor Cyan
        Write-Host "  To start now: .\scripts\install_service.ps1 -Start" -ForegroundColor Cyan
    }
    catch {
        Write-Host ""
        Write-Host "  Failed to register Scheduled Task." -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Falling back to Startup shortcut..." -ForegroundColor Yellow
        Install-StartupShortcut
    }
}

function Install-StartupShortcut {
    $startupFolder = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupFolder "LocalRabbit-Orchestrator.bat"

    $batContent = @"
@echo off
cd /d "$ProjectRoot"
start /min "" "$Python" "$PythonScript"
"@

    Set-Content -Path $shortcutPath -Value $batContent -Encoding ASCII
    Write-Host "  Startup shortcut created: $shortcutPath" -ForegroundColor Green
    Write-Host "  The orchestrator will start on next login." -ForegroundColor Cyan
}

function Uninstall-OrchestratorTask {
    Show-Banner
    Write-Host "Uninstalling $TaskName..." -ForegroundColor Yellow

    # Remove Scheduled Task
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "  Scheduled Task removed." -ForegroundColor Green
    } else {
        Write-Host "  No Scheduled Task found." -ForegroundColor Gray
    }

    # Remove Startup shortcut
    $startupFolder = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupFolder "LocalRabbit-Orchestrator.bat"
    if (Test-Path $shortcutPath) {
        Remove-Item $shortcutPath -Force
        Write-Host "  Startup shortcut removed." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "  Uninstalled successfully." -ForegroundColor Green
}

function Get-OrchestratorStatus {
    Show-Banner
    Write-Host "Status Check:" -ForegroundColor Cyan
    Write-Host ""

    # Check Scheduled Task
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        $taskInfo = $task | Get-ScheduledTaskInfo
        $stateColor = if ($task.State -eq "Running") { "Green" } else { "Yellow" }
        Write-Host "  Scheduled Task: $($task.State)" -ForegroundColor $stateColor
        Write-Host "  Last Run:       $($taskInfo.LastRunTime)" -ForegroundColor Gray
        Write-Host "  Next Run:       $($taskInfo.NextRunTime)" -ForegroundColor Gray
    } else {
        Write-Host "  Scheduled Task: Not installed" -ForegroundColor Red
    }

    # Check running process
    $procs = Get-Process python*, python3* -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*orchestrator*"
    }
    if ($procs) {
        Write-Host "  Process:        Running (PID: $($procs.Id -join ', '))" -ForegroundColor Green
    } else {
        Write-Host "  Process:        Not running" -ForegroundColor Yellow
    }

    # Check log file
    if (Test-Path $LogFile) {
        $logInfo = Get-Item $LogFile
        Write-Host "  Log File:       $($logInfo.Length / 1KB) KB ($($logInfo.LastWriteTime))" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  Last 5 log lines:" -ForegroundColor Cyan
        Get-Content $LogFile -Tail 5 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    } else {
        Write-Host "  Log File:       Not found" -ForegroundColor Yellow
    }
    Write-Host ""
}

function Start-Orchestrator {
    Show-Banner
    Write-Host "Starting orchestrator..." -ForegroundColor Yellow

    # Try Scheduled Task first
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "  Started via Scheduled Task." -ForegroundColor Green
    } else {
        # Start directly
        Start-Process -FilePath $Python -ArgumentList "`"$PythonScript`"" `
            -WorkingDirectory $ProjectRoot -WindowStyle Minimized
        Write-Host "  Started as background process." -ForegroundColor Green
    }
    Write-Host "  Log: $LogFile" -ForegroundColor Gray
}

function Stop-Orchestrator {
    Show-Banner
    Write-Host "Stopping orchestrator..." -ForegroundColor Yellow

    # Stop Scheduled Task
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task -and $task.State -eq "Running") {
        Stop-ScheduledTask -TaskName $TaskName
        Write-Host "  Stopped Scheduled Task." -ForegroundColor Green
    }

    # Kill any running process
    $procs = Get-Process python*, python3* -ErrorAction SilentlyContinue | Where-Object {
        try { $_.CommandLine -like "*orchestrator*" } catch { $false }
    }
    if ($procs) {
        $procs | Stop-Process -Force
        Write-Host "  Killed orchestrator process(es)." -ForegroundColor Green
    } else {
        Write-Host "  No running orchestrator process found." -ForegroundColor Yellow
    }
}

# ─── Main ────────────────────────────────────────────────────────────────────

if ($Install) { Install-OrchestratorTask }
elseif ($Uninstall) { Uninstall-OrchestratorTask }
elseif ($Status) { Get-OrchestratorStatus }
elseif ($Start) { Start-Orchestrator }
elseif ($Stop) { Stop-Orchestrator }
else {
    Show-Banner
    Write-Host "  Usage:" -ForegroundColor White
    Write-Host "    .\scripts\install_service.ps1 -Install    # Register as Scheduled Task" -ForegroundColor Gray
    Write-Host "    .\scripts\install_service.ps1 -Uninstall  # Remove Scheduled Task" -ForegroundColor Gray
    Write-Host "    .\scripts\install_service.ps1 -Status     # Check status" -ForegroundColor Gray
    Write-Host "    .\scripts\install_service.ps1 -Start      # Start orchestrator" -ForegroundColor Gray
    Write-Host "    .\scripts\install_service.ps1 -Stop       # Stop orchestrator" -ForegroundColor Gray
    Write-Host ""
}
