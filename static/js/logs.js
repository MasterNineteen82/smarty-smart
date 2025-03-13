// Import necessary modules (if you modularize further)
// import { displayAlert } from './utils.js'; // Example

// Global variables (consider minimizing these)
let refreshInterval;

document.addEventListener('DOMContentLoaded', function() {
    // DOM element references
    const logOutput = document.getElementById('logOutput');
    const logFilter = document.getElementById('logFilter');
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    const logLevelSelect = document.getElementById('log-level');
    const logFileSelect = document.getElementById('log-file');
    const logLinesSelect = document.getElementById('log-lines');
    const logSearchInput = document.getElementById('log-search');
    const logContainer = document.getElementById('log-container');
    const autoScrollCheckbox = document.getElementById('auto-scroll');
    const logCountElement = document.getElementById('log-count');
    const logStatsElement = document.getElementById('log-stats');
    const clearLogsButton = document.getElementById('clear-logs');

    // Validate critical DOM elements
    if (!logOutput || !logFilter || !autoRefreshCheckbox || !logLevelSelect ||
        !logFileSelect || !logLinesSelect || !logSearchInput || !logContainer ||
        !autoScrollCheckbox || !logCountElement || !logStatsElement) {
        console.error('One or more critical elements not found in the DOM.');
        displayAlert('danger', 'Critical elements missing. Check console for details.');
        return;
    }

    // --- Functions ---

    // Function to fetch logs from the API
    function fetchLogs() {
        const level = logLevelSelect.value;
        const lines = logLinesSelect.value;
        const search = encodeURIComponent(logSearchInput.value);
        const logFile = logFileSelect.value;

        const url = `/api/logs?level=${level}&lines=${lines}&search=${search}&file=${logFile}`;

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.status === 'success') {
                    displayLogs(data);
                } else {
                    displayAlert('danger', data.message || 'Failed to fetch logs');
                }
            })
            .catch(error => {
                console.error('Error fetching logs:', error);
                displayAlert('danger', `Error fetching logs: ${error.message}`);
            });
    }

    // Function to display logs in the UI
    function displayLogs(data) {
        if (!data || !data.logs) {
            displayAlert('warning', 'No logs data received.');
            logContainer.innerHTML = '';
            updateLogStats(0, 0, 'No Log File');
            return;
        }

        const searchTerm = logSearchInput.value.toLowerCase();
        let logsHtml = data.logs.map(log => formatLogLine(log, searchTerm)).join('');

        logContainer.innerHTML = logsHtml;
        updateLogStats(data.showing_lines, data.filtered_lines, data.log_file);

        if (autoScrollCheckbox.checked) {
            scrollToBottom();
        }
    }

    // Function to format a single log line
    function formatLogLine(log, searchTerm) {
        let logHtml = log;
        let statusIcon = getStatusIcon(logHtml);

        logHtml = highlightTimestamp(logHtml);
        logHtml = highlightLogLevel(logHtml);
        logHtml = highlightModuleNames(logHtml);
        logHtml = formatInstallationMessages(logHtml);
        logHtml = highlightSearchTerm(logHtml, searchTerm);
        logHtml = formatDependencies(logHtml);

        return `<div class="log-line">${statusIcon} ${logHtml}</div>`;
    }

    // Function to update log statistics
    function updateLogStats(showingLines, filteredLines, logFile) {
        logCountElement.textContent = `${showingLines} of ${filteredLines} entries`;
        logStatsElement.textContent = `Log Entries (${logFile})`;
    }

    // Function to scroll to the bottom of the log container
    function scrollToBottom() {
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Function to get the status icon for a log line
    function getStatusIcon(logHtml) {
        if (logHtml.includes(' - ERROR - ') || logHtml.includes(' - CRITICAL - ')) {
            return '<span class="log-icon log-error-icon">❗</span>';
        } else if (logHtml.includes(' - WARNING - ')) {
            return '<span class="log-icon log-warning-icon">⚠️</span>';
        } else if (logHtml.includes(' - INFO - ')) {
            return '<span class="log-icon log-info-icon">ℹ️</span>';
        } else if (logHtml.includes(' - DEBUG - ')) {
            return '<span class="log-icon log-debug-icon">🔍</span>';
        } else {
            return '<span class="log-icon">📋</span>';
        }
    }

    // Function to highlight the timestamp in a log line
    function highlightTimestamp(logHtml) {
        return logHtml.replace(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}/,
            match => `<span class="log-timestamp">${match}</span>`);
    }

    // Function to highlight the log level in a log line
    function highlightLogLevel(logHtml) {
        return logHtml.replace(/ - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - /, (match, level) => {
            return ` - <span class="log-${level.toLowerCase()}">${level}</span> - `;
        });
    }

    // Function to highlight module names in a log line
    function highlightModuleNames(logHtml) {
        return logHtml.replace(/ - ([a-zA-Z0-9_\.]+):\d+ - /, (match, module) => {
            const lineNumber = match.split(':')[1].replace(' - ', '');
            return ` - <span class="log-module">${module}</span>:<span class="log-line-number">${lineNumber}</span> - `;
        });
    }

    // Function to format installation messages in a log line
    function formatInstallationMessages(logHtml) {
        logHtml = logHtml.replace(/([a-zA-Z0-9_\.-]+) is not installed/,
            '<strong>$1</strong> is not installed');
        logHtml = logHtml.replace(/Installing ([a-zA-Z0-9_\.-]+)/,
            'Installing <strong>$1</strong>');
        logHtml = logHtml.replace(/([a-zA-Z0-9_\.-]+) was successfully installed/,
            '<strong>$1</strong> was successfully installed');
        return logHtml;
    }

    // Function to highlight the search term in a log line
    function highlightSearchTerm(logHtml, searchTerm) {
        if (searchTerm) {
            const regex = new RegExp(`(${searchTerm})`, 'gi');
            logHtml = logHtml.replace(regex, '<span class="log-highlight">$1</span>');
        }
        return logHtml;
    }

    // Function to format dependencies in a log line
    function formatDependencies(logHtml) {
        if (logHtml.includes('Requirement already satisfied: ')) {
            logHtml = logHtml.replace(/Requirement already satisfied: ([^\s]+)/,
                'Requirement already satisfied: <strong>$1</strong>');

            if (logHtml.includes(' in ')) {
                logHtml = `<span class="log-indent">${logHtml}</span>`;
            }
        }
        return logHtml;
    }

    // Function to clear the logs
    function clearLogs() {
        const logFile = logFileSelect.value;

        if (!confirm(`Are you sure you want to clear the "${logFile}" log file?`)) {
            return;
        }

        fetch('/api/logs/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ file: logFile })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.status === 'success') {
                    displayAlert('success', data.message);
                    fetchLogs();
                } else {
                    displayAlert('danger', data.message || 'Failed to clear logs');
                }
            })
            .catch(error => {
                console.error('Error clearing logs:', error);
                displayAlert('danger', `Error clearing logs: ${error.message}`);
            });
    }

    // Function to toggle the theme
    function toggleTheme() {
        document.body.classList.toggle('light-theme');
        const isDarkTheme = !document.body.classList.contains('light-theme');
        localStorage.setItem('smarty-log-dark-theme', isDarkTheme);
    }

    // Function to set up auto-refresh
    function setupAutoRefresh() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }

        if (autoRefreshCheckbox.checked) {
            refreshInterval = setInterval(fetchLogs, 5000);
        }
    }

    // Function to filter logs based on search input
    function filterLogs(filterText) {
        // This function is no longer used, filtering is done on the backend
        console.warn('filterLogs function is deprecated. Filtering is now done on the backend.');
    }

    // Function to display alerts
    function displayAlert(type, message) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle-fill' : 'exclamation-triangle-fill'} me-2"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        logContainer.prepend(alert); // Prepends to the log container
    }

    // --- Event Listeners ---

    // Event listener for log filter input (deprecated)
    logFilter.addEventListener('keyup', function() {
        console.warn('Log filter input is deprecated. Filtering is now done on the backend.');
    });

    // Event listener for log search input
    logSearchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            fetchLogs();
        }
    });

    // Event listener for auto-refresh checkbox
    autoRefreshCheckbox.addEventListener('change', setupAutoRefresh);

    // Event listener for log level select
    logLevelSelect.addEventListener('change', fetchLogs);

    // Event listener for log file select
    logFileSelect.addEventListener('change', fetchLogs);

    // Event listener for log lines select
    logLinesSelect.addEventListener('change', fetchLogs);

    // Event listener for clear logs button
    if (clearLogsButton) {
        clearLogsButton.addEventListener('click', clearLogs);
    } else {
        console.warn('Clear logs button not found. Ensure it has the ID "clear-logs".');
    }

    // --- Initial Setup ---

    // Set theme based on local storage
    const prefersDarkTheme = localStorage.getItem('smarty-log-dark-theme') !== 'false';
    if (!prefersDarkTheme) {
        document.body.classList.add('light-theme');
    }

    // Set up auto-refresh
    setupAutoRefresh();

    // Fetch logs on page load
    fetchLogs();
});