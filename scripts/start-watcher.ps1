# LOCAL CODERABBIT - START WATCHER WITH NOTIFICATIONS
# Runs watcher and shows Windows toast notifications on critical issues

param(
    [Parameter(Position=0)]
    [string]$WatchPath = "."
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LOCAL CODERABBIT v3.0 - With Notifications" -ForegroundColor Cyan  
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
Write-Host ""

# Check container
$container = docker ps --filter "name=local-coderabbit-zai-cli" --format "{{.Names}}" 2>$null
if (-not $container) {
    Write-Host "[ERROR] Z.AI CLI container not running." -ForegroundColor Red
    Write-Host "        Run: cd 'c:\Users\zakio\Desktop\Work\Local Rabbit'; docker compose up -d" -ForegroundColor Yellow
    exit 1
}

# Ensure OpenAI SDK
Write-Host "[SETUP] Installing dependencies..." -ForegroundColor Gray
docker exec local-coderabbit-zai-cli pip install openai -q 2>$null

Write-Host "[OK] Starting watcher with notifications..." -ForegroundColor Green
Write-Host "     Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ("-" * 50) -ForegroundColor Gray

# Function to show Windows notification
function Show-Notification {
    param([string]$Title, [string]$Message)
    
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        
        $template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">$Title</text>
            <text id="2">$Message</text>
        </binding>
    </visual>
</toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Local CodeRabbit").Show($toast)
    }
    catch {
        # Fallback to BurntToast if available
        if (Get-Command -Name New-BurntToastNotification -ErrorAction SilentlyContinue) {
            New-BurntToastNotification -Text $Title, $Message
        }
    }
}

# Run watcher and monitor output for [NOTIFY] markers
$output = docker exec -it `
    -e OPENAI_API_KEY=$env:ZAI_API_KEY `
    -e OPENAI_API_BASE=$env:ZAI_API_BASE `
    local-coderabbit-zai-cli python /workspace/scripts/watcher.py /workspace 2>&1

# Process output line by line
$output | ForEach-Object {
    $line = $_
    Write-Host $line
    
    # Check for notification marker
    if ($line -match '\[NOTIFY\](.+):(.+)') {
        $title = $Matches[1].Trim()
        $message = $Matches[2].Trim()
        Show-Notification -Title $title -Message $message
    }
}
