import os
import sys
import ast
import logging
import difflib
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import pkgutil
import importlib.util
import re
import subprocess
import venv
import traceback

# Logging setup (reusing debug_startup.py style)
LOG_FILE = "codebase_diagnostic.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CodebaseDiagnostic")

def log_info(message: str, extra: dict = None):
    try:
        extra_str = " Extra: " + str(extra) if extra else ""
        logger.info(f"{message}{extra_str}")
    except Exception as e:
        logger.error(f"Error in log_info: {e}. Original message: {message}, extra: {extra}\n{traceback.format_exc()}")

def log_warning(message: str, extra: dict = None):
    try:
        extra_str = " Extra: " + str(extra) if extra else ""
        logger.warning(f"{message}{extra_str}")
    except Exception as e:
        logger.error(f"Error in log_warning: {e}. Original message: {message}, extra: {extra}\n{traceback.format_exc()}")

def log_error(message: str, extra: dict = None):
    try:
        extra_str = " Extra: " + str(extra) if extra else ""
        logger.error(f"{message}{extra_str}")
    except Exception as e:
        logger.error(f"Error in log_error: {e}. Original message: {message}, extra: {extra}\n{traceback.format_exc()}")


# Configuration
BASE_DIR = Path(__file__).resolve().parent
EXCLUDE_DIRS = {"venv", "__pycache__", "logs", "data", ".git"}
EXCLUDE_FILES = {"__init__.py"}  # Skip empty init files for some checks
EXPECTED_FILES = [
    "smart.py", "app/api/card_routes.py", "app/core/card_manager.py",
    "app/core/card_utils.py", "app/utils/smartcard_utils.py", "requirements.txt"
]
MAX_LINE_LENGTH = 120
SIMILARITY_THRESHOLD = 0.8
MIN_CODE_BLOCK_LENGTH = 10 # Minimum length of code block to consider for duplication

class CodeAnalyzer:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.files: List[Path] = []
        self.code_blocks: Dict[str, List[Tuple[Path, int, str]]] = defaultdict(list)  # Hash -> (file, line, code)
        self.imports: Dict[Path, Set[str]] = defaultdict(set)
        self.used_names: Set[str] = set()
        self.unused_names: Dict[Path, Set[str]] = defaultdict(set)
        self.file_sizes: Dict[Path, int] = {}
        self.complexity_scores: Dict[Path, float] = {}
        self.string_literals: Dict[Path, List[str]] = defaultdict(list) # Collect string literals

    def collect_files(self):
        """Collect all Python files in the codebase."""
        log_info("Collecting files...")
        try:
            for root, dirs, files in os.walk(self.base_dir):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for file in files:
                    if file.endswith(".py"):
                        file_path = Path(root) / file
                        try:
                            self.files.append(file_path)
                            self.file_sizes[file_path] = os.path.getsize(file_path)
                        except OSError as e:
                            log_error(f"Could not get size of {file_path}: {e}")
        except Exception as e:
            log_error(f"Error during file collection: {e}\n{traceback.format_exc()}")
        log_info(f"Collected {len(self.files)} files.")

    def check_file_health(self):
        """Check file existence, encoding, permissions, and file sizes."""
        log_info("Checking file health...")
        for expected in EXPECTED_FILES:
            full_path = self.base_dir / expected
            try:
                if not full_path.exists():
                    log_error(f"Missing expected file: {expected}")
                elif not os.access(full_path, os.R_OK):
                    log_warning(f"No read permission for: {full_path}")
                else:
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        log_info(f"File OK: {full_path}")
                    except UnicodeDecodeError:
                        log_error(f"Encoding issue in {full_path}: Not UTF-8 compatible")
                    except Exception as e:
                        log_error(f"Error reading {full_path}: {e}")

                if full_path.exists():
                    try:
                        file_size = os.path.getsize(full_path)
                        if file_size > 100000:  # 100KB
                            log_warning(f"File size is large: {full_path} ({file_size} bytes)")
                        elif file_size == 0:
                            log_warning(f"File is empty: {full_path}")
                    except OSError as e:
                        log_error(f"Could not get size of {full_path}: {e}")
            except Exception as e:
                log_error(f"Error checking file health for {expected}: {e}\n{traceback.format_exc()}")

    def detect_duplicates(self):
        """Detect duplicate code blocks across files using sequence matching."""
        log_info("Detecting duplicate code blocks...")
        for file in self.files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception as e:
                log_error(f"Error reading file {file} for duplicate detection: {e}")
                continue

            for i, line in enumerate(lines):
                line = line.strip()
                if len(line) > MIN_CODE_BLOCK_LENGTH:  # Ignore short lines
                    code_hash = hashlib.md5(line.encode()).hexdigest()
                    self.code_blocks[code_hash].append((file, i + 1, line))

        for code_hash, occurrences in self.code_blocks.items():
            if len(occurrences) > 1:
                # Use difflib to find similar lines
                for j in range(len(occurrences)):
                    for k in range(j + 1, len(occurrences)):
                        file1, line1, code1 = occurrences[j]
                        file2, line2, code2 = occurrences[k]
                        try:
                            similarity = difflib.SequenceMatcher(None, code1, code2).ratio()
                            if similarity > SIMILARITY_THRESHOLD:
                                 log_warning("Highly similar code detected", extra={
                                    "similarity": similarity,
                                    "locations": [(str(file1), line1), (str(file2), line2)],
                                    "code1": code1,
                                    "code2": code2
                                })
                        except Exception as e:
                            log_error(f"Error comparing code blocks: {e}")

    def analyze_syntax(self):
        """Parse files with AST to detect issues, complexity, and code patterns."""
        log_info("Analyzing syntax and code patterns...")
        for file in self.files:
            if file.name in EXCLUDE_FILES:
                continue
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content, filename=str(file))

                # Collect imports and names
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                        for name in node.names:
                            self.imports[file].add(name.name)
                    elif isinstance(node, ast.Name):
                        self.used_names.add(node.id)
                    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                        self.string_literals[file].append(node.value)

                # Check for issues
                for i, line in enumerate(content.splitlines()):
                    line = line.strip()
                    if len(line) > MAX_LINE_LENGTH:
                        log_warning(f"Line exceeds maximum length ({MAX_LINE_LENGTH}) in {file}:{i+1}")
                    if "import *" in line:
                        log_warning(f"Wildcard import detected in {file}:{i+1}: {line}")
                    if "print(" in line and not line.startswith("#"):
                        log_warning(f"Print statement detected in {file}:{i+1}: {line}")
                    if "os.system" in line and not line.startswith("#"):
                        log_warning(f"os.system call detected in {file}:{i+1}: {line}")
                    if "try:" in line:
                        next_line = content.splitlines()[i + 1].strip() if i + 1 < len(content.splitlines()) else ""
                        if not next_line.startswith("except"):
                            log_warning(f"'try' without immediate 'except' in {file}:{i+1}")
                    if "except Exception" in line:
                        log_warning(f"Broad 'Exception' catch in {file}:{i+1}")
                    if re.search(r'\bpass\b', line) and not line.startswith("#"):
                        log_warning(f"Pass statement detected in {file}:{i+1}: {line}")
                    if re.search(r'\bTODO\b', line):
                        log_warning(f"TODO comment detected in {file}:{i+1}: {line}")
                    if re.search(r'\bFIXME\b', line):
                        log_warning(f"FIXME comment detected in {file}:{i+1}: {line}")

                # Check unused imports
                for imp in self.imports[file]:
                    if imp.split('.')[0] not in self.used_names:
                        self.unused_names[file].add(imp)

                # Calculate Cyclomatic Complexity (very basic)
                complexity = self.calculate_complexity(tree)
                self.complexity_scores[file] = complexity
                if complexity > 10:
                    log_warning(f"High Cyclomatic Complexity detected in {file}: {complexity}")

            except SyntaxError as e:
                log_error(f"Syntax error in {file}", extra={"line": e.lineno, "text": e.text})
            except Exception as e:
                log_error(f"Error processing {file}: {e}\n{traceback.format_exc()}")

    def calculate_complexity(self, tree: ast.AST) -> int:
        """Calculates a basic Cyclomatic Complexity score."""
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler, ast.With)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.FunctionDef):
                complexity +=1 # Each function adds to complexity
        return complexity

    def check_naming_conflicts(self):
        """Check for naming conflicts with external packages and stdlib."""
        log_info("Checking for naming conflicts with external packages...")
        for file in self.files:
            try:
                module_name = file.stem
                if pkgutil.find_loader(module_name) is not None:
                    log_warning(f"Potential naming conflict: {file} may shadow package '{module_name}'")
                if module_name in sys.builtin_module_names:
                     log_warning(f"Potential naming conflict: {file} shadows built-in module '{module_name}'")
                if module_name == "smartcard":
                    log_error(f"File {file} conflicts with 'pyscard.smartcard'. Rename recommended.")
            except Exception as e:
                log_error(f"Error checking naming conflicts for {file}: {e}\n{traceback.format_exc()}")

    def check_naming_conventions(self):
        """Check for consistent naming conventions."""
        log_info("Checking naming conventions...")
        for file in self.files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=str(file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                            log_warning(f"Function '{node.name}' in {file}:{node.lineno} violates snake_case")
                    elif isinstance(node, ast.ClassDef):
                        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                            log_warning(f"Class '{node.name}' in {file}:{node.lineno} violates CamelCase")
                    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                        if not re.match(r'^[A-Z_][A-Z0-9_]*$', node.value):
                            log_warning(f"Constant '{node.value}' in {file}:{node.lineno} violates SCREAMING_SNAKE_CASE")
            except SyntaxError:
                pass  # Already logged in analyze_syntax
            except Exception as e:
                log_error(f"Error checking naming conventions in {file}: {e}\n{traceback.format_exc()}")

    def check_unused_names(self):
        """Report unused imports and variables."""
        log_info("Checking for unused imports...")
        for file, unused in self.unused_names.items():
            try:
                if unused:
                    log_warning(f"Unused imports in {file}", extra={"imports": list(unused)})
            except Exception as e:
                log_error(f"Error checking unused names in {file}: {e}\n{traceback.format_exc()}")

    def check_requirements(self):
        """Validate requirements.txt and installed packages, check for vulnerabilities."""
        log_info("Checking requirements.txt...")
        req_file = self.base_dir / "requirements.txt"
        try:
            if not req_file.exists():
                log_error("requirements.txt not found")
                return

            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    reqs = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except Exception as e:
                log_error(f"Error reading requirements.txt: {e}")
                return

            installed_packages = {}
            try:
                result = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True, check=True)
                for line in result.stdout.splitlines():
                    if '==' in line:
                        package, version = line.split('==')
                        installed_packages[package] = version
            except subprocess.CalledProcessError as e:
                log_error(f"Error listing installed packages: {e}")
                return

            for req in reqs:
                try:
                    package_name = req.split('==')[0].split('>')[0].split('<')[0]
                    spec = importlib.util.find_spec(package_name)
                    if spec is None:
                        log_warning(f"Package '{req}' listed in requirements.txt but not installed")
                    else:
                        if package_name in installed_packages:
                            version_spec = req.split(package_name)[1]
                            if version_spec:
                                # Basic version check (can be expanded)
                                installed_version = installed_packages[package_name]
                                if '==' in version_spec and version_spec.strip() != f'=={installed_version}':
                                    log_warning(f"Version mismatch for {package_name}: requirements.txt specifies {version_spec}, but {installed_version} is installed.")
                except Exception as e:
                    log_warning(f"Error checking requirement '{req}': {e}")

            # Vulnerability check (requires 'safety' package)
            try:
                result = subprocess.run([sys.executable, '-m', 'safety', 'check', '--file=requirements.txt'], capture_output=True, text=True)
                if result.returncode != 0:
                    if "No safety module" in result.stderr:
                        log_warning("Safety module not found. Install it with 'pip install safety' for vulnerability checks.")
                    else:
                        log_warning(f"Potential vulnerabilities found:\n{result.stderr}")
                else:
                    log_info("No known vulnerabilities found in requirements.txt (using safety).")
            except FileNotFoundError:
                log_warning("Safety module not found. Install it with 'pip install safety' for vulnerability checks.")
            except Exception as e:
                log_error(f"Error checking for vulnerabilities: {e}")
        except Exception as e:
            log_error(f"Error during requirements check: {e}\n{traceback.format_exc()}")

    def check_virtual_environment(self):
        """Check if a virtual environment is being used."""
        log_info("Checking for virtual environment...")
        try:
            if 'VIRTUAL_ENV' not in os.environ:
                log_warning("No virtual environment detected. Consider using one to isolate dependencies.")
            else:
                venv_path = Path(os.environ['VIRTUAL_ENV'])
                if not (venv_path.parent.parent / 'pyvenv.cfg').exists():
                    log_warning("Virtual environment may not be properly activated.")
        except Exception as e:
            log_error(f"Error checking virtual environment: {e}\n{traceback.format_exc()}")

    def run_pylint(self):
        """Run Pylint on the codebase."""
        log_info("Running Pylint...")
        try:
            result = subprocess.run([sys.executable, '-m', 'pylint', str(self.base_dir)], capture_output=True, text=True)
            if result.returncode != 0:
                log_warning(f"Pylint found issues:\n{result.stdout}")
            else:
                log_info("Pylint found no issues.")
        except FileNotFoundError:
            log_warning("Pylint not found. Install it with 'pip install pylint'.")
        except Exception as e:
            log_error(f"Error running Pylint: {e}\n{traceback.format_exc()}")

    def find_common_strings(self):
        """Find common string literals across the codebase."""
        log_info("Finding common string literals...")
        string_counts = defaultdict(int)
        for file, strings in self.string_literals.items():
            for s in strings:
                string_counts[s] += 1

        for s, count in string_counts.items():
            if count > 3 and len(s) > 5:  # Report strings used in more than 3 files and longer than 5 chars
                log_warning(f"Common string literal detected: '{s}' (used in {count} files)")

    def run_diagnostics(self):
        """Run all diagnostic checks."""
        try:
            self.collect_files()
            self.check_file_health()
            self.detect_duplicates()
            self.analyze_syntax()
            self.check_naming_conflicts()
            self.check_naming_conventions()
            self.check_unused_names()
            self.check_requirements()
            self.check_virtual_environment()
            self.run_pylint()
            self.find_common_strings()
            log_info("Diagnostics complete. Review codebase_diagnostic.log for details.")
        except Exception as e:
            log_error(f"Fatal error during diagnostics: {e}\n{traceback.format_exc()}")

def main():
    analyzer = CodeAnalyzer(BASE_DIR)
    analyzer.run_diagnostics()

if __name__ == "__main__":
    main()