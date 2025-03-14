// Central configuration for API endpoints

// Get the API base URL (handles both same-origin and cross-origin cases)
async function getApiBaseUrl() {
    // Try to get config from server
    try {
        const response = await fetch('/frontend-config');
        if (response.ok) {
            const config = await response.json();
            return config.api_url;
        }
    } catch (e) {
        console.warn('Could not fetch API config, using default');
    }
    
    // Default to current origin or specific port if needed
    const currentPort = window.location.port;
    const defaultApiPort = 5000;
    
    // If we're already on the API port
    if (currentPort === String(defaultApiPort)) {
        return window.location.origin;
    }
    
    // Otherwise assume API is on the default port
    return `http://${window.location.hostname}:${defaultApiPort}`;
}

// API client for making requests
class ApiClient {
    constructor() {
        this.baseUrl = null;
        this.initialized = false;
    }
    
    async init() {
        if (this.initialized) return;
        this.baseUrl = await getApiBaseUrl();
        this.initialized = true;
        console.log(`API client initialized with base URL: ${this.baseUrl}`);
    }
    
    async request(endpoint, options = {}) {
        await this.init();
        
        // Add leading slash if missing
        if (!endpoint.startsWith('/')) endpoint = '/' + endpoint;
        
        const url = this.baseUrl + endpoint;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include'  // Include cookies for auth if needed
        };
        
        const fetchOptions = { 
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };
        
        try {
            const response = await fetch(url, fetchOptions);
            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }
}

// Export a singleton instance
const apiClient = new ApiClient();