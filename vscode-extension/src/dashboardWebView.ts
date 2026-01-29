import * as vscode from 'vscode';

/**
 * Dashboard WebView provider for the sidebar.
 * Shows health stats, learning info, and quick actions.
 * Enhanced with professional UI/UX following VS Code design language.
 */
export class DashboardViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'localCoderabbit.dashboard';

    private _view?: vscode.WebviewView;
    private _serverUrl: string;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        serverUrl: string
    ) {
        this._serverUrl = serverUrl;
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'refresh':
                    await this.refresh();
                    break;
                case 'resetLearning':
                    await this._resetLearning();
                    break;
                case 'openSettings':
                    vscode.commands.executeCommand('workbench.action.openSettings', 'localCoderabbit');
                    break;
                case 'reviewFile':
                    vscode.commands.executeCommand('localCoderabbit.reviewFile');
                    break;
            }
        });

        // Initial data load
        this.refresh();
    }

    /**
     * Refresh dashboard data
     */
    public async refresh() {
        if (!this._view) return;

        try {
            const [health, feedbackStats, models] = await Promise.all([
                this._fetchApi('/api/health'),
                this._fetchApi('/api/feedback/stats').catch(() => ({ total_feedback: 0, acceptance_rate: 0, learning_active: false })),
                this._fetchApi('/api/models').catch(() => ({ available: [] }))
            ]);

            this._view.webview.postMessage({
                type: 'update',
                data: {
                    health,
                    feedback: feedbackStats,
                    models
                }
            });
        } catch (error) {
            this._view.webview.postMessage({
                type: 'error',
                message: 'Failed to connect to server'
            });
        }
    }

    /**
     * Reset learning data
     */
    private async _resetLearning() {
        try {
            await this._fetchApi('/api/feedback/reset', 'DELETE');
            vscode.window.showInformationMessage('Learning data reset successfully');
            await this.refresh();
        } catch (error) {
            vscode.window.showErrorMessage('Failed to reset learning data');
        }
    }

    /**
     * Fetch from API
     */
    private async _fetchApi(path: string, method: string = 'GET'): Promise<any> {
        const http = require('http');
        const url = new URL(this._serverUrl);
        const port = url.port ? parseInt(url.port) : 8765;

        return new Promise((resolve, reject) => {
            const req = http.request({
                hostname: url.hostname,
                port: port,
                path: path,
                method: method,
                timeout: 5000
            }, (res: any) => {
                let data = '';
                res.on('data', (chunk: string) => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch {
                        reject(new Error('Invalid JSON'));
                    }
                });
            });

            req.on('error', reject);
            req.on('timeout', () => {
                req.destroy();
                reject(new Error('Request timeout'));
            });

            req.end();
        });
    }

    /**
     * Generate HTML for the webview with enhanced UI
     */
    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeRabbit Dashboard</title>
    <style>
        :root {
            --spacing-xs: 4px;
            --spacing-sm: 8px;
            --spacing-md: 12px;
            --spacing-lg: 16px;
            --radius-sm: 4px;
            --radius-md: 6px;
            --transition-fast: 150ms ease;
            --transition-normal: 200ms ease;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: var(--vscode-font-family);
            font-size: 12px;
            color: var(--vscode-foreground);
            background: transparent;
            padding: var(--spacing-md);
            line-height: 1.4;
        }
        
        /* Section styling */
        .section {
            margin-bottom: var(--spacing-lg);
        }
        
        .section-header {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            margin-bottom: var(--spacing-sm);
        }
        
        .section-icon {
            width: 14px;
            height: 14px;
            opacity: 0.7;
        }
        
        .section-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--vscode-descriptionForeground);
            letter-spacing: 0.5px;
        }
        
        .section-badge {
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 10px;
            font-weight: 500;
            margin-left: auto;
        }
        
        .badge-active {
            background: rgba(74, 222, 128, 0.15);
            color: #4ade80;
        }
        
        .badge-inactive {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
        }
        
        /* Stat rows */
        .stat-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--spacing-xs) 0;
        }
        
        .stat-label {
            font-size: 12px;
            color: var(--vscode-foreground);
            opacity: 0.9;
        }
        
        .stat-value {
            font-weight: 600;
            font-size: 12px;
            font-variant-numeric: tabular-nums;
        }
        
        /* Progress bar */
        .progress-container {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            padding: var(--spacing-xs) 0;
        }
        
        .progress-label {
            font-size: 12px;
            opacity: 0.9;
            min-width: 40px;
        }
        
        .progress-bar {
            flex: 1;
            height: 6px;
            background: var(--vscode-input-background);
            border-radius: 3px;
            overflow: hidden;
            position: relative;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }
        
        .progress-fill::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            animation: shimmer 2s infinite;
        }
        
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        
        .progress-good { background: linear-gradient(90deg, #22c55e, #4ade80); }
        .progress-warning { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .progress-critical { background: linear-gradient(90deg, #ef4444, #f87171); }
        
        .progress-value {
            font-weight: 600;
            font-size: 13px;
            min-width: 28px;
            text-align: right;
            font-variant-numeric: tabular-nums;
        }
        
        /* Model status */
        .model-card {
            background: var(--vscode-input-background);
            border-radius: var(--radius-md);
            padding: var(--spacing-md);
            border: 1px solid var(--vscode-input-border, transparent);
        }
        
        .model-status {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            margin-bottom: var(--spacing-sm);
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            position: relative;
        }
        
        .status-indicator.connected {
            background: #22c55e;
            box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.2);
        }
        
        .status-indicator.connected::before {
            content: '';
            position: absolute;
            inset: -2px;
            border-radius: 50%;
            border: 2px solid #22c55e;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 0.5; transform: scale(1); }
            50% { opacity: 0; transform: scale(1.5); }
        }
        
        .status-indicator.disconnected {
            background: #ef4444;
        }
        
        .status-text {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
        }
        
        .model-name {
            font-size: 12px;
            font-weight: 500;
            color: var(--vscode-foreground);
            word-break: break-word;
        }
        
        .model-provider {
            font-size: 10px;
            color: var(--vscode-descriptionForeground);
            margin-top: 2px;
        }
        
        /* Buttons */
        .actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--spacing-sm);
            margin-top: var(--spacing-md);
        }
        
        .actions-full {
            grid-template-columns: 1fr;
        }
        
        button {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 8px 12px;
            font-size: 11px;
            font-weight: 500;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            transition: all var(--transition-fast);
        }
        
        button:hover {
            background: var(--vscode-button-secondaryHoverBackground);
            transform: translateY(-1px);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button svg {
            width: 14px;
            height: 14px;
            opacity: 0.8;
        }
        
        button.primary {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }
        
        button.primary:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        button.danger {
            color: #f87171;
        }
        
        button.danger:hover {
            background: rgba(239, 68, 68, 0.1);
        }
        
        /* Loading & Error states */
        .loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 32px 16px;
            gap: var(--spacing-sm);
        }
        
        .spinner {
            width: 24px;
            height: 24px;
            border: 2px solid var(--vscode-input-background);
            border-top-color: var(--vscode-button-background);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .loading-text {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
        }
        
        .error {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 24px 16px;
            gap: var(--spacing-sm);
        }
        
        .error-icon {
            width: 32px;
            height: 32px;
            color: var(--vscode-errorForeground);
            opacity: 0.7;
        }
        
        .error-text {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
        }
        
        /* Divider */
        .divider {
            height: 1px;
            background: var(--vscode-widget-border, var(--vscode-input-border));
            margin: var(--spacing-lg) 0;
            opacity: 0.5;
        }
        
        /* Quick action card */
        .quick-action {
            background: var(--vscode-input-background);
            border-radius: var(--radius-md);
            padding: var(--spacing-md);
            cursor: pointer;
            transition: all var(--transition-fast);
            border: 1px solid transparent;
        }
        
        .quick-action:hover {
            background: var(--vscode-list-hoverBackground);
            border-color: var(--vscode-focusBorder);
        }
        
        .quick-action-title {
            font-size: 12px;
            font-weight: 500;
            margin-bottom: 4px;
        }
        
        .quick-action-desc {
            font-size: 10px;
            color: var(--vscode-descriptionForeground);
        }
    </style>
</head>
<body>
    <div id="content">
        <div class="loading">
            <div class="spinner"></div>
            <span class="loading-text">Connecting...</span>
        </div>
    </div>
    
    <script>
        const vscode = acquireVsCodeApi();
        
        // SVG Icons (no emojis per UI/UX guidelines)
        const icons = {
            health: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
            learning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>',
            cpu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/></svg>',
            refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>',
            settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>',
            trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2"/></svg>',
            alertCircle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
            play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
        };
        
        // Handle messages from extension
        window.addEventListener('message', event => {
            const message = event.data;
            
            if (message.type === 'update') {
                renderDashboard(message.data);
            } else if (message.type === 'error') {
                renderError(message.message);
            }
        });
        
        function renderDashboard(data) {
            const { health, feedback, models } = data;
            
            // Calculate health score
            const healthScore = feedback && feedback.total_feedback > 0 
                ? Math.round(feedback.acceptance_rate * 100) 
                : 85;
            
            const healthClass = healthScore >= 80 ? 'progress-good' : 
                               healthScore >= 60 ? 'progress-warning' : 'progress-critical';
            
            const isConnected = !!health;
            const modelName = health?.model || 'Unknown';
            const provider = health?.provider || '';
            
            const html = \`
                <!-- Health Section -->
                <div class="section">
                    <div class="section-header">
                        <span class="section-icon">\${icons.health}</span>
                        <span class="section-title">Health</span>
                    </div>
                    <div class="progress-container">
                        <span class="progress-label">Score</span>
                        <div class="progress-bar">
                            <div class="progress-fill \${healthClass}" style="width: \${healthScore}%"></div>
                        </div>
                        <span class="progress-value">\${healthScore}</span>
                    </div>
                </div>
                
                <!-- Learning Section -->
                <div class="section">
                    <div class="section-header">
                        <span class="section-icon">\${icons.learning}</span>
                        <span class="section-title">Learning</span>
                        <span class="section-badge \${feedback?.learning_active ? 'badge-active' : 'badge-inactive'}">
                            \${feedback?.learning_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Feedback given</span>
                        <span class="stat-value">\${feedback?.total_feedback || 0}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Acceptance rate</span>
                        <span class="stat-value">\${feedback ? Math.round(feedback.acceptance_rate * 100) : 0}%</span>
                    </div>
                </div>
                
                <div class="divider"></div>
                
                <!-- Model Section -->
                <div class="section">
                    <div class="section-header">
                        <span class="section-icon">\${icons.cpu}</span>
                        <span class="section-title">Model</span>
                    </div>
                    <div class="model-card">
                        <div class="model-status">
                            <div class="status-indicator \${isConnected ? 'connected' : 'disconnected'}"></div>
                            <span class="status-text">\${isConnected ? 'Connected' : 'Disconnected'}</span>
                        </div>
                        <div class="model-name">\${modelName}</div>
                        \${provider ? \`<div class="model-provider">via \${provider}</div>\` : ''}
                    </div>
                </div>
                
                <!-- Actions -->
                <div class="actions">
                    <button onclick="refresh()">
                        \${icons.refresh}
                        Refresh
                    </button>
                    <button onclick="openSettings()">
                        \${icons.settings}
                        Settings
                    </button>
                </div>
                
                <div class="actions actions-full" style="margin-top: 6px;">
                    <button class="danger" onclick="resetLearning()">
                        \${icons.trash}
                        Reset Learning Data
                    </button>
                </div>
            \`;
            
            document.getElementById('content').innerHTML = html;
        }
        
        function renderError(message) {
            document.getElementById('content').innerHTML = \`
                <div class="error">
                    <span class="error-icon">\${icons.alertCircle}</span>
                    <span class="error-text">\${message}</span>
                    <button onclick="refresh()" style="margin-top: 8px;">
                        \${icons.refresh}
                        Retry
                    </button>
                </div>
            \`;
        }
        
        function refresh() {
            document.getElementById('content').innerHTML = \`
                <div class="loading">
                    <div class="spinner"></div>
                    <span class="loading-text">Refreshing...</span>
                </div>
            \`;
            vscode.postMessage({ type: 'refresh' });
        }
        
        function openSettings() {
            vscode.postMessage({ type: 'openSettings' });
        }
        
        function resetLearning() {
            if (confirm('This will reset all learning data. Are you sure?')) {
                vscode.postMessage({ type: 'resetLearning' });
            }
        }
        
        function reviewFile() {
            vscode.postMessage({ type: 'reviewFile' });
        }
    </script>
</body>
</html>`;
    }
}
