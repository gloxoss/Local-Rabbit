#!/usr/bin/env python3
"""
Local CodeRabbit - Feature Test Suite
Validates all major features without external dependencies when possible.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test(name, passed, message=""):
    status = f"{Colors.GREEN}[PASS]{Colors.RESET}" if passed else f"{Colors.RED}[FAIL]{Colors.RESET}"
    print(f"  {status} {name}")
    if message and not passed:
        print(f"         {Colors.YELLOW}{message}{Colors.RESET}")

def print_section(name):
    print(f"\n{Colors.CYAN}{Colors.BOLD}[*] {name}{Colors.RESET}")
    print("-" * 50)
    sys.stdout.flush()

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent

results = {"passed": 0, "failed": 0, "skipped": 0}

def test(name):
    """Decorator for test functions"""
    def decorator(func):
        def wrapper():
            try:
                passed, msg = func()
                print_test(name, passed, msg)
                if passed:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                return passed
            except Exception as e:
                print_test(name, False, str(e))
                results["failed"] += 1
                return False
        return wrapper
    return decorator

# =============================================================================
# FILE STRUCTURE TESTS
# =============================================================================

print_section("File Structure")

@test("Core scripts exist")
def test_core_scripts():
    required = ["watcher.py", "pre-commit.py", "model_provider.py", "auto-fix.py"]
    missing = [f for f in required if not (PROJECT_ROOT / "scripts" / f).exists()]
    return len(missing) == 0, f"Missing: {missing}"

@test("PowerShell scripts exist")
def test_powershell_scripts():
    required = ["setup.ps1", "start.ps1", "start-watcher.ps1", "install-hook.ps1"]
    missing = [f for f in required if not (PROJECT_ROOT / "scripts" / f).exists()]
    return len(missing) == 0, f"Missing: {missing}"

@test("Configuration files exist")
def test_config_files():
    required = ["config.json", "prompts.json", ".env.example", "docker-compose.yml"]
    missing = [f for f in required if not (PROJECT_ROOT / f).exists()]
    return len(missing) == 0, f"Missing: {missing}"

@test("Dashboard HTML exists")
def test_dashboard():
    return (PROJECT_ROOT / "dashboard.html").exists(), "dashboard.html not found"

@test("Prompt Builder HTML exists")
def test_prompt_builder():
    return (PROJECT_ROOT / "prompt-builder.html").exists(), "prompt-builder.html not found"

@test("GitHub Actions workflow exists")
def test_github_workflow():
    workflow_path = PROJECT_ROOT / ".github" / "workflows"
    return workflow_path.exists() and any(workflow_path.glob("*.yml")), "No workflow files found"

test_core_scripts()
test_powershell_scripts()
test_config_files()
test_dashboard()
test_prompt_builder()
test_github_workflow()

# =============================================================================
# CONFIG VALIDATION TESTS
# =============================================================================

print_section("Configuration Validation")

@test("config.json is valid JSON")
def test_config_json_valid():
    try:
        with open(PROJECT_ROOT / "config.json") as f:
            config = json.load(f)
        return True, ""
    except json.JSONDecodeError as e:
        return False, str(e)

@test("config.json has required fields")
def test_config_fields():
    with open(PROJECT_ROOT / "config.json") as f:
        config = json.load(f)
    required = ["min_severity", "history", "notifications"]
    missing = [f for f in required if f not in config]
    return len(missing) == 0, f"Missing fields: {missing}"

@test("prompts.json is valid JSON")
def test_prompts_json_valid():
    try:
        with open(PROJECT_ROOT / "prompts.json") as f:
            prompts = json.load(f)
        return True, ""
    except json.JSONDecodeError as e:
        return False, str(e)

@test("prompts.json has review_prompt")
def test_prompts_has_prompt():
    with open(PROJECT_ROOT / "prompts.json") as f:
        prompts = json.load(f)
    return "review_prompt" in prompts, "Missing 'review_prompt' field"

test_config_json_valid()
test_config_fields()
test_prompts_json_valid()
test_prompts_has_prompt()

# =============================================================================
# WATCHER MODULE TESTS
# =============================================================================

print_section("Watcher Module")

@test("watcher.py imports successfully")
def test_watcher_import():
    try:
        # Add scripts to path
        scripts_path = PROJECT_ROOT / "scripts"
        sys.path.insert(0, str(scripts_path))
        
        # Try to import core functions
        spec = __import__("watcher")
        required_funcs = ["load_config", "load_custom_prompt", "parse_severity", "save_to_history"]
        missing = [f for f in required_funcs if not hasattr(spec, f)]
        return len(missing) == 0, f"Missing functions: {missing}"
    except Exception as e:
        return False, str(e)

@test("parse_severity detects critical issues")
def test_parse_critical():
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from watcher import parse_severity
    
    text = "🔴 CRITICAL: SQL injection vulnerability\n🟡 WARNING: Missing validation"
    result = parse_severity(text)
    return len(result["critical"]) == 1 and len(result["warning"]) == 1, f"Got: {result}"

@test("parse_severity handles clean code")
def test_parse_clean():
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from watcher import parse_severity
    
    text = "✅ No issues found"
    result = parse_severity(text)
    total = len(result["critical"]) + len(result["warning"]) + len(result["suggestion"])
    return total == 0, f"Expected 0 issues, got {total}"

test_watcher_import()
test_parse_critical()
test_parse_clean()

# =============================================================================
# MODEL PROVIDER TESTS
# =============================================================================

print_section("Model Provider")

@test("model_provider.py imports successfully")
def test_provider_import():
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        spec = __import__("model_provider")
        return hasattr(spec, "ModelProvider"), "Missing ModelProvider class"
    except Exception as e:
        return False, str(e)

test_provider_import()

# =============================================================================
# DASHBOARD TESTS
# =============================================================================

print_section("Dashboard")

@test("dashboard.html has Chart.js")
def test_dashboard_chartjs():
    content = (PROJECT_ROOT / "dashboard.html").read_text(encoding='utf-8')
    return "chart.js" in content.lower(), "Chart.js not found"

@test("dashboard.html has stats elements")
def test_dashboard_stats():
    content = (PROJECT_ROOT / "dashboard.html").read_text(encoding='utf-8')
    required = ["statFiles", "statCritical", "statWarning", "statSuggestion"]
    missing = [r for r in required if r not in content]
    return len(missing) == 0, f"Missing elements: {missing}"

@test("dashboard.html fetches stats.json")
def test_dashboard_fetch():
    content = (PROJECT_ROOT / "dashboard.html").read_text(encoding='utf-8')
    return "reviews/stats.json" in content, "stats.json fetch not found"

@test("dashboard.html has auto-refresh")
def test_dashboard_autorefresh():
    content = (PROJECT_ROOT / "dashboard.html").read_text(encoding='utf-8')
    return "setInterval" in content and "loadStats" in content, "Auto-refresh not configured"

test_dashboard_chartjs()
test_dashboard_stats()
test_dashboard_fetch()
test_dashboard_autorefresh()

# =============================================================================
# DOCKER TESTS
# =============================================================================

print_section("Docker Configuration")

@test("docker-compose.yml is valid")
def test_docker_compose():
    try:
        import yaml
        with open(PROJECT_ROOT / "docker-compose.yml") as f:
            config = yaml.safe_load(f)
        return "services" in config, "No services defined"
    except ImportError:
        return True, "YAML not installed, skipping"
    except Exception as e:
        return False, str(e)

@test("PR-Agent settings exist")
def test_pr_agent_settings():
    settings_path = PROJECT_ROOT / "pr-agent" / "settings"
    if not settings_path.exists():
        return False, "settings folder not found"
    return (settings_path / "configuration.toml").exists(), "configuration.toml not found"

test_docker_compose()
test_pr_agent_settings()

# =============================================================================
# SUMMARY
# =============================================================================

print(f"\n{'='*50}")
print(f"{Colors.BOLD}=== TEST SUMMARY ==={Colors.RESET}")
print(f"{'='*50}")
print(f"  {Colors.GREEN}Passed: {results['passed']}{Colors.RESET}")
print(f"  {Colors.RED}Failed: {results['failed']}{Colors.RESET}")
print(f"  Total:  {results['passed'] + results['failed']}")
print()

if results["failed"] == 0:
    print(f"{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.RESET}")
    sys.exit(0)
else:
    print(f"{Colors.RED}{Colors.BOLD}{results['failed']} test(s) failed{Colors.RESET}")
    sys.exit(1)
