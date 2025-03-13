import os
import re
import json
import logging
from datetime import datetime
import traceback

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define Directories
CODEBASE_DIR = "X:/smarty"  # Main codebase directory
LOGS_DIR = "X:/smarty/logs"  # Logs directory
REPORTS_BASE_DIR = "X:/smarty/tests"  # Base reports directory

# Create a timestamped directory for reports
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORTS_DIR = os.path.join(REPORTS_BASE_DIR, f"test_results_{timestamp}")
try:
    os.makedirs(REPORTS_DIR, exist_ok=True)
except OSError as e:
    logging.error(f"Failed to create report directory: {e}")

# Function to scan JavaScript files for common issues
def scan_js_files(directory):
    """Scans JavaScript files for syntax errors, missing event listeners, and API call issues."""
    issues = []
    js_event_patterns = [
        (r"document\.getElementById\(['\"](\w+)['\"]\)", "Possible missing element ID reference."),
        (r"document\.querySelector\(['\"](.+?)['\"]\)", "Possible missing element selector reference."),
        (r"\.addEventListener\(['\"](click|submit|change)['\"]", "Possible missing event listener assignment."),
        (r"fetch\(['\"](.+?)['\"]\)", "Check API request URLs for incorrect endpoints."),
        (r"console\.log\(", "Debugging statement found; consider removing."),
    ]

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".js"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except IOError as e:
                    logging.error(f"Could not read file {file_path}: {e}")
                    continue  # Skip to the next file

                for pattern, issue_desc in js_event_patterns:
                    try:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            issues.append({"file": file_path, "issue": issue_desc, "detail": match})
                    except re.error as e:
                        logging.error(f"Regex error for pattern '{pattern}': {e}")
    return issues

# Function to scan Python API routes for issues
def scan_python_files(directory):
    """Scans Python API route files for missing/malformed responses."""
    issues = []
    py_patterns = [
        (r"@app\.route\(['\"](/api/.*?)['\"]", "API route defined."),
        (r"return jsonify\((.*?)\)", "Ensure API response format is correct."),
        (r"except Exception as e", "Check exception handling; add logging for better debugging."),
    ]

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except IOError as e:
                    logging.error(f"Could not read file {file_path}: {e}")
                    continue

                for pattern, issue_desc in py_patterns:
                    try:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            issues.append({"file": file_path, "issue": issue_desc, "detail": match})
                    except re.error as e:
                        logging.error(f"Regex error for pattern '{pattern}': {e}")

    return issues

# Function to analyze logs for errors
def analyze_logs(directory):
    """Reads and extracts errors from logs."""
    log_issues = []
    log_pattern = re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (?P<level>\w+) - (?P<module>[\w_]+):(?P<line>\d+) - (?P<message>.*)$")

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if os.stat(file_path).st_size == 0:  # Skip empty logs
                    continue

                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            match = log_pattern.match(line)
                            if match and match.group("level") in ["ERROR", "CRITICAL"]:
                                log_issues.append({
                                    "file": file_path,
                                    "timestamp": match.group("timestamp"),
                                    "module": match.group("module"),
                                    "message": match.group("message"),
                                })
                        except Exception as e:
                            logging.error(f"Error processing line in {file_path}: {e}")
            except FileNotFoundError:
                logging.error(f"Log file not found: {file_path}")
            except OSError as e:
                logging.error(f"Error accessing log file {file_path}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error analyzing log file {file_path}: {e}")
                logging.error(traceback.format_exc())

    return log_issues

# Run the analysis
js_issues = scan_js_files(CODEBASE_DIR)
py_issues = scan_python_files(CODEBASE_DIR)
log_issues = analyze_logs(LOGS_DIR)

# Generate a structured report
report_content = f"# Automated Code & Log Analysis Report\n\n"
report_content += f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

def format_issues(issues, issue_type):
    report = f"## {issue_type} Issues\n\n"
    if issues:
        report += "| File | Issue | Detail |\n|------|-------|--------|\n"
        for issue in issues:
            file = issue.get('file', 'N/A')
            issue_desc = issue.get('issue', 'N/A')
            detail = issue.get('detail', 'N/A')
            timestamp = issue.get('timestamp', 'N/A')
            module = issue.get('module', 'N/A')
            message = issue.get('message', 'N/A')

            if issue_type == "JavaScript":
                report += f"| {file} | {issue_desc} | {detail} |\n"
            elif issue_type == "Python API":
                report += f"| {file} | {issue_desc} | {detail} |\n"
            elif issue_type == "Log File":
                 report += f"| {timestamp} | {file} | {module} | {message} |\n"
    else:
        report += f"No {issue_type} issues detected.\n\n"
    return report

report_content += format_issues(js_issues, "JavaScript")
report_content += format_issues(py_issues, "Python API")
report_content += format_issues(log_issues, "Log File")

# Save the report
report_path = os.path.join(REPORTS_DIR, "code_log_analysis_report.md")
try:
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logging.info(f"Report saved to {report_path}")
    print(f"Analysis complete. Report available at: {report_path}")
except IOError as e:
    logging.error(f"Failed to write report to {report_path}: {e}")
except Exception as e:
    logging.error(f"Unexpected error writing report: {e}")
    logging.error(traceback.format_exc())
