// Global variables
let refreshInterval;
let lastLogCount = 0;

document.addEventListener('DOMContentLoaded', function() {
    // Initial load of logs
    fetchLogs();
    
    // Add event listener for Enter key on search input
    document.getElementById('log-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            fetchLogs();
        }
    });
    
    // Set theme based on saved preference
    const prefersDarkTheme = localStorage.getItem('smarty-log-dark-theme') !== 'false';
    if (!prefersDarkTheme) {
        document.body.classList.add('light-theme');
    }
    
    // Setup auto-refresh toggle
    document.getElementById('auto-refresh').addEventListener('change', function() {
console.log("DEBUG: Ensure event listeners are attached.");
        setupAutoRefresh();
    });
    
    // Listen for level filter changes
    document.getElementById('log-level').addEventListener('change', function() {
console.log("DEBUG: Ensure event listeners are attached.");
        fetchLogs();
    });
    
    // Listen for log file selection changes
    document.getElementById('log-file').addEventListener('change', function() {
console.log("DEBUG: Ensure event listeners are attached.");
        fetchLogs();
    });
    
    // Listen for lines count changes
    document.getElementById('log-lines').addEventListener('change', function() {
console.log("DEBUG: Ensure event listeners are attached.");
        fetchLogs();
    });
});

function setupAutoRefresh() {
    // Clear any existing interval
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    // Setup new interval if auto-refresh is checked
    if (document.getElementById('auto-refresh').checked) {
        refreshInterval = setInterval(fetchLogs, 5000);
    }
}

function fetchLogs() {
    // Get filter parameters
    const level = document.getElementById('log-level').value;
    const lines = document.getElementById('log-lines').value;
    const search = document.getElementById('log-search').value;
    const logFile = document.getElementById('log-file').value;
    
    // Build URL with query parameters
    const url = `/api/logs?level=${level}&lines=${lines}&search=${encodeURIComponent(search)}&file=${logFile}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayLogs(data);
            } else {
                document.getElementById('log-container').innerHTML = 
                    `<div class="alert alert-danger">${data.message || 'Failed to fetch logs'}</div>`;
            }
        })
        .catch(error => {
            document.getElementById('log-container').innerHTML = 
                `<div class="alert alert-danger">Error fetching logs: ${error.message}</div>`;
        });
}

function displayLogs(data) {
    const container = document.getElementById('log-container');
    const searchTerm = document.getElementById('log-search').value.toLowerCase();
    
    let logsHtml = '';
    
    data.logs.forEach(log => {
        // Apply highlighting based on log level
        let logHtml = log;
        
        // Add status icons based on log level
        let statusIcon = '';
        if (logHtml.includes(' - ERROR - ') || logHtml.includes(' - CRITICAL - ')) {
            statusIcon = '<span class="log-icon log-error-icon">❗</span>';
        } else if (logHtml.includes(' - WARNING - ')) {
            statusIcon = '<span class="log-icon log-warning-icon">⚠️</span>';
        } else if (logHtml.includes(' - INFO - ')) {
            statusIcon = '<span class="log-icon log-info-icon">ℹ️</span>';
        } else if (logHtml.includes(' - DEBUG - ')) {
            statusIcon = '<span class="log-icon log-debug-icon">🔍</span>';
        } else {
            statusIcon = '<span class="log-icon">📋</span>';
        }
        
        // Highlight timestamp
        logHtml = logHtml.replace(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}/, 
            match => `<span class="log-timestamp">${match}</span>`);
        
        // Highlight log levels
        logHtml = logHtml.replace(/ - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - /, (match, level) => {
            return ` - <span class="log-${level.toLowerCase()}">${level}</span> - `;
        });
        
        // Highlight module names
        logHtml = logHtml.replace(/ - ([a-zA-Z0-9_\.]+):\d+ - /, (match, module) => {
            return ` - <span class="log-module">${module}</span>:${match.split(':')[1]} - `;
        });
        
        // Format installation messages
        if (logHtml.includes('is not installed. Attempting to install')) {
            logHtml = logHtml.replace(/([a-zA-Z0-9_\.-]+) is not installed/, 
                '<strong>$1</strong> is not installed');
        }
        if (logHtml.includes('Installing ')) {
            logHtml = logHtml.replace(/Installing ([a-zA-Z0-9_\.-]+)/, 
                'Installing <strong>$1</strong>');
        }
        if (logHtml.includes('successfully installed')) {
            logHtml = logHtml.replace(/([a-zA-Z0-9_\.-]+) was successfully installed/, 
                '<strong>$1</strong> was successfully installed');
        }
        
        // Highlight search term if any
        if (searchTerm) {
            const regex = new RegExp(`(${searchTerm})`, 'gi');
            logHtml = logHtml.replace(regex, '<span class="log-highlight">$1</span>');
        }
        
        // Format dependencies with indentation
        if (logHtml.includes('Requirement already satisfied: ')) {
            logHtml = logHtml.replace(/Requirement already satisfied: ([^\s]+)/, 
                'Requirement already satisfied: <strong>$1</strong>');
            
            // Add indentation for nested dependencies
            if (logHtml.includes(' in ')) {
                logHtml = `<span class="log-indent">${logHtml}</span>`;
            }
        }
        
        // Add icon to beginning of log line
        logsHtml += `<div class="log-line">${statusIcon} ${logHtml}</div>`;
    });
    
    container.innerHTML = logsHtml;
    
    // Update log count display
    document.getElementById('log-count').textContent = `${data.showing_lines} of ${data.filtered_lines} entries`;
    
    // Update log stats
    document.getElementById('log-stats').textContent = 
        `Log Entries (${data.log_file})`;
    
    // Auto-scroll to bottom if enabled
    if (document.getElementById('auto-scroll').checked) {
        container.scrollTop = container.scrollHeight;
    }
    
    // Store log count to detect changes
    lastLogCount = data.showing_lines;
}

function clearLogs() {
    // Get the current log file
    const logFile = document.getElementById('log-file').value;
    
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
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Show success message
            const alert = document.createElement('div');
            alert.className = 'alert alert-success alert-dismissible fade show';
            alert.innerHTML = `
                <i class="bi bi-check-circle-fill me-2"></i> ${data.message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            document.querySelector('.container').prepend(alert);
console.log("DEBUG: Ensure this element selector is correct.");
            
            // Refresh logs
            fetchLogs();
        } else {
            // Show error message
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger alert-dismissible fade show';
            alert.innerHTML = `
                <i class="bi bi-exclamation-triangle-fill me-2"></i> ${data.message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            document.querySelector('.container').prepend(alert);
console.log("DEBUG: Ensure this element selector is correct.");
        }
    })
    .catch(error => {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            <i class="bi bi-exclamation-triangle-fill me-2"></i> Error clearing logs: ${error.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.querySelector('.container').prepend(alert);
console.log("DEBUG: Ensure this element selector is correct.");
    });
}

function toggleTheme() {
    document.body.classList.toggle('light-theme');
    
    // Store theme preference
    const isDarkTheme = !document.body.classList.contains('light-theme');
    localStorage.setItem('smarty-log-dark-theme', isDarkTheme);
}