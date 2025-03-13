"""
Smart Card Manager Configuration
Centralizes all application settings and provides environment-specific configurations
"""

import os
import logging  # Move this import to the top with other imports
import json
from typing import Dict, Any, Optional
from pathlib import Path # noqa

# Setup logger for use throughout the module
logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Environment settings
ENV = os.environ.get('SMARTY_ENV', 'development').lower()
DEBUG = ENV != 'production'

# Server configuration
SERVER_HOST = 'localhost'
SERVER_PORT = 5000
DEBUG = True

# Security settings
APP_NAME = "Smart Card Manager"
SECRET_KEY = os.environ.get('SMARTY_SECRET_KEY', 'dev-key-change-in-production')
ADMIN_KEY = os.environ.get('SMARTY_ADMIN_KEY', 'admin123')  # Change in production!
PIN_ENCRYPTION_KEY = os.environ.get('SMARTY_PIN_KEY', 'encryption-key-for-pins')

# File paths
BACKUP_DIR = os.environ.get('SMARTY_BACKUP_DIR', os.path.join(LOG_DIR, 'backups'))
REG_FILE = os.environ.get('SMARTY_REG_FILE', os.path.join(DATA_DIR, 'registered_cards.json'))

# Card operation settings
MAX_PIN_ATTEMPTS = int(os.environ.get('SMARTY_MAX_PIN_ATTEMPTS', 3))
CONNECTION_TIMEOUT = int(os.environ.get('SMARTY_CONN_TIMEOUT', 10))
MAX_CONNECT_RETRIES = int(os.environ.get('SMARTY_MAX_RETRIES', 3))
RETRY_DELAY = float(os.environ.get('SMARTY_RETRY_DELAY', 0.5))

# Reader settings
DEFAULT_READER = None  # Will use first available reader if None
READER_REFRESH_INTERVAL = int(os.environ.get('SMARTY_READER_REFRESH', 5))  # seconds

# Additional settings needed for configuration UI
AUTO_CONNECT = True
COMMAND_TIMEOUT = 5.0
TRANSACTION_TIMEOUT = 30.0
SESSION_TIMEOUT = 30
SECURE_MEMORY = False
CONSOLE_LOGGING = True
RECOVERY_MODE = False
DEBUG_APDU = False

# Create directories if they don't exist
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(os.path.dirname(REG_FILE), exist_ok=True)

# Logging configuration
LOG_FILE = os.path.join(LOG_DIR, 'smarty.log')
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s'

# Reader-specific configurations
READER_CONFIG = {
    'CHERRY_ST': {
        'timeout': float(os.environ.get('SMARTY_CHERRY_TIMEOUT', 10.0)),
        'supports_felica': True,
        'supports_nfc_types': [1, 2, 3, 4]
    },
    'ACR122U': {
        'timeout': float(os.environ.get('SMARTY_ACR122U_TIMEOUT', 3.0)),
        'supports_felica': False,
        'supports_nfc_types': [1, 2, 4]
    }
}

# Environment-specific settings
if ENV == 'development':
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
elif ENV == 'testing':
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
    # Use in-memory storage for testing
    REG_FILE = ':memory:'
    BACKUP_DIR = os.path.join(LOG_DIR, 'test_backups')
elif ENV == 'production':
    DEBUG = False
    LOG_LEVEL = logging.WARNING
    # Load additional production settings if available
    PROD_CONFIG_PATH = os.environ.get('SMARTY_PROD_CONFIG')
    if PROD_CONFIG_PATH and os.path.exists(PROD_CONFIG_PATH):
        with open(PROD_CONFIG_PATH) as f:
            prod_config = json.load(f)
            # Override default settings with production values
            for key, value in prod_config.items():
                if key in globals():
                    globals()[key] = value

# Dynamic configuration loading function
def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from a JSON file and override default settings"""
    if not config_path:
        return {k: v for k, v in globals().items() 
                if k.isupper() and not k.startswith('_')}
    
    try:
        with open(config_path) as f:
            custom_config = json.load(f)
            
        # Update global variables
        for key, value in custom_config.items():
            if key.isupper() and key in globals():
                globals()[key] = value
                
        return load_config()  # Return updated config
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return load_config()

# Function to get reader-specific configuration
def get_reader_config(reader_name: str) -> Dict[str, Any]:
    """Get configuration for a specific reader"""
    reader_name = reader_name.upper()
    
    if 'CHERRY' in reader_name or 'ST' in reader_name:
        return READER_CONFIG['CHERRY_ST']
    elif 'ACR122' in reader_name or 'ACS' in reader_name:
        return READER_CONFIG['ACR122U']
    else:
        # Return default settings
        return {
            'timeout': CONNECTION_TIMEOUT,
            'supports_felica': False,
            'supports_nfc_types': [1, 2]
        }

# Add a load_defaults method
def load_defaults():
    """Reset configuration to default values"""
    global DEBUG, SERVER_HOST, SERVER_PORT, LOG_LEVEL, DEFAULT_READER
    global AUTO_CONNECT, COMMAND_TIMEOUT, TRANSACTION_TIMEOUT
    global MAX_PIN_ATTEMPTS, SESSION_TIMEOUT, SECURE_MEMORY
    global LOG_FORMAT, CONSOLE_LOGGING, RECOVERY_MODE, DEBUG_APDU
    
    # Default settings
    DEBUG = True
    SERVER_HOST = 'localhost'
    SERVER_PORT = 5000
    LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
    
    # Reader settings
    DEFAULT_READER = None
    AUTO_CONNECT = True
    COMMAND_TIMEOUT = 5.0
    TRANSACTION_TIMEOUT = 30.0
    
    # Security settings
    MAX_PIN_ATTEMPTS = 3
    SESSION_TIMEOUT = 30
    SECURE_MEMORY = False
    
    # Logging settings
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s'
    CONSOLE_LOGGING = True
    
    # Advanced settings
    RECOVERY_MODE = False
    DEBUG_APDU = False
    
    logger.info("Configuration reset to defaults")