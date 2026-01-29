"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SSEClient = void 0;
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
            // Note: Full diagnostic details would need to be fetched from stats.json
            // or extended SSE payload
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