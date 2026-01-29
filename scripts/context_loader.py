"""
Context Loader for Local CodeRabbit
Loads and summarizes project context to inject into AI reviews.

Phase 1 of Smart Reviews - makes reviews context-aware.
"""

import os
from pathlib import Path
from typing import Optional
import json

# Maximum tokens for context (leave room for code + response)
MAX_CONTEXT_TOKENS = 2000
# Approximate chars per token
CHARS_PER_TOKEN = 4


class ContextLoader:
    """Loads project context from various sources."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self._cache: Optional[str] = None
        self._cache_key: Optional[str] = None
    
    def load(self) -> str:
        """
        Load and return summarized project context.
        Caches result based on file modification times.
        """
        cache_key = self._get_cache_key()
        if self._cache and self._cache_key == cache_key:
            return self._cache
        
        context_parts = []
        
        # 1. Project README (high priority)
        readme = self._load_readme()
        if readme:
            context_parts.append(f"## Project Overview\n{readme}")
        
        # 2. Architecture docs
        arch = self._load_architecture()
        if arch:
            context_parts.append(f"## Architecture\n{arch}")
        
        # 3. Agent rules (.agent folder)
        agent_rules = self._load_agent_rules()
        if agent_rules:
            context_parts.append(f"## Coding Standards\n{agent_rules}")
        
        # 4. Config files (package.json, tsconfig, etc.)
        configs = self._load_configs()
        if configs:
            context_parts.append(f"## Project Configuration\n{configs}")
        
        # Combine and truncate to fit token limit
        full_context = "\n\n".join(context_parts)
        max_chars = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN
        
        if len(full_context) > max_chars:
            full_context = full_context[:max_chars] + "\n...(truncated)"
        
        self._cache = full_context
        self._cache_key = cache_key
        
        return full_context
    
    def _get_cache_key(self) -> str:
        """Generate cache key based on file modification times."""
        key_files = [
            "README.md", "ARCHITECTURE.md", 
            ".agent/GEMINI.md", "package.json", "tsconfig.json"
        ]
        mtimes = []
        for f in key_files:
            path = self.project_root / f
            if path.exists():
                mtimes.append(f"{f}:{path.stat().st_mtime}")
        return "|".join(mtimes)
    
    def _load_readme(self) -> Optional[str]:
        """Load README.md and extract key info."""
        readme_path = self.project_root / "README.md"
        if not readme_path.exists():
            return None
        
        try:
            content = readme_path.read_text(encoding='utf-8')
            # Extract first 500 chars (project overview)
            lines = content.split('\n')
            summary = []
            char_count = 0
            
            for line in lines:
                if char_count > 500:
                    break
                # Skip badges and images
                if line.strip().startswith('![') or line.strip().startswith('[!['):
                    continue
                summary.append(line)
                char_count += len(line)
            
            return '\n'.join(summary)
        except Exception:
            return None
    
    def _load_architecture(self) -> Optional[str]:
        """Load architecture documentation."""
        arch_files = [
            "ARCHITECTURE.md",
            "docs/ARCHITECTURE.md",
            "docs/architecture.md",
            ".agent/ARCHITECTURE.md"
        ]
        
        for arch_file in arch_files:
            path = self.project_root / arch_file
            if path.exists():
                try:
                    content = path.read_text(encoding='utf-8')
                    # Return first 800 chars
                    return content[:800] + ("..." if len(content) > 800 else "")
                except Exception:
                    continue
        
        return None
    
    def _load_agent_rules(self) -> Optional[str]:
        """Load .agent folder rules (GEMINI.md, etc.)."""
        agent_path = self.project_root / ".agent"
        if not agent_path.exists():
            return None
        
        rules = []
        
        # Check for main config files
        for rule_file in ["GEMINI.md", "rules.md", "standards.md"]:
            path = agent_path / rule_file
            if path.exists():
                try:
                    content = path.read_text(encoding='utf-8')
                    # Extract key rules (first 600 chars)
                    rules.append(f"### {rule_file}\n{content[:600]}")
                except Exception:
                    continue
        
        return '\n'.join(rules) if rules else None
    
    def _load_configs(self) -> Optional[str]:
        """Load project configuration summaries."""
        configs = []
        
        # package.json - extract key info
        pkg_path = self.project_root / "package.json"
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
                deps = list(pkg.get("dependencies", {}).keys())[:10]
                configs.append(f"- **Stack**: {', '.join(deps)}")
            except Exception:
                pass
        
        # tsconfig.json - extract strict mode, target
        ts_path = self.project_root / "tsconfig.json"
        if ts_path.exists():
            try:
                ts = json.loads(ts_path.read_text(encoding='utf-8'))
                opts = ts.get("compilerOptions", {})
                target = opts.get("target", "unknown")
                strict = opts.get("strict", False)
                configs.append(f"- **TypeScript**: target={target}, strict={strict}")
            except Exception:
                pass
        
        # .eslintrc - note that ESLint is configured
        eslint_files = [".eslintrc", ".eslintrc.js", ".eslintrc.json", "eslint.config.js"]
        for eslint in eslint_files:
            if (self.project_root / eslint).exists():
                configs.append("- **ESLint**: Configured (follow project lint rules)")
                break
        
        return '\n'.join(configs) if configs else None
    
    def get_file_context(self, filename: str) -> str:
        """Get context specific to a file type."""
        ext = Path(filename).suffix.lower()
        
        context_hints = {
            '.py': "This is Python code. Follow PEP 8 style.",
            '.ts': "This is TypeScript. Check for type safety issues.",
            '.tsx': "This is React/TSX. Check for hooks rules and component patterns.",
            '.js': "This is JavaScript. Check for potential type issues.",
            '.jsx': "This is React/JSX. Check for hooks rules and component patterns.",
            '.go': "This is Go. Follow Go idioms and error handling patterns.",
            '.rs': "This is Rust. Check for memory safety and ownership issues."
        }
        
        return context_hints.get(ext, "")


# Singleton instance for caching
_loader_instances: dict[str, ContextLoader] = {}


def get_context_loader(project_root: str) -> ContextLoader:
    """Get or create a cached ContextLoader instance."""
    if project_root not in _loader_instances:
        _loader_instances[project_root] = ContextLoader(project_root)
    return _loader_instances[project_root]


def load_project_context(project_root: str) -> str:
    """Convenience function to load project context."""
    loader = get_context_loader(project_root)
    return loader.load()
