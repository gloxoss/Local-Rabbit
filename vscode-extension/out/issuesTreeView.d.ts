import * as vscode from 'vscode';
import { DiagnosticsManager, Issue } from './diagnostics';
/**
 * TreeView provider for displaying code review issues in the sidebar.
 * Groups issues by severity (Critical > Warning > Suggestion).
 */
export declare class IssuesTreeDataProvider implements vscode.TreeDataProvider<IssueTreeItem> {
    private diagnosticsManager;
    private _onDidChangeTreeData;
    readonly onDidChangeTreeData: vscode.Event<IssueTreeItem | undefined | null | void>;
    constructor(diagnosticsManager: DiagnosticsManager);
    /**
     * Refresh the tree view
     */
    refresh(): void;
    getTreeItem(element: IssueTreeItem): vscode.TreeItem;
    getChildren(element?: IssueTreeItem): Thenable<IssueTreeItem[]>;
    /**
     * Get severity group nodes (Critical, Warning, Suggestion)
     * Using VS Code theme icons instead of emojis for professional look
     */
    private getSeverityGroups;
    /**
     * Get issues grouped by file for a severity level
     */
    private getIssuesForSeverity;
    /**
     * Get issues for a specific file and severity
     */
    private getIssuesForFile;
    /**
     * Create a tree item for a single issue
     */
    private createIssueItem;
    /**
     * Get total issue count for badge
     */
    getTotalCount(): number;
}
/**
 * Tree item representing an issue, severity group, or file group
 */
export declare class IssueTreeItem extends vscode.TreeItem {
    readonly label: string;
    readonly collapsibleState: vscode.TreeItemCollapsibleState;
    readonly contextValue: string;
    readonly severity?: string | undefined;
    readonly filePath?: string | undefined;
    readonly issue?: Issue | undefined;
    constructor(label: string, collapsibleState: vscode.TreeItemCollapsibleState, contextValue: string, severity?: string | undefined, filePath?: string | undefined, issue?: Issue | undefined);
}
//# sourceMappingURL=issuesTreeView.d.ts.map