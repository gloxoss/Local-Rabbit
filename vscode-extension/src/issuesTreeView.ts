import * as vscode from 'vscode';
import * as path from 'path';
import { DiagnosticsManager, Issue } from './diagnostics';

/**
 * TreeView provider for displaying code review issues in the sidebar.
 * Groups issues by severity (Critical > Warning > Suggestion).
 */
export class IssuesTreeDataProvider implements vscode.TreeDataProvider<IssueTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<IssueTreeItem | undefined | null | void> =
        new vscode.EventEmitter<IssueTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<IssueTreeItem | undefined | null | void> =
        this._onDidChangeTreeData.event;

    constructor(private diagnosticsManager: DiagnosticsManager) { }

    /**
     * Refresh the tree view
     */
    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: IssueTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: IssueTreeItem): Thenable<IssueTreeItem[]> {
        if (!element) {
            // Root level - return severity groups
            return Promise.resolve(this.getSeverityGroups());
        } else if (element.contextValue === 'severity-group') {
            // Severity group - return issues of this severity
            return Promise.resolve(this.getIssuesForSeverity(element.severity!));
        } else if (element.contextValue === 'file-group') {
            // File group - return issues for this file
            return Promise.resolve(this.getIssuesForFile(element.filePath!, element.severity!));
        }
        return Promise.resolve([]);
    }

    /**
     * Get severity group nodes (Critical, Warning, Suggestion)
     * Using VS Code theme icons instead of emojis for professional look
     */
    private getSeverityGroups(): IssueTreeItem[] {
        const allIssues = this.diagnosticsManager.getAllIssues();
        const groups: IssueTreeItem[] = [];

        const severities: Array<{
            key: 'critical' | 'warning' | 'suggestion',
            icon: string,
            label: string,
            themeIcon: string,
            color?: vscode.ThemeColor
        }> = [
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
                const item = new IssueTreeItem(
                    `${sev.label} (${issues.length})`,
                    vscode.TreeItemCollapsibleState.Expanded,
                    'severity-group',
                    sev.key
                );
                item.iconPath = new vscode.ThemeIcon(sev.themeIcon, sev.color);
                groups.push(item);
            }
        }

        if (groups.length === 0) {
            const emptyItem = new IssueTreeItem(
                'No issues found',
                vscode.TreeItemCollapsibleState.None,
                'empty'
            );
            emptyItem.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('testing.iconPassed'));
            groups.push(emptyItem);
        }

        return groups;
    }


    /**
     * Get issues grouped by file for a severity level
     */
    private getIssuesForSeverity(severity: string): IssueTreeItem[] {
        const allIssues = this.diagnosticsManager.getAllIssues();
        const issues = allIssues.filter(i => i.severity === severity);

        // Group by file
        const byFile = new Map<string, Issue[]>();
        for (const issue of issues) {
            const existing = byFile.get(issue.file) || [];
            existing.push(issue);
            byFile.set(issue.file, existing);
        }

        const items: IssueTreeItem[] = [];
        for (const [filePath, fileIssues] of byFile) {
            const fileName = path.basename(filePath);
            if (fileIssues.length === 1) {
                // Single issue - show directly
                const issue = fileIssues[0];
                items.push(this.createIssueItem(issue, fileName));
            } else {
                // Multiple issues - create file group
                const item = new IssueTreeItem(
                    `${fileName} (${fileIssues.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed,
                    'file-group',
                    severity,
                    filePath
                );
                item.iconPath = new vscode.ThemeIcon('file');
                items.push(item);
            }
        }

        return items;
    }

    /**
     * Get issues for a specific file and severity
     */
    private getIssuesForFile(filePath: string, severity: string): IssueTreeItem[] {
        const allIssues = this.diagnosticsManager.getAllIssues();
        const issues = allIssues.filter(i => i.file === filePath && i.severity === severity);
        const fileName = path.basename(filePath);

        return issues.map(issue => this.createIssueItem(issue, fileName));
    }

    /**
     * Create a tree item for a single issue
     */
    private createIssueItem(issue: Issue, fileName: string): IssueTreeItem {
        const label = `${fileName}:${issue.line}`;
        const item = new IssueTreeItem(
            label,
            vscode.TreeItemCollapsibleState.None,
            'issue',
            issue.severity,
            issue.file,
            issue
        );

        // Truncated message as description
        const maxLen = 50;
        item.description = issue.message.length > maxLen
            ? issue.message.substring(0, maxLen) + '...'
            : issue.message;

        // Full message as tooltip
        item.tooltip = new vscode.MarkdownString(
            `**${issue.severity.toUpperCase()}** - Line ${issue.line}\n\n${issue.message}`
        );

        // Click command to navigate
        item.command = {
            command: 'localCoderabbit.goToIssue',
            title: 'Go to Issue',
            arguments: [issue]
        };

        // Icon based on severity
        const iconMap: Record<string, string> = {
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
    getTotalCount(): number {
        return this.diagnosticsManager.getAllIssues().length;
    }
}

/**
 * Tree item representing an issue, severity group, or file group
 */
export class IssueTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextValue: string,
        public readonly severity?: string,
        public readonly filePath?: string,
        public readonly issue?: Issue
    ) {
        super(label, collapsibleState);
    }
}
