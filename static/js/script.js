function fetchAndDisplay(endpoint, method, data = {}) {
    const headers = { 'Content-Type': 'application/json' };
    const body = method === 'POST' ? JSON.stringify(data) : undefined;

    return fetch(endpoint, { method, headers, body })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data && data.message) {
                showResult(data.message, data.status || 'success');
            } else {
                showResult('No message received from server.', 'warning');
            }
            updateStatus();
            return data;
        })
        .catch(error => {
            console.error(`Error fetching ${endpoint}:`, error);
            showResult(`Error: ${error.message}`, 'error');
            updateStatus();
            throw error;
        });
}

function showResult(message, status, isHtml = false) {
    const outputDiv = document.getElementById('output');

    if (!outputDiv) {
        console.error('Output element not found.');
        return;
    }

    if (isHtml) {
        outputDiv.innerHTML = message;
    } else {
        outputDiv.textContent = message;
    }

    outputDiv.className = `result-message result-${status}`;
    outputDiv.scrollIntoView({ behavior: 'smooth' });
    outputDiv.classList.add('operation-completed');

    setTimeout(() => {
        outputDiv.classList.remove('operation-completed');
    }, 300);
}

function updateStatus() {
    fetchAndDisplay('/card_status', 'GET')
        .then(data => {
            const statusIndicator = document.getElementById('card-status-indicator');
            if (statusIndicator) {
                statusIndicator.textContent = data.message || 'Unknown';
                statusIndicator.className = `card-status status-${data.status || 'unknown'}`;
            }
        })
        .catch(error => {
            console.error('Failed to update status:', error);
        });
}

function startServer() { fetchAndDisplay('/start_server', 'POST'); }
function stopServer() { fetchAndDisplay('/stop_server', 'POST'); }

function connectCard() {
    const reader = document.getElementById('reader-select').value;
    if (!reader) {
        showResult('Please select a reader.', 'error');
        return;
    }
    fetchAndDisplay('/connect', 'POST', { reader: reader });
}

function readMemory() { fetchAndDisplay('/read_memory', 'POST'); }

function
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
    console.log("DEBUG: Verify API request URL is correct.");
    
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
console.log("DEBUG: Ensure this element ID exists in the HTML.");
        document.getElementById('atr').textContent = `ATR: ${data.message.split('ATR: ')[1]?.split('\n')[0] || ''}`;
console.log("DEBUG: Ensure this element ID exists in the HTML.");
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
    console.log("DEBUG: Verify API request URL is correct.");
    
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

// static/js/script.js
function backupCard() {
    fetch('/backup_all', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            let message = data.results.map(r => `${r.reader}: ${r.message}`).join('\n');
            showResult(message, 'success');
            listBackups();
        } else {
            showResult(data.message, data.status);
        }
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

// Ensure other functions use correct Blueprint routes
function connectCard() {
    const reader = document.getElementById('reader-select').value;
    fetch('/connect', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ reader: reader })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('status').textContent = data.message;
        document.getElementById('atr').textContent = `ATR: ${data.atr || ''}`;
        document.getElementById('output').textContent = data.message;
    })
    .catch(error => showResult('Error: ' + error, 'error'));
}

// Existing showResult and updateStatus functions remain compatible

function listBackups() {
    console.log("DEBUG: Verify API request URL is correct.");
    
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
    console.log("DEBUG: Verify API request URL is correct.");
    
    fetch('/check_compatibility')
        .then(response => response.json())
        .then(data => {
            showResult(data.message, data.status);
        })
        .catch(error => {
            console.error('Error checking card compatibility:', error);
            showResult('Error: ' + error.message, 'error');
        });
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
console.log("DEBUG: Ensure this element ID exists in the HTML.");
    
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
console.log("DEBUG: Ensure event listeners are attached.");
        cardList.removeChild(cardItem);
        // Logic to delete card from the backend
        fetch(`/api/cards/${name}`, { method: 'DELETE' })
            .catch(error => console.error('Error deleting card:', error));
    });
}

// Card compatibility check function
function checkCardCompatibility() {
    console.log("DEBUG: Verify API request URL is correct.");
    fetch('/check_compatibility', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        showResult(data.message, data.status);
    })
    .catch(error => {
        console.error('Error checking card compatibility:', error);
        showResult('Error: ' + error.message, 'error');
    });
}

// Card lifecycle management functions
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

// Helper function to display results
function showResult(message, status, isHtml = false) {
    const resultElement = document.getElementById('resultOutput');
    if (resultElement) {
        if (isHtml) {
            resultElement.innerHTML = message;
        } else {
            resultElement.textContent = message;
        }
        
        // Update result styling based on status
        resultElement.className = 'alert';
        switch (status) {
            case 'success':
                resultElement.classList.add('alert-success');
                break;
            case 'error':
                resultElement.classList.add('alert-danger');
                break;
            case 'warning':
                resultElement.classList.add('alert-warning');
                break;
            default:
                resultElement.classList.add('alert-info');
        }
        
        resultElement.classList.remove('d-none');
        
        // If it's an error, add link to logs
        if (status === 'error') {
            resultElement.innerHTML += '<div class="mt-2"><a href="/logs" class="btn btn-sm btn-outline-secondary">View Logs</a></div>';
        }
    }
}

// Update card status display
function updateStatus() {
    fetch('/card_status', { 
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache'
        }
    })
    .then(response => response.json())
    .then(data => {
        const statusIndicator = document.getElementById('card-status-indicator');
        if (statusIndicator && data.status) {
            statusIndicator.textContent = data.status;
            statusIndicator.className = 'badge ' + 
                (data.status === 'ACTIVE' ? 'bg-success' : 
                data.status === 'BLOCKED' ? 'bg-danger' :
                data.status === 'INACTIVE' ? 'bg-warning' : 'bg-secondary');
        }
    })
    .catch(error => console.error('Error updating status:', error));
}

// Make connectCard function available globally
window.connectCard = connectCard;
window.checkCardCompatibility = checkCardCompatibility;
window.activateCard = activateCard;
window.deactivateCard = deactivateCard;
window.blockCard = blockCard;
window.unblockCard = unblockCard;
window.showResult = showResult;
window.updateStatus = updateStatus;

document.addEventListener('DOMContentLoaded', function() {
    const cardIdInput = document.getElementById('cardId');
    const getCardInfoButton = document.getElementById('getCardInfo');
    const authenticateCardButton = document.getElementById('authenticateCard');
    const outputDiv = document.getElementById('output');
    const pinInput = document.getElementById('pin');

    // Function to display messages
    function displayMessage(message, isError = false) {
        outputDiv.textContent = message;
        outputDiv.className = isError ? 'error' : 'success';
    }

    // Event listener for Get Card Info button
    getCardInfoButton.addEventListener('click', function() {
        const cardId = cardIdInput.value;
        if (!cardId) {
            displayMessage('Please enter a Card ID.', true);
            return;
        }

        fetch(`/cards/${cardId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(card => {
                displayMessage(`Card ID: ${card.card_id}, Status: ${card.status}, Balance: ${card.balance}, Type: ${card.card_type}`);
            })
            .catch(error => {
                console.error('Fetch error:', error);
                displayMessage(`Error fetching card info: ${error.message}`, true);
            });
    });

    // Event listener for Authenticate Card button
    authenticateCardButton.addEventListener('click', function() {
        const cardId = cardIdInput.value;
        const pin = pinInput.value;

        if (!cardId || !pin) {
            displayMessage('Please enter both Card ID and PIN.', true);
            return;
        }

        fetch(`/cards/${cardId}/authenticate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ pin: pin })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                displayMessage(data.message);
            })
            .catch(error => {
                console.error('Fetch error:', error);
                displayMessage(`Authentication failed: ${error.message}`, true);
            });
    });
});