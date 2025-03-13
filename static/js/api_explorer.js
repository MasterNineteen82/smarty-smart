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
    const searchInput = document.getElementById('searchInput');
    const apiEndpointsContainer = document.getElementById('apiEndpointsContainer');
    const loadingIndicator = document.querySelector('.spinner-border');

    // Load endpoints on page load
    loadEndpoints();

    // Event listener for search input
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        filterEndpoints(searchTerm);
    });

    // Function to load endpoints from the server
    function loadEndpoints() {
        loadingIndicator.style.display = 'block';
        apiEndpointsContainer.innerHTML = ''; // Clear existing content

        fetch('/api/docs.json') // Adjust the endpoint to fetch API documentation
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                loadingIndicator.style.display = 'none';
                const categorizedRoutes = categorizeEndpoints(data.paths);
                renderEndpoints(categorizedRoutes);
            })
            .catch(error => {
                loadingIndicator.style.display = 'none';
                console.error('Failed to load API endpoints:', error);
                apiEndpointsContainer.innerHTML = `<div class="alert alert-danger">Failed to load API endpoints. Check the console for details.</div>`;
            });
    }

    // Function to categorize endpoints
    function categorizeEndpoints(paths) {
        const categorizedRoutes = {};
        for (const path in paths) {
            const methods = paths[path];
            for (const method in methods) {
                const endpoint = methods[method];
                const tag = endpoint.tags && endpoint.tags[0] ? endpoint.tags[0] : 'Uncategorized';
                if (!categorizedRoutes[tag]) {
                    categorizedRoutes[tag] = [];
                }
                categorizedRoutes[tag].push({ path, method, endpoint });
            }
        }
        return categorizedRoutes;
    }

    // Function to filter endpoints based on search input
    function filterEndpoints(filterText) {
        const endpointContainers = document.querySelectorAll('.endpoint-container');
        endpointContainers.forEach(container => {
            const endpointPath = container.querySelector('.endpoint-path').textContent.toLowerCase();
            const endpointSummary = container.querySelector('.endpoint-summary').textContent.toLowerCase();
            if (endpointPath.includes(filterText) || endpointSummary.includes(filterText)) {
                container.style.display = '';
            } else {
                container.style.display = 'none';
            }
        });
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

    // Render endpoints
    function renderEndpoints(categorizedRoutes) {
        for (const category in categorizedRoutes) {
            const categoryDiv = document.createElement('div');
            categoryDiv.classList.add('api-category');
            categoryDiv.innerHTML = `<h2>${category}</h2>`;
            apiEndpointsContainer.appendChild(categoryDiv);

            categorizedRoutes[category].forEach(route => {
                const endpointDiv = document.createElement('div');
                endpointDiv.classList.add('endpoint-container');
                endpointDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <span class="method-badge method-${route.method.toLowerCase()}">${route.method.toUpperCase()}</span>
                            <span class="endpoint-path">${route.path}</span>
                        </div>
                        <button class="btn btn-sm btn-outline-primary toggle-details-btn" data-endpoint-path="${route.path}" data-endpoint-method="${route.method}">
                            Details
                        </button>
                    </div>
                    <div class="endpoint-summary">${route.endpoint.summary || 'No summary'}</div>
                    <div class="endpoint-details" style="display: none;">
                        <!-- Details will be loaded here -->
                    </div>
                `;
                apiEndpointsContainer.appendChild(endpointDiv);
            });
        }

        // Attach event listeners to toggle buttons after rendering
        const toggleButtons = document.querySelectorAll('.toggle-details-btn');
        toggleButtons.forEach(button => {
            button.addEventListener('click', function() {
                toggleEndpointDetails(this);
            });
        });
    }

    // Render parameters
    function renderParameters(parameters) {
        if (!parameters || parameters.length === 0) {
            return '<p>No parameters.</p>';
        }

        let tableHtml = `
            <table class="table table-bordered table-sm">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>In</th>
                        <th>Description</th>
                        <th>Required</th>
                        <th>Schema</th>
                    </tr>
                </thead>
                <tbody>
        `;

        parameters.forEach(param => {
            tableHtml += `
                <tr>
                    <td>${param.name}</td>
                    <td>${param.in}</td>
                    <td>${param.description || 'No description'}</td>
                    <td>${param.required ? 'Yes' : 'No'}</td>
                    <td>${param.schema ? JSON.stringify(param.schema) : 'No schema'}</td>
                </tr>
            `;
        });

        tableHtml += `
                </tbody>
            </table>
        `;
        return tableHtml;
    }

    // Toggle endpoint details
    function toggleEndpointDetails(button) {
        const endpointDiv = button.closest('.endpoint-container');
        const detailsDiv = endpointDiv.querySelector('.endpoint-details');
        const endpointPath = button.dataset.endpointPath;
        const endpointMethod = button.dataset.endpointMethod;

        if (detailsDiv.style.display === 'none') {
            // Fetch and render details
            fetch(`/api/docs.json`) // Adjust the endpoint to fetch API documentation
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    const endpoint = data.paths[endpointPath][endpointMethod];
                    const parametersHtml = renderParameters(endpoint.parameters);

                    detailsDiv.innerHTML = `
                        <h3>Parameters</h3>
                        ${parametersHtml}
                        <h3>Response</h3>
                        <button class="btn btn-sm btn-primary send-request-btn" data-endpoint-path="${endpointPath}" data-endpoint-method="${endpointMethod}">Send Request</button>
                        <div class="response-container"></div>
                    `;

                    // Attach event listener to send request button
                    const sendRequestButton = detailsDiv.querySelector('.send-request-btn');
                    sendRequestButton.addEventListener('click', function() {
                        sendRequest(endpoint, endpointPath);
                    });

                    detailsDiv.style.display = '';
                    button.textContent = 'Hide Details';
                })
                .catch(error => {
                    console.error('Failed to load endpoint details:', error);
                    detailsDiv.innerHTML = `<div class="alert alert-danger">Failed to load endpoint details. Check the console for details.</div>`;
                });
        } else {
            detailsDiv.style.display = 'none';
            button.textContent = 'Details';
        }
    }

    // Send request
    function sendRequest(endpoint, path) {
        const responseContainer = document.querySelector('.response-container');
        responseContainer.innerHTML = '<p>Sending request...</p>';

        fetch(path, { method: endpoint.method.toUpperCase() })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                responseContainer.innerHTML = `
                    <h3>Response</h3>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
            })
            .catch(error => {
                console.error('Failed to send request:', error);
                responseContainer.innerHTML = `<div class="alert alert-danger">Failed to send request. Check the console for details.</div>`;
            });
    }
});