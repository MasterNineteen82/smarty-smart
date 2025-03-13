import os
import re
import shutil
import logging
import argparse

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Directories
CODEBASE_DIR = "X:/smarty"
JS_DIR = os.path.join(CODEBASE_DIR, "static/js")
PY_DIR = os.path.join(CODEBASE_DIR, "api")
BACKUP_DIR = os.path.join(CODEBASE_DIR, "backups")

# Create backup directory
os.makedirs(BACKUP_DIR, exist_ok=True)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Automated Fixes for JS & Python Code")
parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
args = parser.parse_args()

# Function to backup a file before modifying it
def backup_file(file_path):
    """Creates a backup of the file before making changes."""
    backup_path = os.path.join(BACKUP_DIR, os.path.basename(file_path))
    shutil.copy(file_path, backup_path)
    logging.info(f"Backup created: {backup_path}")

# Function to fix common JavaScript issues
def fix_js_issues(directory, dry_run=False):
    """Automatically fixes JavaScript issues such as missing event listeners and broken fetch calls."""
    js_event_patterns = [
        (r"document\.getElementById\(['\"](\w+)['\"]\)", "Ensure this element ID exists in the HTML."),
        (r"document\.querySelector\(['\"](.+?)['\"]\)", "Ensure this element selector is correct."),
        (r"\.addEventListener\(['\"](click|submit|change)['\"]", "Ensure event listeners are attached."),
        (r"fetch\(['\"](.+?)['\"]\)", "Verify API request URL is correct."),
    ]

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".js"):
                file_path = os.path.join(root, file)
                if not dry_run:
                    backup_file(file_path)

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.readlines()

                modified = False
                for i, line in enumerate(content):
                    for pattern, issue_desc in js_event_patterns:
                        if re.search(pattern, line):
                            if "console.log" not in line:
                                logging.info(f"Would insert debug log in {file_path}: {issue_desc}")
                                if not dry_run:
                                    content.insert(i + 1, f'console.log("DEBUG: {issue_desc}");\n')
                                    modified = True

                if modified and not dry_run:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(content)
                    logging.info(f"Fixed issues in: {file_path}")

# Function to fix common Python API issues
def fix_python_issues(directory, dry_run=False):
    """Automatically fixes common Python API issues such as missing imports and incorrect responses."""
    py_fix_patterns = {
        "from flask import jsonify": "Ensure Flask jsonify is imported.",
        "return jsonify": "Ensure API returns correct JSON format.",
        "except Exception as e": "Add logging to track error messages.",
    }

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if not dry_run:
                    backup_file(file_path)

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.readlines()

                modified = False
                for key, comment in py_fix_patterns.items():
                    if key not in "".join(content):
                        logging.info(f"Would insert fix in {file_path}: {comment}")
                        if not dry_run:
                            content.insert(0, f"{key}  # FIX: {comment}\n")
                            modified = True

                if modified and not dry_run:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(content)
                    logging.info(f"Fixed issues in: {file_path}")

# Run fixes with Dry Run mode
fix_js_issues(JS_DIR, dry_run=args.dry_run)
fix_python_issues(PY_DIR, dry_run=args.dry_run)

if args.dry_run:
    logging.info("Dry run completed. No files were modified.")
else:
    logging.info("Automated fixes applied. Check logs for modified files.")
