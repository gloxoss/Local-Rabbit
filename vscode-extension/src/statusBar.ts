import * as vscode from 'vscode';

export class StatusBarManager implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;
    private isConnected: boolean = false;
    private issueCount: { critical: number; warning: number; suggestion: number } = {
        critical: 0,
        warning: 0,
        suggestion: 0
    };

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'localCoderabbit.showDashboard';
        this.updateDisplay();
        this.statusBarItem.show();
    }

    public setConnected(connected: boolean): void {
        this.isConnected = connected;
        this.updateDisplay();
    }

    public setReviewing(fileName: string): void {
        const shortName = fileName.split(/[/\\]/).pop() || fileName;
        this.statusBarItem.text = `$(sync~spin) Reviewing ${shortName}...`;
        this.statusBarItem.backgroundColor = undefined;
    }

    public setIssueCount(counts: { critical: number; warning: number; suggestion: number }): void {
        this.issueCount = counts;
        this.updateDisplay();
    }

    public showError(message: string): void {
        this.statusBarItem.text = `$(error) ${message}`;
        this.statusBarItem.backgroundColor = new vscode.ThemeColor(
            'statusBarItem.errorBackground'
        );
    }

    private updateDisplay(): void {
        const { critical, warning, suggestion } = this.issueCount;
        const total = critical + warning + suggestion;

        const icon = this.isConnected ? '$(rabbit)' : '$(debug-disconnect)';
        const connectionStatus = this.isConnected ? '' : ' [Offline]';

        if (total === 0) {
            this.statusBarItem.text = `${icon} CodeRabbit${connectionStatus}`;
            this.statusBarItem.tooltip = this.isConnected
                ? 'Local CodeRabbit - No issues found\nClick to open dashboard'
                : 'Local CodeRabbit - Not connected to API\nStart with: docker-compose up -d';
            this.statusBarItem.backgroundColor = undefined;
        } else {
            let text = `${icon}`;

            if (critical > 0) {
                text += ` $(error) ${critical}`;
            }
            if (warning > 0) {
                text += ` $(warning) ${warning}`;
            }
            if (suggestion > 0) {
                text += ` $(info) ${suggestion}`;
            }

            text += connectionStatus;

            this.statusBarItem.text = text;
            this.statusBarItem.tooltip = [
                'Local CodeRabbit Issues:',
                `  Critical: ${critical}`,
                `  Warnings: ${warning}`,
                `  Suggestions: ${suggestion}`,
                '',
                'Click to open dashboard'
            ].join('\n');

            // Set background color based on severity
            if (critical > 0) {
                this.statusBarItem.backgroundColor = new vscode.ThemeColor(
                    'statusBarItem.errorBackground'
                );
            } else if (warning > 0) {
                this.statusBarItem.backgroundColor = new vscode.ThemeColor(
                    'statusBarItem.warningBackground'
                );
            } else {
                this.statusBarItem.backgroundColor = undefined;
            }
        }
    }

    dispose(): void {
        this.statusBarItem.dispose();
    }
}
