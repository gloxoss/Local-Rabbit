#!/usr/bin/env python3
"""
Local CodeRabbit - SAST Security Rules Engine
Custom security rules for common vulnerability patterns.
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class SecurityRule:
    """Defines a security detection rule"""
    id: str
    name: str
    description: str
    severity: str  # critical, high, medium, low
    languages: list[str]
    pattern: str
    message: str
    fix_hint: Optional[str] = None
    cwe: Optional[str] = None  # Common Weakness Enumeration
    owasp: Optional[str] = None  # OWASP category


@dataclass
class SecurityFinding:
    """A detected security issue"""
    rule_id: str
    file: str
    line: int
    column: int
    severity: str
    message: str
    code_snippet: str
    fix_hint: Optional[str]
    cwe: Optional[str]


# ============================================================
# SECURITY RULES - OWASP Top 10 Coverage
# ============================================================

SECURITY_RULES = [
    # ========== A03:2021 - Injection ==========
    SecurityRule(
        id="SEC001",
        name="SQL Injection (Python)",
        description="Potential SQL injection via string formatting",
        severity="critical",
        languages=["python"],
        pattern=r'(cursor\.execute|\.execute)\s*\(\s*["\'].*%[sd].*["\'].*%',
        message="SQL query uses string formatting - vulnerable to SQL injection",
        fix_hint="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        cwe="CWE-89",
        owasp="A03:2021"
    ),
    SecurityRule(
        id="SEC002",
        name="SQL Injection (JavaScript)",
        description="Potential SQL injection via template literals",
        severity="critical",
        languages=["javascript", "typescript"],
        pattern=r'\.query\s*\(\s*`[^`]*\$\{',
        message="SQL query uses template literal interpolation - vulnerable to SQL injection",
        fix_hint="Use parameterized queries with placeholders",
        cwe="CWE-89",
        owasp="A03:2021"
    ),
    SecurityRule(
        id="SEC003",
        name="Command Injection (Python)",
        description="Potential command injection via os.system or subprocess",
        severity="critical",
        languages=["python"],
        pattern=r'(os\.system|subprocess\.(call|run|Popen))\s*\([^)]*\+[^)]*\)|shell=True',
        message="Command execution with user-controlled input",
        fix_hint="Avoid shell=True and use list arguments instead of string concatenation",
        cwe="CWE-78",
        owasp="A03:2021"
    ),
    SecurityRule(
        id="SEC004",
        name="Command Injection (JavaScript)",
        description="Potential command injection via child_process",
        severity="critical",
        languages=["javascript", "typescript"],
        pattern=r'(exec|execSync|spawn)\s*\([^)]*\+[^)]*\)|{.*shell:\s*true',
        message="Command execution with concatenated input",
        fix_hint="Use spawn with array arguments, avoid exec with user input",
        cwe="CWE-78",
        owasp="A03:2021"
    ),
    SecurityRule(
        id="SEC005",
        name="LDAP Injection",
        description="Potential LDAP injection",
        severity="high",
        languages=["python", "javascript"],
        pattern=r'ldap\.(search|bind).*\+.*\)|filter.*=.*\+',
        message="LDAP query with string concatenation",
        fix_hint="Sanitize or escape LDAP special characters",
        cwe="CWE-90",
        owasp="A03:2021"
    ),

    # ========== A07:2021 - XSS ==========
    SecurityRule(
        id="SEC010",
        name="XSS via innerHTML",
        description="Potential XSS through innerHTML assignment",
        severity="high",
        languages=["javascript", "typescript"],
        pattern=r'\.innerHTML\s*=\s*[^"\'`]',
        message="Direct innerHTML assignment with variable - XSS risk",
        fix_hint="Use textContent for text, or sanitize HTML with DOMPurify",
        cwe="CWE-79",
        owasp="A07:2021"
    ),
    SecurityRule(
        id="SEC011",
        name="XSS via document.write",
        description="document.write with dynamic content",
        severity="high",
        languages=["javascript", "typescript"],
        pattern=r'document\.write\s*\([^)]*\+',
        message="document.write with concatenated input - XSS risk",
        fix_hint="Avoid document.write, use DOM manipulation",
        cwe="CWE-79",
        owasp="A07:2021"
    ),
    SecurityRule(
        id="SEC012",
        name="React dangerouslySetInnerHTML",
        description="React dangerouslySetInnerHTML usage",
        severity="medium",
        languages=["javascript", "typescript", "jsx", "tsx"],
        pattern=r'dangerouslySetInnerHTML\s*=\s*\{',
        message="dangerouslySetInnerHTML can lead to XSS if input is not sanitized",
        fix_hint="Sanitize HTML with DOMPurify before using dangerouslySetInnerHTML",
        cwe="CWE-79",
        owasp="A07:2021"
    ),
    SecurityRule(
        id="SEC013",
        name="jQuery html() with variable",
        description="jQuery html() with dynamic content",
        severity="high",
        languages=["javascript", "typescript"],
        pattern=r'\$\([^)]+\)\.html\s*\(\s*[^"\'`\)]',
        message="jQuery html() with variable input - XSS risk",
        fix_hint="Use .text() for plain text or sanitize HTML",
        cwe="CWE-79",
        owasp="A07:2021"
    ),

    # ========== A02:2021 - Cryptographic Failures ==========
    SecurityRule(
        id="SEC020",
        name="Hardcoded Password",
        description="Hardcoded password in code",
        severity="high",
        languages=["python", "javascript", "typescript"],
        pattern=r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
        message="Hardcoded password detected",
        fix_hint="Use environment variables or secrets manager",
        cwe="CWE-798",
        owasp="A02:2021"
    ),
    SecurityRule(
        id="SEC021",
        name="Weak Hashing Algorithm",
        description="Use of weak hashing algorithm (MD5, SHA1)",
        severity="medium",
        languages=["python", "javascript", "typescript"],
        pattern=r'(md5|sha1)\s*\(|hashlib\.(md5|sha1)|crypto\.create(Md5|Sha1)',
        message="Weak hashing algorithm - use SHA-256 or better",
        fix_hint="Use hashlib.sha256() or crypto.createHash('sha256')",
        cwe="CWE-328",
        owasp="A02:2021"
    ),
    SecurityRule(
        id="SEC022",
        name="Insecure Random",
        description="Use of insecure random for security purposes",
        severity="medium",
        languages=["python", "javascript"],
        pattern=r'(random\.random|Math\.random)\s*\(\)',
        message="Insecure random - not suitable for security purposes",
        fix_hint="Use secrets module (Python) or crypto.randomBytes (Node.js)",
        cwe="CWE-330",
        owasp="A02:2021"
    ),

    # ========== A01:2021 - Broken Access Control ==========
    SecurityRule(
        id="SEC030",
        name="Path Traversal",
        description="Potential path traversal vulnerability",
        severity="high",
        languages=["python", "javascript", "typescript"],
        pattern=r'(open|readFile|readFileSync)\s*\([^)]*\+[^)]*\)|\.\./',
        message="File path constructed with user input - path traversal risk",
        fix_hint="Validate and sanitize paths, use path.resolve() and check for ../ ",
        cwe="CWE-22",
        owasp="A01:2021"
    ),
    SecurityRule(
        id="SEC031",
        name="Open Redirect",
        description="Potential open redirect vulnerability",
        severity="medium",
        languages=["javascript", "typescript"],
        pattern=r'(window\.location|location\.href|res\.redirect)\s*=\s*[^"\'`]',
        message="Redirect URL from variable - open redirect risk",
        fix_hint="Validate redirect URLs against allowed domains",
        cwe="CWE-601",
        owasp="A01:2021"
    ),

    # ========== A05:2021 - Security Misconfiguration ==========
    SecurityRule(
        id="SEC040",
        name="Debug Mode Enabled",
        description="Debug mode enabled in production",
        severity="medium",
        languages=["python", "javascript"],
        pattern=r'(DEBUG|debug)\s*[=:]\s*(True|true|1)',
        message="Debug mode should be disabled in production",
        fix_hint="Use environment variables to control debug mode",
        cwe="CWE-489",
        owasp="A05:2021"
    ),
    SecurityRule(
        id="SEC041",
        name="CORS Allow All",
        description="CORS allowing all origins",
        severity="medium",
        languages=["javascript", "typescript", "python"],
        pattern=r'(Access-Control-Allow-Origin|cors)\s*[=:]\s*["\']?\*',
        message="CORS allows all origins - consider restricting",
        fix_hint="Specify allowed origins explicitly",
        cwe="CWE-942",
        owasp="A05:2021"
    ),
    SecurityRule(
        id="SEC042",
        name="Disabled SSL Verification",
        description="SSL certificate verification disabled",
        severity="high",
        languages=["python"],
        pattern=r'verify\s*=\s*False|CERT_NONE',
        message="SSL verification disabled - MITM attack risk",
        fix_hint="Enable SSL verification in production",
        cwe="CWE-295",
        owasp="A05:2021"
    ),

    # ========== A04:2021 - Insecure Design ==========
    SecurityRule(
        id="SEC050",
        name="eval() Usage",
        description="Use of eval() function",
        severity="critical",
        languages=["python", "javascript", "typescript"],
        pattern=r'\beval\s*\(',
        message="eval() is dangerous - can execute arbitrary code",
        fix_hint="Use safer alternatives like JSON.parse() or ast.literal_eval()",
        cwe="CWE-95",
        owasp="A04:2021"
    ),
    SecurityRule(
        id="SEC051",
        name="Pickle Deserialization",
        description="Unsafe pickle deserialization",
        severity="critical",
        languages=["python"],
        pattern=r'pickle\.loads?\s*\(',
        message="Pickle deserialization can execute arbitrary code",
        fix_hint="Use JSON or other safe serialization formats",
        cwe="CWE-502",
        owasp="A04:2021"
    ),
    SecurityRule(
        id="SEC052",
        name="YAML unsafe_load",
        description="Unsafe YAML loading",
        severity="critical",
        languages=["python"],
        pattern=r'yaml\.(load|unsafe_load)\s*\([^)]*\)',
        message="Unsafe YAML loading can execute arbitrary code",
        fix_hint="Use yaml.safe_load() instead",
        cwe="CWE-502",
        owasp="A04:2021"
    ),

    # ========== A06:2021 - Vulnerable Components (handled by dependency_scanner) ==========

    # ========== A08:2021 - Software and Data Integrity ==========
    SecurityRule(
        id="SEC060",
        name="Unsigned Code Execution",
        description="Executing code from URL without verification",
        severity="high",
        languages=["javascript", "typescript"],
        pattern=r'<script\s+src\s*=\s*["\']http:',
        message="Loading script over HTTP - integrity at risk",
        fix_hint="Use HTTPS and SRI (Subresource Integrity)",
        cwe="CWE-494",
        owasp="A08:2021"
    ),

    # ========== A09:2021 - Security Logging Failures ==========
    SecurityRule(
        id="SEC070",
        name="Logging Sensitive Data",
        description="Logging potentially sensitive data",
        severity="medium",
        languages=["python", "javascript", "typescript"],
        pattern=r'(log|console\.log|print)\s*\([^)]*password|token|secret|key',
        message="Sensitive data may be logged",
        fix_hint="Redact sensitive data before logging",
        cwe="CWE-532",
        owasp="A09:2021"
    ),
]


def get_language_from_extension(file_path: Path) -> str:
    """Determine language from file extension"""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".php": "php",
        ".rb": "ruby",
    }
    return ext_map.get(file_path.suffix.lower(), "unknown")


def scan_file(file_path: Path) -> list[SecurityFinding]:
    """Scan a file for security issues"""
    findings = []
    
    language = get_language_from_extension(file_path)
    if language == "unknown":
        return findings
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return findings
    
    lines = content.split('\n')
    
    for rule in SECURITY_RULES:
        # Check if rule applies to this language
        if language not in rule.languages and not any(
            lang in language for lang in rule.languages
        ):
            continue
        
        pattern = re.compile(rule.pattern, re.IGNORECASE)
        
        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                findings.append(SecurityFinding(
                    rule_id=rule.id,
                    file=str(file_path),
                    line=line_num,
                    column=match.start() + 1,
                    severity=rule.severity,
                    message=rule.message,
                    code_snippet=line.strip()[:100],
                    fix_hint=rule.fix_hint,
                    cwe=rule.cwe
                ))
    
    return findings


def scan_directory(root: Path, ignore_dirs: set = None) -> list[SecurityFinding]:
    """Scan a directory for security issues"""
    ignore_dirs = ignore_dirs or {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}
    findings = []
    
    for path in root.rglob("*"):
        if path.is_file():
            if any(ignored in path.parts for ignored in ignore_dirs):
                continue
            
            file_findings = scan_file(path)
            findings.extend(file_findings)
    
    return findings


def generate_report(findings: list[SecurityFinding], format: str = "text") -> str:
    """Generate security report"""
    from datetime import datetime
    
    if format == "json":
        return json.dumps([{
            "ruleId": f.rule_id,
            "file": f.file,
            "line": f.line,
            "column": f.column,
            "severity": f.severity,
            "message": f.message,
            "cwe": f.cwe,
            "fixHint": f.fix_hint
        } for f in findings], indent=2)
    
    elif format == "sarif":
        return json.dumps({
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "Local CodeRabbit SAST",
                        "version": "1.0.0",
                        "rules": [
                            {
                                "id": rule.id,
                                "shortDescription": {"text": rule.name},
                                "fullDescription": {"text": rule.description},
                                "defaultConfiguration": {
                                    "level": "error" if rule.severity == "critical" else "warning"
                                },
                                "properties": {
                                    "security-severity": "9.0" if rule.severity == "critical" else "7.0" if rule.severity == "high" else "5.0"
                                }
                            }
                            for rule in SECURITY_RULES
                        ]
                    }
                },
                "results": [
                    {
                        "ruleId": f.rule_id,
                        "message": {"text": f.message},
                        "locations": [{
                            "physicalLocation": {
                                "artifactLocation": {"uri": f.file},
                                "region": {"startLine": f.line, "startColumn": f.column}
                            }
                        }]
                    }
                    for f in findings
                ]
            }]
        }, indent=2)
    
    else:  # text
        output = []
        output.append("=" * 60)
        output.append("  SAST SECURITY SCAN REPORT")
        output.append(f"  Scanned at: {datetime.now().isoformat()}")
        output.append(f"  Rules: {len(SECURITY_RULES)}")
        output.append("=" * 60)
        output.append("")
        
        critical = [f for f in findings if f.severity == "critical"]
        high = [f for f in findings if f.severity == "high"]
        medium = [f for f in findings if f.severity == "medium"]
        low = [f for f in findings if f.severity == "low"]
        
        output.append(f"SUMMARY: {len(critical)} critical, {len(high)} high, {len(medium)} medium, {len(low)} low")
        output.append("")
        
        for severity, items, icon in [
            ("CRITICAL", critical, "🔴"),
            ("HIGH", high, "🟠"),
            ("MEDIUM", medium, "🟡"),
            ("LOW", low, "🔵")
        ]:
            if items:
                output.append(f"{icon} {severity}:")
                for f in items:
                    output.append(f"  [{f.rule_id}] {Path(f.file).name}:{f.line}")
                    output.append(f"    {f.message}")
                    if f.cwe:
                        output.append(f"    CWE: {f.cwe}")
                    if f.fix_hint:
                        output.append(f"    Fix: {f.fix_hint}")
                    output.append(f"    Code: {f.code_snippet}")
                    output.append("")
        
        if not findings:
            output.append("✅ No security issues found!")
        
        return "\n".join(output)


if __name__ == "__main__":
    import sys
    
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    format_type = sys.argv[2] if len(sys.argv) > 2 else "text"
    
    print(f"Scanning {root} for security issues...")
    print(f"Using {len(SECURITY_RULES)} security rules")
    print()
    
    findings = scan_directory(root)
    
    report = generate_report(findings, format_type)
    print(report)
    
    # Exit with error if critical/high issues found
    severe_count = len([f for f in findings if f.severity in ["critical", "high"]])
    sys.exit(1 if severe_count > 0 else 0)
