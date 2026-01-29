import * as vscode from 'vscode';
import { DiagnosticsManager } from './diagnostics';
export declare class QuickFixProvider implements vscode.CodeActionProvider {
    private diagnosticsManager;
    constructor(diagnosticsManager: DiagnosticsManager);
    provideCodeActions(document: vscode.TextDocument, range: vscode.Range | vscode.Selection, context: vscode.CodeActionContext, token: vscode.CancellationToken): vscode.CodeAction[];
    /**
     * Extract issue type from message for categorization
     */
    private extractIssueType;
}
//# sourceMappingURL=quickFix.d.ts.map