class CardStatusManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000; // 3 seconds
        this.statusListeners = [];
        this.connectionListeners = [];
    }

    connect() {
        // Close any existing connection
        this.disconnect();
        
        // Determine WebSocket URL based on current page location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/card-status`;
        
        console.log(`Connecting to WebSocket at ${wsUrl}`);
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connection established');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this._notifyConnectionListeners(true);
        };
        
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this._notifyStatusListeners(data);
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
            }
        };
        
        this.socket.onclose = (event) => {
            console.log(`WebSocket closed: ${event.code} ${event.reason}`);
            this.isConnected = false;
            this._notifyConnectionListeners(false);
            
            // Attempt to reconnect
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`Reconnecting (attempt ${this.reconnectAttempts})...`);
                setTimeout(() => this.connect(), this.reconnectInterval);
            } else {
                console.error('Maximum reconnect attempts reached');
            }
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
            this.isConnected = false;
        }
    }
    
    addStatusListener(callback) {
        if (typeof callback === 'function') {
            this.statusListeners.push(callback);
        }
        return this; // Allow chaining
    }
    
    removeStatusListener(callback) {
        this.statusListeners = this.statusListeners.filter(listener => listener !== callback);
        return this; // Allow chaining
    }
    
    addConnectionListener(callback) {
        if (typeof callback === 'function') {
            this.connectionListeners.push(callback);
        }
        return this; // Allow chaining
    }
    
    removeConnectionListener(callback) {
        this.connectionListeners = this.connectionListeners.filter(listener => listener !== callback);
        return this; // Allow chaining
    }
    
    _notifyStatusListeners(status) {
        this.statusListeners.forEach(listener => {
            try {
                listener(status);
            } catch (error) {
                console.error('Error in status listener:', error);
            }
        });
    }
    
    _notifyConnectionListeners(connected) {
        this.connectionListeners.forEach(listener => {
            try {
                listener(connected);
            } catch (error) {
                console.error('Error in connection listener:', error);
            }
        });
    }
}

// Create a singleton instance
const cardStatusManager = new CardStatusManager();

// Connect automatically when the script loads
document.addEventListener('DOMContentLoaded', () => {
    cardStatusManager.connect();
});

// Reconnect when the page becomes visible again
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && !cardStatusManager.isConnected) {
        cardStatusManager.connect();
    }
});