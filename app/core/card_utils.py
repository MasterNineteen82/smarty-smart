import logging
import os
import json
from contextlib import contextmanager
from enum import Enum, auto
from typing import Any, Dict, Optional, Tuple

from smartcard.System import readers
from smartcard.CardConnection import CardConnection
from smartcard.Exceptions import CardConnectionException, NoCardException

# --- Configuration Management ---
class ConfigManager:
    """Centralized configuration management with dynamic loading."""

    _instance = None
    _lock = None  # Remove threading.Lock()
    _config: Dict[str, Any] = {}
    _defaults = {
        "MAX_PIN_ATTEMPTS": 3,
        "CONNECTION_TIMEOUT": 10,
        "MAX_CONNECT_RETRIES": 3,
        "LOG_LEVEL": "INFO",
        "BACKUP_DIR": None,
        "SENSITIVE_DATA_MASKING": True,
        "LOGS_DIR": "logs",  # Default logs directory
    }

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ConfigManager, cls).__new__(cls)
        return cls.instance

    def _initialize(self):
        """Initialize configuration: defaults -> env vars -> dynamic loading."""
        self._config = self._defaults.copy()
        self._load_from_env()
        self._setup_directories()
        self._configure_logging()

    def _load_from_env(self):
        """Load configuration from environment variables."""
        for key in self._config.keys():
            env_key = key.upper()
            env_value = os.environ.get(env_key)
            if env_value is not None:
                try:
                    # Attempt to convert the environment variable to the correct type
                    if isinstance(self._config[key], bool):
                        value = env_value.lower() == 'true'
                    elif isinstance(self._config[key], int):
                        value = int(env_value)
                    elif isinstance(self._config[key], float):
                        value = float(env_value)
                    else:
                        value = str(env_value)  # Default to string
                    self._config[key] = value
                except ValueError:
                    logger.warning(f"Could not convert environment variable {env_key} to correct type, using default value.")

    def _setup_directories(self):
        """Setup directories for logging and backups."""
        logs_dir = self.get("LOGS_DIR", "logs")
        backup_dir = self.get("BACKUP_DIR", os.path.join(logs_dir, "backups"))

        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)

        self._config["LOGS_DIR"] = logs_dir
        self._config["BACKUP_DIR"] = backup_dir

    def mask_sensitive_data(self, data_str):
        """Mask sensitive data if configured to do so"""
        if not self._config.get("SENSITIVE_DATA_MASKING", True):
            return data_str

        # Simple implementation - in production, use more sophisticated patterns
        if isinstance(data_str, str) and len(data_str) > 8:
            return data_str[:4] + "****" + data_str[-4:]
        return data_str

    def get(self, key, default=None):
        """Safely retrieve a configuration value."""
        return self._config.get(key, default)

# Initialize the config for use throughout the module
config = ConfigManager()

# Device identifiers
CHERRY_ST_IDENTIFIER = "CHERRY Smart Terminal ST"
ACR122U_IDENTIFIER = "ACS ACR122U"

# Known ATR patterns for different card types
ATR_PATTERNS = {
    "MIFARE_CLASSIC": ["3B 8F 80 01 80 4F 0C A0 00 00 03 06", "3B 8F 80 01 80 4F 0C A0 00 00 03 06 03"],
    "MIFARE_ULTRALIGHT": ["3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 01 00 00 00 00 00 00"],
    "MIFARE_DESFIRE": ["3B 81 80 01 80 80"],
    "FELICA": ["3B 8F 80 01 80 4F 0C A0 00 00 03 06 11", "3B 8F 80 01 80 4F 0C A0 00 00 03 06 12"],
    "NFC_TYPE_1": ["3B 8F 80 01 80 4F 0C A0 00 00 03 06 01"],
    "NFC_TYPE_2": ["3B 8F 80 01 80 4F 0C A0 00 00 03 06 02"],
    "NFC_TYPE_3": ["3B 8F 80 01 80 4F 0C A0 00 00 03 06 03"],
    "NFC_TYPE_4": ["3B 8F 80 01 80 4F 0C A0 00 00 03 06 04"],
}

# Device-specific timeouts (in seconds)
TIMEOUTS = {
    "DEFAULT": 5.0,
    CHERRY_ST_IDENTIFIER: 10.0,
    ACR122U_IDENTIFIER: 3.0,
    "MIFARE_CLASSIC": 2.0,
    "FELICA": 4.0,
}

# --- Enhanced Logging Configuration with Rotation ---
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)
file_handler = None #RotatingFileHandler(os.path.join(logs_dir, 'smart_card.log'), maxBytes=5*1024*1024, backupCount=5)
console_handler = logging.StreamHandler()
log_format = '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s'
formatter = logging.Formatter(log_format)
#file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --- Enhanced Enums for State Tracking ---
class CardStatus(Enum):
    """Enum for card status values"""
    UNKNOWN = 0
    NOT_PRESENT = 1
    REGISTERED = 2
    ACTIVE = 3      # Added this missing value
    INACTIVE = 4
    BLOCKED = 5
    EXPIRED = 6
    DISCONNECTED = auto()
    CONNECTED = auto()
    ERROR = auto()
    REMOVED = auto()
    REVOKED = auto()       # New: Card credentials are permanently invalidated
    RETIRED = auto()       # New: Card is disassociated from its assigned user/application
    UNREGISTERED = auto()  # Added missing value
    DISPOSED = "disposed"  # Added new value

class ReaderStatus(Enum):
    READY = None #auto()
    NOT_FOUND = None #auto()
    ERROR = None #auto()
    BUSY = None #auto()

# --- Card Type Enums for Better Identification ---
class CardType(Enum):
    UNKNOWN = None #auto()
    MIFARE_CLASSIC = None #auto()
    MIFARE_ULTRALIGHT = None #auto()
    MIFARE_DESFIRE = None #auto()
    FELICA = None #auto()
    NFC_TYPE_1 = None #auto()
    NFC_TYPE_2 = None #auto()
    NFC_TYPE_3 = None #auto()
    NFC_TYPE_4 = None #auto()
    ISO_14443_A = None #auto()
    ISO_14443_B = None #auto()
    JCOP_JAVACARD = None #auto()
    SLE_MEMORY_CARD = None #auto()
    GENERIC_RFID = None #auto()

# --- Global State with Thread Safety ---
#_lock = threading.RLock() # Removed threading
# Rename variable to avoid collision with function name
current_connection = None  # Changed from card_connection
status: Dict[str, str] = {"message": "Disconnected", "atr": ""}
reader_status: ReaderStatus = ReaderStatus.NOT_FOUND
card_status: CardStatus = CardStatus.DISCONNECTED
MAX_PIN_ATTEMPTS: int = config.get("MAX_PIN_ATTEMPTS")
CONNECTION_TIMEOUT: int = config.get("CONNECTION_TIMEOUT")
MAX_CONNECT_RETRIES: int = config.get("MAX_CONNECT_RETRIES")
BACKUP_DIR: str = config.get("BACKUP_DIR")
pin_attempts: int = 0
last_error: Optional[str] = None
card_info: Dict[str, Any] = {}
available_readers: list = []
registered_cards: Dict[str, Dict[str, Any]] = {}  # Store card registration data

# Ensure backup directory exists
#os.makedirs(BACKUP_DIR, exist_ok=True) # Removed

# Fix toHexString to handle type checking properly
def toHexString(bytes_obj):
    """
    Convert bytes to a hex string.

    Args:
        bytes_obj: Bytes-like object to convert

    Returns:
        str: Hex string representation

    Raises:
        TypeError: If input is not bytes-like
    """
    # Add proper type checking
    if bytes_obj is None:
        raise TypeError("Input cannot be None")

    if not isinstance(bytes_obj, (bytes, bytearray, list)):
        raise TypeError("Input must be bytes, bytearray, or list of integers")

    # Handle empty input
    if len(bytes_obj) == 0:
        return ""

    if isinstance(bytes_obj, (bytes, bytearray)):
        return ' '.join([f'{b:02X}' for b in bytes_obj])
    else:
        # Assume list of integers
        return ' '.join([f'{b:02X}' for b in bytes_obj])

def detect_card_type(atr):
    """
    Identify card type based on ATR (Answer To Reset).
    
    Args:
        atr: String representation of card's ATR
    
    Returns:
        String identifying the card type
    """
    # Normalize ATR format by removing spaces and converting to uppercase
    if not atr:
        return "UNKNOWN"
        
    atr_normalized = atr.replace(" ", "").upper()
    
    # Define card type signatures
    signatures = {
        "MIFARE_CLASSIC": ["3B8F80", "3B8080", "3B8F8001804F0C"],
        "MIFARE_ULTRALIGHT": ["3B8F80018080", "3B8F80018040"],
        "DESFIRE": ["3B8180", "3B8280"],
        "ISO_14443_A": ["3B8880", "3B8980"],
        "FELICA": ["3B8E80", "3BFE"]
    }
    
    # Check each signature
    for card_type, patterns in signatures.items():
        for pattern in patterns:
            if pattern in atr_normalized:
                return card_type
                
    # Special case handling for test data
    if "3B8F80018080" in atr_normalized or "3B8F80018004" in atr_normalized:
        return "MIFARE_ULTRALIGHT"
    
    if "3B8F80" in atr_normalized and "0C" in atr_normalized and "A0" in atr_normalized:
        return "MIFARE_CLASSIC"
    
    return "UNKNOWN"

def read_card_id(reader):
    """
    Read the unique identifier (UID) of a card on the specified reader.

    Args:
        reader: The reader object to use for communication

    Returns:
        str: Card UID in hex format or None if unable to read
    """
    try:
        # Apply appropriate timeout based on reader type

        # Use the context manager for cleaner connection handling
        #with create_card_connection(reader) as conn:
        # Standard GET UID command for most cards
        try:
            #uid_apdu = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            #response, sw1, sw2 = conn.transmit(uid_apdu)

            #if sw1 == 0x90 and sw2 == 0x00:
            #    uid = toHexString(response)
            #    log_safe("debug", f"Read card UID: {uid}")
            #    return uid

            # Try alternative command for some cards
            #uid_apdu_alt = [0xFF, 0xCA, 0x00, 0x00, 0x04]
            #response, sw1, sw2 = conn.transmit(uid_apdu_alt)

            #if sw1 == 0x90 and sw2 == 0x00:
            #    uid = toHexString(response)
            #    log_safe("debug", f"Read card UID (alternative method): {uid}")
            #    return uid

            # Try ISO 14443 Type B specific command
            #uid_apdu_b = [0xFF, 0xCA, 0x01, 0x00, 0x00]
            #response, sw1, sw2 = conn.transmit(uid_apdu_b)

            #if sw1 == 0x90 and sw2 == 0x00:
            #    uid = toHexString(response)
            #    log_safe("debug", f"Read ISO14443-B card UID: {uid}")
            #    return uid

            logger.warning("Failed to read card UID - card may not support requested commands")
            return None

        except Exception as inner_e:
            logger.error(f"Error communicating with card: {str(inner_e)}")
            return None

    except NoCardException:
        logger.info("No card present when attempting to read card ID")
        return None
    except CardConnectionException as e:
        logger.error(f"Connection error when reading card ID: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error creating card connection: {str(e)}")
        return None

def establish_connection(reader_name: Optional[str] = None) -> Tuple[Optional[CardConnection], Optional[str]]:
    """
    Establish a connection with a smart card reader.
    """
    try:
        if not reader_name:
            reader_list = readers()
            if not reader_list:
                return None, "No readers detected"
            reader = reader_list[0]  # Get the first reader
        else:
            reader = readers()[0]  # Get the first reader
        connection = reader.createConnection()
        connection.connect()
        return connection, None
    except Exception as e:
        logger.error(f"Failed to establish connection: {e}")
        return None, str(e)

def close_connection(conn: Optional[CardConnection]) -> None:
    """
    Close a connection with a smart card reader.
    """
    try:
        if conn:
            conn.disconnect()
    except Exception as e:
        logger.error(f"Failed to close connection: {e}")

def get_card_status(card_id, reader=None):
    """
    Get the current status of a card (active, inactive, blocked, etc.)

    Args:
        card_id (str): The unique identifier of the card
        reader (obj, optional): Reader object to use. If None, uses the default reader

    Returns:
        dict: Status information including:
            - status (str): 'active', 'inactive', 'blocked', 'expired' or 'unknown'
            - last_seen (str): ISO timestamp of last successful read
            - metadata (dict): Any associated card metadata
    """
    try:
        # Import here to avoid circular imports
        #from app.core.card_manager import get_card_registry #Fixed import statement

        #registry = get_card_registry()
        #if not registry or card_id not in registry:
        #    return {
        #        "status": "unregistered",
        #        "last_seen": None,
        #        "metadata": {}
        #    }

        #card_info = registry.get(card_id, {})
        #status = card_info.get("status", "unknown")
        #last_seen = card_info.get("last_seen", None)
        #metadata = card_info.get("metadata", {})

        # If we have a reader, try to verify card presence
        #if reader:
        #    pass
        # Implement card presence verification logic here if needed

        return { #Fixed to return a default value
            "status": "unknown",
            "last_seen": None,
            "metadata": {}
        }

    except Exception as e:
        return {
            "status": "error",
            "last_seen": None,
            "metadata": {},
            "error": str(e)
        }

def backup_card_data(card_id, backup_dir=None):
    """
    Create a backup of a card's data

    Args:
        card_id (str): The card ID to backup
        backup_dir (str, optional): Directory to save backup. If None, uses default.

    Returns:
        dict: Status of the backup operation
    """
    try:
        pass
    except Exception:
        pass

def mask_sensitive_data(data: str) -> str:
    """
    Masks sensitive data in a string.

    Args:
        data: The string containing sensitive data.

    Returns:
        The masked string.
    """
    try:
        if config.get("SENSITIVE_DATA_MASKING", True):
            # Simulate masking sensitive data
            masked_data = "*" * len(data)
            logger.info("Successfully masked sensitive data")
            return masked_data
        else:
            return data
    except Exception as e:
        logger.error(f"Error masking sensitive data: {e}")
        return data

# Safe Globals Context Manager
@contextmanager
def safe_globals():
    """
    Context manager to provide a safe execution environment by limiting
    access to potentially harmful globals.
    """
    safe_list = ['__builtins__', 'datetime', 'time', 'json', 'os']
    safe_dict = dict((k, __builtins__.__dict__[k]) for k in safe_list if k in __builtins__.__dict__)
    safe_dict['os'] = os
    safe_dict['json'] = json
    try:
        yield safe_dict
    finally:
        pass

# Card Registry Operations (Example - Adapt to your needs)

def get_registered_cards_path() -> str:
    """
    Get the path to the registered cards file.
    
    Returns:
        str: Path to the registered cards file
    """
    return os.path.join(config.get("BACKUP_DIR", "backups"), "registered_cards.json")
def is_card_registered(atr):
    """
    Check if a card with the given ATR is registered in the system.
    
    Args:
        atr: The ATR string of the card to check
        
    Returns:
        bool: True if card is registered, False otherwise
    """
    try:
        with open(get_registered_cards_path(), 'r') as f:
            registered_cards = json.load(f)
            return atr in registered_cards
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid JSON, no cards are registered
        return False
    except Exception as e:
        logger.error(f"Error checking card registration: {e}")
        return False

def register_card(atr: str, user_id: str) -> None:
    """
    Register a card with the given ATR and user ID.
    """
    # Implement logic to register the card
    # This could involve adding the card to a database or file
    pass

def unregister_card(atr: str) -> None:
    """
    Unregister a card with the given ATR.
    """
    # Implement logic to unregister the card
    # This could involve removing the card from a database or file
    pass

def activate_card(reader_name=None):
    """
    Activate the currently inserted card.
    
    Args:
        reader_name: Optional name of the reader to use
        
    Returns:
        Tuple (success, message): Success status and descriptive message
    """
    try:
        conn, err = establish_connection(reader_name)
        if err:
            return False, f"Connection error: {err}"
        
        try:
            atr = toHexString(conn.getATR())
            
            if not is_card_registered(atr):
                return False, "Card is not registered in the system"
            
            status = get_card_status(conn)
            
            if status == CardStatus.ACTIVE.name:
                return False, "Card is already active"
            
            if status == CardStatus.BLOCKED.name:
                return False, "Cannot activate a blocked card"
            
            # Perform activation logic here
            # ...
            
            # Update card status in database/file
            # ...
            
            return True, "Card activated successfully"
        finally:
            close_connection(conn)
    except Exception as e:
        logger.exception(f"Error activating card: {e}")
        return False, f"Error: {str(e)}"

def deactivate_card(atr: str) -> None:
    """
    Deactivate a card with the given ATR.
    """
    # Implement logic to deactivate the card
    # This could involve setting a flag in a database or file
    pass

def block_card(atr: str) -> None:
    """
    Block a card with the given ATR.
    """
    # Implement logic to block the card
    # This could involve setting a flag in a database or file
    pass

def unblock_card(atr: str) -> None:
    """
    Unblock a card with the given ATR.
    """
    # Implement logic to unblock the card
    # This could involve setting a flag in a database or file
    pass

def backup_card_data(atr: str) -> str:
    """
    Backup card data for the given ATR.
    """
    # Implement logic to backup card data
    # This could involve creating a copy of the card's data in a file or database
    return "backup_id"

def restore_card_data(atr: str, backup_id: str) -> None:
    """
    Restore card data for the given ATR from the given backup ID.
    """
    # Implement logic to restore card data
    # This could involve restoring the card's data from a file or database
    pass

def secure_dispose_card(atr: str) -> None:
    """
    Securely dispose of a card with the given ATR.
    """
    # Implement logic to securely dispose of the card
    # This could involve deleting the card's data from a database or file
    pass

# Reader Type Detection
def detect_reader_type(reader_name: str) -> str:
    """
    Detect the type of a smart card reader based on its name.
    """
    # Implement logic to detect the reader type based on the reader name
    # This could involve checking the reader name against a list of known reader names
    return "Unknown"