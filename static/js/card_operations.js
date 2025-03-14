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
async function connectCard() {
    showSpinner();
    
    try {
        const data = await api.post('/cards/connect');
        updateStatusMessage(data.message, data.status);
        
        if (data.data && data.data.atr) {
            document.getElementById('card-atr').textContent = data.data.atr;
            document.getElementById('card-details').classList.remove('d-none');
        }
    } catch (error) {
        ApiClient.displayError(error, updateStatusMessage);
    } finally {
        hideSpinner();
    }
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
async function verifyPIN() {
    const pinInput = document.getElementById('pinInput');
    const pin = pinInput ? pinInput.value : '';
    
    if (!pin || pin.length !== 3 || !/^\d{3}$/.test(pin)) {
        updateStatusMessage('PIN must be a 3-digit number', 'error');
        return;
    }
    
    showSpinner('Verifying PIN...');
    
    try {
        const response = await fetch('/verify_pin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ pin: pin })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            updateStatusMessage('PIN verified successfully', 'success');
            // Enable additional operations that require PIN verification
            enableSecureOperations();
        } else {
            updateStatusMessage(data.message, 'error');
        }
    } catch (error) {
        console.error('Error verifying PIN:', error);
        updateStatusMessage('PIN verification failed: ' + error.message, 'error');
    } finally {
        hideSpinner();
        // Clear PIN input for security
        if (pinInput) {
            pinInput.value = '';
        }
    }
}

/**
 * Read memory from the card
 */
async function readMemory() {
    showSpinner('Reading card memory...');
    
    try {
        const response = await fetch('/read_memory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

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
    } catch (error) {
        console.error('Error reading memory:', error);
        updateStatusMessage('Memory read failed: ' + error.message, 'error');
    } finally {
        hideSpinner();
    }
}

/**
 * Update card information display
 */
async function updateCardInfo() {
    try {
        const response = await fetch('/card_info', {
            method: 'GET'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
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
    } catch (error) {
        console.error('Error getting card info:', error);
        const cardInfoElement = document.getElementById('cardInfo');
        if (cardInfoElement) {
            cardInfoElement.innerHTML = `<div class="alert alert-danger">Failed to get card information: ${error.message}</div>`;
        }
    }
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

// Function to connect to a card reader
async function connectCard(reader) {
    try {
        const response = await fetch('/api/cards/connect', { // Replace with your actual API endpoint
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reader })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to connect to card:', error);
        throw error;
    }
}

// Function to read memory from the card
async function readMemory() {
    try {
        const response = await fetch('/api/cards/read_memory'); // Replace with your actual API endpoint
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to read memory:', error);
        throw error;
    }
}

// Function to register a card
async function registerCard(atr, userId, cardType) {
    try {
        const response = await fetch('/api/cards/register', { // Replace with your actual API endpoint
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ atr, user_id: userId, card_type: cardType })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to register card:', error);
        throw error;
    }
}

// Function to perform a card operation
async function performCardOperation(operation, data = {}) {
    try {
        const response = await fetch(`/api/cards/${operation}`, { // Replace with your actual API endpoint
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        return result;
    } catch (error) {
        console.error(`Failed to perform card operation ${operation}:`, error);
        throw error;
    }
}

/**
 * Check card registration status
 */
async function checkRegistration() {
    showSpinner();
    
    try {
        const data = await api.get('/cards/check_registration');
        
        let message = data.data?.registered ?
            'This card is registered in the system.' :
            'This card is not registered.';

        if (data.data?.card_info?.card_type) {
            message += ` Card type: ${data.data.card_info.card_type}`;
        }

        updateStatusMessage(message, data.status);
    } catch (error) {
        ApiClient.displayError(error, updateStatusMessage);
    } finally {
        hideSpinner();
    }
}