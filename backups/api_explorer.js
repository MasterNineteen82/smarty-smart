// Store all endpoints for filtering
let allEndpoints = {};

document.addEventListener('DOMContentLoaded', function() {
    // Fetch API status on page load
    fetchApiStatus();
    
    // Add event listeners to method filter buttons
    document.getElementById('btn-get').addEventListener('change', filterByMethod);
    document.getElementById('btn-post').addEventListener('change', filterByMethod);
    document.getElementById('btn-put').addEventListener('change', filterByMethod);
    document.getElementById('btn-delete').addEventListener('change', filterByMethod);
});

function fetchApiStatus() {
    document.getElementById('apiEndpointsContainer').innerHTML = `
        <div class="d-flex justify-content-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                allEndpoints = data.categorized_routes;
                renderEndpoints(allEndpoints);
                updateApiStats(data);
            } else {
                document.getElementById('apiEndpointsContainer').innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i> ${data.message || 'Failed to load API endpoints'}
                    </div>
                `;
            }
        })
        .catch(error => {
            document.getElementById('apiEndpointsContainer').innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i> Error: ${error.message}
                </div>
            `;
        });
}

function updateApiStats(data) {
    document.getElementById('totalEndpoints').textContent = data.routes_count;
    document.getElementById('totalCategories').textContent = Object.keys(data.categorized_routes).length;
}

function renderEndpoints(categorizedRoutes) {
    // Implementation remains the same
    // ...
}

function renderParameters(parameters) {
    // Implementation remains the same
    // ...
}

function toggleEndpointDetails(button) {
    // Implementation remains the same
    // ...
}

function filterEndpoints(search) {
    // Implementation remains the same
    // ...
}

function filterByMethod() {
    // Implementation remains the same
    // ...
}

function sendRequest(endpoint, path) {
    // Implementation remains the same
    // ...
}