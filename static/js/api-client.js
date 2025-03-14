/**
 * Standardized API client for smarty-smart application
 */
class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || '/api';
        this.headers = {
            'Content-Type': 'application/json',
        };
    }

    /**
     * Send API request with standardized error handling
     * 
     * @param {string} endpoint - API endpoint path
     * @param {Object} options - Request options
     * @returns {Promise<Object>} - Response data
     */
    async request(endpoint, options = {}) {
        // Add leading slash if missing
        if (!endpoint.startsWith('/')) endpoint = '/' + endpoint;
        
        const url = this.baseUrl + endpoint;
        
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    ...this.headers,
                    ...options.headers
                },
                credentials: 'include'
            });
            
            // Parse JSON response
            const data = await response.json();
            
            // Check if response indicates an error
            if (!response.ok || data.status === 'error') {
                const errorMessage = data.message || `HTTP error! status: ${response.status}`;
                const error = new Error(errorMessage);
                
                // Add API response details to the error
                error.status = response.status;
                error.statusText = response.statusText;
                error.apiResponse = data;
                
                // Add suggestion if available
                if (data.suggestion) {
                    error.suggestion = data.suggestion;
                }
                
                throw error;
            }
            
            return data;
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            // Re-throw for component-specific handling
            throw error;
        }
    }

    /**
     * Send GET request
     * 
     * @param {string} endpoint - API endpoint path
     * @param {Object} options - Additional request options
     * @returns {Promise<Object>} - Response data
     */
    async get(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'GET',
            ...options
        });
    }

    /**
     * Send POST request
     * 
     * @param {string} endpoint - API endpoint path
     * @param {Object} data - Request payload
     * @param {Object} options - Additional request options
     * @returns {Promise<Object>} - Response data
     */
    async post(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
            ...options
        });
    }
    
    /**
     * Display standardized error message from API error
     * 
     * @param {Error} error - Error object from API request
     * @param {Function} displayFunc - Function to display error message
     */
    static displayError(error, displayFunc) {
        let message = error.message || 'An unknown error occurred';
        let suggestion = error.suggestion || '';
        
        if (error.apiResponse) {
            message = error.apiResponse.message || message;
            suggestion = error.apiResponse.suggestion || suggestion;
        }
        
        const fullMessage = suggestion ? `${message} (${suggestion})` : message;
        
        if (typeof displayFunc === 'function') {
            displayFunc(fullMessage, 'error');
        } else {
            console.error(fullMessage);
        }
    }
}

// Create global instance
const api = new ApiClient();