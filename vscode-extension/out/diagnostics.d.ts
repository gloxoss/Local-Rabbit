import * as vscode from 'vscode';
export interface Issue {
    file: string;
    line: number;
    column?: number;
    severity: 'critical' | 'warning' | 'suggestion';
    message: string;
    code?: string;
    source?: string;
    fixCode?: string;
}
export declare class DiagnosticsManager implements vscode.Disposable {
    private collection;
    private issuesByFile;
    constructor();
    /**
     * Set diagnostics for a file from parsed issues
     */
    setDiagnostics(uri: vscode.Uri, issues: Issue[]): void;
    /**
     * Parse AI review text and extract issues
     */
    parseReviewText(text: string, filePath: string): Issue[];
    /**
     * Clear diagnostics for a specific file
     */
    clearFile(uri: vscode.Uri): void;
    /**
     * Clear all diagnostics
     */
    clearAll(): void;
    /**
     * Get all issues for a file
     */
    getIssues(filePath: string): Issue[];
    /**
     * Get all issues across all files
     */
    getAllIssues(): Issue[];
    /**
     * Get total issue count
     */
    getTotalCount(): {
        critical: number;
        warning: number;
        suggestion: number;
    };
    private getSeverity;
    private extractLineNumber;
    parseIssueLine(line: string, severity: 'critical' | 'warning' | 'suggestion'): Issue;
    private cleanMessage;
    dispose(): void;
}
//# sourceMappingURL=diagnostics.d.ts.map