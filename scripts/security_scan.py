#!/usr/bin/env python3
"""
Local CodeRabbit - Unified Security Scanner
Combines Secret Detection, Dependency Scanning, and SAST into one tool.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

# Import individual scanners
from secret_scanner import scan_directory as scan_secrets, SecretFinding
from dependency_scanner import scan_dependencies, detect_ecosystem, Vulnerability
from sast_scanner import scan_directory as scan_sast, SecurityFinding


@dataclass  
class SecurityReport:
    """Unified security report"""
    secrets: list
    vulnerabilities: list
    sast_findings: list
    scan_time: str
    summary: dict


def run_full_scan(root: Path) -> SecurityReport:
    """Run all security scanners"""
    print("=" * 60)
    print("  LOCAL CODERABBIT - UNIFIED SECURITY SCAN")
    print("=" * 60)
    print()
    
    # 1. Secret Detection
    print("[1/3] Scanning for secrets...")
    secrets = scan_secrets(root)
    print(f"      Found {len(secrets)} potential secrets")
    
    # 2. Dependency Scanning
    print("[2/3] Scanning dependencies...")
    ecosystem, deps = detect_ecosystem(root)
    if ecosystem != "unknown":
        print(f"      Detected {ecosystem} with {len(deps)} dependencies")
        vulnerabilities = scan_dependencies(root)
        print(f"      Found {len(vulnerabilities)} vulnerable dependencies")
    else:
        print("      No recognized package manager found")
        vulnerabilities = []
    
    # 3. SAST Scanning
    print("[3/3] Running SAST analysis...")
    sast_findings = scan_sast(root)
    print(f"      Found {len(sast_findings)} security issues")
    
    print()
    
    # Build summary
    summary = {
        "secrets": {
            "critical": len([s for s in secrets if s.severity == "critical"]),
            "warning": len([s for s in secrets if s.severity == "warning"])
        },
        "dependencies": {
            "critical": len([v for v in vulnerabilities if v.severity in ["CRITICAL", "HIGH"]]),
            "medium": len([v for v in vulnerabilities if v.severity == "MEDIUM"]),
            "low": len([v for v in vulnerabilities if v.severity in ["LOW", "UNKNOWN"]])
        },
        "sast": {
            "critical": len([f for f in sast_findings if f.severity == "critical"]),
            "high": len([f for f in sast_findings if f.severity == "high"]),
            "medium": len([f for f in sast_findings if f.severity == "medium"]),
            "low": len([f for f in sast_findings if f.severity == "low"])
        }
    }
    
    return SecurityReport(
        secrets=secrets,
        vulnerabilities=vulnerabilities,
        sast_findings=sast_findings,
        scan_time=datetime.now().isoformat(),
        summary=summary
    )


def calculate_security_score(report: SecurityReport) -> int:
    """Calculate overall security score (0-100)"""
    score = 100
    
    # Deduct for secrets
    score -= report.summary["secrets"]["critical"] * 15
    score -= report.summary["secrets"]["warning"] * 5
    
    # Deduct for vulnerabilities
    score -= report.summary["dependencies"]["critical"] * 10
    score -= report.summary["dependencies"]["medium"] * 3
    score -= report.summary["dependencies"]["low"] * 1
    
    # Deduct for SAST findings
    score -= report.summary["sast"]["critical"] * 12
    score -= report.summary["sast"]["high"] * 8
    score -= report.summary["sast"]["medium"] * 3
    score -= report.summary["sast"]["low"] * 1
    
    return max(0, min(100, score))


def generate_text_report(report: SecurityReport) -> str:
    """Generate human-readable report"""
    output = []
    
    output.append("=" * 60)
    output.append("  UNIFIED SECURITY REPORT")
    output.append(f"  Generated: {report.scan_time}")
    output.append("=" * 60)
    output.append("")
    
    score = calculate_security_score(report)
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    
    output.append(f"┌{'─' * 40}┐")
    output.append(f"│ SECURITY SCORE: {score:3d}/100  Grade: {grade}        │")
    output.append(f"└{'─' * 40}┘")
    output.append("")
    
    # Summary table
    output.append("SUMMARY:")
    output.append("┌─────────────────────┬───────┬───────┬───────┐")
    output.append("│ Category            │ Crit  │ High  │ Med   │")
    output.append("├─────────────────────┼───────┼───────┼───────┤")
    output.append(f"│ Secrets             │ {report.summary['secrets']['critical']:5d} │   -   │ {report.summary['secrets']['warning']:5d} │")
    output.append(f"│ Dependencies        │ {report.summary['dependencies']['critical']:5d} │   -   │ {report.summary['dependencies']['medium']:5d} │")
    output.append(f"│ SAST                │ {report.summary['sast']['critical']:5d} │ {report.summary['sast']['high']:5d} │ {report.summary['sast']['medium']:5d} │")
    output.append("└─────────────────────┴───────┴───────┴───────┘")
    output.append("")
    
    # Secrets
    if report.secrets:
        output.append("🔑 SECRETS DETECTED:")
        for s in report.secrets[:5]:  # Top 5
            output.append(f"  [{s.severity.upper()}] {s.file}:{s.line}")
            output.append(f"    {s.description}: {s.masked_match}")
        if len(report.secrets) > 5:
            output.append(f"    ... and {len(report.secrets) - 5} more")
        output.append("")
    
    # Vulnerabilities
    if report.vulnerabilities:
        output.append("📦 VULNERABLE DEPENDENCIES:")
        for v in report.vulnerabilities[:5]:
            output.append(f"  [{v.severity}] {v.package}@{v.installed_version}")
            output.append(f"    {v.title}")
            if v.fixed_version:
                output.append(f"    Fix: Upgrade to {v.fixed_version}")
        if len(report.vulnerabilities) > 5:
            output.append(f"    ... and {len(report.vulnerabilities) - 5} more")
        output.append("")
    
    # SAST
    if report.sast_findings:
        output.append("🔍 SAST FINDINGS:")
        for f in report.sast_findings[:5]:
            output.append(f"  [{f.severity.upper()}] {Path(f.file).name}:{f.line}")
            output.append(f"    {f.message}")
        if len(report.sast_findings) > 5:
            output.append(f"    ... and {len(report.sast_findings) - 5} more")
        output.append("")
    
    if not (report.secrets or report.vulnerabilities or report.sast_findings):
        output.append("✅ No security issues found! Your code looks secure.")
    
    return "\n".join(output)


def generate_json_report(report: SecurityReport) -> str:
    """Generate JSON report"""
    return json.dumps({
        "scanTime": report.scan_time,
        "score": calculate_security_score(report),
        "summary": report.summary,
        "secrets": [
            {
                "file": s.file,
                "line": s.line,
                "type": s.secret_type,
                "severity": s.severity,
                "masked": s.masked_match
            }
            for s in report.secrets
        ],
        "vulnerabilities": [
            {
                "id": v.id,
                "package": v.package,
                "version": v.installed_version,
                "severity": v.severity,
                "title": v.title,
                "fixedVersion": v.fixed_version
            }
            for v in report.vulnerabilities
        ],
        "sast": [
            {
                "ruleId": f.rule_id,
                "file": f.file,
                "line": f.line,
                "severity": f.severity,
                "message": f.message,
                "cwe": f.cwe
            }
            for f in report.sast_findings
        ]
    }, indent=2)


def generate_sarif_report(report: SecurityReport) -> str:
    """Generate SARIF report for GitHub integration"""
    results = []
    
    # Add secrets
    for s in report.secrets:
        results.append({
            "ruleId": f"secrets/{s.secret_type}",
            "level": "error" if s.severity == "critical" else "warning",
            "message": {"text": f"{s.description}: {s.masked_match}"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": s.file},
                    "region": {"startLine": s.line, "startColumn": s.column}
                }
            }]
        })
    
    # Add vulnerabilities
    for v in report.vulnerabilities:
        results.append({
            "ruleId": f"deps/{v.id}",
            "level": "error" if v.severity in ["CRITICAL", "HIGH"] else "warning",
            "message": {"text": f"{v.package}@{v.installed_version}: {v.title}"}
        })
    
    # Add SAST findings
    for f in report.sast_findings:
        results.append({
            "ruleId": f"sast/{f.rule_id}",
            "level": "error" if f.severity in ["critical", "high"] else "warning",
            "message": {"text": f.message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.file},
                    "region": {"startLine": f.line, "startColumn": f.column}
                }
            }]
        })
    
    return json.dumps({
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Local CodeRabbit Security",
                    "version": "1.0.0",
                    "informationUri": "https://github.com/your-org/local-coderabbit"
                }
            },
            "results": results
        }]
    }, indent=2)


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    format_type = sys.argv[2] if len(sys.argv) > 2 else "text"
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    report = run_full_scan(root)
    
    if format_type == "json":
        output = generate_json_report(report)
    elif format_type == "sarif":
        output = generate_sarif_report(report)
    else:
        output = generate_text_report(report)
    
    if output_file:
        Path(output_file).write_text(output)
        print(f"Report saved to: {output_file}")
    else:
        print(output)
    
    # Exit code based on severity
    has_critical = (
        report.summary["secrets"]["critical"] > 0 or
        report.summary["dependencies"]["critical"] > 0 or
        report.summary["sast"]["critical"] > 0
    )
    
    sys.exit(1 if has_critical else 0)


if __name__ == "__main__":
    main()
