import * as vscode from 'vscode';
import { DiagnosticsManager } from './diagnostics';
import { StatusBarManager } from './statusBar';

// Use dynamic import for eventsource to avoid bundling issues
let EventSource: any;

interface SSEMessage {
    type: string;
    file?: string;
    issues?: {
        critical: number;
        warning: number;
        suggestion: number;
    };
    details?: {
        critical: string[];
        warning: string[];
        suggestion: string[];
    };
    message?: string;
    status?: string;
    time?: string;
}

export class SSEClient {
    private serverUrl: string;
    private eventSource: any = null;
    private diagnosticsManager: DiagnosticsManager;
    private statusBar: StatusBarManager;
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 10;
    private reconnectDelay: number = 5000;

    constructor(
        serverUrl: string,
        diagnosticsManager: DiagnosticsManager,
        statusBar: StatusBarManager
    ) {
        this.serverUrl = serverUrl;
        this.diagnosticsManager = diagnosticsManager;
        this.statusBar = statusBar;
    }

    public async connect(): Promise<void> {
        try {
            // Use require for eventsource module (CommonJS)
            if (!EventSource) {
                try {
                    // eslint-disable-next-line @typescript-eslint/no-var-requires
                    EventSource = require('eventsource');
                } catch {
                    // Fall back to native EventSource if available
                    EventSource = (globalThis as any).EventSource;
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

            this.eventSource.addEventListener('connected', (event: any) => {
                console.log('Received connected event:', event.data);
            });

            this.eventSource.addEventListener('update', (event: any) => {
                try {
                    const data: SSEMessage = JSON.parse(event.data);
                    this.handleUpdate(data);
                } catch (e) {
                    console.error('Failed to parse SSE update:', e);
                }
            });

            this.eventSource.addEventListener('status', (event: any) => {
                try {
                    const data: SSEMessage = JSON.parse(event.data);
                    console.log('Status update:', data.message);
                } catch (e) {
                    console.error('Failed to parse SSE status:', e);
                }
            });

            this.eventSource.addEventListener('heartbeat', () => {
                // Keep-alive, no action needed
            });

            this.eventSource.onerror = (error: any) => {
                console.log('SSE connection error, will retry...');
                this.statusBar.setConnected(false);
                this.scheduleReconnect();
            };

        } catch (error) {
            console.error('Failed to connect to SSE server:', error);
            this.statusBar.setConnected(false);
            this.scheduleReconnect();
        }
    }

    private handleUpdate(data: SSEMessage): void {
        if (data.type === 'review' && data.file && data.issues) {
            console.log(`Review completed: ${data.file}`, data.issues);

            // Update status bar with counts
            this.statusBar.setIssueCount(data.issues);

            // Process detailed diagnostics if available
            if (data.details) {
                const allIssues: any[] = [];

                // Parse critical
                if (data.details.critical) {
                    data.details.critical.forEach(line =>
                        allIssues.push(this.diagnosticsManager.parseIssueLine(line, 'critical'))
                    );
                }

                // Parse warning
                if (data.details.warning) {
                    data.details.warning.forEach(line =>
                        allIssues.push(this.diagnosticsManager.parseIssueLine(line, 'warning'))
                    );
                }

                // Parse suggestion
                if (data.details.suggestion) {
                    data.details.suggestion.forEach(line =>
                        allIssues.push(this.diagnosticsManager.parseIssueLine(line, 'suggestion'))
                    );
                }

                // Update diagnostics
                const uri = vscode.Uri.file(data.file);
                this.diagnosticsManager.setDiagnostics(uri, allIssues);
            }
        }
    }

    private scheduleReconnect(): void {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(
                `Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`
            );
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            console.log('Max reconnect attempts reached, giving up');
        }
    }

    public disconnect(): void {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.statusBar.setConnected(false);
    }
}
