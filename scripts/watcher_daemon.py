"""
Watcher Daemon
Monitors filesystem changes and triggers Cortex indexing.
"""

import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from scripts.cortex.indexer import get_indexer

class CodebaseEventHandler(FileSystemEventHandler):
    def __init__(self, project_root):
        self.project_root = project_root
        self.indexer = get_indexer()

    def on_modified(self, event):
        if not event.is_directory:
            print(f"👀 Watcher: File modified: {event.src_path}")
            self.indexer.index_file(event.src_path, self.project_root)

    def on_created(self, event):
        if not event.is_directory:
            print(f"👀 Watcher: File created: {event.src_path}")
            self.indexer.index_file(event.src_path, self.project_root)

    def on_moved(self, event):
        if not event.is_directory:
            print(f"👀 Watcher: File moved: {event.src_path} -> {event.dest_path}")
            self.indexer.index_file(event.dest_path, self.project_root)
            # Todo: Remove old path from index

class WatcherDaemon:
    def __init__(self, project_root):
        self.project_root = project_root
        self.observer = Observer()
        self.event_handler = CodebaseEventHandler(project_root)
        self._thread = None
        self._indexer = get_indexer()

    def start(self):
        """Start the watcher and trigger initial scan."""
        print("👀 Watcher: Starting daemon...")
        
        # 1. Start file system watcher
        self.observer.schedule(self.event_handler, self.project_root, recursive=True)
        self.observer.start()
        
        # 2. Trigger initial scan in background
        self._thread = threading.Thread(target=self._run_initial_scan)
        self._thread.daemon = True
        self._thread.start()

    def _run_initial_scan(self):
        """Run full scan on startup."""
        # Small delay to ensure server is up
        time.sleep(5)
        self._indexer.full_scan(self.project_root)

    def stop(self):
        self.observer.stop()
        self.observer.join()
