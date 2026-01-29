"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const diagnostics_1 = require("./diagnostics");
const sseClient_1 = require("./sseClient");
const statusBar_1 = require("./statusBar");
const reviewService_1 = require("./reviewService");
const quickFix_1 = require("./quickFix");
const issuesTreeView_1 = require("./issuesTreeView");
const dashboardWebView_1 = require("./dashboardWebView");
const chatWebView_1 = require("./chatWebView");
let diagnosticsManager;
let sseClient;
let statusBar;
let reviewService;
let issuesTreeProvider;
let dashboardProvider;
function activate(context) {
    console.log('Local CodeRabbit extension activated');
    // Initialize managers
    diagnosticsManager = new diagnostics_1.DiagnosticsManager();
    statusBar = new statusBar_1.StatusBarManager();
    reviewService = new reviewService_1.ReviewService(diagnosticsManager);
    // Get configuration
    const config = vscode.workspace.getConfiguration('localCoderabbit');
    const serverUrl = config.get('serverUrl', 'http://localhost:8765');
    // Initialize SSE client for real-time updates
    sseClient = new sseClient_1.SSEClient(serverUrl, diagnosticsManager, statusBar);
    // Initialize Issues TreeView
    issuesTreeProvider = new issuesTreeView_1.IssuesTreeDataProvider(diagnosticsManager);
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
    dashboardProvider = new dashboardWebView_1.DashboardViewProvider(context.extensionUri, serverUrl);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(dashboardWebView_1.DashboardViewProvider.viewType, dashboardProvider));
    // Initialize Chat WebView (Phase 4)
    const chatProvider = new chatWebView_1.ChatViewProvider(context.extensionUri, serverUrl);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(chatWebView_1.ChatViewProvider.viewType, chatProvider));
    // Register commands
    context.subscriptions.push(vscode.commands.registerCommand('localCoderabbit.reviewFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            await reviewService.reviewFile(editor.document);
        }
    }), 
    // Navigate to issue location
    vscode.commands.registerCommand('localCoderabbit.goToIssue', async (issue) => {
        if (!issue.file)
            return;
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
    }), vscode.commands.registerCommand('localCoderabbit.reviewWorkspace', async () => {
        await reviewService.reviewWorkspace();
    }), vscode.commands.registerCommand('localCoderabbit.toggleAutoReview', () => {
        const current = config.get('autoReview', true);
        config.update('autoReview', !current, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage(`Auto-review ${!current ? 'enabled' : 'disabled'}`);
    }), vscode.commands.registerCommand('localCoderabbit.showDashboard', () => {
        // Open dashboard on localhost server
        // Note: Server must be running via start-local.ps1
        vscode.env.openExternal(vscode.Uri.parse('http://localhost:8080/dashboard.html'));
    }), vscode.commands.registerCommand('localCoderabbit.clearDiagnostics', () => {
        diagnosticsManager.clearAll();
        vscode.window.showInformationMessage('All diagnostics cleared');
    }), 
    // Feedback commands for learning
    vscode.commands.registerCommand('localCoderabbit.sendFeedback', async (feedback) => {
        await sendFeedbackToApi(serverUrl, feedback);
    }), vscode.commands.registerCommand('localCoderabbit.dismissIssue', async (data) => {
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
    }), vscode.languages.registerCodeActionsProvider({ scheme: 'file' }, new quickFix_1.QuickFixProvider(diagnosticsManager), { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }));
    // Auto-review on save
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (document) => {
        const autoReview = config.get('autoReview', true);
        if (autoReview && isSupportedFile(document)) {
            statusBar.setReviewing(document.fileName);
            await reviewService.reviewFile(document);
        }
    }));
    // Auto-review when active editor changes (for better initial experience)
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(async (editor) => {
        if (!editor)
            return;
        const autoReview = config.get('autoReview', true);
        if (autoReview && isSupportedFile(editor.document)) {
            // Only review if not already reviewed (no diagnostics for this file)
            const existingIssues = diagnosticsManager.getIssues(editor.document.uri.fsPath);
            if (existingIssues.length === 0) {
                statusBar.setReviewing(editor.document.fileName);
                await reviewService.reviewFile(editor.document);
            }
        }
    }));
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
    context.subscriptions.push(diagnosticsManager, statusBar, { dispose: () => sseClient.disconnect() }, { dispose: () => clearInterval(healthCheckInterval) });
    // Show welcome message
    vscode.window.showInformationMessage('Local CodeRabbit activated! Press Ctrl+Shift+R to review current file.');
}
/**
 * Check if the Docker API server is healthy
 */
function checkApiHealth(serverUrl, statusBar) {
    const http = require('http');
    const url = new URL(serverUrl);
    const port = url.port ? parseInt(url.port) : 8765;
    const req = http.get({
        hostname: url.hostname,
        port: port,
        path: '/api/health',
        timeout: 3000
    }, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
            try {
                const response = JSON.parse(data);
                if (response.status === 'ok') {
                    statusBar.setConnected(true);
                    console.log(`Connected to API (${response.provider}/${response.model})`);
                }
            }
            catch {
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
async function sendFeedbackToApi(serverUrl, feedback) {
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
        }, (res) => {
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
function isSupportedFile(document) {
    const supportedExtensions = [
        '.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs', '.vue', '.svelte'
    ];
    return supportedExtensions.some(ext => document.fileName.endsWith(ext));
}
function deactivate() {
    if (sseClient) {
        sseClient.disconnect();
    }
    console.log('Local CodeRabbit extension deactivated');
}
//# sourceMappingURL=extension.js.map