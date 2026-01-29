import * as vscode from 'vscode';
import { DiagnosticsManager } from './diagnostics';
export declare class ReviewService {
    private diagnosticsManager;
    private outputChannel;
    private _onReviewComplete;
    readonly onReviewComplete: vscode.Event<void>;
    constructor(diagnosticsManager: DiagnosticsManager);
    /**
     * Review a single file using the API server
     */
    reviewFile(document: vscode.TextDocument): Promise<void>;
    /**
     * Review all files in the workspace
     */
    reviewWorkspace(): Promise<void>;
    /**
     * Get issues from the stats.json file
     */
    private getIssuesFromStats;
    /**
     * Call the review API server
     */
    private callReviewAPI;
    /**
     * Get language identifier from filename
     */
    private getLanguageFromFilename;
    /**
     * Trigger a Python-based review for a file (legacy fallback)
     */
    private triggerPythonReview;
    /**
     * Find project root containing scripts/watcher.py
     * First checks all open workspace folders, then walks up from the file
     */
    private findProjectRoot;
}
//# sourceMappingURL=reviewService.d.ts.map