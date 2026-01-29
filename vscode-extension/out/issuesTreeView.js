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
exports.IssueTreeItem = exports.IssuesTreeDataProvider = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
/**
 * TreeView provider for displaying code review issues in the sidebar.
 * Groups issues by severity (Critical > Warning > Suggestion).
 */
class IssuesTreeDataProvider {
    diagnosticsManager;
    _onDidChangeTreeData = new vscode.EventEmitter();
    onDidChangeTreeData = this._onDidChangeTreeData.event;
    constructor(diagnosticsManager) {
        this.diagnosticsManager = diagnosticsManager;
    }
    /**
     * Refresh the tree view
     */
    refresh() {
        this._onDidChangeTreeData.fire();
    }
    getTreeItem(element) {
        return element;
    }
    getChildren(element) {
        if (!element) {
            // Root level - return severity groups
            return Promise.resolve(this.getSeverityGroups());
        }
        else if (element.contextValue === 'severity-group') {
            // Severity group - return issues of this severity
            return Promise.resolve(this.getIssuesForSeverity(element.severity));
        }
        else if (element.contextValue === 'file-group') {
            // File group - return issues for this file
            return Promise.resolve(this.getIssuesForFile(element.filePath, element.severity));
        }
        return Promise.resolve([]);
    }
    /**
     * Get severity group nodes (Critical, Warning, Suggestion)
     * Using VS Code theme icons instead of emojis for professional look
     */
    getSeverityGroups() {
        const allIssues = this.diagnosticsManager.getAllIssues();
        const groups = [];
        const severities = [
            {
                key: 'critical',
                icon: '',
                label: 'Critical',
                themeIcon: 'error',
                color: new vscode.ThemeColor('errorForeground')
            },
            {
                key: 'warning',
                icon: '',
                label: 'Warning',
                themeIcon: 'warning',
                color: new vscode.ThemeColor('editorWarning.foreground')
            },
            {
                key: 'suggestion',
                icon: '',
                label: 'Suggestions',
                themeIcon: 'lightbulb',
                color: new vscode.ThemeColor('editorInfo.foreground')
            }
        ];
        for (const sev of severities) {
            const issues = allIssues.filter(i => i.severity === sev.key);
            if (issues.length > 0) {
                const item = new IssueTreeItem(`${sev.label} (${issues.length})`, vscode.TreeItemCollapsibleState.Expanded, 'severity-group', sev.key);
                item.iconPath = new vscode.ThemeIcon(sev.themeIcon, sev.color);
                groups.push(item);
            }
        }
        if (groups.length === 0) {
            const emptyItem = new IssueTreeItem('No issues found', vscode.TreeItemCollapsibleState.None, 'empty');
            emptyItem.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('testing.iconPassed'));
            groups.push(emptyItem);
        }
        return groups;
    }
    /**
     * Get issues grouped by file for a severity level
     */
    getIssuesForSeverity(severity) {
        const allIssues = this.diagnosticsManager.getAllIssues();
        const issues = allIssues.filter(i => i.severity === severity);
        // Group by file
        const byFile = new Map();
        for (const issue of issues) {
            const existing = byFile.get(issue.file) || [];
            existing.push(issue);
            byFile.set(issue.file, existing);
        }
        const items = [];
        for (const [filePath, fileIssues] of byFile) {
            const fileName = path.basename(filePath);
            if (fileIssues.length === 1) {
                // Single issue - show directly
                const issue = fileIssues[0];
                items.push(this.createIssueItem(issue, fileName));
            }
            else {
                // Multiple issues - create file group
                const item = new IssueTreeItem(`${fileName} (${fileIssues.length})`, vscode.TreeItemCollapsibleState.Collapsed, 'file-group', severity, filePath);
                item.iconPath = new vscode.ThemeIcon('file');
                items.push(item);
            }
        }
        return items;
    }
    /**
     * Get issues for a specific file and severity
     */
    getIssuesForFile(filePath, severity) {
        const allIssues = this.diagnosticsManager.getAllIssues();
        const issues = allIssues.filter(i => i.file === filePath && i.severity === severity);
        const fileName = path.basename(filePath);
        return issues.map(issue => this.createIssueItem(issue, fileName));
    }
    /**
     * Create a tree item for a single issue
     */
    createIssueItem(issue, fileName) {
        const label = `${fileName}:${issue.line}`;
        const item = new IssueTreeItem(label, vscode.TreeItemCollapsibleState.None, 'issue', issue.severity, issue.file, issue);
        // Truncated message as description
        const maxLen = 50;
        item.description = issue.message.length > maxLen
            ? issue.message.substring(0, maxLen) + '...'
            : issue.message;
        // Full message as tooltip
        item.tooltip = new vscode.MarkdownString(`**${issue.severity.toUpperCase()}** - Line ${issue.line}\n\n${issue.message}`);
        // Click command to navigate
        item.command = {
            command: 'localCoderabbit.goToIssue',
            title: 'Go to Issue',
            arguments: [issue]
        };
        // Icon based on severity
        const iconMap = {
            'critical': 'error',
            'warning': 'warning',
            'suggestion': 'lightbulb'
        };
        item.iconPath = new vscode.ThemeIcon(iconMap[issue.severity] || 'circle');
        return item;
    }
    /**
     * Get total issue count for badge
     */
    getTotalCount() {
        return this.diagnosticsManager.getAllIssues().length;
    }
}
exports.IssuesTreeDataProvider = IssuesTreeDataProvider;
/**
 * Tree item representing an issue, severity group, or file group
 */
class IssueTreeItem extends vscode.TreeItem {
    label;
    collapsibleState;
    contextValue;
    severity;
    filePath;
    issue;
    constructor(label, collapsibleState, contextValue, severity, filePath, issue) {
        super(label, collapsibleState);
        this.label = label;
        this.collapsibleState = collapsibleState;
        this.contextValue = contextValue;
        this.severity = severity;
        this.filePath = filePath;
        this.issue = issue;
    }
}
exports.IssueTreeItem = IssueTreeItem;
//# sourceMappingURL=issuesTreeView.js.map