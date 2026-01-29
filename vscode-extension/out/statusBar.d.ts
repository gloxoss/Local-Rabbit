import * as vscode from 'vscode';
export declare class StatusBarManager implements vscode.Disposable {
    private statusBarItem;
    private isConnected;
    private issueCount;
    constructor();
    setConnected(connected: boolean): void;
    setReviewing(fileName: string): void;
    setIssueCount(counts: {
        critical: number;
        warning: number;
        suggestion: number;
    }): void;
    showError(message: string): void;
    private updateDisplay;
    dispose(): void;
}
//# sourceMappingURL=statusBar.d.ts.map