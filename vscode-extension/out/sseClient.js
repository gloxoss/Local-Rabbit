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
exports.SSEClient = void 0;
const vscode = __importStar(require("vscode"));
// Use dynamic import for eventsource to avoid bundling issues
let EventSource;
class SSEClient {
    serverUrl;
    eventSource = null;
    diagnosticsManager;
    statusBar;
    reconnectAttempts = 0;
    maxReconnectAttempts = 10;
    reconnectDelay = 5000;
    constructor(serverUrl, diagnosticsManager, statusBar) {
        this.serverUrl = serverUrl;
        this.diagnosticsManager = diagnosticsManager;
        this.statusBar = statusBar;
    }
    async connect() {
        try {
            // Use require for eventsource module (CommonJS)
            if (!EventSource) {
                try {
                    // eslint-disable-next-line @typescript-eslint/no-var-requires
                    EventSource = require('eventsource');
                }
                catch {
                    // Fall back to native EventSource if available
                    EventSource = globalThis.EventSource;
                }
            }
            if (!EventSource) {
                console.log('EventSource not available');
                this.statusBar.setConnected(false);
                return;
            }
            const eventsUrl = `${this.serverUrl}/events`;
            console.log(`Connecting to SSE server at ${eventsUrl}`);
            this.eventSource = new EventSource(eventsUrl);
            this.eventSource.onopen = () => {
                console.log('SSE connection established');
                this.reconnectAttempts = 0;
                this.statusBar.setConnected(true);
            };
            this.eventSource.addEventListener('connected', (event) => {
                console.log('Received connected event:', event.data);
            });
            this.eventSource.addEventListener('update', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleUpdate(data);
                }
                catch (e) {
                    console.error('Failed to parse SSE update:', e);
                }
            });
            this.eventSource.addEventListener('status', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('Status update:', data.message);
                }
                catch (e) {
                    console.error('Failed to parse SSE status:', e);
                }
            });
            this.eventSource.addEventListener('heartbeat', () => {
                // Keep-alive, no action needed
            });
            this.eventSource.onerror = (error) => {
                console.log('SSE connection error, will retry...');
                this.statusBar.setConnected(false);
                this.scheduleReconnect();
            };
        }
        catch (error) {
            console.error('Failed to connect to SSE server:', error);
            this.statusBar.setConnected(false);
            this.scheduleReconnect();
        }
    }
    handleUpdate(data) {
        if (data.type === 'review' && data.file && data.issues) {
            console.log(`Review completed: ${data.file}`, data.issues);
            // Update status bar with counts
            this.statusBar.setIssueCount(data.issues);
            // Process detailed diagnostics if available
            if (data.details) {
                const allIssues = [];
                // Parse critical
                if (data.details.critical) {
                    data.details.critical.forEach(line => allIssues.push(this.diagnosticsManager.parseIssueLine(line, 'critical')));
                }
                // Parse warning
                if (data.details.warning) {
                    data.details.warning.forEach(line => allIssues.push(this.diagnosticsManager.parseIssueLine(line, 'warning')));
                }
                // Parse suggestion
                if (data.details.suggestion) {
                    data.details.suggestion.forEach(line => allIssues.push(this.diagnosticsManager.parseIssueLine(line, 'suggestion')));
                }
                // Update diagnostics
                const uri = vscode.Uri.file(data.file);
                this.diagnosticsManager.setDiagnostics(uri, allIssues);
            }
        }
    }
    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        }
        else {
            console.log('Max reconnect attempts reached, giving up');
        }
    }
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.statusBar.setConnected(false);
    }
}
exports.SSEClient = SSEClient;
//# sourceMappingURL=sseClient.js.map