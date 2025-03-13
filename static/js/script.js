// Function to fetch and display data from an API endpoint
async function fetchAndDisplay(endpoint, method, data = {}) {
    const headers = { 'Content-Type': 'application/json' };
    const body = method === 'POST' ? JSON.stringify(data) : undefined;

    try {
        const response = await fetch(endpoint, { method, headers, body });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! Status: ${response.status}, Detail: ${errorData.detail || 'Unknown error'}`);
        }
        const responseData = await response.json();
        if (responseData && responseData.message) {
            showResult(responseData.message, responseData.status || 'success');
        } else {
            showResult('No message received from server.', 'warning');
        }
        updateStatus();
        return responseData;
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        showResult(`Error: ${error.message}`, 'error');
        updateStatus();
        throw error;
    }
}

// Function to display results in the UI
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

// Function to update the card status display
async function updateStatus() {
    try {
        const data = await fetchAndDisplay('/cards/status', 'GET');
        const statusIndicator = document.getElementById('card-status-indicator');
        if (statusIndicator) {
            statusIndicator.textContent = data.message || 'Unknown';
            statusIndicator.className = `card-status status-${data.status || 'unknown'}`;
        }
    } catch (error) {
        console.error('Failed to update status:', error);
    }
}

// Function to start the server
async function startServer() {
    await fetchAndDisplay('/server/start', 'POST');
}

// Function to stop the server
async function stopServer() {
    await fetchAndDisplay('/server/stop', 'POST');
}

// Function to connect to a card reader
async function connectCard() {
    const reader = document.getElementById('reader-select').value;
    if (!reader) {
        showResult('Please select a reader.', 'error');
        return;
    }
    try {
        const data = await fetchAndDisplay('/cards/connect', 'POST', { reader });
        document.getElementById('status').textContent = data.message;
        document.getElementById('atr').textContent = `ATR: ${data.atr || ''}`;
    } catch (error) {
        console.error('Failed to connect to card:', error);
    }
}

// Function to read memory from the card
async function readMemory() {
    try {
        const data = await fetchAndDisplay('/cards/read_memory', 'POST');
        document.getElementById('memoryDisplay').textContent = data.memory || 'No memory data received.';
    } catch (error) {
        console.error('Failed to read memory:', error);
    }
}

// Function to write memory to the card
async function writeMemory() {
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

    try {
        const response = await fetch('/cards/write_memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ offset, data })
        });
        const responseData = await response.json();
        showResult(responseData.message, responseData.status);
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to change the card PIN
async function changePin() {
    const oldPin = document.getElementById('old-pin').value.trim();
    const newPin = document.getElementById('change-new-pin').value.trim();

    if (!oldPin || !newPin) {
        showResult('Please enter both current and new PINs', 'error');
        return;
    }

    if (!confirm('Are you sure you want to change the card PIN?')) {
        return;
    }

    try {
        const response = await fetch('/cards/change_pin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_pin: oldPin, new_pin: newPin })
        });
        const responseData = await response.json();
        showResult(responseData.message, responseData.status);
        if (responseData.status === 'success') {
            document.getElementById('old-pin').value = '';
            document.getElementById('change-new-pin').value = '';
        }
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to get card information
async function getCardInfo() {
    try {
        const data = await fetchAndDisplay('/cards/info', 'GET');
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
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to get card status
async function getCardStatus() {
    await fetchAndDisplay('/cards/status', 'GET');
}

// Function to confirm card formatting
async function confirmFormat() {
    if (confirm('Are you sure you want to format the card?')) {
        await fetchAndDisplay('/cards/format', 'POST', { confirm: true });
    }
}

// Function to confirm card blocking
async function confirmBlockCard() {
    if (confirm('Are you sure you want to block the card?')) {
        await fetchAndDisplay('/cards/block', 'POST', { confirm: true });
    }
}

// Real-time status update (every 1 second)
setInterval(updateStatus, 1000);

// Card Registration Functions
async function registerCard() {
    const name = document.getElementById('card-name').value;
    const userId = document.getElementById('user-id').value;

    if (!name || !userId) {
        showResult('Please enter both name and user ID', 'error');
        return;
    }

    try {
        const data = await fetchAndDisplay('/cards/register', 'POST', { name, user_id: userId });
        if (data.status === 'success') {
            updateStatus();
        }
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to check card registration
async function checkRegistration() {
    try {
        const data = await fetchAndDisplay('/cards/check_registration', 'GET');
        let message = data.registered ?
            'This card is registered in the system.' :
            'This card is not registered.';

        if (data.card_info && data.card_info.card_type) {
            message += ` Card type: ${data.card_info.card_type}`;
        }

        showResult(message, data.status);
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to unregister a card
async function unregisterCard() {
    if (!confirm('Are you sure you want to unregister this card?')) {
        return;
    }

    try {
        const data = await fetchAndDisplay('/cards/unregister', 'POST');
        if (data.status === 'success') {
            document.getElementById('card-name').value = '';
            document.getElementById('user-id').value = '';
            updateStatus();
        }
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Lifecycle Management Functions
async function activateCard() {
    try {
        const data = await fetchAndDisplay('/cards/activate', 'POST');
        updateStatus();
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to deactivate a card
async function deactivateCard() {
    if (!confirm('Are you sure you want to deactivate this card?')) {
        return;
    }

    try {
        const data = await fetchAndDisplay('/cards/deactivate', 'POST');
        updateStatus();
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to block a card
async function blockCard() {
    if (!confirm('WARNING: Blocking a card is a security measure that may be difficult to reverse. Continue?')) {
        return;
    }

    try {
        const data = await fetchAndDisplay('/cards/block', 'POST', { confirm: true });
        updateStatus();
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to unblock a card
async function unblockCard() {
    try {
        const data = await fetchAndDisplay('/cards/unblock', 'POST');
        updateStatus();
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to dispose of a card
async function disposeCard() {
    if (!confirm('WARNING: This will permanently erase all data from the card. This cannot be undone!')) {
        return;
    }

    if (!confirm('FINAL WARNING: Card data will be permanently and irreversibly destroyed. Continue?')) {
        return;
    }

    try {
        const data = await fetchAndDisplay('/cards/dispose', 'POST', { confirm: true, double_confirm: true });
        updateStatus();
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to backup all cards
async function backupCard() {
    try {
        const data = await fetchAndDisplay('/cards/backup_all', 'POST');
        if (data.status === 'success') {
            let message = data.results.map(r => `${r.reader}: ${r.message}`).join('\n');
            showResult(message, 'success');
            listBackups();
        } else {
            showResult(data.message, data.status);
        }
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to list backups
async function listBackups() {
    try {
        const data = await fetchAndDisplay('/backups/list', 'GET');
        const container = document.getElementById('backups-container');
        const list = document.getElementById('backups-list');

        if (data.backups && data.backups.length > 0) {
            list.innerHTML = '';
            data.backups.forEach(backup => {
                const row = document.createElement('tr');

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
            container.style.display = 'block';
        } else {
            list.innerHTML = '<tr><td colspan="4" class="text-center">No backups available</td></tr>';
            container.style.display = 'block';
        }
    } catch (error) {
        showResult('Error listing backups: ' + error, 'error');
    }
}

// Function to restore a backup
async function restoreBackup(backupId) {
    if (!confirm('Are you sure you want to restore this backup? Current card data will be overwritten.')) {
        return;
    }

    try {
        const data = await fetchAndDisplay('/backups/restore', 'POST', { backup_id: backupId });
        showResult(data.message, data.status);
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to delete a backup
async function deleteBackup(backupId) {
    if (!confirm('Are you sure you want to delete this backup? This cannot be undone.')) {
        return;
    }

    try {
        const data = await fetchAndDisplay('/backups/delete', 'POST', { backup_id: backupId });
        if (data.status === 'success') {
            listBackups();
        }
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to check card compatibility
async function checkCardCompatibility() {
    try {
        const data = await fetchAndDisplay('/cards/check_compatibility', 'GET');
        showResult(data.message, data.status);
    } catch (error) {
        console.error('Error checking card compatibility:', error);
        showResult('Error: ' + error.message, 'error');
    }
}

// Function to toggle recovery mode
async function toggleRecoveryMode(enable) {
    const adminKey = prompt("Enter admin key to " + (enable ? "enable" : "disable") + " recovery mode:");
    if (!adminKey) return;

    try {
        const data = await fetchAndDisplay('/admin/recovery_mode', 'POST', {
            enable: enable,
            admin_key: adminKey
        });
        showResult(data.message, data.status);
    } catch (error) {
        showResult('Error: ' + error, 'error');
    }
}

// Function to run tests
async function runTests() {
    showResult("Starting tests, please wait...", "info");

    try {
        const data = await fetchAndDisplay('/tests/run', 'POST');
        if (data.status === 'success') {
            window.open('/tests/results', '_blank');
        } else {
            showResult(`Failed to run tests: ${data.message}`, 'error');
        }
    } catch (error) {
        showResult(`Error: ${error}`, 'error');
    }
}

// Function to view test results
function viewTestResults() {
    window.open('/tests/results', '_blank');
}

// Function to add a card (UI only)
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

// Initialize tabs and load data on page load
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap 5 tab initialization is automatic

    // Check if card is connected on page load
    updateStatus();

    // Load available readers on page load
    loadReaders();

    // Load existing cards on page load
    listCards();

    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.altKey && e.key === 'c') {
            connectCard();
        }
        if (e.ctrlKey && e.altKey && e.key === 'r') {
            registerCard();
        }
        if (e.ctrlKey && e.altKey && e.key === 'b') {
            backupCard();
        }
    });
});

// Function to load available readers
async function loadReaders() {
    try {
        const data = await fetchAndDisplay('/readers', 'GET');
        const readerSelect = document.getElementById('reader-select');
        readerSelect.innerHTML = '';
        data.readers.forEach(reader => {
            const option = document.createElement('option');
            option.value = reader;
            option.textContent = reader;
            readerSelect.appendChild(option);
        });
    } catch (error) {
        showResult('Error loading readers: ' + error, 'error');
    }
}

// Function to list existing cards
async function listCards() {
    try {
        const data = await fetchAndDisplay('/cards', 'GET');
        const cardList = document.getElementById('card-list');
        cardList.innerHTML = '';
        if (data.cards && data.cards.length > 0) {
            data.cards.forEach(card => {
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item';
                listItem.innerHTML = `
                    <span>${card.atr}</span>
                    <button class="btn btn-danger delete-card-btn" data-card-id="${card.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
                cardList.appendChild(listItem);

                const deleteCardBtn = listItem.querySelector('.delete-card-btn');
                deleteCardBtn.addEventListener('click', function() {
                    const cardId = this.dataset.cardId;
                    deleteCard(cardId);
                });
            });
        } else {
            cardList.innerHTML = '<li class="list-group-item">No cards available</li>';
        }
    } catch (error) {
        showResult('Error listing cards: ' + error, 'error');
    }
}

// Function to delete a card
async function deleteCard(cardId) {
    try {
        const data = await fetchAndDisplay(`/cards/${cardId}`, 'DELETE');
        showResult(data.message, data.status);
        listCards();
    } catch (error) {
        showResult('Error deleting card: ' + error, 'error');
    }
}

// Make functions available globally
window.connectCard = connectCard;
window.checkCardCompatibility = checkCardCompatibility;
window.activateCard = activateCard;
window.deactivateCard = deactivateCard;
window.blockCard = blockCard;
window.unblockCard = unblockCard;
window.showResult = showResult;
window.updateStatus = updateStatus;
window.listBackups = listBackups;
window.restoreBackup = restoreBackup;
window.deleteBackup = deleteBackup;