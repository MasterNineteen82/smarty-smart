// Enhanced API Explorer Script

// Utility function to display errors
function displayError(message, containerId = 'apiEndpointsContainer') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i> ${message}
            </div>
        `;
    } else {
        console.error(`Container element with ID '${containerId}' not found.`);
    }
}

// Utility function to show loading spinner
function showLoading(containerId = 'apiEndpointsContainer') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="d-flex justify-content-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    } else {
        console.error(`Container element with ID '${containerId}' not found.`);
    }
}

// Fetch API endpoints
async function fetchApiEndpoints() {
    showLoading();
    try {
        const response = await fetch('/static/api_endpoints.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching API endpoints:', error);
        displayError(`Failed to load API endpoints: ${error.message}`);
        return null;
    }
}

// Display API endpoints
function displayApiEndpoints(endpoints, containerId = 'apiEndpointsContainer') {
    const apiEndpointsContainer = document.getElementById(containerId);
    if (!apiEndpointsContainer) {
        console.error(`Container element with ID '${containerId}' not found.`);
        return;
    }

    apiEndpointsContainer.innerHTML = ''; // Clear existing content

    if (!endpoints || endpoints.length === 0) {
        apiEndpointsContainer.innerHTML = '<p>No endpoints found.</p>';
        return;
    }

    endpoints.forEach(endpoint => {
        const endpointElement = document.createElement('div');
        endpointElement.className = 'api-endpoint';
        endpointElement.innerHTML = `
            <h3>${endpoint.name || 'No Name'}</h3>
            <p>Path: ${endpoint.path || 'No Path'}</p>
            <p>Method: ${endpoint.method || 'No Method'}</p>
            <p>Description: ${endpoint.description || 'No Description'}</p>
        `;
        apiEndpointsContainer.appendChild(endpointElement);
    });
}

// Filter API endpoints
function filterEndpoints(searchText, endpoints) {
    if (!endpoints) {
        console.warn('Endpoints array is undefined or null. Returning empty array.');
        return [];
    }

    const searchTextLower = searchText.toLowerCase();
    return endpoints.filter(endpoint => {
        const name = endpoint.name || '';
        const path = endpoint.path || '';
        const description = endpoint.description || '';

        return name.toLowerCase().includes(searchTextLower) ||
               path.toLowerCase().includes(searchTextLower) ||
               description.toLowerCase().includes(searchTextLower);
    });
}

// Filter by method
function filterByMethod(endpoints) {
    const checkedMethods = Array.from(document.querySelectorAll('input[name="method"]:checked'))
        .map(input => input.value.toLowerCase());

    if (checkedMethods.length === 0) {
        return endpoints; // Show all if no methods are selected
    }

    return endpoints.filter(endpoint => {
        const method = endpoint.method ? endpoint.method.toLowerCase() : '';
        return checkedMethods.includes(method);
    });
}

// Fetch API status
async function fetchApiStatus() {
    showLoading();
    try {
        const response = await fetch('/api/status');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.status === 'success') {
            allEndpoints = data.categorized_routes;
            renderEndpoints(allEndpoints);
            updateApiStats(data);
        } else {
            displayError(data.message || 'Failed to load API endpoints');
        }
    } catch (error) {
        console.error('Error fetching API status:', error);
        displayError(`Failed to load API endpoints: ${error.message}`);
    }
}

// Update API stats
function updateApiStats(data) {
    setTextContent('totalEndpoints', data.routes_count);
    setTextContent('totalCategories', Object.keys(data.categorized_routes).length);
}

// Helper function to set text content, with error handling
function setTextContent(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    } else {
        console.error(`Element with ID '${elementId}' not found.`);
    }
}

// Render endpoints (Implementation remains the same, ensure error handling and edge cases)
function renderEndpoints(categorizedRoutes) {
    // Implementation remains the same
    // ...
}

// Render parameters (Implementation remains the same, ensure error handling and edge cases)
function renderParameters(parameters) {
    // Implementation remains the same
    // ...
}

// Toggle endpoint details (Implementation remains the same, ensure error handling and edge cases)
function toggleEndpointDetails(button) {
    // Implementation remains the same
    // ...
}

// Send request (Implementation remains the same, ensure error handling and edge cases)
function sendRequest(endpoint, path) {
    // Implementation remains the same
    // ...
}

document.addEventListener('DOMContentLoaded', function() {
    let apiEndpoints = [];
    const searchInput = document.getElementById('searchInput');
    const apiEndpointsContainer = document.getElementById('apiEndpointsContainer');
    const refreshApisButton = document.getElementById('refreshApisButton');

    // Load endpoints
    fetchApiEndpoints().then(endpoints => {
        if (endpoints) {
            apiEndpoints = endpoints;
            displayApiEndpoints(apiEndpoints);
        }
    });

    // Search functionality
    searchInput.addEventListener('keyup', function() {
        const filtered = filterEndpoints(this.value, apiEndpoints);
        displayApiEndpoints(filtered);
    });

    // Method filter event listeners
    const methodButtons = document.querySelectorAll('input[name="method"]');
    methodButtons.forEach(button => {
        button.addEventListener('change', function() {
            const filtered = filterByMethod(apiEndpoints);
            displayApiEndpoints(filtered);
        });
    });

    // Refresh APIs button
    refreshApisButton.addEventListener('click', function() {
        fetchApiStatus();
    });
});