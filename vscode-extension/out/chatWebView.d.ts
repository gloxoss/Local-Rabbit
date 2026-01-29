import * as vscode from 'vscode';
/**
 * Chat WebView provider for the sidebar.
 * Implements "UI/UX Pro Max" standards:
 * - Streaming responses
 * - Markdown rendering via markdown-it
 * - Syntax highlighting via highlight.js
 * - Context awareness
 * - SVG Icons & Glassmorphism
 */
export declare class ChatViewProvider implements vscode.WebviewViewProvider {
    private readonly _extensionUri;
    static readonly viewType = "localCoderabbit.chat";
    private _view?;
    private _serverUrl;
    private _md;
    constructor(_extensionUri: vscode.Uri, serverUrl: string);
    resolveWebviewView(webviewView: vscode.WebviewView, context: vscode.WebviewViewResolveContext, _token: vscode.CancellationToken): void;
    private _handleQuery;
    private _loadHistory;
    private _getHtmlForWebview;
}
//# sourceMappingURL=chatWebView.d.ts.map