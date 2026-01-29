import * as vscode from 'vscode';
import * as path from 'path';
import { DiagnosticsManager } from './diagnostics';

export class QuickFixProvider implements vscode.CodeActionProvider {
    constructor(private diagnosticsManager: DiagnosticsManager) { }

    provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        // Get issues for this file
        const issues = this.diagnosticsManager.getIssues(document.uri.fsPath);
        if (!issues || issues.length === 0) return [];

        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source !== 'Local CodeRabbit') continue;

            // Find matching issue
            const issue = issues.find(i =>
                // Diagnostic lines are 0-indexed, Issue lines are 1-indexed (usually)
                // In DiagnosticsManager.setDiagnostics, we did: line = issue.line - 1
                (Math.max(0, (i.line || 1) - 1) === diagnostic.range.start.line) &&
                i.message === diagnostic.message
            );

            if (issue && issue.fixCode) {
                // Create the apply fix action
                const applyAction = new vscode.CodeAction('✅ Apply Fix', vscode.CodeActionKind.QuickFix);
                applyAction.edit = new vscode.WorkspaceEdit();
                applyAction.edit.replace(document.uri, diagnostic.range, issue.fixCode);
                applyAction.diagnostics = [diagnostic];
                applyAction.isPreferred = true;

                // Add command to send feedback after applying
                applyAction.command = {
                    title: 'Send Feedback',
                    command: 'localCoderabbit.sendFeedback',
                    arguments: [{
                        issue_type: this.extractIssueType(issue.message),
                        severity: issue.severity,
                        action: 'accepted',
                        filename: path.basename(document.uri.fsPath),
                        language: document.languageId
                    }]
                };

                actions.push(applyAction);

                // Add dismiss action
                const dismissAction = new vscode.CodeAction('❌ Dismiss', vscode.CodeActionKind.QuickFix);
                dismissAction.diagnostics = [diagnostic];
                dismissAction.command = {
                    title: 'Dismiss and Send Feedback',
                    command: 'localCoderabbit.dismissIssue',
                    arguments: [{
                        issue_type: this.extractIssueType(issue.message),
                        severity: issue.severity,
                        action: 'rejected',
                        filename: path.basename(document.uri.fsPath),
                        language: document.languageId,
                        diagnostic: diagnostic
                    }]
                };

                actions.push(dismissAction);
            }
        }

        return actions;
    }

    /**
     * Extract issue type from message for categorization
     */
    private extractIssueType(message: string): string {
        const lowerMsg = message.toLowerCase();

        // Common patterns
        if (lowerMsg.includes('unused') || lowerMsg.includes('dead code')) return 'unused-code';
        if (lowerMsg.includes('error handling') || lowerMsg.includes('try') || lowerMsg.includes('catch')) return 'error-handling';
        if (lowerMsg.includes('type') || lowerMsg.includes('any')) return 'type-safety';
        if (lowerMsg.includes('null') || lowerMsg.includes('undefined')) return 'null-check';
        if (lowerMsg.includes('const') || lowerMsg.includes('let') || lowerMsg.includes('var')) return 'variable-declaration';
        if (lowerMsg.includes('async') || lowerMsg.includes('await') || lowerMsg.includes('promise')) return 'async-patterns';
        if (lowerMsg.includes('sql') || lowerMsg.includes('injection')) return 'security-injection';
        if (lowerMsg.includes('password') || lowerMsg.includes('secret') || lowerMsg.includes('key')) return 'security-secrets';
        if (lowerMsg.includes('performance') || lowerMsg.includes('loop') || lowerMsg.includes('optimization')) return 'performance';
        if (lowerMsg.includes('naming') || lowerMsg.includes('convention')) return 'naming-convention';
        if (lowerMsg.includes('comment') || lowerMsg.includes('documentation')) return 'documentation';

        return 'general';
    }
}
