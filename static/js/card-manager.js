function pollCardStatus() {
    const POLL_INTERVAL = 2000;

    async function checkStatus() {
        try {
            const response = await fetch('/cards/status', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (!data) {
                throw new Error('No data received from /cards/status');
            }

            updateCardStatusDisplay(data);

        } catch (error) {
            console.error('Error checking card status:', error);
            handleCardStatusError(error);
        } finally {
            setTimeout(checkStatus, POLL_INTERVAL);
        }
    }

    checkStatus();
}

function updateCardStatusDisplay(data) {
    const statusElement = document.getElementById('cardStatus');
    if (statusElement) {
        statusElement.textContent = `Card Status: ${data.status || 'Unknown'}`;
    } else {
        console.warn('Card status element not found.');
    }
}

function handleCardStatusError(error) {
    const errorElement = document.getElementById('cardStatusError');
    if (errorElement) {
        errorElement.textContent = `Error: ${error.message || 'Unknown error'}`;
    } else {
        console.error('Error display element not found.');
    }
}