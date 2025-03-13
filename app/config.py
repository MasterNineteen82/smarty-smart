"""
Smart Card Manager Configuration
Centralizes application settings with environment-specific configurations.
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Initialize logger
logger = logging.getLogger(__name__)

# --- Base Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR / 'logs'
BACKUP_DIR = Path(os.environ.get('SMARTY_BACKUP_DIR', LOG_DIR / 'backups'))
REG_FILE = Path(os.environ.get('SMARTY_REG_FILE', DATA_DIR / 'registered_cards.json'))

# Create directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
REG_FILE.parent.mkdir(parents=True, exist_ok=True)

# --- Environment Configuration ---
ENV = os.environ.get('SMARTY_ENV', 'development').lower()
DEBUG = ENV != 'production'

# --- Server Configuration ---
SERVER_HOST = 'localhost'
SERVER_PORT = 5000

# --- Security Settings ---
APP_NAME = "Smart Card Manager"
SECRET_KEY = os.environ.get('SMARTY_SECRET_KEY', 'dev-key-change-in-production')
ADMIN_KEY = os.environ.get('SMARTY_ADMIN_KEY', 'admin123')
PIN_ENCRYPTION_KEY = os.environ.get('SMARTY_PIN_KEY', 'encryption-key-for-pins')

# --- Card Operation Settings ---
MAX_PIN_ATTEMPTS = int(os.environ.get('SMARTY_MAX_PIN_ATTEMPTS', '3'))
CONNECTION_TIMEOUT = float(os.environ.get('SMARTY_CONN_TIMEOUT', '10'))
MAX_CONNECT_RETRIES = int(os.environ.get('SMARTY_MAX_RETRIES', '3'))
RETRY_DELAY = float(os.environ.get('SMARTY_RETRY_DELAY', '0.5'))

# --- Reader Settings ---
DEFAULT_READER = None
READER_REFRESH_INTERVAL = int(os.environ.get('SMARTY_READER_REFRESH', '5'))

# --- UI Configuration ---
AUTO_CONNECT = True
COMMAND_TIMEOUT = 5.0
TRANSACTION_TIMEOUT = 30.0
SESSION_TIMEOUT = 30
SECURE_MEMORY = False
CONSOLE_LOGGING = True
RECOVERY_MODE = False
DEBUG_APDU = False

# --- Logging Configuration ---
LOG_DIR = Path(__file__).resolve().parent.parent / 'app' / 'logs'
LOG_FILE = LOG_DIR / 'smarty.log'
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s'
BROWSER_LOG_FILE = LOG_DIR / 'browsererrors.log'

# --- Database Configuration ---
DATABASE_URL = os.environ.get('SMARTY_DATABASE_URL', 'sqlite:///smarty.db')

# --- Feature Flags ---
ENABLE_NFC_SUPPORT = os.environ.get('SMARTY_ENABLE_NFC', 'True').lower() == 'true'

# --- Reader-Specific Configurations ---
READER_CONFIG = {
    'CHERRY_ST': {
        'timeout': float(os.environ.get('SMARTY_CHERRY_TIMEOUT', '10.0')),
        'supports_felica': True,
        'supports_nfc_types': [1, 2, 3, 4]
    },
    'ACR122U': {
        'timeout': float(os.environ.get('SMARTY_ACR122U_TIMEOUT', '3.0')),
        'supports_felica': False,
        'supports_nfc_types': [1, 2, 4]
    }
}

# --- Environment-Specific Overrides ---
if ENV == 'development':
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
elif ENV == 'testing':
    DEBUG = True
    LOG_LEVEL = logging.DEBUG
    REG_FILE = Path(':memory:')  # In-memory for testing
    BACKUP_DIR = LOG_DIR / 'test_backups'
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
elif ENV == 'production':
    DEBUG = False
    LOG_LEVEL = logging.INFO

# --- Load Production Configuration ---
PROD_CONFIG_PATH = os.environ.get('SMARTY_PROD_CONFIG')
if PROD_CONFIG_PATH:
    try:
        with open(PROD_CONFIG_PATH) as f:
            prod_config = json.load(f)
            for key, value in prod_config.items():
                if key.isupper() and key in globals():
                    globals()[key] = value
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load production config from {PROD_CONFIG_PATH}: {e}")

# --- Configuration Loading Functions ---
def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from a JSON file, overriding defaults."""
    config = {k: v for k, v in globals().items() if k.isupper() and not k.startswith('_')}

    if config_path:
        try:
            with open(config_path, 'r') as f:
                custom_config = json.load(f)
                for key, value in custom_config.items():
                    if key.isupper() and key in config:  # Use config instead of globals()
                        config[key] = value
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading config from {config_path}: {e}")

    return config


def get_reader_config(reader_name: str) -> Dict[str, Any]:
    """Get configuration for a specific reader."""
    reader_name = reader_name.upper()

    if 'CHERRY' in reader_name or 'ST' in reader_name:
        return READER_CONFIG['CHERRY_ST']
    elif 'ACR122' in reader_name or 'ACS' in reader_name:
        return READER_CONFIG['ACR122U']
    else:
        logger.warning(f"No specific config found for reader: {reader_name}. Using default.")
        return {
            'timeout': CONNECTION_TIMEOUT,
            'supports_felica': False,
            'supports_nfc_types': [1, 2]
        }


def load_defaults():
    """Reset configuration to default values."""
    global DEBUG, SERVER_HOST, SERVER_PORT, LOG_LEVEL, DEFAULT_READER
    global AUTO_CONNECT, COMMAND_TIMEOUT, TRANSACTION_TIMEOUT
    global MAX_PIN_ATTEMPTS, SESSION_TIMEOUT, SECURE_MEMORY
    global LOG_FORMAT, CONSOLE_LOGGING, RECOVERY_MODE, DEBUG_APDU

    DEBUG = True
    SERVER_HOST = 'localhost'
    SERVER_PORT = 5000
    LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

    DEFAULT_READER = None
    AUTO_CONNECT = True
    COMMAND_TIMEOUT = 5.0
    TRANSACTION_TIMEOUT = 30.0

    MAX_PIN_ATTEMPTS = 3
    SESSION_TIMEOUT = 30
    SECURE_MEMORY = False

    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s'
    CONSOLE_LOGGING = True

    RECOVERY_MODE = False
    DEBUG_APDU = False

    logger.info("Configuration reset to defaults")
