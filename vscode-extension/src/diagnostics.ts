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

export class DiagnosticsManager implements vscode.Disposable {
    private collection: vscode.DiagnosticCollection;
    private issuesByFile: Map<string, Issue[]> = new Map();

    constructor() {
        this.collection = vscode.languages.createDiagnosticCollection('localCoderabbit');
    }

    /**
     * Set diagnostics for a file from parsed issues
     */
    public setDiagnostics(uri: vscode.Uri, issues: Issue[]): void {
        const diagnostics: vscode.Diagnostic[] = issues.map(issue => {
            const line = Math.max(0, (issue.line || 1) - 1);
            const column = Math.max(0, (issue.column || 1) - 1);

            const range = new vscode.Range(
                new vscode.Position(line, column),
                new vscode.Position(line, Number.MAX_VALUE)
            );

            const diagnostic = new vscode.Diagnostic(
                range,
                issue.message,
                this.getSeverity(issue.severity)
            );

            diagnostic.source = 'Local CodeRabbit';
            diagnostic.code = issue.code || issue.severity.toUpperCase();

            return diagnostic;
        });

        this.collection.set(uri, diagnostics);
        this.issuesByFile.set(uri.fsPath, issues);
    }

    /**
     * Parse AI review text and extract issues
     */
    public parseReviewText(text: string, filePath: string): Issue[] {
        const issues: Issue[] = [];
        const lines = text.split('\n');

        let currentIssue: Issue | null = null;
        let capturingCode = false;
        let codeBlock = '';

        const isHeader = (l: string) => {
            const u = l.toUpperCase();
            return (u.includes('[CRITICAL]') || l.includes('🔴')) ||
                (u.includes('[WARNING]') || l.includes('🟡')) ||
                (u.includes('[SUGGESTION]') || l.includes('🔵'));
        };

        for (const line of lines) {
            if (isHeader(line) && !capturingCode) {
                if (currentIssue) issues.push(currentIssue);

                const u = line.toUpperCase();
                const severity = (u.includes('CRITICAL') || line.includes('🔴')) ? 'critical' :
                    (u.includes('WARNING') || line.includes('🟡')) ? 'warning' : 'suggestion';

                currentIssue = {
                    file: filePath,
                    line: this.extractLineNumber(line) || 1,
                    severity: severity,
                    message: this.cleanMessage(line, severity.toUpperCase() || 'SUGGESTION')
                };
            }
            else if (line.trim().startsWith('```suggestion')) {
                capturingCode = true;
                codeBlock = '';
            }
            else if (line.trim() === '```' && capturingCode) {
                if (currentIssue) {
                    currentIssue.fixCode = codeBlock.replace(/\n$/, '');
                }
                capturingCode = false;
            }
            else if (capturingCode) {
                codeBlock += line + '\n';
            }
        }

        if (currentIssue) issues.push(currentIssue);

        return issues;
    }

    /**
     * Clear diagnostics for a specific file
     */
    public clearFile(uri: vscode.Uri): void {
        this.collection.delete(uri);
        this.issuesByFile.delete(uri.fsPath);
    }

    /**
     * Clear all diagnostics
     */
    public clearAll(): void {
        this.collection.clear();
        this.issuesByFile.clear();
    }

    /**
     * Get all issues for a file
     */
    public getIssues(filePath: string): Issue[] {
        return this.issuesByFile.get(filePath) || [];
    }

    /**
     * Get all issues across all files
     */
    public getAllIssues(): Issue[] {
        const allIssues: Issue[] = [];
        for (const issues of this.issuesByFile.values()) {
            allIssues.push(...issues);
        }
        return allIssues;
    }

    /**
     * Get total issue count
     */
    public getTotalCount(): { critical: number; warning: number; suggestion: number } {
        let critical = 0, warning = 0, suggestion = 0;

        for (const issues of this.issuesByFile.values()) {
            for (const issue of issues) {
                if (issue.severity === 'critical') critical++;
                else if (issue.severity === 'warning') warning++;
                else suggestion++;
            }
        }

        return { critical, warning, suggestion };
    }

    private getSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'critical':
                return vscode.DiagnosticSeverity.Error;
            case 'warning':
                return vscode.DiagnosticSeverity.Warning;
            case 'suggestion':
            default:
                return vscode.DiagnosticSeverity.Information;
        }
    }

    private extractLineNumber(text: string): number | null {
        // Try to find line number patterns like "line 42", ":42:", "L42"
        const patterns = [
            /line\s*(\d+)/i,
            /:(\d+):/,
            /L(\d+)/,
            /\[(\d+)\]/
        ];

        for (const pattern of patterns) {
            const match = text.match(pattern);
            if (match) {
                return parseInt(match[1], 10);
            }
        }
        return null;
    }

    private cleanMessage(text: string, severity: string): string {
        return text
            .replace(/🔴|🟡|🔵/g, '')
            .replace(new RegExp(severity + '\\s*:?', 'gi'), '')
            .replace(/line\s*\d+\s*:?/gi, '')
            .trim();
    }

    dispose(): void {
        this.collection.dispose();
    }
}
