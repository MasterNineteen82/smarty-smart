/**
 * Card Operations JavaScript
 * Handles card-related UI operations and API calls
 */

// Global state
let currentReader = null;
let cardConnected = false;

/**
 * Connect to a card in the selected reader
 */
function connectCard() {
    const readerSelect = document.getElementById('readerSelect');
    const selectedReader = readerSelect ? readerSelect.value : null;
    
    // Show loading spinner
    showSpinner('Connecting to card...');
    
    fetch('/connect', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reader: selectedReader })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            cardConnected = true;
            currentReader = selectedReader;
            updateStatusMessage(data.message, 'success');
            enableCardOperations();
            updateCardInfo();
        } else {
            updateStatusMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error connecting to card:', error);
        updateStatusMessage('Connection failed: ' + error.message, 'error');
    })
    .finally(() => {
        hideSpinner();
    });
}

/**
 * Enable card operation buttons when a card is connected
 */
function enableCardOperations() {
    const cardButtons = document.querySelectorAll('.card-operation-btn');
    cardButtons.forEach(button => {
        button.disabled = false;
    });
    
    // Update connection button text
    const connectButton = document.getElementById('connectButton');
    if (connectButton) {
        connectButton.innerText = 'Reconnect Card';
        connectButton.classList.remove('btn-primary');
        connectButton.classList.add('btn-success');
    }
}

/**
 * Verify PIN for the connected card
 */
function verifyPIN() {
    const pinInput = document.getElementById('pinInput');
    const pin = pinInput ? pinInput.value : '';
    
    if (!pin || pin.length !== 3 || !/^\d{3}$/.test(pin)) {
        updateStatusMessage('PIN must be a 3-digit number', 'error');
        return;
    }
    
    showSpinner('Verifying PIN...');
    
    fetch('/verify_pin', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ pin: pin })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateStatusMessage('PIN verified successfully', 'success');
            // Enable additional operations that require PIN verification
            enableSecureOperations();
        } else {
            updateStatusMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error verifying PIN:', error);
        updateStatusMessage('PIN verification failed: ' + error.message, 'error');
    })
    .finally(() => {
        hideSpinner();
        // Clear PIN input for security
        if (pinInput) {
            pinInput.value = '';
        }
    });
}

/**
 * Read memory from the card
 */
function readMemory() {
    showSpinner('Reading card memory...');
    
    fetch('/read_memory', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Display memory content in a pre-formatted area
            const memoryDisplay = document.getElementById('memoryDisplay');
            if (memoryDisplay) {
                memoryDisplay.innerText = data.message;
                memoryDisplay.classList.remove('d-none');
            }
            updateStatusMessage('Memory read successfully', 'success');
        } else {
            updateStatusMessage(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error reading memory:', error);
        updateStatusMessage('Memory read failed: ' + error.message, 'error');
    })
    .finally(() => {
        hideSpinner();
    });
}

/**
 * Update card information display
 */
function updateCardInfo() {
    fetch('/card_info', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        const cardInfoElement = document.getElementById('cardInfo');
        if (cardInfoElement) {
            if (data.status === 'success') {
                try {
                    const info = JSON.parse(data.message);
                    let htmlContent = `
                        <div class="card mb-3">
                            <div class="card-header bg-info text-white">
                                <h5 class="mb-0">Card Information</h5>
                            </div>
                            <div class="card-body">
                                <p><strong>ATR:</strong> ${info.atr}</p>
                                <p><strong>Card Type:</strong> ${info.card_type}</p>
                                <p><strong>Reader:</strong> ${info.reader_type}</p>
                                <p><strong>Protocol:</strong> ${info.protocol}</p>
                                <p><strong>Status:</strong> <span class="${info.card_status === 'ACTIVE' ? 'text-success' : 'text-warning'}">${info.card_status}</span></p>
                                <p><strong>Registered:</strong> <span class="${info.registered ? 'text-success' : 'text-danger'}">${info.registered ? 'Yes' : 'No'}</span></p>
                            </div>
                        </div>
                    `;
                    cardInfoElement.innerHTML = htmlContent;
                    cardInfoElement.classList.remove('d-none');
                } catch (e) {
                    console.error('Error parsing card info:', e);
                    cardInfoElement.innerHTML = `<div class="alert alert-warning">Error parsing card information</div>`;
                }
            } else if (data.status === 'warning') {
                cardInfoElement.innerHTML = `<div class="alert alert-warning">${data.message}</div>`;
            } else {
                cardInfoElement.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
            }
        }
    })
    .catch(error => {
        console.error('Error getting card info:', error);
        const cardInfoElement = document.getElementById('cardInfo');
        if (cardInfoElement) {
            cardInfoElement.innerHTML = `<div class="alert alert-danger">Failed to get card information: ${error.message}</div>`;
        }
    });
}

/**
 * Enable operations that require PIN verification
 */
function enableSecureOperations() {
    const secureButtons = document.querySelectorAll('.secure-operation-btn');
    secureButtons.forEach(button => {
        button.disabled = false;
    });
}

/**
 * Display status message with appropriate styling
 * @param {string} message - The message to display
 * @param {string} type - Message type (success, error, warning, info)
 */
function updateStatusMessage(message, type = 'info') {
    const statusElement = document.getElementById('statusMessage');
    if (statusElement) {
        // Clear existing classes
        statusElement.className = 'alert';
        
        // Add appropriate class based on type
        switch (type) {
            case 'success':
                statusElement.classList.add('alert-success');
                break;
            case 'error':
                statusElement.classList.add('alert-danger');
                break;
            case 'warning':
                statusElement.classList.add('alert-warning');
                break;
            default:
                statusElement.classList.add('alert-info');
        }
        
        statusElement.innerText = message;
        statusElement.classList.remove('d-none');
    }
}

/**
 * Show loading spinner with message
 * @param {string} message - Loading message to display
 */
function showSpinner(message = 'Loading...') {
    const spinner = document.getElementById('loadingSpinner');
    const spinnerMessage = document.getElementById('spinnerMessage');
    
    if (spinner) {
        if (spinnerMessage) {
            spinnerMessage.innerText = message;
        }
        spinner.classList.remove('d-none');
    }
}

/**
 * Hide loading spinner
 */
function hideSpinner() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.classList.add('d-none');
    }
}

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI components
    const readerSelect = document.getElementById('readerSelect');
    const connectButton = document.getElementById('connectButton');
    
    if (readerSelect && connectButton) {
        connectButton.addEventListener('click', connectCard);
    }
    
    // Set up other button handlers
    const verifyPinButton = document.getElementById('verifyPinButton');
    if (verifyPinButton) {
        verifyPinButton.addEventListener('click', verifyPIN);
    }
    
    const readMemoryButton = document.getElementById('readMemoryButton');
    if (readMemoryButton) {
        readMemoryButton.addEventListener('click', readMemory);
    }
});