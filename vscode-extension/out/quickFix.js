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
exports.QuickFixProvider = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
class QuickFixProvider {
    diagnosticsManager;
    constructor(diagnosticsManager) {
        this.diagnosticsManager = diagnosticsManager;
    }
    provideCodeActions(document, range, context, token) {
        const actions = [];
        // Get issues for this file
        const issues = this.diagnosticsManager.getIssues(document.uri.fsPath);
        if (!issues || issues.length === 0)
            return [];
        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source !== 'Local CodeRabbit')
                continue;
            // Find matching issue
            const issue = issues.find(i => 
            // Diagnostic lines are 0-indexed, Issue lines are 1-indexed (usually)
            // In DiagnosticsManager.setDiagnostics, we did: line = issue.line - 1
            (Math.max(0, (i.line || 1) - 1) === diagnostic.range.start.line) &&
                i.message === diagnostic.message);
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
    extractIssueType(message) {
        const lowerMsg = message.toLowerCase();
        // Common patterns
        if (lowerMsg.includes('unused') || lowerMsg.includes('dead code'))
            return 'unused-code';
        if (lowerMsg.includes('error handling') || lowerMsg.includes('try') || lowerMsg.includes('catch'))
            return 'error-handling';
        if (lowerMsg.includes('type') || lowerMsg.includes('any'))
            return 'type-safety';
        if (lowerMsg.includes('null') || lowerMsg.includes('undefined'))
            return 'null-check';
        if (lowerMsg.includes('const') || lowerMsg.includes('let') || lowerMsg.includes('var'))
            return 'variable-declaration';
        if (lowerMsg.includes('async') || lowerMsg.includes('await') || lowerMsg.includes('promise'))
            return 'async-patterns';
        if (lowerMsg.includes('sql') || lowerMsg.includes('injection'))
            return 'security-injection';
        if (lowerMsg.includes('password') || lowerMsg.includes('secret') || lowerMsg.includes('key'))
            return 'security-secrets';
        if (lowerMsg.includes('performance') || lowerMsg.includes('loop') || lowerMsg.includes('optimization'))
            return 'performance';
        if (lowerMsg.includes('naming') || lowerMsg.includes('convention'))
            return 'naming-convention';
        if (lowerMsg.includes('comment') || lowerMsg.includes('documentation'))
            return 'documentation';
        return 'general';
    }
}
exports.QuickFixProvider = QuickFixProvider;
//# sourceMappingURL=quickFix.js.map