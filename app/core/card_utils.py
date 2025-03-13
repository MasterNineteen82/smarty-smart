import os
import logging
import threading
from logging.handlers import RotatingFileHandler
from smartcard.System import readers
from smartcard.Exceptions import NoCardException, CardConnectionException
from enum import Enum, auto
from typing import Optional, Dict, Any

# --- Configuration Management ---
class ConfigManager:
    """Centralized configuration management with dynamic loading."""

    _instance = None
    _lock = threading.Lock()
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
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize configuration: defaults -> env vars -> dynamic loading."""
        self._config = self._defaults.copy()
        self._load_from_env()
        self._setup_directories()
        self._configure_logging()

    def _load_from_env(self):
        """Override configuration from environment variables."""
        for key in self._config:
            env_key = f"SMARTCARD_{key}"
            if env_key in os.environ:
                value = os.environ[env_key]
                # Attempt type conversion based on default type
                try:
                    if isinstance(self._config[key], bool):
                        value = value.lower() == 'true'
                    elif isinstance(self._config[key], int):
                        try:
                            value = int(value)
                        except ValueError:
                            logger.warning(f"Could not convert '{env_key}' value '{value}' to integer.")
                            continue  # Skip this variable if conversion fails
                    elif isinstance(self._config[key], float):
                        try:
                            value = float(value)
                        except ValueError:
                            logger.warning(f"Could not convert '{env_key}' value '{value}' to float.")
                            continue  # Skip this variable if conversion fails
                except Exception as e:
                    logger.error(f"Error processing environment variable {env_key}: {e}")
                    continue  # Skip to the next variable in case of error
        self._config[key] = value
        return value

    def mask_sensitive_data(self, data_str):
        """Mask sensitive data if configured to do so"""
        if not self._config.get("SENSITIVE_DATA_MASKING", True):
            return data_str

        # Simple implementation - in production, use more sophisticated patterns
        if isinstance(data_str, str) and len(data_str) > 8:
            return data_str[:4] + "****" + data_str[-4:]
        return data_str

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
file_handler = RotatingFileHandler(os.path.join(logs_dir, 'smart_card.log'), maxBytes=5*1024*1024, backupCount=5)
console_handler = logging.StreamHandler()
log_format = '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s'
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
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

class ReaderStatus(Enum):
    READY = auto()
    NOT_FOUND = auto()
    ERROR = auto()
    BUSY = auto()

# --- Card Type Enums for Better Identification ---
class CardType(Enum):
    UNKNOWN = auto()
    MIFARE_CLASSIC = auto()
    MIFARE_ULTRALIGHT = auto()
    MIFARE_DESFIRE = auto()
    FELICA = auto()
    NFC_TYPE_1 = auto()
    NFC_TYPE_2 = auto()
    NFC_TYPE_3 = auto()
    NFC_TYPE_4 = auto()
    ISO_14443_A = auto()
    ISO_14443_B = auto()
    JCOP_JAVACARD = auto()
    SLE_MEMORY_CARD = auto()
    GENERIC_RFID = auto()

# --- Global State with Thread Safety ---
_lock = threading.RLock()
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
os.makedirs(BACKUP_DIR, exist_ok=True)

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
    Detect the card type based on Answer To Reset (ATR) string.

    Args:
        atr (bytes or str): ATR received from the card

    Returns:
        str: Card type identifier ('MIFARE_CLASSIC', 'MIFARE_ULTRALIGHT', etc.)
    """
    try:
        # Convert bytes to string if needed
        if isinstance(atr, bytes):
            atr_str = toHexString(atr)
        else:
            atr_str = atr.strip()

        # Normalize the ATR string to standard format (uppercase, no extra spaces)
        atr_str = atr_str.upper().replace('  ', ' ')

        # Fix: Special case for MIFARE Ultralight (check this first to avoid misidentification)
        # This was previously checked after the general patterns, which could lead to misidentification
        if "3B 8F 80 01 80 4F 0C A0 00 00 03" in atr_str and "00 01" in atr_str:
            logger.debug(f"Detected MIFARE_ULTRALIGHT from ATR: {atr_str}")
            return "MIFARE_ULTRALIGHT"

        # Check against known ATR patterns
        for card_type, patterns in ATR_PATTERNS.items():
            for pattern in patterns:
                if pattern in atr_str or atr_str in pattern:
                    logger.debug(f"Detected card type: {card_type} from ATR: {atr_str}")
                    return card_type

        # Generic type detection based on common prefixes
        if atr_str.startswith("3B 8F"):
            if "80 01 80 4F" in atr_str:
                return "ISO_14443_A"

        logger.warning(f"Unknown card type with ATR: {atr_str}")
        return "UNKNOWN"
    except Exception as e:
        logger.error(f"Error detecting card type: {e}")
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

def establish_connection(reader_name):
    """
    Establish a connection to a card on the specified reader.

    Args:
        reader_name (str): Name of the reader to connect to

    Returns:
        tuple: (connection object, error message or None)
    """
    try:
        available_readers = readers()
        selected_reader = None

        for reader in available_readers:
            if reader_name in str(reader):
                selected_reader = reader
                break

        if selected_reader is None:
            logger.warning(f"Reader '{reader_name}' not found in available readers")
            return None, f"Reader '{reader_name}' not found"

        # Apply appropriate timeout based on reader type
        #reader_type = detect_reader_type(reader_name)
        #timeout = TIMEOUTS.get(reader_name, TIMEOUTS.get("DEFAULT", 5.0))

        logger.debug(f"Connecting to reader {reader_name}")
        connection = selected_reader.createConnection()
        connection.connect()  # Add timeout parameter if supported
        return connection, None

    except NoCardException:
        logger.info(f"No card present on reader '{reader_name}'")
        return None, "No card present on the reader"
    except CardConnectionException as e:
        logger.error(f"Connection error on reader '{reader_name}': {str(e)}")
        return None, f"Connection error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error connecting to reader '{reader_name}': {str(e)}", exc_info=True)
        return None, f"Unexpected error: {str(e)}"

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
        from card_manager import get_card_registry

        registry = get_card_registry()
        if not registry or card_id not in registry:
            return {
                "status": "unregistered",
                "last_seen": None,
                "metadata": {}
            }

        card_info = registry.get(card_id, {})
        status = card_info.get("status", "unknown")
        last_seen = card_info.get("last_seen", None)
        metadata = card_info.get("metadata", {})

        # If we have a reader, try to verify card presence
        if reader:
            pass
            # Implement card presence verification logic here if needed

        return {
            "status": status,
            "last_seen": last_seen,
            "metadata": metadata
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