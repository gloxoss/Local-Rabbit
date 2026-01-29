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
exports.ReviewService = void 0;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
class ReviewService {
    diagnosticsManager;
    outputChannel;
    // Event emitter for review completion
    _onReviewComplete = new vscode.EventEmitter();
    onReviewComplete = this._onReviewComplete.event;
    constructor(diagnosticsManager) {
        this.diagnosticsManager = diagnosticsManager;
        this.outputChannel = vscode.window.createOutputChannel('Local CodeRabbit');
    }
    /**
     * Review a single file using the API server
     */
    async reviewFile(document) {
        const filePath = document.uri.fsPath;
        const fileName = path.basename(filePath);
        const code = document.getText();
        this.outputChannel.appendLine(`\n--- Reviewing: ${fileName} ---`);
        this.outputChannel.show(true);
        try {
            // Get server URL from settings
            const config = vscode.workspace.getConfiguration('localCoderabbit');
            const serverUrl = config.get('serverUrl', 'http://localhost:8765');
            // Call the API server
            const issues = await this.callReviewAPI(serverUrl, code, fileName);
            if (issues.length > 0) {
                this.diagnosticsManager.setDiagnostics(document.uri, issues);
                this.outputChannel.appendLine(`Found ${issues.length} issues`);
            }
            else {
                this.diagnosticsManager.clearFile(document.uri);
                this.outputChannel.appendLine('✅ No issues found');
            }
            // Fire event to update TreeView
            this._onReviewComplete.fire();
        }
        catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            this.outputChannel.appendLine(`Error: ${message}`);
            // If server is not available, show helpful message
            if (message.includes('ECONNREFUSED')) {
                vscode.window.showWarningMessage('Local CodeRabbit server not running. Start with: docker-compose up -d', 'Show Instructions').then(selection => {
                    if (selection === 'Show Instructions') {
                        vscode.env.openExternal(vscode.Uri.parse('https://github.com/local-coderabbit'));
                    }
                });
            }
            else {
                vscode.window.showErrorMessage(`Review failed: ${message}`);
            }
        }
    }
    /**
     * Review all files in the workspace
     */
    async reviewWorkspace() {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showWarningMessage('No workspace folder open');
            return;
        }
        const supportedExtensions = ['.ts', '.tsx', '.js', '.jsx', '.py'];
        const files = await vscode.workspace.findFiles('**/*.{ts,tsx,js,jsx,py}', '**/node_modules/**');
        this.outputChannel.appendLine(`\n=== Workspace Review: ${files.length} files ===`);
        this.outputChannel.show(true);
        let totalIssues = 0;
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Local CodeRabbit: Reviewing workspace',
            cancellable: true
        }, async (progress, token) => {
            for (let i = 0; i < files.length; i++) {
                if (token.isCancellationRequested) {
                    break;
                }
                const file = files[i];
                const fileName = path.basename(file.fsPath);
                progress.report({
                    message: `${fileName} (${i + 1}/${files.length})`,
                    increment: 100 / files.length
                });
                try {
                    const document = await vscode.workspace.openTextDocument(file);
                    await this.reviewFile(document);
                    totalIssues += this.diagnosticsManager.getIssues(file.fsPath).length;
                }
                catch {
                    // Skip files that can't be opened
                }
            }
        });
        vscode.window.showInformationMessage(`Workspace review complete: ${totalIssues} issues in ${files.length} files`);
    }
    /**
     * Get issues from the stats.json file
     */
    async getIssuesFromStats(filePath) {
        const workspaceFolder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(filePath));
        if (!workspaceFolder) {
            return [];
        }
        const statsPath = path.join(workspaceFolder.uri.fsPath, 'reviews', 'stats.json');
        try {
            if (!fs.existsSync(statsPath)) {
                return [];
            }
            const statsContent = fs.readFileSync(statsPath, 'utf-8');
            const stats = JSON.parse(statsContent);
            // Find the most recent review for this file
            const relativePath = path.relative(workspaceFolder.uri.fsPath, filePath);
            const recentEntry = stats.recent?.find((r) => r.file === relativePath || r.file === filePath);
            if (!recentEntry) {
                return [];
            }
            // Convert stats entry to issues
            const issues = [];
            if (recentEntry.critical > 0) {
                issues.push({
                    file: filePath,
                    line: 1,
                    severity: 'critical',
                    message: `${recentEntry.critical} critical issue(s) detected`
                });
            }
            if (recentEntry.warning > 0) {
                issues.push({
                    file: filePath,
                    line: 1,
                    severity: 'warning',
                    message: `${recentEntry.warning} warning(s) detected`
                });
            }
            if (recentEntry.suggestion > 0) {
                issues.push({
                    file: filePath,
                    line: 1,
                    severity: 'suggestion',
                    message: `${recentEntry.suggestion} suggestion(s) available`
                });
            }
            return issues;
        }
        catch {
            return [];
        }
    }
    /**
     * Call the review API server
     */
    async callReviewAPI(serverUrl, code, filename) {
        const http = require('http');
        // Parse URL properly
        const url = new URL(serverUrl);
        const port = url.port ? parseInt(url.port) : 8765;
        this.outputChannel.appendLine(`Calling API: ${url.hostname}:${port}/api/review`);
        // Get workspace root for context loading
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const projectRoot = workspaceFolder?.uri.fsPath || '';
        const postData = JSON.stringify({
            code: code,
            filename: filename,
            language: this.getLanguageFromFilename(filename),
            project_root: projectRoot
        });
        return new Promise((resolve, reject) => {
            const req = http.request({
                hostname: url.hostname,
                port: port,
                path: '/api/review',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                }
            }, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => {
                    this.outputChannel.appendLine(`Response status: ${res.statusCode}`);
                    // Check if response looks like HTML
                    if (data.startsWith('<!') || data.startsWith('<html')) {
                        reject(new Error(`Server returned HTML instead of JSON. Is the API running on port ${port}?`));
                        return;
                    }
                    try {
                        const response = JSON.parse(data);
                        if (res.statusCode !== 200) {
                            reject(new Error(response.detail || `HTTP ${res.statusCode}`));
                            return;
                        }
                        // Convert API response to Issue format
                        const issues = response.issues.map((issue) => ({
                            file: filename,
                            line: issue.line || 1,
                            severity: issue.severity,
                            message: issue.message,
                            fixCode: issue.fixCode
                        }));
                        this.outputChannel.appendLine(`API returned ${issues.length} issues (model: ${response.model})`);
                        resolve(issues);
                    }
                    catch (e) {
                        this.outputChannel.appendLine(`Parse error. Raw data: ${data.substring(0, 200)}`);
                        reject(new Error(`Failed to parse response: ${e}`));
                    }
                });
            });
            req.on('error', (e) => {
                this.outputChannel.appendLine(`Request error: ${e.message}`);
                reject(e);
            });
            req.write(postData);
            req.end();
        });
    }
    /**
     * Get language identifier from filename
     */
    getLanguageFromFilename(filename) {
        const ext = path.extname(filename).toLowerCase();
        const langMap = {
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.py': 'python',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cs': 'csharp',
            '.cpp': 'cpp',
            '.c': 'c'
        };
        return langMap[ext] || 'text';
    }
    /**
     * Trigger a Python-based review for a file (legacy fallback)
     */
    async triggerPythonReview(filePath) {
        // Find the project root by looking for scripts/watcher.py
        let projectRoot = this.findProjectRoot(filePath);
        if (!projectRoot) {
            // Fallback: try workspace folder
            const workspaceFolder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(filePath));
            if (workspaceFolder) {
                projectRoot = workspaceFolder.uri.fsPath;
            }
        }
        if (!projectRoot) {
            this.outputChannel.appendLine('Could not determine project root');
            return [];
        }
        const scriptPath = path.join(projectRoot, 'scripts', 'watcher.py');
        if (!fs.existsSync(scriptPath)) {
            this.outputChannel.appendLine(`Script not found at: ${scriptPath}`);
            return [];
        }
        this.outputChannel.appendLine(`Project root: ${projectRoot}`);
        return new Promise((resolve) => {
            const { spawn } = require('child_process');
            const pythonCode = `
import sys, os
sys.path.insert(0, r'${projectRoot}')
os.chdir(r'${projectRoot}')

# Load .env file
env_path = r'${path.join(projectRoot, '.env')}'
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key.strip()] = val.strip()

from scripts.watcher import review_file, get_client, load_agent_context, load_custom_prompt
client = get_client()
agent_context = load_agent_context(r'${projectRoot}')
custom_prompt = load_custom_prompt(r'${projectRoot}')
result = review_file(client, r'${filePath}', agent_context, custom_prompt)
print(result if result else '')
`;
            const proc = spawn('python', ['-c', pythonCode], {
                cwd: projectRoot,
                env: { ...process.env }
            });
            let output = '';
            let error = '';
            proc.stdout.on('data', (data) => {
                output += data.toString();
            });
            proc.stderr.on('data', (data) => {
                error += data.toString();
            });
            proc.on('close', () => {
                if (error) {
                    this.outputChannel.appendLine(`Python: ${error.substring(0, 500)}`);
                }
                if (output) {
                    this.outputChannel.appendLine(`Got ${output.length} chars from Python`);
                    const issues = this.diagnosticsManager.parseReviewText(output, filePath);
                    resolve(issues);
                }
                else {
                    resolve([]);
                }
            });
            setTimeout(() => {
                proc.kill();
                this.outputChannel.appendLine('Review timed out (30s)');
                resolve([]);
            }, 30000);
        });
    }
    /**
     * Find project root containing scripts/watcher.py
     * First checks all open workspace folders, then walks up from the file
     */
    findProjectRoot(filePath) {
        // First, check ALL open workspace folders for one containing scripts/watcher.py
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders) {
            for (const folder of workspaceFolders) {
                if (fs.existsSync(path.join(folder.uri.fsPath, 'scripts', 'watcher.py'))) {
                    return folder.uri.fsPath;
                }
            }
        }
        // Fallback: walk up from the file
        let dir = path.dirname(filePath);
        for (let i = 0; i < 10; i++) {
            if (fs.existsSync(path.join(dir, 'scripts', 'watcher.py'))) {
                return dir;
            }
            const parent = path.dirname(dir);
            if (parent === dir)
                break;
            dir = parent;
        }
        return null;
    }
}
exports.ReviewService = ReviewService;
//# sourceMappingURL=reviewService.js.map