import * as vscode from 'vscode';
/**
 * Dashboard WebView provider for the sidebar.
 * Shows health stats, learning info, and quick actions.
 * Enhanced with professional UI/UX following VS Code design language.
 */
export declare class DashboardViewProvider implements vscode.WebviewViewProvider {
    private readonly _extensionUri;
    static readonly viewType = "localCoderabbit.dashboard";
    private _view?;
    private _serverUrl;
    constructor(_extensionUri: vscode.Uri, serverUrl: string);
    resolveWebviewView(webviewView: vscode.WebviewView, context: vscode.WebviewViewResolveContext, _token: vscode.CancellationToken): void;
    /**
     * Refresh dashboard data
     */
    refresh(): Promise<void>;
    private _resetLearning;
    /**
     * Fetch from API
     */
    private _fetchApi;
    /**
     * Generate HTML for the webview with enhanced UI
     */
    private _getHtmlForWebview;
}
//# sourceMappingURL=dashboardWebView.d.ts.map