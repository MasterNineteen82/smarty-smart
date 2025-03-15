import os
import re
import sys
import json
import logging
import hashlib
import traceback
import ast
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any, Optional
from collections import defaultdict, Counter
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup
import numpy as np
import asyncio
import aiofiles
import csv
from concurrent.futures import ProcessPoolExecutor

# Configuration
DEFAULT_LOG_FILE = "codebase_diagnostic.log"
OUTPUT_DIR = Path("diagnostic_reports")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
HISTORY_FILE = OUTPUT_DIR / "analysis_history.json"
CSV_REPORT_FILE = OUTPUT_DIR / f"diagnostic_report_{TIMESTAMP}.csv"  # CSV output

# Enhanced configuration with better error handling
try:
    # Check for custom log file in command line arguments
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        LOG_FILE = Path(sys.argv[1])
    else:
        LOG_FILE = Path(DEFAULT_LOG_FILE)

    # Create report subdirectories
    CHARTS_DIR = OUTPUT_DIR / "charts"
    CHARTS_DIR.mkdir(exist_ok=True)

    # Report configuration
    REPORT_CONFIG = {
        "html_theme": "default",  # Options: default, dark, highcontrast
        "include_charts": True,
        "max_issues_per_category": 100,
        "max_recommendations": 10,
        "chart_colormap": "viridis",  # Options: viridis, plasma, inferno, magma, cividis
    }

    # Visualization settings
    VIZ_CONFIG = {
        "chart_size": (10, 6),
        "dpi": 100,
        "font_scale": 1.2,
        "style": "whitegrid"
    }

    # Action plan priority thresholds
    PRIORITY_THRESHOLDS = {
        "high": 7,    # Issues with severity >= 7 are high priority
        "medium": 4,  # Issues with severity >= 4 are medium priority
        "low": 0      # Everything else is low priority
    }

except Exception as e:
    print(f"Error in configuration setup: {e}")
    # Fallback to minimal configuration
    LOG_FILE = Path(DEFAULT_LOG_FILE)
    CHARTS_DIR = OUTPUT_DIR / "charts"
    CHARTS_DIR.mkdir(exist_ok=True)
    REPORT_CONFIG = {"html_theme": "default", "include_charts": True}
    VIZ_CONFIG = {"chart_size": (10, 6), "dpi": 100}
    PRIORITY_THRESHOLDS = {"high": 7, "medium": 4, "low": 0}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / f"analyzer_{TIMESTAMP}.log")
    ]
)
logger = logging.getLogger("LogAnalyzer")

# Enhanced regex patterns for parsing log lines - handles multiline entries
LOG_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - CodebaseDiagnostic - (INFO|WARNING|ERROR) - (.*?)(?= Extra: |$)( Extra: (.*))?$',
    re.DOTALL
)

# Issue categorization rules with severity and icon mappings
CATEGORIZATION_RULES = [
    {
        "name": "File Health",
        "patterns": ["missing expected file", "encoding issue", "file size", "file is empty", "no read permission"],
        "severity": 8,
        "icon": "fa-file-medical-alt",
        "color": "danger"
    },
    {
        "name": "Code Duplication",
        "patterns": ["duplicate code", "highly similar code"],
        "severity": 7,
        "icon": "fa-copy",
        "color": "warning"
    },
    {
        "name": "Syntax and Patterns",
        "patterns": [
            "wildcard import", "print statement", "os.system",
            "try without immediate", "broad 'exception'", "pass statement",
            "todo", "fixme", "line exceeds maximum length"
        ],
        "severity": 6,
        "icon": "fa-code",
        "color": "warning"
    },
    {
        "name": "Naming Conflicts",
        "patterns": ["naming conflict", "shadows package", "shadows built-in"],
        "severity": 8,
        "icon": "fa-exclamation-triangle",
        "color": "danger"
    },
    {
        "name": "Naming Conventions",
        "patterns": ["violates snake_case", "violates camelcase", "violates screaming_snake_case"],
        "severity": 5,
        "icon": "fa-signature",
        "color": "info"
    },
    {
        "name": "Unused Code",
        "patterns": ["unused imports", "unused variables"],
        "severity": 4,
        "icon": "fa-trash",
        "color": "secondary"
    },
    {
        "name": "Dependencies",
        "patterns": ["requirements.txt", "version mismatch", "vulnerabilities", "listed in requirements.txt but not installed"],
        "severity": 9,
        "icon": "fa-cubes",
        "color": "warning"
    },
    {
        "name": "Environment",
        "patterns": ["virtual environment", "venv"],
        "severity": 6,
        "icon": "fa-box",
        "color": "info"
    },
    {
        "name": "Pylint Findings",
        "patterns": ["pylint"],
        "severity": 5,
        "icon": "fa-check-circle",
        "color": "secondary"
    },
    {
        "name": "String Literals",
        "patterns": ["string literal", "common string"],
        "severity": 3,
        "icon": "fa-quote-right",
        "color": "info"
    },
    {
        "name": "Code Complexity",
        "patterns": ["cyclomatic complexity", "complex", "high complexity"],
        "severity": 7,
        "icon": "fa-route",
        "color": "warning"
    },
    {
        "name": "Error Handling",
        "patterns": ["except", "error catching", "exception handling"],
        "severity": 6,
        "icon": "fa-exclamation-circle",
        "color": "warning"
    },
    {
        "name": "Security",
        "patterns": ["security", "vulnerability", "insecure", "CVE"],
        "severity": 10,
        "icon": "fa-shield-alt",
        "color": "danger"
    }
]

async def read_file_async(file_path: Path, encoding: str = 'utf-8') -> str:
    """Asynchronously read a file."""
    try:
        async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
            return await f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return ""

async def write_file_async(file_path: Path, content: str) -> None:
    """Asynchronously write content to a file."""
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {e}")

def run_in_process(func, *args):
    """Run a function in a separate process."""
    with ProcessPoolExecutor() as executor:
        return executor.submit(func, *args).result()
    
class LogAnalyzer:
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.issues: Dict[str, List[Dict]] = {
            "ERROR": [],
            "WARNING": [],
            "INFO": []
        }
        self.categories: Dict[str, List[Dict]] = defaultdict(list)
        self.categorization_rules = CATEGORIZATION_RULES
        self.recommendations: List[Dict] = []  # Store recommendations with metadata
        self.history: Dict = self._load_history()
        self.issue_hashes: Set[str] = set()  # Track unique issue hashes
        self.stats: Dict[str, Any] = {
            "total_issues": 0,
            "by_level": {},
            "by_category": {},
            "recurrent_issues": 0,
            "new_issues": 0,
            "resolved_issues": 0
        }

    def _load_history(self) -> Dict:
        """Load analysis history from previous runs"""
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"runs": [], "issue_hashes": set(), "trends": {}}
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return {"runs": [], "issue_hashes": set(), "trends": {}}

    def _save_history(self):
        """Save analysis history for future reference"""
        try:
            # Convert sets to lists for JSON serialization
            serializable_history = self.history.copy()
            if "issue_hashes" in serializable_history:
                serializable_history["issue_hashes"] = list(serializable_history["issue_hashes"])

            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(serializable_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    async def parse_log(self):
        """Parse the log file into structured data with robust error handling."""
        if not self.log_file.exists():
            logger.error(f"Log file {self.log_file} not found.")
            sys.exit(1)

        try:
            content = await read_file_async(self.log_file, encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning("UTF-8 decoding failed, trying with latin-1 encoding")
            try:
                content = await read_file_async(self.log_file, encoding='latin-1')
            except Exception as e:
                logger.error(f"Error reading log file with latin-1 encoding: {e}\n{traceback.format_exc()}")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error reading log file: {e}\n{traceback.format_exc()}")
            sys.exit(1)

        # Process log entries
        self._process_log_content(content)

        # Calculate statistics
        self._calculate_statistics()

        logger.info(f"Parsed {sum(len(issues) for issues in self.issues.values())} issues from the log file.")

    def _process_log_content(self, content: str):
        """Process the log content to extract issues"""
        current_pos = 0
        while True:
            match = LOG_PATTERN.search(content, current_pos)
            if not match:
                break

            try:
                timestamp, level, message, _, extra_raw = match.groups()
                message = message.strip()

                # Parse the message based on its content
                parsed_issue = self._parse_message(message, extra_raw)
                if not parsed_issue:
                    logger.warning(f"Could not parse message: {message}")
                    current_pos = match.end()
                    continue

                # Create issue hash for deduplication and tracking
                issue_hash = self._create_issue_hash(message, level)

                issue = {
                    "timestamp": timestamp,
                    "level": level,
                    "hash": issue_hash,
                    **parsed_issue
                }

                self.issues[level].append(issue)
                self.issue_hashes.add(issue_hash)
                self._categorize_issue(issue, level)

                current_pos = match.end()

            except Exception as e:
                logger.error(f"Error processing log entry: {e}\n{traceback.format_exc()}")
                # Skip this entry and continue with the next one
                current_pos = match.end() if match else current_pos + 1
                
    def _parse_message(self, message: str, extra_raw: str) -> Optional[Dict]:
        """Parse the log message and extract granular data."""
        if "Line exceeds maximum length" in message:
            match = re.search(r"in (.*?):(\d+)", message)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                actual_length = int(message.split("(")[1].split(")")[0].split("/")[0])
                max_length = int(message.split("(")[1].split(")")[0].split("/")[1])
                return {
                    "type": "line_length",
                    "file": file_path,
                    "line_number": line_number,
                    "actual_length": actual_length,
                    "max_length": max_length
                }
        elif "Highly similar code detected" in message:
            try:
                extra = json.loads(extra_raw)
                file1, line1 = extra["locations"][0]
                file2, line2 = extra["locations"][1]
                similarity = extra["similarity"]
                return {
                    "type": "code_duplication",
                    "file1": file1,
                    "line1": line1,
                    "file2": file2,
                    "line2": line2,
                    "similarity": similarity
                }
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.warning(f"Could not parse extra data for code duplication: {extra_raw}")
                return None
        elif "Unused imports" in message:
            try:
                extra = json.loads(extra_raw)
                imports = extra["imports"]
                return {
                    "type": "unused_imports",
                    "imports": imports
                }
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.warning(f"Could not parse extra data for unused imports: {extra_raw}")
                return None
        elif "Syntax error in" in message:
            try:
                extra = json.loads(extra_raw)
                line = extra["line"]
                text = extra["text"]
                return {
                    "type": "syntax_error",
                    "line": line,
                    "text": text
                }
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.warning(f"Could not parse extra data for syntax error: {extra_raw}")
                return None
        return None

    def _create_issue_hash(self, message: str, level: str) -> str:
        """Create a hash of the issue for deduplication and tracking"""
        # Remove variable parts like timestamps, line numbers, etc.
        normalized_message = re.sub(r'\d+', 'N', message)
        return hashlib.md5(f"{level}:{normalized_message}".encode()).hexdigest()

    def _categorize_issue(self, issue: Dict, level: str):
        """Categorize issues based on message content using the rules engine."""
        message = issue["message"].lower()
        categorized = False

        for rule in self.categorization_rules:
            if any(pattern.lower() in message for pattern in rule["patterns"]):
                category_data = {
                    **issue,
                    "level": level,
                    "severity": rule["severity"],
                    "icon": rule.get("icon", "fa-circle"),
                    "color": rule.get("color", "secondary")
                }
                self.categories[rule["name"]].append(category_data)
                categorized = True
                break

        if not categorized:
            # Default category if no rules match
            self.categories["General"].append({
                **issue,
                "level": level,
                "severity": 5,
                "icon": "fa-info-circle",
                "color": "primary"
            })

    def _calculate_statistics(self):
        """Calculate statistics about the issues"""
        self.stats["total_issues"] = sum(len(issues) for issues in self.issues.values())
        self.stats["by_level"] = {
            level: len(issues) for level, issues in self.issues.items()
        }
        self.stats["by_category"] = {
            category: len(issues) for category, issues in self.categories.items()
        }

        # Compare with history for recurrent issues
        if self.history.get("issue_hashes"):
            previous_hashes = set(self.history["issue_hashes"])
            current_hashes = self.issue_hashes

            self.stats["recurrent_issues"] = len(previous_hashes.intersection(current_hashes))
            self.stats["new_issues"] = len(current_hashes - previous_hashes)
            self.stats["resolved_issues"] = len(previous_hashes - current_hashes)

        # Update history
        self.history["runs"].append({
            "timestamp": TIMESTAMP,
            "total_issues": self.stats["total_issues"],
            "by_level": self.stats["by_level"],
            "by_category": self.stats["by_category"]
        })
        self.history["issue_hashes"] = list(self.issue_hashes)

    def generate_console_report(self):
        """Generate a concise console report."""
        print("\n=== Codebase Diagnostic Report ===")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Issues: {self.stats['total_issues']}")
        print(f"Errors: {self.stats['by_level'].get('ERROR', 0)}, "
              f"Warnings: {self.stats['by_level'].get('WARNING', 0)}, "
              f"Info: {self.stats['by_level'].get('INFO', 0)}")

        if self.stats.get("recurrent_issues") is not None:
            print(f"Recurrent Issues: {self.stats['recurrent_issues']}, "
                  f"New Issues: {self.stats['new_issues']}, "
                  f"Resolved Issues: {self.stats['resolved_issues']}")

        print("\nSummary by Category:")
        for category, issues in sorted(self.categories.items(),
                                      key=lambda x: sum(1 for i in x[1] if i["level"] in ["ERROR", "WARNING"]),
                                      reverse=True):
            errors = len([i for i in issues if i["level"] == "ERROR"])
            warnings = len([i for i in issues if i["level"] == "WARNING"])
            if errors > 0 or warnings > 0:
                print(f"- {category}: {len(issues)} issues (Errors: {errors}, Warnings: {warnings})")

        print("\nCritical Errors:")
        for issue in self.issues["ERROR"]:
            print(f"  [{issue['timestamp']}] {issue['message']}")
            if issue["extra"]:
                print(f"    Details: {issue['extra']}")

        print("\nTop Recommendations:")
        for rec in self.generate_recommendations()[:5]:
            print(f"  - {rec['title']}: {rec['description']}")
        print("")
    def generate_csv_report(self, output_file: Path):
        """Generate a CSV report of all issues."""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Timestamp', 'Level', 'Category', 'Message', 'Severity', 'Extra']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for level, issues in self.issues.items():
                    for issue in issues:
                        writer.writerow({
                            'Timestamp': issue['timestamp'],
                            'Level': level,
                            'Category': issue.get('category', 'General'),
                            'Message': issue['message'],
                            'Severity': issue.get('severity', 5),
                            'Extra': json.dumps(issue['extra']) if issue['extra'] else ''
                        })
            logger.info(f"CSV report generated successfully at {output_file}")
        except Exception as e:
            logger.error(f"Error generating CSV report: {e}")

    def generate_html_report(self, output_file: Path):
        """Generate a comprehensive HTML report with Bootstrap 5 and FontAwesome."""
        try:
            # Create base HTML template
            html_theme = REPORT_CONFIG.get("html_theme", "default")
            theme_class = "light" if html_theme == "default" else html_theme
            
            # Create HTML structure with responsive design
            html_content = f"""<!DOCTYPE html>
            <html lang="en" data-bs-theme="{theme_class}">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Codebase Diagnostic Report - {TIMESTAMP}</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    .issue-card {{
                        transition: transform 0.2s;
                        margin-bottom: 1rem;
                    }}
                    .issue-card:hover {{
                        transform: translateY(-5px);
                    }}
                    .severity-indicator {{
                        width: 15px;
                        height: 15px;
                        border-radius: 50%;
                        display: inline-block;
                        margin-right: 5px;
                    }}
                    .severity-high {{ background-color: #dc3545; }}
                    .severity-medium {{ background-color: #ffc107; }}
                    .severity-low {{ background-color: #0dcaf0; }}
                    .trend-up {{ color: #dc3545; }}
                    .trend-down {{ color: #198754; }}
                    .trend-neutral {{ color: #6c757d; }}
                    .chart-container {{
                        height: 300px;
                        margin-bottom: 2rem;
                    }}
                    @media print {{
                        .no-print {{ display: none; }}
                        .chart-container {{ break-inside: avoid; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container-fluid py-4">
                    <div class="row mb-4">
                        <div class="col">
                            <h1 class="display-5 fw-bold">Codebase Diagnostic Report</h1>
                            <p class="lead">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                            <div class="d-flex gap-2 no-print">
                                <button class="btn btn-outline-primary" onclick="window.print()">
                                    <i class="fas fa-print"></i> Print Report
                                </button>
                                <button class="btn btn-outline-secondary" onclick="toggleAllDetails()">
                                    <i class="fas fa-expand-alt"></i> Toggle All Details
                                </button>
                            </div>
                        </div>
                        <div class="col-md-auto">
                            <div class="card border-0 shadow-sm h-100">
                                <div class="card-body">
                                    <h5 class="card-title">Summary</h5>
                                    <div class="d-flex flex-column">
                                        <div class="d-flex justify-content-between">
                                            <span>Total Issues:</span>
                                            <span class="fw-bold">{self.stats['total_issues']}</span>
                                        </div>
                                        <div class="d-flex justify-content-between">
                                            <span>Errors:</span>
                                            <span class="fw-bold text-danger">{self.stats['by_level'].get('ERROR', 0)}</span>
                                        </div>
                                        <div class="d-flex justify-content-between">
                                            <span>Warnings:</span>
                                            <span class="fw-bold text-warning">{self.stats['by_level'].get('WARNING', 0)}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
            """

            # Only add trend information if we have history
            if self.stats.get("recurrent_issues") is not None:
                trend_icon = "fa-arrow-up trend-up" if self.stats["new_issues"] > self.stats["resolved_issues"] else \
                            "fa-arrow-down trend-down" if self.stats["new_issues"] < self.stats["resolved_issues"] else \
                            "fa-arrows-h trend-neutral"
                
                html_content += f"""
                    <div class="row mb-4">
                        <div class="col-12">
                            <div class="card shadow-sm">
                                <div class="card-body">
                                    <h5 class="card-title">Issue Trends</h5>
                                    <div class="row text-center">
                                        <div class="col">
                                            <div class="display-6">{self.stats["recurrent_issues"]}</div>
                                            <div>Recurrent Issues</div>
                                        </div>
                                        <div class="col">
                                            <div class="display-6">{self.stats["new_issues"]}</div>
                                            <div>New Issues</div>
                                        </div>
                                        <div class="col">
                                            <div class="display-6">{self.stats["resolved_issues"]}</div>
                                            <div>Resolved Issues</div>
                                        </div>
                                        <div class="col">
                                            <div class="display-6">
                                                <i class="fas {trend_icon}"></i>
                                            </div>
                                            <div>Overall Trend</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                """

            # Visualizations - only if we have data and charts are enabled
            if REPORT_CONFIG.get("include_charts", True) and self.stats["total_issues"] > 0:
                html_content += """
                    <div class="row mb-4">
                        <div class="col-md-6 mb-4">
                            <div class="card shadow-sm h-100">
                                <div class="card-body">
                                    <h5 class="card-title">Issues by Severity</h5>
                                    <div class="chart-container">
                                        <canvas id="severityChart"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6 mb-4">
                            <div class="card shadow-sm h-100">
                                <div class="card-body">
                                    <h5 class="card-title">Issues by Category</h5>
                                    <div class="chart-container">
                                        <canvas id="categoryChart"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                """
            
            # Recommendations section
            recommendations = self.generate_recommendations()
            if recommendations:
                html_content += """
                    <div class="row mb-4">
                        <div class="col-12">
                            <div class="card shadow-sm">
                                <div class="card-body">
                                    <h5 class="card-title">Action Plan & Recommendations</h5>
                                    <div class="table-responsive">
                                        <table class="table">
                                            <thead>
                                                <tr>
                                                    <th>Priority</th>
                                                    <th>Recommendation</th>
                                                    <th>Details</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                """
                
                for i, rec in enumerate(recommendations[:REPORT_CONFIG.get("max_recommendations", 10)]):
                    priority_class = "danger" if rec.get("priority") == "high" else \
                                     "warning" if rec.get("priority") == "medium" else "info"
                    html_content += f"""
                                <tr>
                                    <td><span class="badge bg-{priority_class}">{rec.get("priority", "medium").title()}</span></td>
                                    <td>{rec["title"]}</td>
                                    <td>{rec["description"]}</td>
                                </tr>
                    """
                
                html_content += """
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                """

            # Add detailed issue sections by category
            if self.categories:
                html_content += """
                    <div class="row mb-4">
                        <div class="col-12">
                            <h3>Issues by Category</h3>
                        </div>
                    </div>
                    
                    <div class="accordion" id="issueAccordion">
                """
                
                for i, (category, issues) in enumerate(sorted(self.categories.items(), 
                                                           key=lambda x: sum(issue["severity"] for issue in x[1]), 
                                                           reverse=True)):
                    # Skip empty categories
                    if not issues:
                        continue
                    
                    # Get category details
                    high_severity = sum(1 for issue in issues if issue.get("severity", 0) >= PRIORITY_THRESHOLDS["high"])
                    medium_severity = sum(1 for issue in issues if PRIORITY_THRESHOLDS["medium"] <= issue.get("severity", 0) < PRIORITY_THRESHOLDS["high"])
                    total_issues = len(issues)
                    
                    # Get icon from the first issue in the category or default
                    icon = issues[0].get("icon", "fa-exclamation-circle") if issues else "fa-exclamation-circle"
                    
                    html_content += f"""
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button {'collapsed' if i > 0 else ''}" type="button" 
                                        data-bs-toggle="collapse" data-bs-target="#collapse{i}">
                                    <i class="fas {icon} me-2"></i> {category} 
                                    <span class="ms-2 badge bg-secondary">{total_issues}</span>
                                    {f'<span class="ms-1 badge bg-danger">{high_severity} High</span>' if high_severity else ''}
                                    {f'<span class="ms-1 badge bg-warning">{medium_severity} Medium</span>' if medium_severity else ''}
                                </button>
                            </h2>
                            <div id="collapse{i}" class="accordion-collapse collapse {'show' if i == 0 else ''}" 
                                data-bs-parent="#issueAccordion">
                                <div class="accordion-body">
                                    <div class="table-responsive">
                                        <table class="table table-striped table-hover">
                                            <thead>
                                                <tr>
                                                    <th>Severity</th>
                                                    <th>Level</th>
                                                    <th>Message</th>
                                                    <th>Timestamp</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                    """
                    
                    # Limit number of issues displayed to avoid huge HTML files
                    display_limit = min(len(issues), REPORT_CONFIG.get("max_issues_per_category", 100))
                    for issue in sorted(issues, key=lambda x: x.get("severity", 0), reverse=True)[:display_limit]:
                        severity = issue.get("severity", 5)
                        severity_class = "high" if severity >= PRIORITY_THRESHOLDS["high"] else \
                                        "medium" if severity >= PRIORITY_THRESHOLDS["medium"] else "low"
                        
                        html_content += f"""
                                                <tr>
                                                    <td><span class="severity-indicator severity-{severity_class}"></span> {severity}/10</td>
                                                    <td><span class="badge bg-{'danger' if issue['level'] == 'ERROR' else 'warning' if issue['level'] == 'WARNING' else 'info'}">{issue["level"]}</span></td>
                                                    <td>{issue["message"]}</td>
                                                    <td>{issue["timestamp"]}</td>
                                                </tr>
                        """
                    
                    # Add note if issues were truncated
                    if len(issues) > display_limit:
                        html_content += f"""
                                                <tr>
                                                    <td colspan="4" class="text-center text-muted">
                                                        {len(issues) - display_limit} more issues not shown
                                                    </td>
                                                </tr>
                        """
                    
                    html_content += """
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    """
                
                html_content += """
                    </div>
                """
            
            # JavaScript for charts and interactivity
            html_content += """
                </div> <!-- End container -->
                
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
                <script>
                    // Function to toggle all accordion items
                    function toggleAllDetails() {
                        const accordionItems = document.querySelectorAll('.accordion-collapse');
                        const allClosed = Array.from(accordionItems).every(item => !item.classList.contains('show'));
                        
                        accordionItems.forEach(item => {
                            if (allClosed) {
                                item.classList.add('show');
                            } else {
                                item.classList.remove('show');
                            }
                        });
                    }
                """
                
            # Add chart initialization if we have data
            if REPORT_CONFIG.get("include_charts", True) and self.stats["total_issues"] > 0:
                # Prepare data for severity chart
                severity_data = {}
                for category_issues in self.categories.values():
                    for issue in category_issues:
                        severity = issue.get("severity", 5)
                        severity_label = "High" if severity >= PRIORITY_THRESHOLDS["high"] else \
                                       "Medium" if severity >= PRIORITY_THRESHOLDS["medium"] else "Low"
                        severity_data[severity_label] = severity_data.get(severity_label, 0) + 1
                
                # Prepare data for category chart
                category_data = {cat: len(issues) for cat, issues in self.categories.items() if issues}
                
                # Only include top categories to avoid cluttered chart
                if len(category_data) > 8:
                    sorted_categories = sorted(category_data.items(), key=lambda x: x[1], reverse=True)
                    top_categories = dict(sorted_categories[:7])
                    others = sum(count for _, count in sorted_categories[7:])
                    top_categories["Others"] = others
                    category_data = top_categories
                
                chart_colormap = REPORT_CONFIG.get("chart_colormap", "viridis")
                
                html_content += f"""
                    // Chart.js configuration - Severity Distribution
                    document.addEventListener('DOMContentLoaded', function() {{
                        // Severity chart
                        const severityCtx = document.getElementById('severityChart').getContext('2d');
                        const severityChart = new Chart(severityCtx, {{
                            type: 'doughnut',
                            data: {{
                                labels: {list(severity_data.keys())},
                                datasets: [{{
                                    data: {list(severity_data.values())},
                                    backgroundColor: [
                                        '#dc3545',  // High - Red
                                        '#ffc107',  // Medium - Yellow
                                        '#0dcaf0'   // Low - Blue
                                    ],
                                    borderWidth: 1
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {{
                                    legend: {{
                                        position: 'right',
                                    }},
                                    title: {{
                                        display: true,
                                        text: 'Issues by Severity Level'
                                    }}
                                }}
                            }}
                        }});
                        
                        // Category chart
                        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
                        const categoryChart = new Chart(categoryCtx, {{
                            type: 'bar',
                            data: {{
                                labels: {list(category_data.keys())},
                                datasets: [{{
                                    label: 'Number of Issues',
                                    data: {list(category_data.values())},
                                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                                    borderColor: 'rgba(54, 162, 235, 1)',
                                    borderWidth: 1
                                }}]
                            }},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {{
                                    y: {{
                                        beginAtZero: true,
                                        title: {{
                                            display: true,
                                            text: 'Count'
                                        }}
                                    }},
                                    x: {{
                                        ticks: {{
                                            autoSkip: false,
                                            maxRotation: 45,
                                            minRotation: 45
                                        }}
                                    }}
                                }},
                                plugins: {{
                                    title: {{
                                        display: true,
                                        text: 'Issues by Category'
                                    }}
                                }}
                            }}
                        }});
                    }});
                """
                
            html_content += """
                </script>
            </body>
            </html>
            """
            
            # Write the report to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated successfully at {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}\n{traceback.format_exc()}")
            # Create a minimal error report
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"""<!DOCTYPE html>
                    <html>
                    <head><title>Error Generating Report</title></head>
                    <body>
                        <h1>Error Generating Diagnostic Report</h1>
                        <p>An error occurred while generating the report: {e}</p>
                        <pre>{traceback.format_exc()}</pre>
                    </body>
                    </html>""")
                return output_file
            except:
                logger.error("Failed to create even the error report")
                return None

    def generate_recommendations(self) -> List[Dict]:
        """Generate detailed recommendations based on the identified issues."""
        recommendations = []
        
        # Handle edge case: no issues found
        if self.stats["total_issues"] == 0:
            recommendations.append({
                "title": "No issues detected",
                "description": "No issues were found in the diagnostic log. This could mean your codebase is in good shape, or the diagnostic tool didn't run completely.",
                "priority": "low"
            })
            return recommendations
        
        # Analyze code complexity issues
        complexity_issues = [issue for category, issues in self.categories.items() 
                            if category == "Code Complexity" 
                            for issue in issues]
        if complexity_issues:
            high_complexity_count = sum(1 for issue in complexity_issues if issue.get("severity", 0) >= 8)
            if high_complexity_count > 0:
                recommendations.append({
                    "title": "Review High Complexity Code",
                    "description": f"Found {high_complexity_count} functions with excessive cyclomatic complexity. Consider breaking these functions into smaller, more manageable units with clear responsibilities.",
                    "priority": "high"
                })
            else:
                recommendations.append({
                    "title": "Improve Code Complexity",
                    "description": f"Found {len(complexity_issues)} functions with elevated complexity. Consider refactoring using design patterns and extracting helper methods.",
                    "priority": "medium"
                })
        
        # Check for security issues - always high priority
        security_issues = [issue for category, issues in self.categories.items() 
                          if category == "Security" 
                          for issue in issues]
        if security_issues:
            recommendations.append({
                "title": "Address Security Vulnerabilities",
                "description": f"Found {len(security_issues)} security issues that require immediate attention. Review and fix vulnerabilities to prevent potential exploits.",
                "priority": "high"
            })
        
        # Check for dependency issues
        dependency_issues = [issue for category, issues in self.categories.items() 
                            if category == "Dependencies" 
                            for issue in issues]
        if dependency_issues:
            outdated_deps = sum(1 for issue in dependency_issues if "outdated" in issue["message"].lower())
            vulnerability_deps = sum(1 for issue in dependency_issues if "vulnerab" in issue["message"].lower())
            if vulnerability_deps > 0:
                recommendations.append({
                    "title": "Update Vulnerable Dependencies",
                    "description": f"Found {vulnerability_deps} dependencies with known security vulnerabilities. Update these dependencies to their latest secure versions immediately.",
                    "priority": "high"
                })
            elif outdated_deps > 0:
                recommendations.append({
                    "title": "Update Outdated Dependencies",
                    "description": f"Found {outdated_deps} outdated dependencies. Consider updating to benefit from bug fixes, performance improvements, and new features.",
                    "priority": "medium"
                })
        
        # Check for code duplication
        duplication_issues = [issue for category, issues in self.categories.items() 
                              if category == "Code Duplication" 
                              for issue in issues]
        if duplication_issues:
            recommendations.append({
                "title": "Reduce Code Duplication",
                "description": f"Found {len(duplication_issues)} instances of duplicated code. Extract common functionality into shared methods or classes to improve maintainability.",
                "priority": "medium"
            })
        
        # Check for unused code
        unused_code_issues = [issue for category, issues in self.categories.items() 
                             if category == "Unused Code" 
                             for issue in issues]
        if unused_code_issues:
            unused_imports = sum(1 for issue in unused_code_issues if "import" in issue["message"].lower())
            unused_vars = sum(1 for issue in unused_code_issues if "variable" in issue["message"].lower())
            recommendations.append({
                "title": "Clean Up Unused Code",
                "description": f"Found {unused_imports} unused imports and {unused_vars} unused variables. Remove dead code to improve readability and performance.",
                "priority": "low"
            })
        
        # Check naming conventions
        naming_issues = [issue for category, issues in self.categories.items() 
                        if "Naming" in category 
                        for issue in issues]
        if naming_issues:
            recommendations.append({
                "title": "Standardize Naming Conventions",
                "description": f"Found {len(naming_issues)} naming convention issues. Establish and follow consistent naming patterns to improve code readability.",
                "priority": "low" if len(naming_issues) < 10 else "medium"
            })
        
        # Check for error handling
        error_handling_issues = [issue for category, issues in self.categories.items() 
                                if category == "Error Handling" 
                                for issue in issues]
        if error_handling_issues:
            broad_exceptions = sum(1 for issue in error_handling_issues if "broad except" in issue["message"].lower())
            if broad_exceptions > 0:
                recommendations.append({
                    "title": "Improve Exception Handling",
                    "description": f"Found {broad_exceptions} instances of overly broad exception catching. Catch specific exceptions to handle errors properly.",
                    "priority": "medium"
                })
        
        # File health issues
        file_health_issues = [issue for category, issues in self.categories.items() 
                             if category == "File Health" 
                             for issue in issues]
        if file_health_issues:
            missing_files = sum(1 for issue in file_health_issues if "missing" in issue["message"].lower())
            empty_files = sum(1 for issue in file_health_issues if "empty" in issue["message"].lower())
            if missing_files > 0:
                recommendations.append({
                    "title": "Restore Missing Files",
                    "description": f"Found {missing_files} missing expected files. Restore these files or update project configuration to avoid dependency errors.",
                    "priority": "high"
                })
            if empty_files > 0:
                recommendations.append({
                    "title": "Address Empty Files",
                    "description": f"Found {empty_files} empty files. Either add content or remove these files to maintain a clean codebase.",
                    "priority": "low"
                })
        
        # Add general recommendations if specific ones are few
        if len(recommendations) < 3:
            # Analyze most common issue categories
            categories_count = Counter([category for category, issues in self.categories.items() for _ in issues])
            most_common = categories_count.most_common(3)
            
            for category, count in most_common:
                if not any(rec["title"].startswith(f"Improve {category}") for rec in recommendations):
                    recommendations.append({
                        "title": f"Improve {category}",
                        "description": f"Focus on addressing the {count} issues found in the {category} category to improve overall code quality.",
                        "priority": "medium"
                    })
        
        # Add general CI/CD recommendation based on recurrent issues if they exist
        if self.stats.get("recurrent_issues", 0) > 5:
            recommendations.append({
                "title": "Automate Code Quality Checks",
                "description": f"Found {self.stats['recurrent_issues']} recurrent issues across runs. Consider integrating static analysis into your CI/CD pipeline to catch issues earlier.",
                "priority": "medium"
            })
        
        # Handle edge case: too many recommendations
        max_recommendations = REPORT_CONFIG.get("max_recommendations", 10)
        if len(recommendations) > max_recommendations:
            # Sort by priority first, then return the top N
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_recommendations = sorted(recommendations, 
                                          key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
            return sorted_recommendations[:max_recommendations]
        
        return recommendations

async def main():
    """Main function to run the log analysis with enhanced error handling and reporting."""
    start_time = datetime.now()
    success_flags = {"parsing": False, "console": False, "csv": False, "html": False}
    
    try:
        # Handle command line arguments more robustly
        log_files = [Path(arg) for arg in sys.argv[1:] if os.path.isfile(arg)]
        if not log_files:
            if not LOG_FILE.exists():
                logger.error(f"Log file {LOG_FILE} not found. Please provide a valid log file path.")
                print(f"Error: Log file {LOG_FILE} not found. Please provide a valid log file path.")
                return 1
            log_files = [LOG_FILE]
        
        # Process multiple log files if provided
        all_issues = 0
        for log_file in log_files:
            logger.info(f"Processing log file: {log_file}")
            print(f"\n[+] Analyzing log file: {log_file}")
            
            # Verify file is readable and not empty
            if not os.access(log_file, os.R_OK):
                logger.error(f"Cannot read log file: {log_file} (Permission denied)")
                print(f"Error: Cannot read log file - Permission denied")
                continue
                
            if os.path.getsize(log_file) == 0:
                logger.warning(f"Log file {log_file} is empty")
                print(f"Warning: Log file {log_file} is empty - skipping analysis")
                continue
            
            # Create analyzer and parse logs
            analyzer = LogAnalyzer(log_file)
            print("[*] Parsing log file...")
            await analyzer.parse_log()
            success_flags["parsing"] = True
            all_issues += analyzer.stats["total_issues"]
            
            # Generate reports with progress indicators
            if analyzer.stats["total_issues"] > 0:
                print(f"[*] Generating console report for {analyzer.stats['total_issues']} issues...")
                analyzer.generate_console_report()
                success_flags["console"] = True
                
                # Create directory for output files if it doesn't exist
                try:
                    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
                except PermissionError:
                    logger.error(f"Cannot create output directory: {OUTPUT_DIR} (Permission denied)")
                    print(f"Error: Cannot create output directory - Permission denied")
                    # Fall back to current directory
                    output_dir = Path(".")
                
                # Generate CSV report
                try:
                    print("[*] Generating CSV report...")
                    csv_file = OUTPUT_DIR / f"diagnostic_report_{log_file.stem}_{TIMESTAMP}.csv"
                    analyzer.generate_csv_report(csv_file)
                    success_flags["csv"] = True
                    print(f"[+] CSV report saved to: {csv_file}")
                except Exception as e:
                    logger.error(f"CSV report generation failed: {e}")
                    print(f"[-] CSV report generation failed: {str(e)}")
                
                # Generate HTML report
                try:
                    print("[*] Generating HTML report...")
                    html_file = OUTPUT_DIR / f"diagnostic_report_{log_file.stem}_{TIMESTAMP}.html"
                    html_path = analyzer.generate_html_report(html_file)
                    if html_path:
                        success_flags["html"] = True
                        print(f"[+] HTML report saved to: {html_path}")
                except Exception as e:
                    logger.error(f"HTML report generation failed: {e}")
                    print(f"[-] HTML report generation failed: {str(e)}")
            else:
                print("No issues found in the log file. No detailed reports generated.")
                
            # Save analysis history
            try:
                analyzer._save_history()
                print("[+] Analysis history updated")
            except Exception as e:
                logger.error(f"Failed to save analysis history: {e}")
                print(f"[-] Failed to save analysis history: {str(e)}")
        
        # Summary of all processed files
        elapsed_time = (datetime.now() - start_time).total_seconds()
        print(f"\n=== Summary ===")
        print(f"Processed {len(log_files)} log file(s) in {elapsed_time:.2f} seconds")
        print(f"Total issues found: {all_issues}")
        print(f"Reports generated: " + 
              f"{'Console ✓ ' if success_flags['console'] else 'Console ✗ '}" +
              f"{'CSV ✓ ' if success_flags['csv'] else 'CSV ✗ '}" +
              f"{'HTML ✓' if success_flags['html'] else 'HTML ✗'}")
        
        # Check if any reports were successfully generated
        if not any(success_flags.values()):
            logger.warning("No reports were successfully generated")
            return 1
        
        return 0
            
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user.")
        return 130
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}\n{traceback.format_exc()}")
        print(f"\n[-] An error occurred: {e}")
        if "permission" in str(e).lower():
            print("   This may be due to insufficient permissions. Try running with elevated privileges.")
        elif "disk" in str(e).lower():
            print("   This may be due to insufficient disk space. Free up some disk space and try again.")
        return 1
    finally:
        print(f"\nAnalysis completed in {(datetime.now() - start_time).total_seconds():.2f} seconds")

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)