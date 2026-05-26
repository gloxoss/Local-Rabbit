#!/usr/bin/env python3
"""
Local CodeRabbit - Test Generator
Generate unit tests for code using AI.
"""

import json
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import urllib.request


@dataclass
class GeneratedTest:
    """A generated test file"""
    original_file: str
    test_file: str
    test_code: str
    framework: str
    coverage_estimate: list[str]  # Functions covered


class TestGenerator:
    """Generates unit tests using AI"""
    
    def __init__(self, ollama_url: str = None, model: str = None):
        self.ollama_url = ollama_url or os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        self.model = model or os.environ.get('OLLAMA_MODEL', 'qwen2.5-coder')
    
    def detect_framework(self, file_path: Path) -> str:
        """Detect appropriate test framework based on file type"""
        ext = file_path.suffix.lower()
        
        framework_map = {
            '.py': 'pytest',
            '.js': 'jest',
            '.jsx': 'jest',
            '.ts': 'jest',
            '.tsx': 'jest',
            '.go': 'go_test',
            '.rs': 'rust_test'
        }
        
        return framework_map.get(ext, 'generic')
    
    def extract_functions(self, code: str, language: str) -> list[str]:
        """Extract function names from code"""
        functions = []
        
        if language == 'python':
            matches = re.findall(r'^\s*def\s+(\w+)\s*\(', code, re.MULTILINE)
            functions = [m for m in matches if not m.startswith('_')]
        elif language in ['javascript', 'typescript']:
            # Function declarations
            matches = re.findall(r'function\s+(\w+)\s*\(', code)
            functions.extend(matches)
            # Arrow functions
            matches = re.findall(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(', code)
            functions.extend(matches)
            # Methods
            matches = re.findall(r'^\s*(\w+)\s*\([^)]*\)\s*{', code, re.MULTILINE)
            functions.extend(matches)
        
        return list(set(functions))
    
    def generate_tests(self, file_path: Path) -> Optional[GeneratedTest]:
        """Generate tests for a file"""
        try:
            code = file_path.read_text(encoding='utf-8')
        except Exception:
            return None
        
        framework = self.detect_framework(file_path)
        language = self._get_language(file_path)
        functions = self.extract_functions(code, language)
        
        if not functions:
            return None
        
        prompt = self._build_prompt(code, framework, language, functions)
        
        try:
            response = self._query_ollama(prompt)
            test_code = self._extract_code_block(response)
            if not test_code:
                test_code = response
            
            test_file = self._generate_test_filename(file_path, framework)
            
            return GeneratedTest(
                original_file=str(file_path),
                test_file=test_file,
                test_code=test_code,
                framework=framework,
                coverage_estimate=functions
            )
        
        except Exception as e:
            print(f"Error generating tests: {e}")
            return None
    
    def _build_prompt(self, code: str, framework: str, language: str, functions: list[str]) -> str:
        """Build the prompt for test generation"""
        framework_hints = {
            'pytest': """Use pytest with:
- test functions starting with test_
- Use pytest.raises for exceptions
- Use pytest.fixture for setup
- Include happy path, edge cases, and error cases""",
            
            'jest': """Use Jest with:
- describe() blocks for grouping
- it() or test() for individual tests
- expect() assertions
- Mock external dependencies with jest.mock()
- Include happy path, edge cases, and error cases""",
            
            'go_test': """Use standard Go testing:
- func Test<Name>(t *testing.T)
- Use t.Error or t.Errorf for failures
- Table-driven tests where appropriate""",
        }
        
        return f"""Generate comprehensive unit tests for the following {language} code.

CODE TO TEST:
```{language}
{code}
```

FUNCTIONS TO COVER: {', '.join(functions)}

FRAMEWORK: {framework}
{framework_hints.get(framework, '')}

REQUIREMENTS:
1. Test each function's happy path
2. Test edge cases (empty input, null, boundaries)
3. Test error cases
4. Use meaningful test names
5. Add comments explaining what each test verifies

Generate ONLY the test code, no explanations."""

    def _query_ollama(self, prompt: str) -> str:
        """Query Ollama API"""
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 2048
            }
        }).encode()
        
        req = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.load(response)
            return data.get("response", "")
    
    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract code from markdown code block"""
        match = re.search(r'```(?:\w+)?\n(.*?)```', text, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _get_language(self, file_path: Path) -> str:
        """Get language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust'
        }
        return ext_map.get(file_path.suffix.lower(), 'unknown')
    
    def _generate_test_filename(self, file_path: Path, framework: str) -> str:
        """Generate appropriate test filename"""
        name = file_path.stem
        ext = file_path.suffix
        
        if framework == 'pytest':
            return f"test_{name}{ext}"
        elif framework in ['jest', 'vitest']:
            return f"{name}.test{ext}"
        elif framework == 'go_test':
            return f"{name}_test{ext}"
        else:
            return f"test_{name}{ext}"
    
    def save_tests(self, test: GeneratedTest, output_dir: Path = None) -> Path:
        """Save generated tests to file"""
        if output_dir:
            test_path = output_dir / test.test_file
        else:
            original = Path(test.original_file)
            test_path = original.parent / test.test_file
        
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(test.test_code, encoding='utf-8')
        
        return test_path


def generate_batch_tests(directory: Path, output_dir: Path = None) -> list[GeneratedTest]:
    """Generate tests for all files in directory"""
    generator = TestGenerator()
    tests = []
    
    extensions = ['.py', '.js', '.ts', '.jsx', '.tsx']
    
    for ext in extensions:
        for file_path in directory.rglob(f"*{ext}"):
            # Skip existing tests and node_modules
            if 'test' in file_path.name.lower():
                continue
            if 'node_modules' in str(file_path):
                continue
            
            print(f"Generating tests for {file_path.name}...")
            test = generator.generate_tests(file_path)
            
            if test:
                tests.append(test)
                if output_dir:
                    generator.save_tests(test, output_dir)
                print(f"  ✓ Generated {test.test_file}")
            else:
                print(f"  ✗ Skipped (no functions found)")
    
    return tests


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_generator.py <file_or_directory> [output_dir]")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    generator = TestGenerator()
    
    if path.is_file():
        print(f"Generating tests for {path.name}...")
        test = generator.generate_tests(path)
        
        if test:
            print(f"\n{'=' * 50}")
            print(f"Generated test: {test.test_file}")
            print(f"Framework: {test.framework}")
            print(f"Functions covered: {', '.join(test.coverage_estimate)}")
            print(f"{'=' * 50}\n")
            print(test.test_code)
            
            if output_dir:
                saved_path = generator.save_tests(test, output_dir)
                print(f"\nSaved to: {saved_path}")
        else:
            print("Could not generate tests")
    
    elif path.is_dir():
        tests = generate_batch_tests(path, output_dir)
        print(f"\n{'=' * 50}")
        print(f"Generated {len(tests)} test files")
