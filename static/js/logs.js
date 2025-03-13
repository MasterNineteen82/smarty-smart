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
        const logLevel = logLevelSelect.value;
        const logFile = logFileSelect.value;
        const searchTerm = logSearchInput.value;
        const logLines = logLinesSelect.value;

        // Construct the URL with query parameters
        let url = `/api/logs?level=${logLevel}&file=${logFile}&search=${searchTerm}&lines=${logLines}`;

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                displayLogs(data);
            })
            .catch(error => {
                console.error('Failed to fetch logs:', error);
                displayAlert('danger', 'Failed to load logs. Check the console for details.');
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
        const logHtml = escapeHtml(log); // Escape HTML entities to prevent XSS
        const highlightedLog = highlightSearchTerm(logHtml, searchTerm);

        return `<div class="log-line">${highlightedLog}</div>`;
    }

    // Function to escape HTML entities
    function escapeHtml(text) {
        let map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };

        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    // Function to highlight the search term in the log line
    function highlightSearchTerm(logHtml, searchTerm) {
        if (!searchTerm) return logHtml;

        const regex = new RegExp(escapeRegex(searchTerm), 'gi');
        return logHtml.replace(regex, '<span class="log-highlight">$&</span>');
    }

    // Function to escape regex special characters
    function escapeRegex(string) {
        return string.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    }

    // Function to update log statistics
    function updateLogStats(showingLines, filteredLines, logFile) {
        logCountElement.textContent = `${showingLines} entries`;
        logStatsElement.textContent = `Showing ${filteredLines} of ${showingLines} entries from ${logFile}`;
    }

    // Function to scroll to the bottom of the log container
    function scrollToBottom() {
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Function to get the status icon for a log line
    function getStatusIcon(logHtml) {
        if (logHtml.includes('ERROR')) return '<i class="bi bi-x-circle log-error-icon"></i>';
        if (logHtml.includes('WARNING')) return '<i class="bi bi-exclamation-triangle log-warning-icon"></i>';
        if (logHtml.includes('INFO')) return '<i class="bi bi-info-circle log-info-icon"></i>';
        if (logHtml.includes('DEBUG')) return '<i class="bi bi-bug log-debug-icon"></i>';
        return '';
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
        const alertContainer = document.getElementById('alert-container');
        alertContainer.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
        setTimeout(() => {
            alertContainer.innerHTML = '';
        }, 5000);
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

// Function to clear logs
async function clearLogs() {
    try {
        const response = await fetch('/api/logs/clear', { method: 'POST' }); // Replace with your actual API endpoint
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        displayAlert('success', 'Logs cleared successfully.');
        fetchLogs(); // Refresh the log display
    } catch (error) {
        console.error('Failed to clear logs:', error);
        displayAlert('danger', 'Failed to clear logs. Check the console for details.');
    }
}