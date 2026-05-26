#!/usr/bin/env python3
"""
Local CodeRabbit - Orchestrator Daemon
Central daemon that ties watcher + scanners + reports + notifications
into an autonomous 24/7 AI auditor.

Modes:
  - watch:    Real-time file watching (like watcher.py but event-based)
  - audit:    Scheduled full codebase audits
  - combined: Both watch + scheduled audits (default)

Usage:
  python scripts/orchestrator.py                    # Combined mode
  python scripts/orchestrator.py --mode watch       # Watch only
  python scripts/orchestrator.py --mode audit       # Audit only
  python scripts/orchestrator.py --audit-now        # Run audit immediately and exit
  python scripts/orchestrator.py --dry-run --once   # Dry run (no AI calls)
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Force UTF-8 output for Windows PowerShell
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure scripts dir is in sys.path
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Load .env if python-dotenv available
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# ─── Direct Imports (SOLID modules) ──────────────────────────────────────────
from config import load_config, load_custom_prompt, load_agent_context, DEFAULT_CONFIG
from client import get_client

WATCHER_AVAILABLE = False
try:
    from watcher import process_file_review, find_files, get_file_hash
    WATCHER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Watcher module unavailable: {e}")


def _import_watchdog():
    """Import watchdog for event-based file watching."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        return Observer, FileSystemEventHandler
    except ImportError:
        logging.warning("watchdog not installed. Using polling fallback. Install: pip install watchdog")
        return None, None


# ─── Logging Setup ───────────────────────────────────────────────────────────

def setup_logging(log_file: str = None):
    """Configure logging to file and console."""
    log_path = Path(log_file) if log_file else PROJECT_ROOT / "data" / "orchestrator.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_path), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_path


# ─── Config ──────────────────────────────────────────────────────────────────

# Orchestrator-specific defaults (merged on top of config.py's DEFAULT_CONFIG)
_ORCHESTRATOR_DEFAULTS = {
    "orchestrator": {"mode": "combined", "log_file": "data/orchestrator.log", "projects": ["."]},
    "schedule": {"daily_audit": "18:00", "enabled": True},
    "email": {
        "enabled": False, "smtp_host": "", "smtp_port": 587, "smtp_user": "",
        "smtp_password_env": "SMTP_PASSWORD", "from": "", "to": [],
        "on_critical": True, "daily_digest": True,
    },
}


def load_orchestrator_config() -> dict:
    """Load config.json reusing config.py, then merge orchestrator defaults."""
    config = load_config(str(PROJECT_ROOT))
    for key, val in _ORCHESTRATOR_DEFAULTS.items():
        if key not in config:
            config[key] = val
        elif isinstance(val, dict):
            for k, v in val.items():
                config[key].setdefault(k, v)
    return config


# ─── Event-Based File Watcher ────────────────────────────────────────────────

class CodeChangeHandler:
    """Handles file change events and queues them for review."""

    def __init__(self, project_root: str, config: dict, dry_run: bool = False):
        self.project_root = os.path.abspath(project_root)
        self.config = config
        self.dry_run = dry_run
        self.pending = {}
        self.lock = threading.Lock()
        self.debounce = config.get("debounce_seconds", 3)
        self.extensions = set(config.get("watch_extensions", DEFAULT_CONFIG["watch_extensions"]))
        self.ignore_dirs = set(config.get("ignore_dirs", DEFAULT_CONFIG["ignore_dirs"]))

        # Initialize AI client and context via SOLID modules
        self.client = None
        self.agent_context = ""
        self.custom_prompt = ""

        if not dry_run and WATCHER_AVAILABLE:
            self.client = get_client()
            self.agent_context = load_agent_context(self.project_root)
            self.custom_prompt = load_custom_prompt(self.project_root)

    def should_process(self, path: str) -> bool:
        """Check if file should be reviewed."""
        p = Path(path)
        if p.suffix not in self.extensions:
            return False
        if any(ignored in p.parts for ignored in self.ignore_dirs):
            return False
        return True

    def on_file_changed(self, path: str):
        """Queue a file for review after debounce."""
        if not self.should_process(path):
            return
        with self.lock:
            self.pending[path] = time.time()

    def process_pending(self):
        """Process files that have passed the debounce window."""
        now = time.time()
        to_review = []

        with self.lock:
            for path, ts in list(self.pending.items()):
                if now - ts >= self.debounce:
                    to_review.append(path)
            for path in to_review:
                del self.pending[path]

        for filepath in to_review:
            if self.dry_run:
                logging.info(f"[DRY RUN] Would review: {filepath}")
            elif WATCHER_AVAILABLE and self.client:
                try:
                    process_file_review(
                        filepath, self.project_root, self.config,
                        self.client, self.agent_context, self.custom_prompt
                    )
                except Exception as e:
                    logging.error(f"Review failed for {filepath}: {e}")


def _create_watchdog_handler(change_handler: CodeChangeHandler):
    """Create a watchdog FileSystemEventHandler that delegates to CodeChangeHandler."""
    _, FileSystemEventHandler = _import_watchdog()
    if FileSystemEventHandler is None:
        return None

    class WatchdogAdapter(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory:
                change_handler.on_file_changed(event.src_path)

        def on_created(self, event):
            if not event.is_directory:
                change_handler.on_file_changed(event.src_path)

    return WatchdogAdapter()


# ─── Daily Audit ─────────────────────────────────────────────────────────────

def run_daily_audit(project_path: str, config: dict, dry_run: bool = False) -> dict:
    """Run a full codebase audit on a project.

    Delegates to daily_audit.run_audit() which provides health scoring,
    security scanning, report generation, and notification delivery.
    """
    try:
        from daily_audit import run_audit
        logging.info(f"{'[DRY RUN] ' if dry_run else ''}Starting daily audit: {project_path}")
        results = run_audit(
            project_path=project_path,
            dry_run=dry_run,
            changed_only=False,
            output_format="text",
        )
        logging.info(f"  ✅ Audit complete for {project_path}")
        return results
    except ImportError:
        logging.error("  ❌ daily_audit module not available")
        return {"project": project_path, "errors": ["daily_audit module not available"]}
    except Exception as e:
        logging.error(f"  ❌ Audit failed: {e}")
        return {"project": project_path, "errors": [str(e)]}


# ─── Scheduler ───────────────────────────────────────────────────────────────

class AuditScheduler:
    """Schedule-based audit runner using threading."""

    def __init__(self, config: dict, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self._stop_event = threading.Event()
        self._thread = None
        self._last_audit_date = None

    def start(self):
        """Start the scheduler in a background thread."""
        schedule_cfg = self.config.get("schedule", {})
        if not schedule_cfg.get("enabled", True):
            logging.info("⏰ Scheduler disabled in config")
            return

        audit_time = schedule_cfg.get("daily_audit", "18:00")
        logging.info(f"⏰ Scheduler started — daily audit at {audit_time}")

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self):
        """Main scheduler loop — checks every 30 seconds if it's time for an audit."""
        schedule_cfg = self.config.get("schedule", {})
        audit_time_str = schedule_cfg.get("daily_audit", "18:00")

        try:
            audit_hour, audit_minute = map(int, audit_time_str.split(":"))
        except ValueError:
            logging.error(f"Invalid schedule time: {audit_time_str}")
            return

        while not self._stop_event.is_set():
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # Check if we should run (within 1-minute window, haven't run today)
            if (now.hour == audit_hour and now.minute == audit_minute
                    and self._last_audit_date != today_str):
                self._last_audit_date = today_str
                self._run_scheduled_audit()

            self._stop_event.wait(30)  # Check every 30 seconds

    def _run_scheduled_audit(self):
        """Run audit on all configured projects."""
        projects = self.config.get("orchestrator", {}).get("projects", ["."])
        logging.info(f"⏰ Scheduled audit triggered for {len(projects)} project(s)")

        for project_path in projects:
            abs_path = str((PROJECT_ROOT / project_path).resolve())
            try:
                run_daily_audit(abs_path, self.config, self.dry_run)
            except Exception as e:
                logging.error(f"Scheduled audit failed for {project_path}: {e}")

    def run_now(self):
        """Trigger an immediate audit (for --audit-now flag)."""
        self._run_scheduled_audit()


# ─── Main Orchestrator ───────────────────────────────────────────────────────

class Orchestrator:
    """Main orchestrator that manages all subsystems."""

    def __init__(self, mode: str = "combined", dry_run: bool = False):
        self.mode = mode
        self.dry_run = dry_run
        self.config = load_orchestrator_config()
        self._shutdown = threading.Event()
        self._observer = None
        self._scheduler = None
        self._change_handler = None
        self._processor_thread = None

    def start(self):
        """Start the orchestrator."""
        log_file = self.config.get("orchestrator", {}).get("log_file", "data/orchestrator.log")
        log_path = setup_logging(str(PROJECT_ROOT / log_file))

        logging.info("=" * 60)
        logging.info("  🐰 LOCAL RABBIT ORCHESTRATOR")
        logging.info(f"  Mode: {self.mode.upper()}")
        logging.info(f"  Dry Run: {self.dry_run}")
        logging.info(f"  Log: {log_path}")
        logging.info("=" * 60)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if self.mode in ("watch", "combined"):
            self._start_watcher()

        if self.mode in ("audit", "combined"):
            self._start_scheduler()

        logging.info("🚀 Orchestrator running. Press Ctrl+C to stop.")
        self._wait_for_shutdown()

    def _start_watcher(self):
        """Start the file watcher subsystem."""
        if not WATCHER_AVAILABLE and not self.dry_run:
            logging.error("❌ Cannot start watcher: watcher module unavailable")
            return

        projects = self.config.get("orchestrator", {}).get("projects", ["."])
        project_path = str((PROJECT_ROOT / projects[0]).resolve())

        # Load project-specific config via SOLID module
        project_config = self.config.copy()
        project_config.update(load_config(project_path))

        self._change_handler = CodeChangeHandler(
            project_path, project_config, self.dry_run
        )

        # Try watchdog (event-based), fall back to polling
        Observer, _ = _import_watchdog()
        if Observer:
            handler = _create_watchdog_handler(self._change_handler)
            self._observer = Observer()
            self._observer.schedule(handler, project_path, recursive=True)
            self._observer.start()
            logging.info(f"👁️ File watcher started (watchdog): {project_path}")
        else:
            logging.info(f"👁️ File watcher started (polling): {project_path}")

        # Start pending-review processor thread
        self._processor_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._processor_thread.start()

    def _process_loop(self):
        """Continuously process pending file reviews."""
        while not self._shutdown.is_set():
            if self._change_handler:
                self._change_handler.process_pending()

            # If no watchdog, also poll for changes
            if self._observer is None and self._change_handler and WATCHER_AVAILABLE:
                try:
                    projects = self.config.get("orchestrator", {}).get("projects", ["."])
                    project_path = str((PROJECT_ROOT / projects[0]).resolve())
                    current = find_files(project_path, self.config)
                    if not hasattr(self, '_known_files'):
                        self._known_files = current
                    else:
                        for fp, fh in current.items():
                            if fp not in self._known_files or self._known_files[fp] != fh:
                                self._change_handler.on_file_changed(fp)
                        self._known_files = current
                except Exception as e:
                    logging.error(f"Polling error: {e}")

            self._shutdown.wait(1)

    def _start_scheduler(self):
        """Start the scheduled audit subsystem."""
        self._scheduler = AuditScheduler(self.config, self.dry_run)
        self._scheduler.start()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logging.info("\n🛑 Shutdown signal received...")
        self.stop()

    def stop(self):
        """Gracefully stop all subsystems."""
        self._shutdown.set()

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            logging.info("👁️ File watcher stopped")

        if self._scheduler:
            self._scheduler.stop()
            logging.info("⏰ Scheduler stopped")

        logging.info("🐰 Orchestrator stopped. Goodbye!")

    def _wait_for_shutdown(self):
        """Block main thread until shutdown."""
        try:
            while not self._shutdown.is_set():
                self._shutdown.wait(1)
        except KeyboardInterrupt:
            self.stop()

    def audit_now(self):
        """Run an immediate audit and exit."""
        log_file = self.config.get("orchestrator", {}).get("log_file", "data/orchestrator.log")
        setup_logging(str(PROJECT_ROOT / log_file))

        logging.info("=" * 60)
        logging.info("  🐰 LOCAL RABBIT — IMMEDIATE AUDIT")
        logging.info("=" * 60)

        projects = self.config.get("orchestrator", {}).get("projects", ["."])
        all_results = []
        for project_path in projects:
            abs_path = str((PROJECT_ROOT / project_path).resolve())
            result = run_daily_audit(abs_path, self.config, self.dry_run)
            all_results.append(result)

        return all_results


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🐰 Local Rabbit Orchestrator — 24/7 AI Auditor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode", choices=["watch", "audit", "combined"], default="combined",
        help="Operating mode (default: combined)",
    )
    parser.add_argument(
        "--audit-now", action="store_true",
        help="Run an immediate audit and exit",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate actions without making AI calls or sending emails",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run once and exit (useful with --dry-run)",
    )

    args = parser.parse_args()
    orchestrator = Orchestrator(mode=args.mode, dry_run=args.dry_run)

    if args.audit_now or args.once:
        results = orchestrator.audit_now()
        for r in results:
            health = (r.get("health") or {}).get("total_score", "?")
            security = (r.get("security") or {}).get("score", "?")
            print(f"\n📊 Health: {health}/100 | 🔒 Security: {security}/100")
        return

    orchestrator.start()


if __name__ == "__main__":
    main()
