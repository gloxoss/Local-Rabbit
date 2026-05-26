#!/usr/bin/env python3
"""
Local CodeRabbit - Daily Audit Runner
Standalone script for running a complete codebase audit.

This is the entry point for manual or scheduled full audits.
It runs health score, security scan, and report generation,
then delivers results via email and webhooks.

Usage:
  python scripts/daily_audit.py                    # Audit current directory
  python scripts/daily_audit.py /path/to/project   # Audit specific project
  python scripts/daily_audit.py . --dry-run         # Simulate without AI calls
  python scripts/daily_audit.py . --format json     # Output as JSON
  python scripts/daily_audit.py . --changed-only    # Only audit git-changed files
"""

import os
import sys
import json
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure scripts dir is in sys.path
SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


# ─── Git Diff Awareness ─────────────────────────────────────────────────────

def get_changed_files(project_root: str, since: str = "HEAD~1") -> list[str]:
    """Get list of files changed since a given git ref.

    Args:
        project_root: Path to project
        since: Git ref to compare against (default: last commit)

    Returns:
        List of changed file paths (absolute)
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", since],
            capture_output=True, text=True, cwd=project_root, timeout=10,
        )
        if result.returncode == 0:
            files = [
                str((Path(project_root) / f.strip()).resolve())
                for f in result.stdout.strip().split("\n")
                if f.strip()
            ]
            return files
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: try unstaged changes
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, cwd=project_root, timeout=10,
        )
        if result.returncode == 0:
            files = [
                str((Path(project_root) / f.strip()).resolve())
                for f in result.stdout.strip().split("\n")
                if f.strip()
            ]
            return files
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return []


def get_last_audit_timestamp() -> str:
    """Get timestamp of the last audit from audit history."""
    audit_dir = PROJECT_ROOT / "data" / "audit_history"
    if not audit_dir.exists():
        return None

    audits = sorted(audit_dir.glob("audit-*.json"), reverse=True)
    if audits:
        try:
            data = json.loads(audits[0].read_text(encoding="utf-8"))
            return data.get("timestamp")
        except Exception:
            pass
    return None


# ─── Audit Runner ────────────────────────────────────────────────────────────

def run_audit(
    project_path: str,
    dry_run: bool = False,
    changed_only: bool = False,
    output_format: str = "text",
) -> dict:
    """Run a complete audit on a project.

    Returns:
        Dict with health, security, report, and metadata.
    """
    audit_start = datetime.now()
    root = Path(project_path).resolve()

    logging.info("=" * 60)
    logging.info("  🐰 LOCAL RABBIT — CODEBASE AUDIT")
    logging.info(f"  📁 Project: {root}")
    logging.info(f"  🕐 Started: {audit_start.strftime('%H:%M:%S')}")
    if changed_only:
        logging.info("  📝 Mode: Changed files only")
    logging.info("=" * 60)

    results = {
        "project": str(root),
        "timestamp": audit_start.isoformat(),
        "mode": "changed_only" if changed_only else "full",
        "health": None,
        "security": None,
        "report": None,
        "changed_files": [],
        "errors": [],
    }

    # Get changed files if requested
    if changed_only:
        changed = get_changed_files(str(root))
        results["changed_files"] = changed
        logging.info(f"\n📝 Changed files: {len(changed)}")
        for f in changed[:10]:
            logging.info(f"   • {os.path.relpath(f, str(root))}")
        if len(changed) > 10:
            logging.info(f"   ... and {len(changed) - 10} more")
        if not changed:
            logging.info("   No changes detected — auditing full codebase instead")
            changed_only = False

    # 1. Health Score
    logging.info("\n📊 PHASE 1: Health Score Analysis")
    logging.info("-" * 40)
    try:
        from health_score import analyze_directory, calculate_health_score, generate_health_report
        if not dry_run:
            metrics = analyze_directory(root)
            if changed_only and results["changed_files"]:
                # Filter to only changed files
                changed_set = set(results["changed_files"])
                metrics = [m for m in metrics if str(Path(m.path).resolve()) in changed_set]

            score = calculate_health_score(metrics)
            report_text = generate_health_report(score)
            results["health"] = {
                "total_score": score.total_score,
                "complexity": score.complexity_score,
                "maintainability": score.maintainability_score,
                "security": score.security_score,
                "test_coverage": score.test_coverage_score,
                "documentation": score.documentation_score,
                "files_analyzed": len(metrics),
                "details": score.details,
            }
            logging.info(report_text)
        else:
            logging.info("[DRY RUN] Would analyze health score")
    except ImportError:
        results["errors"].append("health_score module not available")
        logging.warning("⚠️ health_score module not available")
    except Exception as e:
        results["errors"].append(f"health_score: {e}")
        logging.error(f"❌ Health score error: {e}")

    # 2. Security Scan
    logging.info("\n🔒 PHASE 2: Security Scan")
    logging.info("-" * 40)
    try:
        from security_scan import run_full_scan, calculate_security_score, generate_text_report as gen_sec_report
        if not dry_run:
            sec_report = run_full_scan(root)
            sec_score = calculate_security_score(sec_report)
            sec_text = gen_sec_report(sec_report)
            results["security"] = {
                "score": sec_score,
                "secrets": len(sec_report.secrets),
                "vulnerabilities": len(sec_report.vulnerabilities),
                "sast_findings": len(sec_report.sast_findings),
                "text": sec_text,
            }
            logging.info(sec_text)
        else:
            logging.info("[DRY RUN] Would run security scan")
    except ImportError:
        results["errors"].append("security_scan module not available")
        logging.warning("⚠️ security_scan module not available")
    except Exception as e:
        results["errors"].append(f"security_scan: {e}")
        logging.error(f"❌ Security scan error: {e}")

    # 3. Report Generation
    logging.info("\n📝 PHASE 3: Report Generation")
    logging.info("-" * 40)
    try:
        from report_generator import generate_report
        reviews_dir = root / "reviews"
        if reviews_dir.exists() and not dry_run:
            report = generate_report(reviews_dir, format="detailed")
            results["report"] = report
            logging.info(report)
        elif dry_run:
            logging.info("[DRY RUN] Would generate report")
        else:
            logging.info("No reviews directory found — skipping report generation")
    except ImportError:
        results["errors"].append("report_generator module not available")
        logging.warning("⚠️ report_generator module not available")
    except Exception as e:
        results["errors"].append(f"report_generator: {e}")
        logging.error(f"❌ Report generation error: {e}")

    # 4. Save Results
    audit_dir = PROJECT_ROOT / "data" / "audit_history"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_dir / f"audit-{audit_start.strftime('%Y-%m-%d_%H%M%S')}.json"

    if not dry_run:
        try:
            # Create serializable copy (remove large text fields for JSON)
            save_data = json.loads(json.dumps(results, default=str))
            with open(audit_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2)
            logging.info(f"\n💾 Audit saved: {audit_file}")
        except Exception as e:
            logging.error(f"Failed to save audit: {e}")

    # 5. Send Notifications
    if not dry_run:
        _deliver_results(results)

    # Summary
    duration = (datetime.now() - audit_start).total_seconds()
    logging.info("\n" + "=" * 60)
    logging.info("  🐰 AUDIT COMPLETE")
    logging.info(f"  ⏱️  Duration: {duration:.1f}s")
    if results.get("health"):
        logging.info(f"  📊 Health: {results['health']['total_score']}/100")
    if results.get("security"):
        logging.info(f"  🔒 Security: {results['security']['score']}/100")
    if results.get("errors"):
        logging.info(f"  ⚠️  Errors: {len(results['errors'])}")
    logging.info("=" * 60)

    return results


def _deliver_results(results: dict):
    """Send audit results via configured channels."""
    config_path = PROJECT_ROOT / "config.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    email_cfg = config.get("email", {})

    # Build digest text
    parts = [
        f"🐰 LOCAL RABBIT — DAILY AUDIT REPORT",
        f"📅 {datetime.now().strftime('%A, %B %d, %Y at %H:%M')}",
        f"📁 Project: {results['project']}",
        "=" * 50,
    ]

    if results.get("health"):
        h = results["health"]
        parts.append(f"\n📊 HEALTH SCORE: {h['total_score']}/100")
        parts.append(f"   Files analyzed:  {h.get('files_analyzed', '?')}")
        parts.append(f"   Complexity:      {h['complexity']}%")
        parts.append(f"   Maintainability: {h['maintainability']}%")
        parts.append(f"   Security:        {h['security']}%")
        parts.append(f"   Test Coverage:   {h['test_coverage']}%")

    if results.get("security"):
        s = results["security"]
        parts.append(f"\n🔒 SECURITY SCORE: {s['score']}/100")
        parts.append(f"   Secrets:         {s['secrets']}")
        parts.append(f"   Vulnerabilities: {s['vulnerabilities']}")
        parts.append(f"   SAST findings:   {s['sast_findings']}")

    digest = "\n".join(parts)

    # Email
    if email_cfg.get("enabled") and email_cfg.get("daily_digest"):
        try:
            from email_reporter import send_daily_digest
            send_daily_digest(digest, email_cfg)
        except Exception as e:
            logging.error(f"Email delivery failed: {e}")

    # Webhooks
    try:
        from webhooks import notify_webhooks
        webhook_config = config.get("webhooks", {})
        if webhook_config.get("enabled"):
            issues = {
                "critical": [f"Health: {results.get('health', {}).get('total_score', '?')}/100"],
                "warning": [f"Security: {results.get('security', {}).get('score', '?')}/100"],
                "suggestion": [],
            }
            notify_webhooks(config, "Daily Audit Report", issues)
    except ImportError:
        pass
    except Exception as e:
        logging.error(f"Webhook delivery failed: {e}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🐰 Local Rabbit — Daily Codebase Audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project", nargs="?", default=".",
        help="Path to project to audit (default: current directory)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate without AI calls or sending notifications",
    )
    parser.add_argument(
        "--changed-only", action="store_true",
        help="Only audit files changed since last commit",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    results = run_audit(
        project_path=args.project,
        dry_run=args.dry_run,
        changed_only=args.changed_only,
        output_format=args.format,
    )

    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
