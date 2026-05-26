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
exports.DiagnosticsManager = void 0;
const vscode = __importStar(require("vscode"));
class DiagnosticsManager {
    collection;
    issuesByFile = new Map();
    constructor() {
        this.collection = vscode.languages.createDiagnosticCollection('localCoderabbit');
    }
    /**
     * Set diagnostics for a file from parsed issues
     */
    setDiagnostics(uri, issues) {
        const diagnostics = issues.map(issue => {
            const line = Math.max(0, (issue.line || 1) - 1);
            const column = Math.max(0, (issue.column || 1) - 1);
            const range = new vscode.Range(new vscode.Position(line, column), new vscode.Position(line, Number.MAX_VALUE));
            const diagnostic = new vscode.Diagnostic(range, issue.message, this.getSeverity(issue.severity));
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
    parseReviewText(text, filePath) {
        const issues = [];
        const lines = text.split('\n');
        let currentIssue = null;
        let capturingCode = false;
        let codeBlock = '';
        const isHeader = (l) => {
            const u = l.toUpperCase();
            return (u.includes('[CRITICAL]') || l.includes('🔴')) ||
                (u.includes('[WARNING]') || l.includes('🟡')) ||
                (u.includes('[SUGGESTION]') || l.includes('🔵'));
        };
        for (const line of lines) {
            if (isHeader(line) && !capturingCode) {
                if (currentIssue)
                    issues.push(currentIssue);
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
        if (currentIssue)
            issues.push(currentIssue);
        return issues;
    }
    /**
     * Clear diagnostics for a specific file
     */
    clearFile(uri) {
        this.collection.delete(uri);
        this.issuesByFile.delete(uri.fsPath);
    }
    /**
     * Clear all diagnostics
     */
    clearAll() {
        this.collection.clear();
        this.issuesByFile.clear();
    }
    /**
     * Get all issues for a file
     */
    getIssues(filePath) {
        return this.issuesByFile.get(filePath) || [];
    }
    /**
     * Get all issues across all files
     */
    getAllIssues() {
        const allIssues = [];
        for (const issues of this.issuesByFile.values()) {
            allIssues.push(...issues);
        }
        return allIssues;
    }
    /**
     * Get total issue count
     */
    getTotalCount() {
        let critical = 0, warning = 0, suggestion = 0;
        for (const issues of this.issuesByFile.values()) {
            for (const issue of issues) {
                if (issue.severity === 'critical')
                    critical++;
                else if (issue.severity === 'warning')
                    warning++;
                else
                    suggestion++;
            }
        }
        return { critical, warning, suggestion };
    }
    getSeverity(severity) {
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
    extractLineNumber(text) {
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
    parseIssueLine(line, severity) {
        return {
            file: '',
            line: this.extractLineNumber(line) || 1,
            severity: severity,
            message: this.cleanMessage(line, severity.toUpperCase())
        };
    }
    cleanMessage(text, severity) {
        return text
            .replace(/🔴|🟡|🔵/g, '')
            .replace(new RegExp(severity + '\\s*:?', 'gi'), '')
            .replace(/line\s*\d+\s*:?/gi, '')
            .trim();
    }
    dispose() {
        this.collection.dispose();
    }
}
exports.DiagnosticsManager = DiagnosticsManager;
//# sourceMappingURL=diagnostics.js.map