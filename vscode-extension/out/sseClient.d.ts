import { DiagnosticsManager } from './diagnostics';
import { StatusBarManager } from './statusBar';
export declare class SSEClient {
    private serverUrl;
    private eventSource;
    private diagnosticsManager;
    private statusBar;
    private reconnectAttempts;
    private maxReconnectAttempts;
    private reconnectDelay;
    constructor(serverUrl: string, diagnosticsManager: DiagnosticsManager, statusBar: StatusBarManager);
    connect(): Promise<void>;
    private handleUpdate;
    private scheduleReconnect;
    disconnect(): void;
}
//# sourceMappingURL=sseClient.d.ts.map