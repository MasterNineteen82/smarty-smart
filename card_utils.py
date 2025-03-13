import logging
from logging.handlers import RotatingFileHandler
from smartcard.System import readers
from smartcard.util import toHexString, toBytes
from smartcard.CardConnection import CardConnection
from smartcard.Exceptions import NoCardException, CardConnectionException, CardRequestTimeoutException
from smartcard.CardRequest import CardRequest
from smartcard.scard import SCardEstablishContext, SCardListReaders, SCardReleaseContext, SCARD_SCOPE_USER, SCardConnect, SCardDisconnect, SCardGetContext, SCARD_LEAVE_CARD, SCARD_SHARE_SHARED, SCARD_PROTOCOL_T0, SCARD_PROTOCOL_T1, SCARD_S_SUCCESS, SCardGetErrorMessage # noqa
import time
import threading
import os
import hashlib
import json
from enum import Enum, auto
from typing import Optional, Dict, Any, Tuple, List
from contextlib import contextmanager
from datetime import datetime
import random
import uuid  # Add this import at the top

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
selected_reader = None
card = None
status: Dict[str, str] = {"message": "Disconnected", "atr": ""}
reader_status: ReaderStatus = ReaderStatus.NOT_FOUND
card_status: CardStatus = CardStatus.DISCONNECTED
MAX_PIN_ATTEMPTS: int = 3
CONNECTION_TIMEOUT: int = 10
MAX_CONNECT_RETRIES: int = 3
BACKUP_DIR: str = os.path.join(logs_dir, 'backups')
pin_attempts: int = 0
last_error: Optional[str] = None
card_info: Dict[str, Any] = {}
available_readers: list = []
registered_cards: Dict[str, Dict[str, Any]] = {}  # Store card registration data

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

# --- Thread-Safe Context Manager with Enhanced Error Handling ---
@contextmanager
def safe_globals():
    with _lock:
        try:
            yield
        except Exception as e:
            logger.exception(f"Thread-safe operation failed: {e}")
            raise
        finally:
            # Ensure any necessary cleanup
            try:
                # Example cleanup operation, replace with actual if needed
                cleanup_temp_files()
            except Exception as cleanup_error:
                logger.error(f"Cleanup after thread-safe operation failed: {cleanup_error}")

def cleanup_temp_files():
    """Example cleanup function to remove temporary files"""
    temp_dir = os.path.join(logs_dir, 'temp')
    if os.path.exists(temp_dir):
        for temp_file in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, temp_file))
                logger.debug(f"Removed temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_file}: {e}")

# --- Enhanced Operation Timing Decorator with Edge Case Handling ---
def log_operation_timing(operation_name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"{operation_name} completed in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{operation_name} failed after {elapsed:.3f}s: {e}")
                raise
            finally:
                if 'start_time' in locals():
                    elapsed = time.time() - start_time
                    logger.debug(f"{operation_name} finished with elapsed time: {elapsed:.3f}s")
        return wrapper
    return decorator

# --- Reader Detection and Selection with Enhanced Error Handling ---
def update_available_readers() -> List[Any]:
    global available_readers
    try:
        available_readers = readers()
        if available_readers:
            logger.info(f"Detected readers: {[str(r) for r in available_readers]}")
        else:
            logger.warning("No readers detected")
        return available_readers
    except Exception as e:
        logger.error(f"Failed to detect readers: {e}")
        available_readers = []
        return available_readers

def select_reader(reader_name: str = None) -> Tuple[Optional[Any], Optional[str]]:
    global selected_reader, reader_status
    with safe_globals():
        readers_list = update_available_readers()
        if not readers_list:
            reader_status = ReaderStatus.NOT_FOUND
            return None, "No readers detected."
        
        # If reader name is provided, try to find it
        if reader_name:
            for reader in readers_list:
                if reader_name.lower() in str(reader).lower():
                    selected_reader = reader
                    reader_status = ReaderStatus.READY
                    logger.info(f"Selected reader: {selected_reader}")
                    return selected_reader, None
            return None, f"Reader '{reader_name}' not found."
        
        # Auto-selection priorities: Cherry ST > NFC/RFID readers > first available
        for reader in readers_list:
            reader_str = str(reader).lower()
            if "cherry" in reader_str:
                selected_reader = reader
                reader_status = ReaderStatus.READY
                logger.info(f"Auto-selected Cherry reader: {selected_reader}")
                return selected_reader, None
            if any(keyword in reader_str for keyword in ["nfc", "rfid", "acr122"]):
                selected_reader = reader
                reader_status = ReaderStatus.READY
                logger.info(f"Auto-selected NFC/RFID reader: {selected_reader}")
                return selected_reader, None
        
        # If no specialized reader found, use first available
        selected_reader = readers_list[0]
        reader_status = ReaderStatus.READY
        logger.info(f"Auto-selected first available reader: {selected_reader}")
        return selected_reader, None

# --- Enhanced Card Polling with Better Exception Handling ---
def poll_card_presence():
    global card_status, card_connection, status, card_info
    with safe_globals():
        if not selected_reader:
            threading.Timer(2.0, poll_card_presence).start()
            return
        
        conn = selected_reader.createConnection()
        try:
            conn.connect(CardConnection.T0_protocol | CardConnection.T1_protocol)
            atr = conn.getATR()
            atr_hex = toHexString(atr)
            
            if card_status not in [CardStatus.CONNECTED, CardStatus.REGISTERED, CardStatus.BLOCKED]:
                card_status = CardStatus.CONNECTED
                status["message"] = "Card Inserted"
                status["atr"] = atr_hex
                
                # Update card info with detected type
                card_info["atr"] = atr_hex
                card_info["card_type"] = detect_card_type(atr_hex)
                logger.info(f"Card inserted: ATR={atr_hex}, Type={card_info.get('card_type', 'Unknown')}")
            
            conn.disconnect()
        except NoCardException:
            if card_status not in [CardStatus.DISCONNECTED, CardStatus.REMOVED]:
                card_status = CardStatus.REMOVED
                status["message"] = "Card Removed"
                status["atr"] = ""
                card_connection = None
                logger.info("Card removed")
        except CardConnectionException as e:
            logger.warning(f"Connection error during polling: {e}")
            # Don't change status on transient errors
        except Exception as e:
            logger.debug(f"Polling error: {e}")
        finally:
            # Schedule next poll with increased delay if error occurred
            poll_delay = 2.0 if card_status == CardStatus.ERROR else 1.0
            threading.Timer(poll_delay, poll_card_presence).start()

def establish_connection(reader_name):
    try:
        hresult, hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
        if hresult != SCARD_S_SUCCESS:
            return None, f"Failed to establish context: {SCardGetErrorMessage(hresult)}"
        
        hresult, hcard, dwActiveProtocol = SCardConnect(hcontext, reader_name, SCARD_SHARE_SHARED, SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1)
        if hresult != SCARD_S_SUCCESS:
            SCardReleaseContext(hcontext)
            return None, f"Failed to connect: {SCardGetErrorMessage(hresult)}"
        
        return hcard, None
    except Exception as e:
        return None, str(e)

def toHexString(bytes):
    return " ".join([f"{b:02X}" for b in bytes])

def detect_card_type(atr_hex):
    atr = atr_hex.replace(" ", "").upper()
    if atr.startswith("3B8F8001"):
        return "MIFARE Classic"
    elif atr.startswith("3B8F800180"):
        return "FeliCa"
    elif atr.startswith("3B8"):
        return "ISO 14443 Type A"
    return "Unknown"

def backup_card_data(reader_name):
    conn, err = establish_connection(reader_name)
    if err:
        return False, err, None
    try:
        atr = toHexString(conn.getATR())
        card_type = detect_card_type(atr)
        backup_dir = os.path.abspath(os.environ.get('SMARTY_BACKUP_DIR', 'backups'))
        os.makedirs(backup_dir, exist_ok=True)
        backup_id = f"backup_{reader_name}_{time.strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join(backup_dir, f"{backup_id}.json")
        with open(backup_path, 'w') as f:
            f.write(f"{{\"atr\": \"{atr}\", \"type\": \"{card_type}\"}}")
        return True, f"Backup created at {backup_path}", backup_id
    except Exception as e:
        return False, str(e), None
    finally:
        if conn:
            SCardDisconnect(conn, SCARD_LEAVE_CARD)
            SCardReleaseContext(SCardGetContext(conn))

def detect_card_type(atr):
    """Detect card type based on Answer To Reset (ATR) string."""
    if not atr:
        return "UNKNOWN"
    
    # Convert string ATR to uppercase for consistent comparison
    atr_str = atr.upper() if isinstance(atr, str) else str(atr).upper()
    
    # MIFARE Ultralight detection - add correct pattern
    if isinstance(atr_str, str) and '3B 8E' in atr_str and '03 00 01 00' in atr_str:
        return "MIFARE_ULTRALIGHT"
        
    # MIFARE Classic detection
    if isinstance(atr_str, str) and '3B 8F 80 01 80 4F 0C A0 00' in atr_str:
        return "MIFARE_CLASSIC"
    
    # ISO 14443 Type A cards (general detection)
    if isinstance(atr_str, str) and ('3B 8F' in atr_str or '3B 8E' in atr_str):
        return "ISO_14443_A"
    
    return "UNKNOWN"

# Fix for card type detection
#def detect_card_type(atr):
#    """Detect card type based on Answer To Reset (ATR) string."""
#    if not atr:
#        return "UNKNOWN"
#    
    # Convert string ATR to uppercase for consistent comparison
#    atr_str = atr.upper() if isinstance(atr, str) else atr
#    
    # MIFARE Classic detection - add this pattern
#    if isinstance(atr_str, str) and '3B 8F 80 01 80 4F 0C A0 00' in atr_str:
#        return "MIFARE_CLASSIC"
#    
#    # ISO 14443 Type A cards
#    if isinstance(atr_str, str) and ('3B 8F' in atr_str or '3B 8E' in atr_str):
#        if '03 00 01 00' in atr_str:
#            return "MIFARE_ULTRALIGHT"
#        return "ISO_14443_A"
#    
#    # Other card types...
#    # [existing code...]
#    
#    return "UNKNOWN"

# Example usage and testing
if __name__ == "__main__":
    test_atrs = [
        "3B 8F 80 01 80 4F",                    # ISO 14443 A
        "3B 8E 80 01 80 31",                    # ISO 14443 B
        "06 03 00 01 00 00 00",                # MIFARE Ultralight
        "80 4F 0C A0 00 00 03 06",             # MIFARE Classic
        "80 4F 0C A0 00 00 03 06 DF",          # DESFire
        "3B 89 80 01",                         # JCOP JavaCard
        "3B 0F",                               # SLE Memory Card
        "3B 8F 80 01 80 4F 0C A0 00 00 03 06 11", # FeliCa
        "3B 8F 80 01 80 4F 0C A0 00 00 03 06 01", # NFC Type 1
        "3B 8F 80 01 80 4F 0C A0 00 00 03 06 02", # NFC Type 2
        "3B 8F 80 01 80 4F 0C A0 00 00 03 06 03", # NFC Type 3
        "3B 8F 80 01 80 4F 0C A0 00 00 03 06 04"  # NFC Type 4
    ]
    
    for atr in test_atrs:
        try:
            card_type = detect_card_type(atr)
            print(f"ATR: {atr} -> Card Type: {card_type}")
        except Exception as e:
            print(f"Error detecting card type for ATR {atr}: {e}")

# --- Establish Connection with Enhanced NFC/RFID Support ---
def establish_connection() -> Tuple[Optional[CardConnection], Optional[str]]:
    """Establish connection to a card with enhanced detection and error handling"""
    global selected_reader, card_status, card_info
    
    with safe_globals():
        try:
            if selected_reader is None:
                return None, "No reader selected"
            
            try:
                # Get appropriate timeout for this reader
                timeout = get_reader_timeout(selected_reader.name)
                
                # Create a card request for all protocols
                card_request = CardRequest(readers=[selected_reader.name], timeout=timeout)
                card_service = card_request.waitforcard()
                
                # Try to connect with different protocols
                for protocol in [CardConnection.T0_protocol, CardConnection.T1_protocol, CardConnection.RAW_protocol]:
                    try:
                        conn = card_service.connection
                        conn.connect(protocol)
                        
                        # Get ATR and detect card type
                        atr = toHexString(conn.getATR())
                        card_type = detect_card_type(atr)
                        
                        # Update card info
                        card_info = {
                            "atr": atr,
                            "card_type": card_type,
                            "reader_type": detect_reader_type(selected_reader.name),
                            "protocol": "T=0" if protocol == CardConnection.T0_protocol else 
                                       "T=1" if protocol == CardConnection.T1_protocol else "RAW"
                        }
                        
                        # Special handling for FeliCa cards
                        if card_type == "FELICA":
                            if not initialize_felica(conn):
                                logger.warning("FeliCa card detected but initialization failed")
                        
                        # Update status
                        card_status = CardStatus.CONNECTED
                        logger.info(f"Connected to {card_type} card using {card_info['protocol']} protocol")
                        
                        return conn, None
                    except CardConnectionException as e:
                        # Try next protocol
                        logger.debug(f"Protocol {protocol} failed: {e}, trying next")
                        continue
                
                # If all protocols failed
                return None, "Failed to connect with any protocol"
            
            except CardRequestTimeoutException:
                card_status = CardStatus.NOT_PRESENT
                return None, "No card present"
            except CardConnectionException as e:
                card_status = CardStatus.ERROR
                logger.error(f"Connection error: {e}")
                return None, f"Connection error: {e}"
            
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            card_status = CardStatus.ERROR
            return None, f"Unexpected error: {e}"

# --- FeliCa specific initialization with enhanced error handling ---
def initialize_felica(conn: CardConnection) -> bool:
    """Initialize FeliCa card with specific commands"""
    try:
        # FeliCa polling command
        polling_cmd = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        resp, sw1, sw2 = conn.transmit(polling_cmd)
        
        if sw1 != 0x90 or sw2 != 0x00:
            logger.warning(f"FeliCa polling failed: SW1={sw1:02X}, SW2={sw2:02X}")
            return False
            
        # Further FeliCa initialization could be added here
        logger.info("FeliCa card initialized successfully")
        return True
    except CardConnectionException as e:
        logger.error(f"FeliCa initialization failed due to connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during FeliCa initialization: {e}")
        return False

# --- Enhanced Connection Close with comprehensive error handling ---
def close_connection(conn: Optional[CardConnection]) -> bool:
    if not conn:
        return True
    try:
        conn.disconnect()
        logger.debug("Connection closed successfully")
        return True
    except CardConnectionException as e:
        logger.error(f"Failed to close connection cleanly: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error closing connection: {e}")
        return False

# --- New: Card Registration and Management ---
def register_card(name: str, user_id: str, card_data: Dict[str, Any] = None) -> Tuple[bool, str]:
    """Register a card in the system with associated data"""
    global card_status, registered_cards
    
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot register card: {err}"
        
        try:
            atr = toHexString(conn.getATR())
            
            if atr in registered_cards:
                return False, f"Card already registered as '{registered_cards[atr].get('name', 'unnamed')}'"
            
            # Create registration data
            registration_data = {
                "name": name,
                "user_id": user_id,
                "atr": atr,
                "card_type": card_info.get("card_type", "Unknown"),
                "registration_time": datetime.now().isoformat(),
                "custom_data": card_data or {},
                "status": "active"
            }
            
            # Store registration
            registered_cards[atr] = registration_data
            card_status = CardStatus.REGISTERED
            
            # Save to persistent storage
            save_registered_cards()
            
            logger.info(f"Card registered: {name}, User: {user_id}, ATR: {atr}")
            return True, "Card registered successfully"
        except Exception as e:
            logger.error(f"Card registration failed: {e}")
            return False, f"Registration failed: {e}"
        finally:
            close_connection(conn)

def is_card_registered(atr: str) -> Tuple[bool, str]:
    """Check if a card is registered by ATR with enhanced error handling"""
    try:
        load_registered_cards()  # Ensure data is loaded
        if atr in registered_cards:
            return True, f"Card is registered as '{registered_cards[atr].get('name', 'unnamed')}'"
        else:
            return False, "Card is not registered"
    except Exception as e:
        logger.error(f"Error checking card registration: {e}")
        return False, f"Error checking registration: {e}"

def unregister_card() -> Tuple[bool, str]:
    """Remove a card from the system"""
    global card_status, registered_cards
    
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot unregister card: {err}"
        
        try:
            atr = toHexString(conn.getATR())
            
            if atr not in registered_cards:
                return False, "Card not registered"
            
            # Remove from registered cards
            name = registered_cards[atr].get("name", "unnamed")
            del registered_cards[atr]
            card_status = CardStatus.UNREGISTERED
            
            # Save to persistent storage
            save_registered_cards()
            
            logger.info(f"Card unregistered: {name}, ATR: {atr}")
            return True, "Card unregistered successfully"
        except Exception as e:
            logger.error(f"Card unregistration failed: {e}")
            return False, f"Unregistration failed: {e}"
        finally:
            close_connection(conn)

def save_registered_cards() -> bool:
    """Save registered cards to persistent storage with enhanced error handling"""
    try:
        with safe_globals():
            with open(os.path.join(logs_dir, "registered_cards.json"), 'w') as f:
                json.dump(registered_cards, f, indent=2)
            logger.info("Registered cards saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save registered cards: {e}")
        return False

def load_registered_cards() -> bool:
    """Load registered cards from persistent storage with enhanced error handling"""
    global registered_cards
    try:
        with safe_globals():
            path = os.path.join(logs_dir, "registered_cards.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    registered_cards = json.load(f)
                logger.debug(f"Loaded {len(registered_cards)} registered cards")
            else:
                logger.warning("Registered cards file not found, starting with empty registry")
                registered_cards = {}
        return True
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error while loading registered cards: {e}")
        registered_cards = {}
        return False
    except Exception as e:
        logger.error(f"Failed to load registered cards: {e}")
        registered_cards = {}
        return False

# --- New: Card Activation/Deactivation ---
def activate_card() -> Tuple[bool, str]:
    """Activate a card (make it usable in the system)"""
    global card_status
    
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot activate card: {err}"
        
        try:
            atr = toHexString(conn.getATR())
            
            if atr not in registered_cards:
                return False, "Card not registered"
                
            # Check if already active
            if registered_cards[atr].get("status") == "active":
                return True, "Card is already active"
            
            # Activate the card
            registered_cards[atr]["status"] = "active"
            registered_cards[atr]["activation_time"] = datetime.now().isoformat()
            
            # Try to send activation command
            apdu = [0xFF, 0xD0, 0x00, 0x01, 0x01, 0x01]  # Example activation command
            try:
                _, sw1, sw2 = conn.transmit(apdu)
                if sw1 != 0x90 or sw2 != 0x00:
                    logger.warning(f"Activation command returned: SW1={sw1:02X}, SW2={sw2:02X}")
            except Exception as e:
                logger.warning(f"Activation command failed: {e}")
            
            # Save to persistent storage
            save_registered_cards()
            
            logger.info(f"Card activated: {registered_cards[atr].get('name', 'unnamed')}")
            return True, "Card activated successfully"
        except Exception as e:
            logger.error(f"Card activation failed: {e}")
            return False, f"Activation failed: {e}"
        finally:
            close_connection(conn)

def deactivate_card() -> Tuple[bool, str]:
    """Deactivate a card (make it temporarily unusable)"""
    global card_status
    
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot deactivate card: {err}"
        
        try:
            atr = toHexString(conn.getATR())
            
            if atr not in registered_cards:
                return False, "Card not registered"
                
            # Check if already inactive
            if registered_cards[atr].get("status") != "active":
                return True, "Card is already inactive"
            
            # Deactivate the card
            registered_cards[atr]["status"] = "inactive"
            registered_cards[atr]["deactivation_time"] = datetime.now().isoformat()
            
            # Try to send deactivation command
            apdu = [0xFF, 0xD0, 0x00, 0x01, 0x01, 0x00]  # Example deactivation command
            try:
                _, sw1, sw2 = conn.transmit(apdu)
                if sw1 != 0x90 or sw2 != 0x00:
                    logger.warning(f"Deactivation command returned: SW1={sw1:02X}, SW2={sw2:02X}")
            except Exception as e:
                logger.warning(f"Deactivation command failed: {e}")
            
            # Save to persistent storage
            save_registered_cards()
            
            logger.info(f"Card deactivated: {registered_cards[atr].get('name', 'unnamed')}")
            return True, "Card deactivated successfully"
        finally:
            close_connection(conn)

# --- New: Card Locking/Unlocking ---
def block_card() -> Tuple[bool, str]:
    """Block a card (security measure, harder to reverse than deactivation)"""
    global card_status
    
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot block card: {err}"
        
        try:
            atr = toHexString(conn.getATR())
            
            # Check if already blocked
            if card_status == CardStatus.BLOCKED:
                return True, "Card is already blocked"
            
            # Send block command
            apdu = [0xFF, 0xD0, 0x01, 0x00, 0x01, 0xFF]
            _, sw1, sw2 = conn.transmit(apdu)
            
            if sw1 == 0x90 and sw2 == 0x00:
                card_status = CardStatus.BLOCKED
                
                # Update registration if registered
                if atr in registered_cards:
                    registered_cards[atr]["status"] = "blocked"
                    registered_cards[atr]["blocked_time"] = datetime.now().isoformat()
                    save_registered_cards()
                
                logger.info(f"Card blocked successfully, ATR: {atr}")
                return True, "Card blocked successfully"
            else:
                logger.error(f"Block failed: SW1={sw1:02X}, SW2={sw2:02X}")
                return False, f"Block failed: SW1={sw1:02X}, SW2={sw2:02X}"
        except Exception as e:
            logger.error(f"Card blocking failed: {e}")
            return False, f"Blocking failed: {e}"
        finally:
            close_connection(conn)

def unblock_card() -> Tuple[bool, str]:
    """Unblock a previously blocked card"""
    global card_status
    
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot unblock card: {err}"
        
        try:
            atr = toHexString(conn.getATR())
            
            # Check if not blocked
            if card_status != CardStatus.BLOCKED:
                return True, "Card is not blocked"
            
            # Send unblock command
            apdu = [0xFF, 0xD0, 0x01, 0x00, 0x01, 0x00]
            _, sw1, sw2 = conn.transmit(apdu)
            
            if sw1 == 0x90 and sw2 == 0x00:
                card_status = CardStatus.CONNECTED
                
                # Update registration if registered
                if atr in registered_cards:
                    registered_cards[atr]["status"] = "active"
                    registered_cards[atr]["unblocked_time"] = datetime.now().isoformat()
                    save_registered_cards()
                
                logger.info(f"Card unblocked successfully, ATR: {atr}")
                return True, "Card unblocked successfully"
            else:
                logger.error(f"Unblock failed: SW1={sw1:02X}, SW2={sw2:02X}")
                return False, f"Unblock failed: SW1={sw1:02X}, SW2={sw2:02X}"
        except Exception as e:
            logger.error(f"Card unblocking failed: {e}")
            return False, f"Unblocking failed: {e}"
        finally:
            close_connection(conn)

# --- New: Card Backup and Restoration ---
def backup_card_data() -> Tuple[bool, str, Optional[str]]:
    """Create a backup of card data"""
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot backup card: {err}", None
        
        try:
            atr = toHexString(conn.getATR())
            
            # Read memory contents
            apdu = [0xFF, 0xB0, 0x00, 0x00, 0x00]
            data, sw1, sw2 = conn.transmit(apdu)
            
            if sw1 != 0x90 or sw2 != 0x00:
                return False, f"Memory read failed: SW1={sw1:02X}, SW2={sw2:02X}", None
            
            # Create backup data
            backup_data = {
                "atr": atr,
                "card_type": card_info.get("card_type", "Unknown"),
                "backup_time": datetime.now().isoformat(),
                "memory_data": toHexString(data),
                "checksum": hashlib.sha256(bytes(data)).hexdigest()
            }
            
            # Save backup to file
            backup_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{atr.replace(' ', '_')}"
            backup_file = os.path.join(BACKUP_DIR, f"backup_{backup_id}.json")
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Card backup created: {backup_file}")
            return True, "Backup created successfully", backup_id
        except Exception as e:
            logger.error(f"Card backup failed: {e}")
            return False, f"Backup failed: {e}", None
        finally:
            close_connection(conn)

def restore_card_data(backup_id: str) -> Tuple[bool, str]:
    """Restore card data from a backup"""
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot restore card: {err}"
        
        try:
            # Load backup file
            backup_file = None
            for file in os.listdir(BACKUP_DIR):
                if backup_id in file and file.endswith('.json'):
                    backup_file = os.path.join(BACKUP_DIR, file)
                    break
            
            if not backup_file:
                return False, f"Backup ID '{backup_id}' not found"
            
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Verify card type matches
            if backup_data.get("card_type") != card_info.get("card_type"):
                logger.warning(f"Card type mismatch: Backup={backup_data.get('card_type')}, Current={card_info.get('card_type')}")
                # Continue anyway but log warning
            
            # Convert hex string back to byte array
            memory_data = toBytes(backup_data["memory_data"])
            
            # Calculate checksum to verify data integrity
            current_checksum = hashlib.sha256(bytes(memory_data)).hexdigest()
            if current_checksum != backup_data["checksum"]:
                return False, "Backup data integrity check failed"
            
            # Write data back to card
            chunk_size = 64  # Adjust based on card capabilities
            for offset in range(0, len(memory_data), chunk_size):
                chunk = memory_data[offset:offset+chunk_size]
                apdu = [0xFF, 0xD6, offset >> 8, offset & 0xFF, len(chunk)] + chunk
                _, sw1, sw2 = conn.transmit(apdu)
                
                if sw1 != 0x90 or sw2 != 0x00:
                    return False, f"Restore failed at offset {offset}: SW1={sw1:02X}, SW2={sw2:02X}"
            
            logger.info(f"Card restored successfully from backup {backup_id}")
            return True, "Card restored successfully"
        except Exception as e:
            logger.error(f"Card restoration failed: {e}")
            return False, f"Restoration failed: {e}"
        finally:
            close_connection(conn)

def list_backups() -> List[Dict[str, Any]]:
    """List available backups with metadata"""
    try:
        backups = []
        for file in os.listdir(BACKUP_DIR):
            if file.endswith('.json') and file.startswith('backup_'):
                try:
                    with open(os.path.join(BACKUP_DIR, file), 'r') as f:
                        data = json.load(f)
                        backups.append({
                            "backup_id": file.replace("backup_", "").replace(".json", ""),
                            "card_type": data.get("card_type", "Unknown"),
                            "backup_time": data.get("backup_time", "Unknown"),
                            "atr": data.get("atr", "Unknown")
                        })
                except Exception as e:
                    logger.error(f"Error reading backup file {file}: {e}")
        
        return sorted(backups, key=lambda x: x.get("backup_time", ""), reverse=True)
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        return []

def delete_backup(backup_id: str) -> Tuple[bool, str]:
    """Delete a backup file"""
    try:
        for file in os.listdir(BACKUP_DIR):
            if backup_id in file and file.endswith('.json'):
                os.remove(os.path.join(BACKUP_DIR, file))
                logger.info(f"Backup {backup_id} deleted")
                return True, f"Backup {backup_id} deleted successfully"
        
        return False, f"Backup ID '{backup_id}' not found"
    except Exception as e:
        logger.error(f"Failed to delete backup {backup_id}: {e}")
        return False, f"Failed to delete backup: {e}"

# Fix for reader type detection
#def detect_reader_type(reader_name):
#    """Detect reader type based on reader name."""
#    try:
#        if reader_name is None or not isinstance(reader_name, str):
#            return "UNKNOWN"
#            
#        reader_name_upper = reader_name.upper()
#        
#        # CHERRY Smart Terminal detection
#        if "CHERRY" in reader_name_upper or "ST-" in reader_name_upper:
#            return "CHERRY_SMART_TERMINAL"
#            
#        # ACS ACR122 detection
#        if "ACS" in reader_name_upper or "ACR122" in reader_name_upper:
#            return "ACS_ACR122"
#        
#        # Always return GENERIC for any other reader that's provided
#        return "GENERIC"
#        
#    except Exception as e:
#        logging.error(f"Error detecting reader type for '{reader_name}': {str(e)}")
#        return "UNKNOWN"

def detect_reader_type(reader_name: str) -> Dict[str, Any]:
    """
    Detect the type of reader based on its name.
    Returns a dictionary with reader information.
    Handles edge cases and exceptions.
    """
    try:
        if CHERRY_ST_IDENTIFIER in reader_name:
            return {
                'type': "CHERRY_ST",
                'manufacturer': "CHERRY",
                'timeout_factor': 2.0,  # Cherry readers need longer timeouts
                'supports_felica': True
            }
        elif ACR122U_IDENTIFIER in reader_name:
            return {
                'type': "ACR122U",
                'manufacturer': "ACS",
                'timeout_factor': 1.0,
                'supports_felica': False
            }
        else:
            return {
                'type': "GENERIC",
                'manufacturer': "Unknown",
                'timeout_factor': 1.5,
                'supports_felica': False
            }
    except Exception as e:
        logger.error(f"Error detecting reader type for '{reader_name}': {e}")
        return {
            'type': "UNKNOWN",
            'manufacturer': "Unknown",
            'timeout_factor': 1.0,
            'supports_felica': False
        }

def get_reader_timeout(reader_name: str) -> float:
    """Get the appropriate timeout for a specific reader with enhanced error handling"""
    try:
        reader_type_info = detect_reader_type(reader_name)
        timeout_factor = reader_type_info.get('timeout_factor', 1.0)
        base_timeout = TIMEOUTS.get(reader_type_info.get('type'), TIMEOUTS["DEFAULT"])
        return base_timeout * timeout_factor
    except Exception as e:
        logger.error(f"Error getting timeout for reader '{reader_name}': {e}")
        return TIMEOUTS["DEFAULT"]

def get_card_timeout(card_type: str) -> float:
    """Get the appropriate timeout for a specific card type with enhanced error handling"""
    try:
        return TIMEOUTS.get(card_type, TIMEOUTS["DEFAULT"])
    except Exception as e:
        logger.error(f"Error getting timeout for card type '{card_type}': {e}")
        return TIMEOUTS["DEFAULT"]

def secure_dispose_card() -> Tuple[bool, str]:
    """Securely wipe all accessible data from a card before disposal"""
    global card_status
    
    with safe_globals():
        conn, err = establish_connection()
        if err:
            return False, f"Cannot dispose card: {err}"
        
        try:
            atr = toHexString(conn.getATR())
            card_type = detect_card_type(atr)
            
            # For MIFARE Classic, we need to authenticate sectors before writing
            if card_type == "MIFARE_CLASSIC":
                # Try to overwrite entire memory with random data
                success, message = wipe_mifare_classic(conn)
                if not success:
                    return False, message
            
            # For other cards, overwrite accessible memory areas
            elif card_type in ["MIFARE_ULTRALIGHT", "NFC_TYPE_2"]:
                # These cards have simpler memory model
                success, message = wipe_ultralight_card(conn)
                if not success:
                    return False, message
            
            # For other card types, try generic approach
            else:
                # Try to write random data to memory areas
                # Start from address 0 and try blocks of 16 bytes
                for offset in range(0, 1024, 16):  # Try first 1KB
                    try:
                        # Generate random data
                        random_data = [random.randint(0, 255) for _ in range(16)]
                        apdu = [0xFF, 0xD6, offset >> 8, offset & 0xFF, len(random_data)] + random_data
                        
                        # Try to write and ignore errors (some areas may be protected)
                        try:
                            _, sw1, sw2 = conn.transmit(apdu)
                        except Exception:
                            pass  # Ignore errors and continue
                    except Exception:
                        break  # Stop if we hit a major exception
            
            # Reset the card if possible
            try:
                reset_apdu = [0xFF, 0x30, 0x00, 0x00, 0x01, 0x01]  # Generic card reset
                conn.transmit(reset_apdu)
            except Exception:
                pass  # Ignore if reset isn't supported
            
            logger.info("Card data securely wiped for disposal")
            card_status = CardStatus.DISPOSED
            return True, "Card wiped and ready for physical disposal"
        
        except Exception as e:
            logger.error(f"Secure disposal failed: {e}")
            return False, f"Disposal failed: {e}"
        finally:
            close_connection(conn)

def wipe_mifare_classic(conn: CardConnection) -> Tuple[bool, str]:
    """Securely wipe a MIFARE Classic card with enhanced error handling"""
    try:
        # Try authentication with default keys
        default_keys = [
            [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],  # Factory default
            [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5],  # Common alternative
            [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7],  # Common alternative
        ]
        
        # Try to authenticate and wipe sectors
        for sector in range(16):  # MIFARE Classic has 16 sectors
            authenticated = False
            
            # Try each key
            for key in default_keys:
                try:
                    # Authenticate with key A
                    auth_cmd = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, sector, 0x60] + key
                    _, sw1, sw2 = conn.transmit(auth_cmd)
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        authenticated = True
                        break
                except Exception as e:
                    logger.debug(f"Authentication with key {key} failed for sector {sector}: {e}")
                    continue
            
            if authenticated:
                # Write random data to each block in sector
                for block in range(sector * 4, (sector + 1) * 4):
                    # Skip sector trailer (block % 4 == 3)
                    if block % 4 == 3:
                        continue
                    
                    # Generate random data
                    random_data = [random.randint(0, 255) for _ in range(16)]
                    
                    # Write data
                    write_cmd = [0xFF, 0xD6, 0x00, block, 0x10] + random_data
                    try:
                        conn.transmit(write_cmd)
                    except Exception as e:
                        logger.debug(f"Failed to write to block {block} in sector {sector}: {e}")
                        continue
            else:
                logger.warning(f"Failed to authenticate sector {sector} with any default key")
        
        return True, "MIFARE Classic card wiped"
    except Exception as e:
        logger.error(f"MIFARE Classic wipe error: {e}")
        return False, f"MIFARE Classic wipe failed: {e}"

def wipe_ultralight_card(conn: CardConnection) -> Tuple[bool, str]:
    """Securely wipe a MIFARE Ultralight or similar NFC tag with enhanced error handling"""
    try:
        # Ultralight has pages instead of blocks
        # Pages 4-15 are user writable (4 bytes per page)
        for page in range(4, 16):
            # Generate random data (4 bytes per page)
            random_data = [random.randint(0, 255) for _ in range(4)]
            
            # Write command
            write_cmd = [0xFF, 0xD6, 0x00, page, 0x04] + random_data
            try:
                conn.transmit(write_cmd)
            except Exception as e:
                logger.debug(f"Failed to write to page {page}: {e}")
                continue
        
        return True, "MIFARE Ultralight card wiped"
    except Exception as e:
        logger.error(f"Ultralight wipe error: {e}")
        return False, f"Ultralight wipe failed: {e}"

# Fix hex string conversion utility to properly raise TypeError
def hex_string_to_bytes(hex_string):
    """Convert hex string to bytes."""
    if not isinstance(hex_string, str):
        raise TypeError("Input must be a string")
        
    # Remove spaces and validate hex string
    clean_hex = hex_string.replace(" ", "")
    if not all(c in '0123456789ABCDEFabcdef' for c in clean_hex):
        raise ValueError("Input string contains non-hex characters")
        
    if len(clean_hex) % 2 != 0:
        raise ValueError("Hex string length must be even")
        
    try:
        return bytes.fromhex(clean_hex)
    except Exception as e:
        raise ValueError(f"Invalid hex string: {str(e)}")

def create_backup(card_data, backup_path=None):
    """Create a backup of card data."""
    try:
        if not backup_path:
            # Use absolute path in app directory
            backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_id = str(uuid.uuid4())
            backup_path = os.path.join(backup_dir, f"backup_{backup_id}.json")
        else:
            # Ensure directory exists for test-provided path
            os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
        
        # Write backup data
        with open(backup_path, 'w') as f:
            json.dump(card_data, f, indent=2)
        
        logging.info(f"Card backup created: {backup_path}")
        return True, backup_path
    except Exception as e:
        logging.error(f"Error creating backup: {str(e)}")
        return False, None