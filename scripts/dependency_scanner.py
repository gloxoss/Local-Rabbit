#!/usr/bin/env python3
"""
Local CodeRabbit - Dependency Vulnerability Scanner
Scans package dependencies for known vulnerabilities.
Uses GitHub Advisory Database and OSV (Open Source Vulnerabilities).
"""

import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class Vulnerability:
    """Represents a discovered vulnerability"""
    id: str
    package: str
    installed_version: str
    severity: str
    title: str
    description: str
    fixed_version: Optional[str]
    url: str
    source: str


def parse_package_json(path: Path) -> dict[str, str]:
    """Parse package.json and extract dependencies"""
    with open(path) as f:
        data = json.load(f)
    
    deps = {}
    deps.update(data.get("dependencies", {}))
    deps.update(data.get("devDependencies", {}))
    
    # Clean version strings
    for pkg, version in deps.items():
        # Remove ^ and ~ prefixes
        clean_version = re.sub(r'^[\^~>=<]+', '', version)
        deps[pkg] = clean_version.split(' ')[0]
    
    return deps


def parse_requirements_txt(path: Path) -> dict[str, str]:
    """Parse requirements.txt"""
    deps = {}
    
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Handle various formats: pkg==1.0, pkg>=1.0, pkg~=1.0
            match = re.match(r'^([a-zA-Z0-9_\-]+)[=<>~!]+(.+)$', line)
            if match:
                deps[match.group(1).lower()] = match.group(2)
            elif line and not line.startswith('-'):
                # Package without version
                pkg = line.split('[')[0]  # Remove extras like [dev]
                deps[pkg.lower()] = "*"
    
    return deps


def parse_poetry_lock(path: Path) -> dict[str, str]:
    """Parse poetry.lock (TOML format)"""
    deps = {}
    
    content = path.read_text()
    
    # Simple TOML parsing for package entries
    current_package = None
    for line in content.split('\n'):
        if line.startswith('name = "'):
            current_package = line.split('"')[1].lower()
        elif line.startswith('version = "') and current_package:
            version = line.split('"')[1]
            deps[current_package] = version
            current_package = None
    
    return deps


def parse_go_mod(path: Path) -> dict[str, str]:
    """Parse go.mod"""
    deps = {}
    
    content = path.read_text()
    
    # Find require blocks
    in_require = False
    for line in content.split('\n'):
        if line.strip() == 'require (':
            in_require = True
            continue
        if line.strip() == ')':
            in_require = False
            continue
        
        if in_require:
            match = re.match(r'\s*([^\s]+)\s+v?([^\s]+)', line)
            if match:
                deps[match.group(1)] = match.group(2)
    
    return deps


def parse_cargo_toml(path: Path) -> dict[str, str]:
    """Parse Cargo.toml for Rust dependencies"""
    deps = {}
    
    content = path.read_text()
    in_deps = False
    
    for line in content.split('\n'):
        if '[dependencies]' in line or '[dev-dependencies]' in line:
            in_deps = True
            continue
        if line.startswith('[') and in_deps:
            in_deps = False
            continue
        
        if in_deps:
            # Simple: pkg = "1.0.0"
            match = re.match(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]+)"', line)
            if match:
                deps[match.group(1)] = match.group(2)
            # Complex: pkg = { version = "1.0.0", ... }
            match = re.match(r'([a-zA-Z0-9_-]+)\s*=\s*\{.*version\s*=\s*"([^"]+)"', line)
            if match:
                deps[match.group(1)] = match.group(2)
    
    return deps


def detect_ecosystem(root: Path) -> tuple[str, dict[str, str]]:
    """Detect package ecosystem and parse dependencies"""
    
    if (root / "package.json").exists():
        return "npm", parse_package_json(root / "package.json")
    
    if (root / "requirements.txt").exists():
        return "pip", parse_requirements_txt(root / "requirements.txt")
    
    if (root / "poetry.lock").exists():
        return "pip", parse_poetry_lock(root / "poetry.lock")
    
    if (root / "Pipfile.lock").exists():
        # Parse Pipfile.lock (JSON format)
        with open(root / "Pipfile.lock") as f:
            data = json.load(f)
        deps = {}
        for pkg, info in data.get("default", {}).items():
            version = info.get("version", "").replace("==", "")
            deps[pkg.lower()] = version
        return "pip", deps
    
    if (root / "go.mod").exists():
        return "go", parse_go_mod(root / "go.mod")
    
    if (root / "Cargo.toml").exists():
        return "cargo", parse_cargo_toml(root / "Cargo.toml")
    
    return "unknown", {}


def query_osv(ecosystem: str, package: str, version: str) -> list[dict]:
    """Query OSV API for vulnerabilities"""
    osv_ecosystem_map = {
        "npm": "npm",
        "pip": "PyPI",
        "go": "Go",
        "cargo": "crates.io"
    }
    
    osv_eco = osv_ecosystem_map.get(ecosystem)
    if not osv_eco:
        return []
    
    url = "https://api.osv.dev/v1/query"
    payload = json.dumps({
        "package": {
            "name": package,
            "ecosystem": osv_eco
        },
        "version": version
    }).encode()
    
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
            return data.get("vulns", [])
    except Exception as e:
        return []


def get_severity_from_osv(vuln: dict) -> str:
    """Extract severity from OSV vulnerability"""
    severity_score = vuln.get("database_specific", {}).get("severity")
    if severity_score:
        return severity_score.upper()
    
    # Try CVSS
    for cvss in vuln.get("severity", []):
        score = cvss.get("score", "")
        if isinstance(score, (int, float)):
            if score >= 9.0:
                return "CRITICAL"
            elif score >= 7.0:
                return "HIGH"
            elif score >= 4.0:
                return "MEDIUM"
            else:
                return "LOW"
    
    return "UNKNOWN"


def get_fixed_version(vuln: dict) -> Optional[str]:
    """Extract fixed version from OSV vulnerability"""
    for affected in vuln.get("affected", []):
        for range_info in affected.get("ranges", []):
            for event in range_info.get("events", []):
                if "fixed" in event:
                    return event["fixed"]
    return None


def scan_dependencies(root: Path) -> list[Vulnerability]:
    """Scan dependencies for vulnerabilities"""
    ecosystem, deps = detect_ecosystem(root)
    
    if ecosystem == "unknown":
        return []
    
    vulnerabilities = []
    
    for package, version in deps.items():
        if version == "*":
            continue  # Can't check without version
        
        osv_vulns = query_osv(ecosystem, package, version)
        
        for vuln in osv_vulns:
            vulnerabilities.append(Vulnerability(
                id=vuln.get("id", "UNKNOWN"),
                package=package,
                installed_version=version,
                severity=get_severity_from_osv(vuln),
                title=vuln.get("summary", "No summary"),
                description=vuln.get("details", "")[:200],
                fixed_version=get_fixed_version(vuln),
                url=f"https://osv.dev/vulnerability/{vuln.get('id', '')}",
                source="OSV"
            ))
    
    return vulnerabilities


def generate_report(vulnerabilities: list[Vulnerability], format: str = "text") -> str:
    """Generate vulnerability report"""
    if format == "json":
        return json.dumps([{
            "id": v.id,
            "package": v.package,
            "installedVersion": v.installed_version,
            "severity": v.severity,
            "title": v.title,
            "fixedVersion": v.fixed_version,
            "url": v.url
        } for v in vulnerabilities], indent=2)
    
    elif format == "sarif":
        return json.dumps({
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "Local CodeRabbit Dependency Scanner",
                        "version": "1.0.0"
                    }
                },
                "results": [
                    {
                        "ruleId": v.id,
                        "message": {"text": f"{v.package}@{v.installed_version}: {v.title}"},
                        "level": "error" if v.severity in ["CRITICAL", "HIGH"] else "warning"
                    }
                    for v in vulnerabilities
                ]
            }]
        }, indent=2)
    
    else:  # text
        output = []
        output.append("=" * 60)
        output.append("  DEPENDENCY VULNERABILITY REPORT")
        output.append(f"  Scanned at: {datetime.now().isoformat()}")
        output.append("=" * 60)
        output.append("")
        
        critical = [v for v in vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]
        medium = [v for v in vulnerabilities if v.severity in ["MEDIUM"]]
        low = [v for v in vulnerabilities if v.severity in ["LOW", "UNKNOWN"]]
        
        output.append(f"SUMMARY: {len(critical)} critical/high, {len(medium)} medium, {len(low)} low")
        output.append("")
        
        if critical:
            output.append("🔴 CRITICAL/HIGH:")
            for v in critical:
                output.append(f"  {v.package}@{v.installed_version}")
                output.append(f"    [{v.id}] {v.title}")
                if v.fixed_version:
                    output.append(f"    Fix: Upgrade to {v.fixed_version}")
                output.append(f"    URL: {v.url}")
                output.append("")
        
        if medium:
            output.append("🟡 MEDIUM:")
            for v in medium:
                output.append(f"  {v.package}@{v.installed_version}")
                output.append(f"    [{v.id}] {v.title}")
                output.append("")
        
        if not vulnerabilities:
            output.append("✅ No vulnerabilities found!")
        
        return "\n".join(output)


def scan_npm_audit(root: Path) -> list[Vulnerability]:
    """Use npm audit for more complete npm scanning"""
    import subprocess
    
    if not (root / "package-lock.json").exists():
        return []
    
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=60
        )
        
        data = json.loads(result.stdout)
        vulnerabilities = []
        
        for vuln_id, vuln in data.get("vulnerabilities", {}).items():
            severity = vuln.get("severity", "unknown").upper()
            for via in vuln.get("via", []):
                if isinstance(via, dict):
                    vulnerabilities.append(Vulnerability(
                        id=via.get("source", "npm"),
                        package=vuln.get("name", vuln_id),
                        installed_version=vuln.get("range", "unknown"),
                        severity=severity,
                        title=via.get("title", "Unknown vulnerability"),
                        description=via.get("title", ""),
                        fixed_version=vuln.get("fixAvailable", {}).get("version"),
                        url=via.get("url", ""),
                        source="npm audit"
                    ))
        
        return vulnerabilities
    except Exception:
        return []


if __name__ == "__main__":
    import sys
    
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    format_type = sys.argv[2] if len(sys.argv) > 2 else "text"
    
    ecosystem, deps = detect_ecosystem(root)
    print(f"Detected ecosystem: {ecosystem}")
    print(f"Found {len(deps)} dependencies")
    print("Scanning for vulnerabilities...")
    print()
    
    vulnerabilities = scan_dependencies(root)
    
    # Also try npm audit if available
    if ecosystem == "npm":
        npm_vulns = scan_npm_audit(root)
        # Deduplicate by package name
        seen = {v.package for v in vulnerabilities}
        for v in npm_vulns:
            if v.package not in seen:
                vulnerabilities.append(v)
    
    report = generate_report(vulnerabilities, format_type)
    print(report)
    
    # Exit with error if critical vulnerabilities found
    critical_count = len([v for v in vulnerabilities if v.severity in ["CRITICAL", "HIGH"]])
    sys.exit(1 if critical_count > 0 else 0)
