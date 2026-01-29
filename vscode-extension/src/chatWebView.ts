import * as vscode from 'vscode';
// Fix for 'This expression is not constructable' - standard import hack
const MarkdownIt = require('markdown-it');
const hljs = require('highlight.js');

/**
 * Chat WebView provider for the sidebar.
 * Implements "UI/UX Pro Max" standards:
 * - Streaming responses
 * - Markdown rendering via markdown-it
 * - Syntax highlighting via highlight.js
 * - Context awareness
 * - SVG Icons & Glassmorphism
 */
export class ChatViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'localCoderabbit.chat';

    private _view?: vscode.WebviewView;
    private _serverUrl: string;
    private _md: any;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        serverUrl: string
    ) {
        this._serverUrl = serverUrl;

        // Initialize Markdown-it with Highlight.js
        this._md = new MarkdownIt({
            html: true,
            linkify: true,
            typographer: true,
            highlight: (str: string, lang: string) => {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return '<pre class="hljs"><code>' +
                            hljs.highlight(str, { language: lang, ignoreIllegals: true } as any).value +
                            '</code></pre>';
                    } catch (__) { }
                }

                return '<pre class="hljs"><code>' + this._md.utils.escapeHtml(str) + '</code></pre>';
            }
        });
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

        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'query':
                    await this._handleQuery(data.value);
                    break;
                case 'loadHistory':
                    await this._loadHistory();
                    break;
            }
        });
    }

    private async _handleQuery(query: string) {
        if (!this._view) return;

        // Get Context
        const editor = vscode.window.activeTextEditor;
        const selection = editor ? editor.document.getText(editor.selection) : undefined;
        const filename = editor ? editor.document.fileName : undefined;
        const projectRoot = vscode.workspace.workspaceFolders?.[0].uri.fsPath;

        const context = {
            file: filename,
            selection: selection,
            project_root: projectRoot
        };

        try {
            const response = await fetch(`${this._serverUrl}/api/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, context })
            });

            if (!response.ok) throw new Error(response.statusText);
            if (!response.body) throw new Error('No response body');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            this._view.webview.postMessage(data);
                        } catch (e) {
                            // Ignore incomplete JSON
                        }
                    }
                }
            }

        } catch (error: any) {
            this._view.webview.postMessage({
                type: 'error',
                content: error.message
            });
        }
    }

    private async _loadHistory() {
        if (!this._view) return;
        try {
            const response = await fetch(`${this._serverUrl}/api/history`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this._view.webview.postMessage({
                    type: 'history',
                    data: (data as any).history
                });
            }
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        // We'll use a CDN for highlight.js CSS for simplicity in WebView
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rabbit Chat</title>
    <!-- Highlight.js VS 2015 Theme -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    
    <!-- Markdown-it (Browser bundle for client-side rendering during stream) -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/markdown-it/13.0.1/markdown-it.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <style>
        :root {
            --input-bg: var(--vscode-input-background);
            --input-fg: var(--vscode-input-foreground);
            --border: var(--vscode-input-border);
            --card-bg: var(--vscode-editor-background);
            --primary: var(--vscode-button-background);
            --primary-hover: var(--vscode-button-hoverBackground);
            --scrollbar-bg: var(--vscode-scrollbarSlider-background);
            --scrollbar-hover: var(--vscode-scrollbarSlider-hoverBackground);
        }
        body { 
            font-family: var(--vscode-font-family); 
            padding: 0; 
            margin: 0;
            color: var(--vscode-foreground); 
            display: flex;
            flex-direction: column;
            height: 100vh;
            background: var(--vscode-editor-background); 
        }
        
        /* Chat Area */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            scroll-behavior: smooth;
        }
        .chat-container::-webkit-scrollbar {
            width: 10px;
        }
        .chat-container::-webkit-scrollbar-thumb {
            background: var(--scrollbar-bg);
            border-radius: 5px;
        }
        .chat-container::-webkit-scrollbar-thumb:hover {
            background: var(--scrollbar-hover);
        }

        /* Messages */
        .message {
            display: flex;
            gap: 16px;
            animation: slideUp 0.3s ease-out;
            max-width: 100%;
        }
        .message.user {
            flex-direction: row-reverse;
        }
        
        .avatar {
            width: 32px;
            height: 32px;
            border-radius: 8px; /* Smooth rounded corners */
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .avatar.ai { 
            background: linear-gradient(135deg, #6366f1, #a855f7); /* Indigo to Purple */
            color: white;
        }
        .avatar.user { 
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }
        
        .content {
            background: var(--vscode-editor-inactiveSelectionBackground); /* Subtle card bg */
            padding: 12px 16px;
            border-radius: 12px;
            border-top-left-radius: 2px; /* Chat bubble effect */
            max-width: 85%;
            font-size: 14px;
            line-height: 1.6;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            overflow-wrap: break-word;
        }
        .message.user .content {
            background: var(--primary);
            color: white; /* Always white on primary */
            border-top-left-radius: 12px;
            border-top-right-radius: 2px;
        }
        
        /* Markdown Content Styling */
        .content p { margin: 0 0 10px 0; }
        .content p:last-child { margin: 0; }
        .content pre {
            background: #1e1e1e !important; /* Code block bg */
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 10px 0;
            border: 1px solid #333;
        }
        .content code {
            font-family: var(--vscode-editor-font-family, 'Consolas', monospace);
            font-size: 0.9em;
            background: rgba(127, 127, 127, 0.15);
            padding: 2px 4px;
            border-radius: 3px;
        }
        .content pre code {
            background: transparent;
            padding: 0;
            color: #d4d4d4;
        }
        .content ul, .content ol { padding-left: 20px; margin: 10px 0; }
        .content blockquote {
            border-left: 3px solid var(--primary);
            margin: 0;
            padding-left: 12px;
            opacity: 0.8;
        }

        /* Input Area */
        .input-area {
            padding: 20px;
            border-top: 1px solid var(--vscode-panel-border);
            background: var(--vscode-sideBar-background);
        }
        .input-wrapper {
            position: relative;
            display: flex;
            align-items: flex-end;
            background: var(--input-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 10px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .input-wrapper:focus-within {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px var(--vscode-focusBorder);
        }
        
        textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--input-fg);
            font-family: inherit;
            font-size: 14px;
            resize: none;
            min-height: 24px;
            max-height: 200px;
            outline: none;
            padding: 4px;
            padding-right: 40px; /* Space for button */
        }
        
        /* Floating Send Button */
        button.send-btn {
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            width: 32px;
            height: 32px;
            cursor: cursor;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.1s, background 0.2s;
            opacity: 0.9;
        }
        button.send-btn:hover { 
            background: var(--primary-hover); 
            opacity: 1;
            transform: scale(1.05);
        }
        button.send-btn:active { transform: scale(0.95); }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
    </style>
</head>
<body>
    <div class="chat-container" id="chat-container">
        <!-- Messages go here -->
    </div>
    
    <div class="input-area">
        <div class="input-wrapper">
            <textarea id="chat-input" placeholder="Message Local Rabbit..." rows="1" oninput="autoResize(this)" onkeydown="handleKey(event)"></textarea>
            <button class="send-btn" onclick="sendMessage()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
            </button>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const chatContainer = document.getElementById('chat-container');
        const input = document.getElementById('chat-input');
        
        // Client-side Markdown instance for streaming updates
        // Note: The backend could send MD, but we render here.
        // Since we import scripts via CDN for WebView sandbox, we use global markdownit
        const md = window.markdownit({
            html: true,
            linkify: true,
            highlight: function (str, lang) {
                if (lang && window.hljs.getLanguage(lang)) {
                    try {
                        return window.hljs.highlight(str, { language: lang }).value;
                    } catch (__) {}
                }
                return ''; // use external default escaping
            }
        });

        let currentAiMessageDiv = null;
        let currentAiRawText = "";

        function autoResize(el) {
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, 200) + 'px';
        }

        function handleKey(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        function sendMessage() {
            const text = input.value.trim();
            if (!text) return;

            // Render User Message immediately
            addMessage(text, 'user');
            input.value = '';
            input.style.height = 'auto';

            // Send to Extension
            vscode.postMessage({ type: 'query', value: text });
            
            // Prepare AI Placeholder
            currentAiMessageDiv = createMessageDiv('ai');
            currentAiRawText = "";
            renderAiContent("Thinking..."); // Initial state
        }

        function createMessageDiv(role) {
            const div = document.createElement('div');
            div.className = \`message \${role}\`;
            
            const icon = role === 'ai' 
                ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8-8 8zm-5-9c.83 0 1.5-.67 1.5-1.5S7.83 8 7 8s-1.5.67-1.5 1.5S6.17 11 7 11zm3.5 4c2.33 0 4.31-1.46 5.11-3.5H8.39c.8 2.04 2.78 3.5 5.11 3.5zm3.5-5.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5z"/></svg>' // Rabbit Icon
                : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'; // User Icon

            div.innerHTML = \`
                <div class="avatar \${role}">\${icon}</div>
                <div class="content"></div>
            \`;
            
            chatContainer.appendChild(div);
            // Auto scroll
            requestAnimationFrame(() => chatContainer.scrollTop = chatContainer.scrollHeight);
            
            return div;
        }

        function addMessage(text, role) {
            const div = createMessageDiv(role);
            const contentDiv = div.querySelector('.content');
            
            if (role === 'user') {
                contentDiv.textContent = text; // User text is raw
            } else {
                // Render Markdown for AI history
                contentDiv.innerHTML = md.render(text);
            }
        }

        function renderAiContent(text) {
             if (currentAiMessageDiv) {
                 const contentDiv = currentAiMessageDiv.querySelector('.content');
                 contentDiv.innerHTML = md.render(text);
                 // Scroll to bottom efficiently
                 chatContainer.scrollTop = chatContainer.scrollHeight;
             }
        }

        // Listen for streaming updates
        window.addEventListener('message', event => {
            const msg = event.data;
            
            if (msg.type === 'status') {
                 // Update status text (e.g. "Searching...")
                 if (!currentAiRawText) {
                     renderAiContent("*" + msg.content + "*");
                 }
            }
            else if (msg.type === 'token') {
                currentAiRawText += msg.content;
                renderAiContent(currentAiRawText);
            } 
            else if (msg.type === 'history') {
                // Load history strictly
                msg.data.forEach(m => addMessage(m.content, m.role === 'user' ? 'user' : 'ai'));
            }
            else if (msg.type === 'error') {
                 if (currentAiMessageDiv) {
                     currentAiRawText += "\\n\\n**Error:** " + msg.content;
                     renderAiContent(currentAiRawText);
                 }
            }
        });

        // Load History on Startup
        vscode.postMessage({ type: 'loadHistory' });
    </script>
</body>
</html>`;
    }
}
