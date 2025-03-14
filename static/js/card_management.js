/**
 * Card registration handler
 */
async function registerCard() {
    const userIdInput = document.getElementById('user-id');
    const cardNameInput = document.getElementById('card-name');
    
    if (!userIdInput || !cardNameInput) {
        showError("UI elements not found. Please refresh the page.");
        return;
    }
    
    const userId = userIdInput.value.trim();
    const cardName = cardNameInput.value.trim();
    
    if (!userId) {
        showError("Please enter a user ID");
        userIdInput.focus();
        return;
    }
    
    showSpinner();
    
    try {
        const data = await api.post('/cards/register', {
            user_id: userId,
            card_name: cardName
        });
        
        showSuccess(data.message || "Card registered successfully");
        
        // Clear form fields
        userIdInput.value = '';
        cardNameInput.value = '';
        
        // Update card status display
        await updateCardStatus();
    } catch (error) {
        ApiClient.displayError(error, showError);
    } finally {
        hideSpinner();
    }
}

/**
 * Display error message
 */
function showError(message) {
    const alertElement = document.getElementById('status-alert');
    if (!alertElement) return;
    
    alertElement.textContent = message;
    alertElement.className = 'alert alert-danger';
    alertElement.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertElement.style.display = 'none';
    }, 5000);
}

/**
 * Display success message
 */
function showSuccess(message) {
    const alertElement = document.getElementById('status-alert');
    if (!alertElement) return;
    
    alertElement.textContent = message;
    alertElement.className = 'alert alert-success';
    alertElement.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertElement.style.display = 'none';
    }, 5000);
}