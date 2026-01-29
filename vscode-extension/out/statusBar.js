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
exports.StatusBarManager = void 0;
const vscode = __importStar(require("vscode"));
class StatusBarManager {
    statusBarItem;
    isConnected = false;
    issueCount = {
        critical: 0,
        warning: 0,
        suggestion: 0
    };
    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.statusBarItem.command = 'localCoderabbit.showDashboard';
        this.updateDisplay();
        this.statusBarItem.show();
    }
    setConnected(connected) {
        this.isConnected = connected;
        this.updateDisplay();
    }
    setReviewing(fileName) {
        const shortName = fileName.split(/[/\\]/).pop() || fileName;
        this.statusBarItem.text = `$(sync~spin) Reviewing ${shortName}...`;
        this.statusBarItem.backgroundColor = undefined;
    }
    setIssueCount(counts) {
        this.issueCount = counts;
        this.updateDisplay();
    }
    showError(message) {
        this.statusBarItem.text = `$(error) ${message}`;
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    }
    updateDisplay() {
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
        }
        else {
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
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
            }
            else if (warning > 0) {
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
            }
            else {
                this.statusBarItem.backgroundColor = undefined;
            }
        }
    }
    dispose() {
        this.statusBarItem.dispose();
    }
}
exports.StatusBarManager = StatusBarManager;
//# sourceMappingURL=statusBar.js.map