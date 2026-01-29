import * as vscode from 'vscode';
import { DiagnosticsManager, Issue } from './diagnostics';
import { SSEClient } from './sseClient';
import { StatusBarManager } from './statusBar';
import { ReviewService } from './reviewService';
import { QuickFixProvider } from './quickFix';
import { IssuesTreeDataProvider } from './issuesTreeView';
import { DashboardViewProvider } from './dashboardWebView';
import { ChatViewProvider } from './chatWebView';

let diagnosticsManager: DiagnosticsManager;
let sseClient: SSEClient;
let statusBar: StatusBarManager;
let reviewService: ReviewService;
let issuesTreeProvider: IssuesTreeDataProvider;
let dashboardProvider: DashboardViewProvider;

export function activate(context: vscode.ExtensionContext) {
    console.log('Local CodeRabbit extension activated');

    // Initialize managers
    diagnosticsManager = new DiagnosticsManager();
    statusBar = new StatusBarManager();
    reviewService = new ReviewService(diagnosticsManager);

    // Get configuration
    const config = vscode.workspace.getConfiguration('localCoderabbit');
    const serverUrl = config.get<string>('serverUrl', 'http://localhost:8765');

    // Initialize SSE client for real-time updates
    sseClient = new SSEClient(serverUrl, diagnosticsManager, statusBar);

    // Initialize Issues TreeView
    issuesTreeProvider = new IssuesTreeDataProvider(diagnosticsManager);
    const issuesTreeView = vscode.window.createTreeView('localCoderabbit.issues', {
        treeDataProvider: issuesTreeProvider,
        showCollapseAll: true
    });

    // Update tree when diagnostics change
    reviewService.onReviewComplete(() => {
        issuesTreeProvider.refresh();
        // Update badge
        const count = issuesTreeProvider.getTotalCount();
        issuesTreeView.badge = count > 0 ? { value: count, tooltip: `${count} issues` } : undefined;
        // Also refresh dashboard
        dashboardProvider?.refresh();
    });

    // Initialize Dashboard WebView
    dashboardProvider = new DashboardViewProvider(context.extensionUri, serverUrl);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            DashboardViewProvider.viewType,
            dashboardProvider
        )
    );

    // Initialize Chat WebView (Phase 4)
    const chatProvider = new ChatViewProvider(context.extensionUri, serverUrl);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            ChatViewProvider.viewType,
            chatProvider
        )
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('localCoderabbit.reviewFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                await reviewService.reviewFile(editor.document);
            }
        }),

        // Navigate to issue location
        vscode.commands.registerCommand('localCoderabbit.goToIssue', async (issue: Issue) => {
            if (!issue.file) return;

            const doc = await vscode.workspace.openTextDocument(issue.file);
            const editor = await vscode.window.showTextDocument(doc);
            const line = Math.max(0, (issue.line || 1) - 1);
            const position = new vscode.Position(line, 0);
            editor.selection = new vscode.Selection(position, position);
            editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenter);
        }),

        // Refresh issues tree
        vscode.commands.registerCommand('localCoderabbit.refreshIssues', () => {
            issuesTreeProvider.refresh();
        }),

        // Focus sidebar
        vscode.commands.registerCommand('localCoderabbit.focusSidebar', () => {
            vscode.commands.executeCommand('localCoderabbit.issues.focus');
        }),

        vscode.commands.registerCommand('localCoderabbit.reviewWorkspace', async () => {
            await reviewService.reviewWorkspace();
        }),

        vscode.commands.registerCommand('localCoderabbit.toggleAutoReview', () => {
            const current = config.get<boolean>('autoReview', true);
            config.update('autoReview', !current, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(
                `Auto-review ${!current ? 'enabled' : 'disabled'}`
            );
        }),

        vscode.commands.registerCommand('localCoderabbit.showDashboard', () => {
            // Open dashboard on localhost server
            // Note: Server must be running via start-local.ps1
            vscode.env.openExternal(vscode.Uri.parse('http://localhost:8080/dashboard.html'));
        }),

        vscode.commands.registerCommand('localCoderabbit.clearDiagnostics', () => {
            diagnosticsManager.clearAll();
            vscode.window.showInformationMessage('All diagnostics cleared');
        }),

        // Feedback commands for learning
        vscode.commands.registerCommand('localCoderabbit.sendFeedback', async (feedback: any) => {
            await sendFeedbackToApi(serverUrl, feedback);
        }),

        vscode.commands.registerCommand('localCoderabbit.dismissIssue', async (data: any) => {
            // Send rejection feedback
            await sendFeedbackToApi(serverUrl, {
                issue_type: data.issue_type,
                severity: data.severity,
                action: 'rejected',
                filename: data.filename,
                language: data.language
            });
            // Clear the specific diagnostic
            if (data.diagnostic) {
                vscode.window.showInformationMessage('Issue dismissed. Feedback recorded.');
            }
        }),

        vscode.languages.registerCodeActionsProvider(
            { scheme: 'file' },
            new QuickFixProvider(diagnosticsManager),
            { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
        )
    );

    // Auto-review on save
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async (document) => {
            const autoReview = config.get<boolean>('autoReview', true);
            if (autoReview && isSupportedFile(document)) {
                statusBar.setReviewing(document.fileName);
                await reviewService.reviewFile(document);
            }
        })
    );

    // Auto-review when active editor changes (for better initial experience)
    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(async (editor) => {
            if (!editor) return;
            const autoReview = config.get<boolean>('autoReview', true);
            if (autoReview && isSupportedFile(editor.document)) {
                // Only review if not already reviewed (no diagnostics for this file)
                const existingIssues = diagnosticsManager.getIssues(editor.document.uri.fsPath);
                if (existingIssues.length === 0) {
                    statusBar.setReviewing(editor.document.fileName);
                    await reviewService.reviewFile(editor.document);
                }
            }
        })
    );

    // Also review the currently active file on startup
    if (vscode.window.activeTextEditor) {
        const editor = vscode.window.activeTextEditor;
        if (isSupportedFile(editor.document)) {
            // Delay slightly to let extension fully initialize
            setTimeout(async () => {
                statusBar.setReviewing(editor.document.fileName);
                await reviewService.reviewFile(editor.document);
            }, 1000);
        }
    }

    // Connect to SSE server (fallback for watcher mode)
    sseClient.connect();

    // Check Docker API health on startup
    checkApiHealth(serverUrl, statusBar);

    // Check API health periodically (every 30 seconds)
    const healthCheckInterval = setInterval(() => {
        checkApiHealth(serverUrl, statusBar);
    }, 30000);

    // Register disposables
    context.subscriptions.push(
        diagnosticsManager,
        statusBar,
        { dispose: () => sseClient.disconnect() },
        { dispose: () => clearInterval(healthCheckInterval) }
    );

    // Show welcome message
    vscode.window.showInformationMessage(
        'Local CodeRabbit activated! Press Ctrl+Shift+R to review current file.'
    );
}

/**
 * Check if the Docker API server is healthy
 */
function checkApiHealth(serverUrl: string, statusBar: StatusBarManager): void {
    const http = require('http');
    const url = new URL(serverUrl);
    const port = url.port ? parseInt(url.port) : 8765;

    const req = http.get({
        hostname: url.hostname,
        port: port,
        path: '/api/health',
        timeout: 3000
    }, (res: any) => {
        let data = '';
        res.on('data', (chunk: string) => data += chunk);
        res.on('end', () => {
            try {
                const response = JSON.parse(data);
                if (response.status === 'ok') {
                    statusBar.setConnected(true);
                    console.log(`Connected to API (${response.provider}/${response.model})`);
                }
            } catch {
                statusBar.setConnected(false);
            }
        });
    });

    req.on('error', () => {
        statusBar.setConnected(false);
    });

    req.on('timeout', () => {
        req.destroy();
        statusBar.setConnected(false);
    });
}

/**
 * Send feedback to the API server
 */
async function sendFeedbackToApi(serverUrl: string, feedback: any): Promise<void> {
    const http = require('http');
    const url = new URL(serverUrl);
    const port = url.port ? parseInt(url.port) : 8765;

    const postData = JSON.stringify(feedback);

    return new Promise((resolve) => {
        const req = http.request({
            hostname: url.hostname,
            port: port,
            path: '/api/feedback',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        }, (res: any) => {
            res.on('data', () => { });
            res.on('end', () => {
                console.log(`Feedback sent: ${feedback.action} - ${feedback.issue_type}`);
                resolve();
            });
        });

        req.on('error', () => {
            console.log('Failed to send feedback');
            resolve();
        });

        req.write(postData);
        req.end();
    });
}

function isSupportedFile(document: vscode.TextDocument): boolean {
    const supportedExtensions = [
        '.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs', '.vue', '.svelte'
    ];
    return supportedExtensions.some(ext => document.fileName.endsWith(ext));
}

export function deactivate() {
    if (sseClient) {
        sseClient.disconnect();
    }
    console.log('Local CodeRabbit extension deactivated');
}
