/**
 * Configuration Manager JavaScript
 * Handles UI interactions for the configuration manager interface
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize configuration form handling
    const configForm = document.getElementById('configForm');
    if (configForm) {
        configForm.addEventListener('submit', handleConfigSubmit);
    } else {
        console.warn('Configuration form not found.');
    }

    // Initialize validation
    setupValidation();
    
    // Setup config section toggles
    setupSectionToggles();

    // Setup reset to defaults functionality
    const resetButton = document.getElementById('resetConfigButton');
    if (resetButton) {
        resetButton.addEventListener('click', resetToDefaults);
    } else {
        console.warn('Reset button not found.');
    }
});

/**
 * Handle configuration form submission
 * @param {Event} event - Form submit event
 */
function handleConfigSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const configData = {};
    
    // Convert form data to nested object structure
    for (const [key, value] of formData.entries()) {
        const parts = key.split('.');
        
        if (parts.length === 2) {
            const [section, setting] = parts;
            
            if (!configData[section]) {
                configData[section] = {};
            }
            
            // Convert boolean values and numbers
            if (value === 'true' || value === 'false') {
                configData[section][setting] = (value === 'true');
            } else if (!isNaN(value) && value.trim() !== '') {
                const numValue = Number(value);
                if (Number.isFinite(numValue)) {
                    configData[section][setting] = numValue;
                } else {
                    console.warn(`Invalid numeric value for ${key}: ${value}`);
                    showConfigStatus(false, `Invalid numeric value for ${key}: ${value}`);
                    return; // Stop submission
                }
            } else {
                configData[section][setting] = value;
            }
        }
    }
    
    // Send configuration to server
    fetch('/api/save_config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(configData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {  // Attempt to read error message from the server
                throw new Error(err.message || 'Failed to save configuration');
            });
        }
        return response.json();
    })
    .then(data => {
        showConfigStatus(true, data.message || 'Configuration saved successfully'); // Use message from server if available
    })
    .catch(error => {
        console.error('Error saving configuration:', error);
        showConfigStatus(false, 'Failed to save configuration: ' + error.message);
    });
}

/**
 * Display configuration status message
 * @param {boolean} success - Whether operation was successful
 * @param {string} message - Status message to display
 */
function showConfigStatus(success, message) {
    const statusEl = document.getElementById('configStatus');
    
    if (statusEl) {
        statusEl.className = success ? 'alert alert-success' : 'alert alert-danger';
        statusEl.innerHTML = `<i class="bi bi-${success ? 'check' : 'x'}-circle me-2"></i> ${message}`;
        statusEl.classList.remove('d-none');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            statusEl.classList.add('d-none');
        }, 5000);
    } else {
        console.warn('Status element not found.');
    }
}

/**
 * Setup form validation
 */
function setupValidation() {
    // Add validation for path fields
    const pathInputs = document.querySelectorAll('input[data-type="path"]');
    
    pathInputs.forEach(input => {
        input.addEventListener('blur', function() {
            validatePath(this);
        });
    });
    
    // Add validation for numeric fields
    const numericInputs = document.querySelectorAll('input[type="number"]');
    
    numericInputs.forEach(input => {
        input.addEventListener('input', function() {
            validateNumeric(this);
        });
        input.addEventListener('blur', function() {
            validateNumeric(this); // Validate on blur as well
        });
    });
}

/**
 * Validate path input
 * @param {HTMLInputElement} input - Path input element
 */
function validatePath(input) {
    const value = input.value.trim();
    
    if (value.length === 0) {
         setInputValidity(input, false, 'Path cannot be empty');
         return;
    }

    const invalidChars = /[<>:"|?*]/g;
    
    if (invalidChars.test(value)) {
        setInputValidity(input, false, 'Path contains invalid characters');
    } else {
        setInputValidity(input, true);
    }
}

/**
 * Validate numeric input
 * @param {HTMLInputElement} input - Numeric input element
 */
function validateNumeric(input) {
    const min = parseFloat(input.getAttribute('min') || '-Infinity');
    const max = parseFloat(input.getAttribute('max') || 'Infinity');
    const value = parseFloat(input.value);
    
    if (isNaN(value)) {
        setInputValidity(input, false, 'Please enter a valid number');
    } else if (value < min) {
        setInputValidity(input, false, `Value must be at least ${min}`);
    } else if (value > max) {
        setInputValidity(input, false, `Value must be at most ${max}`);
    } else {
        setInputValidity(input, true);
    }
}

/**
 * Set input validity state
 * @param {HTMLInputElement} input - Input element
 * @param {boolean} isValid - Whether input is valid
 * @param {string} message - Error message if invalid
 */
function setInputValidity(input, isValid, message = '') {
    const feedbackEl = input.nextElementSibling;
    
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
            feedbackEl.textContent = '';
        }
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        if (feedbackEl && feedbackEl.classList.contains('invalid-feedback')) {
            feedbackEl.textContent = message;
        } else {
            // Create feedback element if it doesn't exist
            const newFeedback = document.createElement('div');
            newFeedback.className = 'invalid-feedback';
            newFeedback.textContent = message;
            input.parentNode.insertBefore(newFeedback, input.nextSibling);
        }
    }
}

/**
 * Setup collapsible section toggles
 */
function setupSectionToggles() {
    const toggleButtons = document.querySelectorAll('[data-bs-toggle="collapse"]');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const icon = this.querySelector('i.bi');
            if (icon) {
                if (icon.classList.contains('bi-chevron-down')) {
                    icon.classList.replace('bi-chevron-down', 'bi-chevron-up');
                } else {
                    icon.classList.replace('bi-chevron-up', 'bi-chevron-down');
                }
            }
        });
    });
}

/**
 * Reset configuration to defaults
 */
function resetToDefaults() {
    if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
        fetch('/api/reset_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                 return response.json().then(err => {  // Attempt to read error message from the server
                    throw new Error(err.message || 'Failed to reset configuration');
                });
            }
            return response.json();
        })
        .then(data => {
            showConfigStatus(true, data.message || 'Configuration reset to defaults');
            // Reload the page to show updated values
            setTimeout(() => window.location.reload(), 1000);
        })
        .catch(error => {
            console.error('Error resetting configuration:', error);
            showConfigStatus(false, 'Failed to reset configuration: ' + error.message);
        });
    }
}

// Function to fetch and display the current configuration
async function fetchConfig() {
    try {
        const response = await fetch('/api/config'); // Replace with your actual API endpoint
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const config = await response.json();
        displayConfigJson(config);
    } catch (error) {
        console.error('Failed to fetch configuration:', error);
        displayError('Failed to load configuration. Check the console for details.');
    }
}

// Function to display the configuration as a JSON string
function displayConfigJson(config) {
    const configJsonDisplay = document.getElementById('config-json-display');
    configJsonDisplay.textContent = JSON.stringify(config, null, 4);
}

// Function to copy the configuration JSON to the clipboard
function copyConfigJson() {
    const configJsonDisplay = document.getElementById('config-json-display');
    navigator.clipboard.writeText(configJsonDisplay.textContent)
        .then(() => showToast('Copied!', 'Configuration copied to clipboard.', 'success'))
        .catch(err => {
            console.error('Failed to copy config:', err);
            showToast('Copy Failed', 'Could not copy configuration to clipboard.', 'error');
        });
}

// Function to import a configuration from a JSON string
async function importConfig() {
    const configImport = document.getElementById('config-import');
    try {
        const config = JSON.parse(configImport.value);
        const response = await fetch('/api/config', { // Replace with your actual API endpoint
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        if (!response.ok) {
            const errorDetail = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, detail: ${errorDetail.detail}`);
        }

        showToast('Import Successful', 'Configuration imported successfully.', 'success');
        fetchConfig(); // Refresh the displayed configuration
    } catch (error) {
        console.error('Failed to import configuration:', error);
        showToast('Import Failed', `Could not import configuration: ${error}`, 'error');
    }
}

// Function to save the configuration to the server
async function saveConfig() {
    try {
        const form = document.getElementById('configForm');
        const formData = {};

        // Group data by section
        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => {
            const nameParts = input.name.split('.');
            if (nameParts.length !== 2) {
                console.warn(`Invalid input name format: ${input.name}. Skipping.`);
                return;
            }

            const section = nameParts[0];
            const field = nameParts[1];

            if (!formData[section]) {
                formData[section] = {};
            }

            let value = input.type === 'checkbox' ? input.checked : input.value;

            if (input.type === 'number' && value !== '') {
                const numValue = Number(value);
                if (isNaN(numValue)) {
                    showToast('Validation Error', `Invalid number format for ${input.name}.`, 'error');
                    return;
                }
                value = numValue;
            }

            formData[section][field] = value;
        });

        const response = await fetch('/api/config', { // Replace with your actual API endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const errorDetail = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, detail: ${errorDetail.detail}`);
        }

        showToast('Save Successful', 'Configuration saved successfully.', 'success');
        fetchConfig(); // Refresh the displayed configuration
    } catch (error) {
        console.error('Failed to save configuration:', error);
        showToast('Save Failed', `Could not save configuration: ${error}`, 'error');
    }
}

// Function to reset the form to its default values
function resetForm() {
    fetchConfig(); // Reload the configuration to reset the form
    showToast('Reset', 'Form reset to default values.', 'info');
}

// Function to confirm the reset action
async function confirmReset() {
    try {
        const response = await fetch('/api/config/reset', { // Replace with your actual API endpoint
            method: 'POST'
        });

        if (!response.ok) {
            const errorDetail = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, detail: ${errorDetail.detail}`);
        }

        showToast('Reset Successful', 'Configuration reset to default values.', 'success');
        fetchConfig(); // Refresh the displayed configuration
    } catch (error) {
        console.error('Failed to reset configuration:', error);
        showToast('Reset Failed', `Could not reset configuration: ${error}`, 'error');
    }
}

// Function to display toast messages
function showToast(title, message, type) {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.classList.add('toast', `bg-${type}`);
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
    });
}

// Call fetchConfig when the page loads
document.addEventListener('DOMContentLoaded', fetchConfig);