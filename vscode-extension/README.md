# Local CodeRabbit - VS Code Extension

AI-powered code review with real-time diagnostics, fully offline with Ollama.

## Features

- **Inline Diagnostics**: Red/yellow/blue squiggles for issues directly in editor
- **Real-time Updates**: SSE connection to watcher for instant feedback
- **Auto-review on Save**: Automatically reviews files when you save
- **Status Bar**: Connection status + issue count at a glance
- **Keyboard Shortcut**: `Ctrl+Shift+R` to review current file

## Installation

### 1. Install Dependencies

```bash
cd vscode-extension
npm install
```

### 2. Compile

```bash
npm run compile
```

### 3. Package (Optional)

```bash
npm run package
# Creates local-coderabbit-1.0.0.vsix
```

### 4. Install in VS Code

**Option A: Development Mode**
1. Open this folder in VS Code
2. Press `F5` to launch Extension Development Host

**Option B: Install Package**
1. Run `npm run package`
2. In VS Code: Extensions > ... > Install from VSIX
3. Select the generated `.vsix` file

## Usage

### Prerequisites

Start the watcher in your project:
```bash
python scripts/watcher.py /path/to/your/project
```

The watcher starts an SSE server on `http://localhost:8765` for real-time updates.

### Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| Review Current File | `Ctrl+Shift+R` | Review active file |
| Review Workspace | - | Review all supported files |
| Toggle Auto-Review | - | Enable/disable review on save |
| Open Dashboard | - | Open web dashboard |
| Clear Diagnostics | - | Clear all issues |

### Configuration

Open VS Code Settings and search for "Local CodeRabbit":

| Setting | Default | Description |
|---------|---------|-------------|
| `serverUrl` | `http://localhost:8765` | SSE server URL |
| `autoReview` | `true` | Review files on save |
| `minSeverity` | `suggestion` | Minimum severity to show |
| `enableStatusBar` | `true` | Show status bar item |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ VS Code                                                         │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────────┐ │
│  │ Diagnostics   │   │ Status Bar    │   │ Commands          │ │
│  │ (squiggles)   │   │ (issue count) │   │ (review, clear)   │ │
│  └───────────────┘   └───────────────┘   └───────────────────┘ │
│          ▲                  ▲                     │             │
│          │                  │                     ▼             │
│  ┌───────┴──────────────────┴─────────────────────────────────┐ │
│  │                    SSE Client                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                             ▲                                   │
└─────────────────────────────┼───────────────────────────────────┘
                              │ SSE (Server-Sent Events)
┌─────────────────────────────┼───────────────────────────────────┐
│ Python Watcher              │                                   │
│  ┌──────────────────────────┴────────────────────────────────┐ │
│  │                    realtime_server.py                     │ │
│  │                    (SSE on :8765)                         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             ▲                                   │
│                             │ Reviews                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    watcher.py                             │ │
│  │                    (monitors files → AI review)           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             ▲                                   │
│                             │ LLM API                           │
│                     ┌───────────────────┐                       │
│                     │     Ollama        │                       │
│                     │ (local AI model)  │                       │
│                     └───────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## Development

### Project Structure

```
vscode-extension/
├── package.json        # Extension manifest
├── tsconfig.json       # TypeScript config
├── src/
│   ├── extension.ts    # Entry point
│   ├── diagnostics.ts  # Issue display
│   ├── statusBar.ts    # Status bar UI
│   ├── sseClient.ts    # Real-time connection
│   └── reviewService.ts # Review logic
└── out/                # Compiled JS
```

### Building Changes

```bash
npm run watch  # Auto-compile on changes
```

### Debugging

1. Open the extension folder in VS Code
2. Press F5 to launch Extension Development Host
3. Open a project with the watcher running
4. Save a file to trigger auto-review

## Troubleshooting

### "Not connected to watcher"

1. Ensure the watcher is running: `python scripts/watcher.py .`
2. Check the server URL in settings matches the watcher output
3. Check if port 8765 is available

### No diagnostics showing

1. Check the Output panel → "Local CodeRabbit" for errors
2. Ensure the file type is supported (.ts, .tsx, .js, .jsx, .py)
3. Try the "Review Current File" command manually

## License

MIT
