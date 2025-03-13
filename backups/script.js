function fetchAndDisplay(endpoint, method, data = {}) {
    fetch(endpoint, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: method === 'POST' ? JSON.stringify(data) : undefined
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('output').textContent = data.message;
        document.getElementById('status').textContent = data.status === 'error' ? 'Error' : 'Connected';
    })
    .catch(err => {
        document.getElementById('output').textContent = `Error: ${err}`;
    });
}

function startServer() { fetchAndDisplay('/start_server', 'POST'); }
function stopServer() { fetchAndDisplay('/stop_server', 'POST'); }

function connectCard() {
    const reader = document.getElementById('reader-select').value;
    fetch('/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reader: reader })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('status').textContent = data.message;
        document.getElementById('atr').textContent = `ATR: ${data.atr || ''}`;
        document.getElementById('output').textContent = data.message;
    });
}

function readMemory() { fetchAndDisplay('/read_memory', 'POST'); }
function verifyPin() {
    const pin = document.getElementById('old-pin').value.trim();
    
    if (!pin) {
        showResult('Please enter a PIN', 'error');
        return;
    }
    
    fetch('/verify_pin', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ pin })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}
function updatePin() {
    const pin = document.getElementById('new-pin').value;
    fetchAndDisplay('/update_pin', 'POST', { pin: pin });
}
function readMemoryRegion() {
    const offset = parseInt(document.getElementById('memory-offset').value, 10);
    const length = parseInt(document.getElementById('memory-length').value, 10);
    
    if (isNaN(offset) || isNaN(length) || offset < 0 || length <= 0) {
        showResult('Invalid offset or length values', 'error');
        return;
    }
    
    fetch('/read_memory_region', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ offset, length })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message.replace(/\n/g, '<br>'), data.status, true);
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}
function writeMemory() {
    const offset = parseInt(document.getElementById('memory-offset').value, 10);
    const data = document.getElementById('memory-data').value.trim();
    
    if (isNaN(offset) || offset < 0) {
        showResult('Invalid offset value', 'error');
        return;
    }
    
    if (!data.match(/^[0-9A-Fa-f]+$/)) {
        showResult('Memory data must be valid hexadecimal', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to write to card memory? This operation cannot be undone.')) {
        return;
    }
    
    fetch('/write_memory', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ offset, data })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}
function changePin() {
    const oldPin = document.getElementById('old-pin').value.trim();
    const newPin = document.getElementById('change-new-pin').value.trim();
    
    if (!oldPin || !newPin) {
        showResult('Please enter both current and new PINs', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to change the card PIN?')) {
        return;
    }
    
    fetch('/change_pin', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ old_pin: oldPin, new_pin: newPin })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        if (data.status === 'success') {
            document.getElementById('old-pin').value = '';
            document.getElementById('change-new-pin').value = '';
        }
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}
function getCardInfo() {
    fetch('/card_info')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                try {
                    const info = JSON.parse(data.message);
                    let detailsHtml = `
                        <h5>Card Information</h5>
                        <div class="table-responsive">
                            <table class="table table-striped table-sm">
                                <tr>
                                    <th>ATR</th>
                                    <td><code>${info.atr || 'Unknown'}</code></td>
                                </tr>
                                <tr>
                                    <th>Card Type</th>
                                    <td>${info.card_type || 'Unknown'}</td>
                                </tr>
                                <tr>
                                    <th>Reader Type</th>
                                    <td>${info.reader_type || 'Unknown'}</td>
                                </tr>
                                <tr>
                                    <th>Protocol</th>
                                    <td>${info.protocol || 'Unknown'}</td>
                                </tr>
                                <tr>
                                    <th>Status</th>
                                    <td><span class="badge bg-${info.card_status === 'ACTIVE' ? 'success' : 
                                           info.card_status === 'BLOCKED' ? 'danger' : 
                                           info.card_status === 'INACTIVE' ? 'warning' : 'secondary'}">${info.card_status}</span></td>
                                </tr>
                                <tr>
                                    <th>Registered</th>
                                    <td>${info.registered ? 'Yes' : 'No'}</td>
                                </tr>
                            </table>
                        </div>
                    `;
                    
                    // Add extra info if available
                    if (info.extra && Object.keys(info.extra).length > 0) {
                        detailsHtml += `
                            <h5 class="mt-3">Additional Information</h5>
                            <div class="table-responsive">
                                <table class="table table-striped table-sm">
                                    ${Object.entries(info.extra).map(([key, value]) => 
                                        `<tr>
                                            <th>${key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' ')}</th>
                                            <td>${value}</td>
                                        </tr>`
                                    ).join('')}
                                </table>
                            </div>
                        `;
                    }
                    
                    showResult(detailsHtml, data.status, true);
                } catch (e) {
                    showResult('Error parsing card info: ' + e, 'error');
                }
            } else {
                showResult(data.message, data.status);
            }
        })
        .catch(error => showResult('Error: ' + error, 'error'));
}
function getCardStatus() { fetchAndDisplay('/card_status', 'GET'); }
function confirmFormat() {
    if (confirm('Are you sure you want to format the card?')) {
        fetchAndDisplay('/format_card', 'POST', { confirm: true });
    }
}
function confirmBlockCard() {
    if (confirm('Are you sure you want to block the card?')) {
        fetchAndDisplay('/block_card', 'POST', { confirm: true });
    }
}

// Real-time status update
setInterval(() => {
    fetch('/card_status', { method: 'GET' })
    .then(response => response.json())
    .then(data => {
        document.getElementById('status').textContent = data.message.split('\n')[0].replace('Card Status: ', '');
        document.getElementById('atr').textContent = `ATR: ${data.message.split('ATR: ')[1]?.split('\n')[0] || ''}`;
    })
    .catch(() => {});
}, 1000);

// Add these functions to handle the new functionality

// Card Registration Functions
function registerCard() {
    const name = document.getElementById('card-name').value;
    const userId = document.getElementById('user-id').value;
    
    if (!name || !userId) {
        showResult('Please enter both name and user ID', 'error');
        return;
    }
    
    fetch('/register_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        if (data.status === 'success') {
            // Update UI to reflect registered state
            updateStatus();
        }
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

function checkRegistration() {
    fetch('/check_registration')
        .then(response => response.json())
        .then(data => {
            let message = data.registered ? 
                'This card is registered in the system.' : 
                'This card is not registered.';
            
            if (data.card_info && data.card_info.card_type) {
                message += ` Card type: ${data.card_info.card_type}`;
            }
            
            showResult(message, data.status);
        })
        .catch(error => showResult('Error: ' + error, 'error'));
}

function unregisterCard() {
    if (!confirm('Are you sure you want to unregister this card?')) {
        return;
    }
    
    fetch('/unregister_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        if (data.status === 'success') {
            // Clear input fields
            document.getElementById('card-name').value = '';
            document.getElementById('user-id').value = '';
            updateStatus();
        }
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

// Lifecycle Management Functions
function activateCard() {
    fetch('/activate_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        updateStatus();
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

function deactivateCard() {
    if (!confirm('Are you sure you want to deactivate this card?')) {
        return;
    }
    
    fetch('/deactivate_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        updateStatus();
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

function blockCard() {
    if (!confirm('WARNING: Blocking a card is a security measure that may be difficult to reverse. Continue?')) {
        return;
    }
    
    fetch('/block_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ confirm: true })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        updateStatus();
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

function unblockCard() {
    fetch('/unblock_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        updateStatus();
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

// Add this function for card disposal
function disposeCard() {
    if (!confirm('WARNING: This will permanently erase all data from the card. This cannot be undone!')) {
        return;
    }
    
    if (!confirm('FINAL WARNING: Card data will be permanently and irreversibly destroyed. Continue?')) {
        return;
    }
    
    fetch('/dispose_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            confirm: true, 
            double_confirm: true 
        })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        updateStatus();
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

// Backup and Restoration Functions
function backupCard() {
    fetch('/backup_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        if (data.status === 'success') {
            listBackups(); // Refresh backup list
        }
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

function listBackups() {
    fetch('/list_backups')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('backups-container');
            const list = document.getElementById('backups-list');
            
            if (data.backups && data.backups.length > 0) {
                // Clear existing list
                list.innerHTML = '';
                
                // Add each backup to the table
                data.backups.forEach(backup => {
                    const row = document.createElement('tr');
                    
                    // Format the date nicely
                    let dateDisplay = 'Unknown';
                    try {
                        if (backup.backup_time) {
                            const date = new Date(backup.backup_time);
                            dateDisplay = date.toLocaleString();
                        }
                    } catch (e) {
                        console.error('Date formatting error:', e);
                    }
                    
                    row.innerHTML = `
                        <td>${backup.backup_id.substring(0, 10)}...</td>
                        <td>${dateDisplay}</td>
                        <td>${backup.card_type}</td>
                        <td>
                            <button class="btn btn-sm btn-success" onclick="restoreBackup('${backup.backup_id}')">Restore</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteBackup('${backup.backup_id}')">Delete</button>
                        </td>
                    `;
                    list.appendChild(row);
                });
                
                // Show the container
                container.style.display = 'block';
            } else {
                list.innerHTML = '<tr><td colspan="4" class="text-center">No backups available</td></tr>';
                container.style.display = 'block';
            }
        })
        .catch(error => showResult('Error listing backups: ' + error, 'error'));
}

function restoreBackup(backupId) {
    if (!confirm('Are you sure you want to restore this backup? Current card data will be overwritten.')) {
        return;
    }
    
    fetch('/restore_card', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ backup_id: backupId })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

function deleteBackup(backupId) {
    if (!confirm('Are you sure you want to delete this backup? This cannot be undone.')) {
        return;
    }
    
    fetch('/delete_backup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ backup_id: backupId })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
        if (data.status === 'success') {
            listBackups(); // Refresh backup list
        }
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

// Add these functions for card compatibility and recovery mode
function checkCardCompatibility() {
    fetch('/card_compatibility')
        .then(response => response.json())
        .then(data => {
            let messageClass = data.compatible ? 'text-success' : 'text-warning';
            
            let detailsHtml = '';
            if (data.details) {
                detailsHtml = `
                    <hr>
                    <p><strong>Reader:</strong> ${data.details.reader_type}</p>
                    <p><strong>Card:</strong> ${data.details.card_type}</p>
                    <p><strong>ATR:</strong> ${data.details.atr || 'Unknown'}</p>
                `;
                
                if (data.details.incompatibility_reason) {
                    detailsHtml += `<p class="text-danger"><strong>Note:</strong> ${data.details.incompatibility_reason}</p>`;
                }
            }
            
            showResult(
                `<span class="${messageClass}">${data.message}</span>${detailsHtml}`, 
                data.status, 
                true
            );
        })
        .catch(error => showResult('Error: ' + error, 'error'));
}

// For admin use only - toggle recovery mode
function toggleRecoveryMode(enable) {
    const adminKey = prompt("Enter admin key to " + (enable ? "enable" : "disable") + " recovery mode:");
    if (!adminKey) return;
    
    fetch('/recovery_mode', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            enable: enable,
            admin_key: adminKey
        })
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

// Add this function for test execution
function runTests() {
    showResult("Starting tests, please wait...", "info");
    
    fetch('/run_tests', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Open the test results in a new page/tab
            window.open('/test_results', '_blank');
        } else {
            showResult(`Failed to run tests: ${data.message}`, 'error');
        }
    })
    .catch(error => showResult(`Error: ${error}`, 'error'));
}

function viewTestResults() {
    window.open('/test_results', '_blank');
}

// Update showResult function to add a logs link for error messages
function showResult(message, status, isHtml = false) {
    const outputDiv = document.getElementById('output');
    
    if (isHtml) {
        outputDiv.innerHTML = message;
    } else {
        if (status === 'error') {
            // Add a link to logs for error messages
            const logsLink = '<div class="mt-2"><a href="/logs" class="btn btn-sm btn-outline-secondary" target="_blank">' +
                '<i class="bi bi-journal-code"></i> View Logs for Details</a></div>';
            outputDiv.innerHTML = `<div>${message}</div>${logsLink}`;
        } else {
            outputDiv.textContent = message;
        }
    }
    
    outputDiv.className = `result-message result-${status}`;
    
    // Scroll to the message
    outputDiv.scrollIntoView({ behavior: 'smooth' });
    
    // Add visual indication that operation completed
    outputDiv.classList.add('operation-completed');
    setTimeout(() => {
        outputDiv.classList.remove('operation-completed');
    }, 300);
}

// Add this function to update the card status display
function updateStatus() {
    fetch('/card_info', { method: 'GET' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                try {
                    const info = JSON.parse(data.message);
                    const statusIndicator = document.getElementById('card-status-indicator');
                    if (statusIndicator) {
                        // Update status based on card_status if available
                        if (info.card_status) {
                            statusIndicator.textContent = info.card_status;
                            statusIndicator.className = 'card-status status-' + info.card_status.toLowerCase();
                        } else {
                            statusIndicator.textContent = 'Connected';
                            statusIndicator.className = 'card-status status-active';
                        }
                    }
                } catch (e) {
                    console.error("Error parsing card info:", e);
                }
            }
        })
        .catch(error => console.error("Error updating status:", error));
}

// Initialize tabs when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap 5 tab initialization is automatic
    
    // Check if card is connected on page load
    updateStatus();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+Alt+C = Connect Card
        if (e.ctrlKey && e.altKey && e.key === 'c') {
            connectCard();
        }
        // Ctrl+Alt+R = Register Card
        if (e.ctrlKey && e.altKey && e.key === 'r') {
            registerCard();
        }
        // Ctrl+Alt+B = Backup Card
        if (e.ctrlKey && e.altKey && e.key === 'b') {
            backupCard();
        }
    });
});

function addCard(name) {
    const cardItem = document.createElement('div');
    cardItem.className = 'list-group-item list-group-item-action';
    cardItem.innerHTML = `
        <span>${name}</span>
        <button class="btn btn-danger btn-sm delete-card-btn">Delete</button>
    `;
    cardList.appendChild(cardItem);

    const deleteBtn = cardItem.querySelector('.delete-card-btn');
    deleteBtn.addEventListener('click', function() {
        cardList.removeChild(cardItem);
        // Logic to delete card from the backend
        fetch(`/api/cards/${name}`, { method: 'DELETE' })
            .catch(error => console.error('Error deleting card:', error));
    });
}