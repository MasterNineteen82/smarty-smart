/**
 * Configuration Manager JavaScript
 * Handles UI interactions for the configuration manager interface
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize configuration form handling
    const configForm = document.getElementById('configForm');
    if (configForm) {
        configForm.addEventListener('submit', handleConfigSubmit);
    }

    // Initialize validation
    setupValidation();
    
    // Setup config section toggles
    setupSectionToggles();
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
                configData[section][setting] = Number(value);
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
            throw new Error('Failed to save configuration');
        }
        return response.json();
    })
    .then(data => {
        showConfigStatus(true, 'Configuration saved successfully');
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
    });
}

/**
 * Validate path input
 * @param {HTMLInputElement} input - Path input element
 */
function validatePath(input) {
    const value = input.value.trim();
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
    const min = parseInt(input.getAttribute('min') || '-Infinity');
    const max = parseInt(input.getAttribute('max') || 'Infinity');
    const value = parseInt(input.value);
    
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
                throw new Error('Failed to reset configuration');
            }
            return response.json();
        })
        .then(data => {
            showConfigStatus(true, 'Configuration reset to defaults');
            // Reload the page to show updated values
            setTimeout(() => window.location.reload(), 1000);
        })
        .catch(error => {
            console.error('Error resetting configuration:', error);
            showConfigStatus(false, 'Failed to reset configuration: ' + error.message);
        });
    }
}