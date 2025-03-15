"""Card manager module."""
import os
import json
import asyncio
import logging
import shutil
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime


# Import the session_scope context manager and Card model from app/db.py
from app.db import session_scope, Card, Session

# Configuration & Constants
class Config:
    """Centralized configuration management."""
    
    # Default values (can be overridden by environment variables or config file)
    MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))
    RETRY_DELAY = float(os.environ.get("RETRY_DELAY", 0.5))  # seconds
    
    # Registry file configuration
    REGISTRY_SUBDIR = os.environ.get("REGISTRY_SUBDIR", "data")
    REGISTRY_FILENAME = os.environ.get("REGISTRY_FILENAME", "card_registry.json")
    BACKUP_SUBDIR = os.environ.get("BACKUP_SUBDIR", "backups")
    
    @classmethod
    def get_registry_path(cls) -> str:
        """Construct the registry path."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, cls.REGISTRY_SUBDIR, cls.REGISTRY_FILENAME)
    
    @classmethod
    def get_backup_dir(cls) -> str:
        """Construct the backup directory path."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, cls.BACKUP_SUBDIR)

# Configure logging (after Config is defined in case we want to configure logging via env vars)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('card_manager')

def handle_file_operation(filepath: str, operation: str = 'read', data: Optional[Any] = None):
    """Handles file read/write operations with comprehensive error handling."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if operation == 'read':
            with open(filepath, 'r') as f:
                return json.load(f)
        elif operation == 'write' and data is not None:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        elif operation == 'delete':
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")
            os.remove(filepath)
            return True
        else:
            raise ValueError(f"Unsupported file operation: {operation}")
    
    except FileNotFoundError as e:
        logger.warning(f"File operation failed: {e}")
        if operation == 'read':
            return {}  # Return empty dict for registry read if file not found
        else:
            return False
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {} if operation == 'read' else False
    except Exception as e:
        logger.error(f"File operation failed: {e}")
        return False

class CardError(Exception):
    """Custom exception for card-related errors."""
    pass

class CardManager:
    """
    Manages smart card interactions, including reader detection,
    card connection, and data retrieval.
    """
    def __init__(self):
        """Initializes the CardManager."""
        self.readers = []
        self.current_reader = None
        self.smart_card = None
        self.refresh_readers()
        logger.debug("CardManager initialized.")

    def refresh_readers(self):
        """Refreshes the list of available smart card readers."""
        try:
            self.readers = list_readers()  # Use list_readers from app/utils/smartcard.py
            if not self.readers:
                logger.warning("No smart card readers found.")
            else:
                logger.info(f"Found {len(self.readers)} smart card readers.")
        except Exception as e:
            logger.error(f"Error refreshing readers: {e}")
            self.readers = []

    def get_readers(self) -> List[str]:
        """Returns a list of available smart card readers."""
        return self.readers

    def set_reader(self, reader_name: str) -> None:
        """Sets the current smart card reader."""
        if reader_name in self.readers:
            self.current_reader = reader_name
            logger.info(f"Current reader set to: {reader_name}")
        else:
            logger.error(f"Reader not found: {reader_name}")
            raise ValueError(f"Reader not found: {reader_name}")

    def connect_card(self) -> None:
        """Connects to the smart card using the current reader."""
        try:
            if not self.current_reader:
                raise CardConnectionError("No reader selected.")

            self.smart_card = SmartCard(self.current_reader)
            self.smart_card.connect()
            logger.info(f"Connected to card on reader: {self.current_reader}")

        except Exception as e:
            logger.error(f"Error connecting to card: {e}")
            raise CardConnectionError(f"Error connecting to card: {e}")

    def disconnect_card(self) -> None:
        """Disconnects from the smart card."""
        try:
            if self.smart_card:
                self.smart_card.disconnect()
                self.smart_card = None
                logger.info("Disconnected from card.")
        except Exception as e:
            logger.error(f"Error disconnecting from card: {e}")
            raise SmartCardError(f"Error disconnecting from card: {e}")

    def get_atr(self) -> Optional[str]:
        """Gets the ATR (Answer To Reset) of the smart card."""
        try:
            if not self.smart_card:
                raise CardConnectionError("Not connected to card.")
            atr = self.smart_card.get_atr()
            logger.debug(f"ATR: {atr}")
            return atr
        except Exception as e:
            logger.error(f"Error getting ATR: {e}")
            raise CardDataError(f"Error getting ATR: {e}")

    def authenticate(self, pin: str) -> bool:
        """Authenticates with the smart card using the provided PIN."""
        try:
            if not self.smart_card:
                raise CardConnectionError("Not connected to card.")
            # Perform authentication logic here
            # This is a placeholder, replace with actual authentication
            if pin == "1234":
                logger.info("Authentication successful.")
                return True
            else:
                logger.warning("Authentication failed.")
                raise CardAuthenticationError("Invalid PIN.")
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            raise CardAuthenticationError(f"Error during authentication: {e}")

    async def handle_operation(self, operation_func, *args, **kwargs) -> Tuple[bool, str, Optional[Any]]:
        """Execute card operation with retry logic and error handling."""
        retries = 0
        self.last_operation = operation_func.__name__
        self.last_operation_time = datetime.now()
        
        while retries < Config.MAX_RETRIES:
            try:
                # Attempt operation
                result = await operation_func(*args, **kwargs)
                if isinstance(result, tuple):
                    success, message, *extra = result
                    extra_data = extra[0] if extra else None  # Safely extract extra data
                    return success, message, extra_data
                else:
                    return result, "Operation successful", None  # Adapt for non-tuple returns
                    
            except Exception as e:
                logger.error(f"Operation {self.last_operation} failed: {e}")
                retries += 1
                
                if retries < Config.MAX_RETRIES:
                    logger.info(f"Retrying operation (attempt {retries+1}/{Config.MAX_RETRIES})...")
                    await asyncio.sleep(Config.RETRY_DELAY)
                else:
                    return False, f"Operation failed after {Config.MAX_RETRIES} attempts: {str(e)}", None
        
        return False, "Operation failed with unknown error", None
    
    # def lifecycle_transition(self, from_states: List[CardStatus], to_state: CardStatus, 
    #                          operation_func, atr: str, *args, **kwargs) -> Tuple[bool, str, Optional[Any]]:
    #     """Handle lifecycle state transitions with validation."""
    #     try:
    #         with session_scope() as db:
    #             card = db.query(Card).filter(Card.atr == atr).first()
    #             if not card:
    #                 return False, "Card not registered", None
    # 
    #             current_status = CardStatus(card.status)
    #             if current_status not in from_states and not self.recovery_mode:
    #                 valid_states = [state.name for state in from_states]
    #                 return False, f"Invalid state transition. Card must be in one of these states: {', '.join(valid_states)}. Current state: {current_status.name}", None
    #             
    #             success, message, extra = self.handle_operation(operation_func, atr, *args, **kwargs)
    #             
    #             if success:
    #                 # Update card status in DB if operation was successful
    #                 card.status = to_state.value
    #                 db.commit()
    #                 return True, f"Transition to {to_state.name} successful: {message}", extra
    #             else:
    #                 return False, f"Transition to {to_state.name} failed: {message}", extra
    #     
    #     except Exception as e:
    #         logger.error(f"Lifecycle transition failed: {e}")
    #         return False, f"Lifecycle transition encountered an error: {str(e)}", None
    
    def register_new_card(self, atr: str, user_id: str) -> Tuple[bool, str]:
        """Register a new card."""
        try:
            with session_scope() as db:
                # Check if card already exists
                existing_card = db.query(Card).filter(Card.atr == atr).first()
                if existing_card:
                    return False, "Card already registered"

                # Create new card
                new_card = Card(atr=atr, user_id=user_id, status=CardStatus.REGISTERED.value)
                db.add(new_card)
                db.commit()
                return True, "Card registered successfully"
        except Exception as e:
            logger.error(f"Error registering card: {e}")
            return False, f"Error registering card: {str(e)}"
    
    def unregister_existing_card(self, atr: str) -> Tuple[bool, str]:
        """Unregister a card."""
        try:
            with session_scope() as db:
                # Check if card exists
                existing_card = db.query(Card).filter(Card.atr == atr).first()
                if not existing_card:
                    return False, "Card not registered"

                # Delete card
                db.delete(existing_card)
                db.commit()
                return True, "Card unregistered successfully"
        except Exception as e:
            logger.error(f"Error unregistering card: {e}")
            return False, f"Error unregistering card: {str(e)}"
    
    def activate_inactive_card(self, atr: str) -> Tuple[bool, str]:
        """Activate a card."""
        try:
            with session_scope() as db:
                # Check if card exists
                existing_card = db.query(Card).filter(Card.atr == atr).first()
                if not existing_card:
                    return False, "Card not registered"

                # Activate card
                existing_card.is_blocked = False
                existing_card.status = CardStatus.ACTIVE.value
                db.commit()
                return True, "Card activated successfully"
        except Exception as e:
            logger.error(f"Error activating card: {e}")
            return False, f"Error activating card: {str(e)}"
    
    def deactivate_active_card(self, atr: str) -> Tuple[bool, str]:
        """Deactivate a card."""
        try:
            with session_scope() as db:
                # Check if card exists
                existing_card = db.query(Card).filter(Card.atr == atr).first()
                if not existing_card:
                    return False, "Card not registered"

                # Deactivate card
                existing_card.is_blocked = True
                existing_card.status = CardStatus.INACTIVE.value
                db.commit()
                return True, "Card deactivated successfully"
        except Exception as e:
            logger.error(f"Error deactivating card: {e}")
            return False, f"Error deactivating card: {str(e)}"
    
    def block_active_card(self, atr: str) -> Tuple[bool, str]:
        """Block a card."""
        try:
            with session_scope() as db:
                # Check if card exists
                existing_card = db.query(Card).filter(Card.atr == atr).first()
                if not existing_card:
                    return False, "Card not registered"

                # Block card
                existing_card.is_blocked = True
                existing_card.status = CardStatus.BLOCKED.value
                db.commit()
                return True, "Card blocked successfully"
        except Exception as e:
            logger.error(f"Error blocking card: {e}")
            return False, f"Error blocking card: {str(e)}"
    
    def unblock_blocked_card(self, atr: str) -> Tuple[bool, str]:
        """Unblock a card."""
        try:
            with session_scope() as db:
                # Check if card exists
                existing_card = db.query(Card).filter(Card.atr == atr).first()
                if not existing_card:
                    return False, "Card not registered"

                # Unblock card
                existing_card.is_blocked = False
                existing_card.status = CardStatus.INACTIVE.value
                db.commit()
                return True, "Card unblocked successfully"
        except Exception as e:
            logger.error(f"Error unblocking card: {e}")
            return False, f"Error unblocking card: {str(e)}"
    
    def create_backup(self) -> Tuple[bool, str, Optional[str]]:
        """Create a backup of card data."""
        try:
            backup_dir = Config.get_backup_dir()
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f'card_db_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sqlite')

            # Get the database URL from app/db.py
            from app.db import DATABASE_URL

            # Copy the database file to the backup location
            shutil.copy2(DATABASE_URL.replace("sqlite:///", ""), backup_path)

            return True, "Database backed up successfully", backup_path
        except Exception as e:
            logger.error(f"Create backup failed: {e}")
            return False, f"Create backup encountered an error: {str(e)}", None
    
    def restore_from_backup(self, backup_path: str) -> Tuple[bool, str]:
        """Restore card data from a backup."""
        try:
            # Get the database URL from app/db.py
            from app.db import DATABASE_URL

            # Restore the database from the backup file
            shutil.copy2(backup_path, DATABASE_URL.replace("sqlite:///", ""))

            return True, "Database restored successfully"
        except Exception as e:
            logger.error(f"Restore from backup failed: {e}")
            return False, f"Restore from backup encountered an error: {str(e)}"
    
    def securely_dispose(self, atr: str) -> Tuple[bool, str]:
        """Securely dispose of a card (remove from database)."""
        try:
            with session_scope() as db:
                # Check if card exists
                existing_card = db.query(Card).filter(Card.atr == atr).first()
                if not existing_card:
                    return False, "Card not registered"

                # Delete card
                db.delete(existing_card)
                db.commit()
                return True, "Card disposed successfully"
        except Exception as e:
            logger.error(f"Error disposing card: {e}")
            return False, f"Error disposing card: {str(e)}"
    
    def get_device_card_compatibility(self) -> Dict:
        """Check compatibility between current reader and card."""
        card_info = {}  # Initialize card_info
        with safe_globals():
            conn, err = establish_connection()
            if err:
                return {
                    "compatible": False,
                    "error": err,
                    "reader_type": "Unknown",
                    "card_type": "Unknown"
                }
            
            try:
                atr = conn.getATR()
                atr_hex = ''.join([hex(b)[2:].upper().zfill(2) for b in atr])  # Convert ATR to hex string
                card_type = detect_card_type(atr_hex)
                # Ensure card_info is defined before accessing it
                reader_type = detect_reader_type(card_info.get("reader_name", "Unknown"))
                
                # Check for specific incompatibilities
                incompatible = False
                reason = ""
                
                # ACR122U has limited support for certain card types
                if reader_type == ACR122U_IDENTIFIER:
                    if card_type == "FELICA":
                        incompatible = True
                        reason = "ACR122U has limited support for FeliCa cards"
                    elif card_type == "NFC_TYPE_3":
                        incompatible = True
                        reason = "ACR122U has limited support for NFC Type 3 tags"
                
                return {
                    "compatible": not incompatible,
                    "reader_type": reader_type,
                    "card_type": card_type,
                    "incompatibility_reason": reason if incompatible else "",
                    "atr": atr_hex
                }
                
            except Exception as e:
                logger.error(f"Compatibility check failed: {e}")
                return {
                    "compatible": False,
                    "error": str(e),
                    "reader_type": "Unknown",
                    "card_type": "Unknown"
                }
            finally:
                close_connection(conn)
    
    def enable_recovery_mode(self) -> None:
        """Enable recovery mode to bypass state checks (for admin use only)."""
        if not self.recovery_mode:
            self.recovery_mode = True
            logger.warning("Recovery mode enabled! State transitions will not be validated.")
        else:
            logger.info("Recovery mode is already enabled.")
    
    def disable_recovery_mode(self) -> None:
        """Disable recovery mode."""
        if self.recovery_mode:
            self.recovery_mode = False
            logger.info("Recovery mode disabled. State transitions will be validated.")
        else:
            logger.info("Recovery mode is already disabled.")
    
    
    # def get_card_status_from_db(self, atr: str) -> Optional[CardStatus]:
    #     """Get the card status from the database."""
    #     try:
    #         with session_scope() as db:
    #             card = db.query(Card).filter(Card.atr == atr).first()
    #             if card:
    #                 return CardStatus(card.status)
    #             else:
    #                 return None
    #     except Exception as e:
    #         logger.error(f"Error getting card status from db: {e}")
    #         return None

    # def update_card_status_in_db(self, atr: str, status: CardStatus) -> bool:
    #     """Update the card status in the database."""
    #     try:
    #         with session_scope() as db:
    #             card = db.query(Card).filter(Card.atr == atr).first()
    #             if card:
    #                 card.status = status.value
    #                 db.commit()
    #                 return True
    #             else:
    #                 return False
    #     except Exception as e:
    #         logger.error(f"Error updating card status in db: {e}")
    #         return False

    # def is_card_registered(self, atr: str) -> bool:
    #     """Check if a card is registered in the database."""
    #     try:
    #         with session_scope() as db:
    #             existing_card = db.query(Card).filter(Card.atr == atr).first()
    #             return existing_card is not None
    #     except Exception as e:
    #         logger.error(f"Error checking card registration: {e}")
    #         return False

def backup_registry(backup_path=None):
    """Backup the card registry to a file."""
    if backup_path is None:
        backup_dir = Config.get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f'card_registry_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    
    result = handle_file_operation(backup_path, operation='write', data=get_card_registry())
    if result:
        return {"status": "success", "path": backup_path}
    else:
        return {"status": "error", "error": "Backup failed (see logs for details)"}

def delete_backup(backup_path):
    """Delete a backup file."""
    result = handle_file_operation(backup_path, operation='delete')
    if result:
        return {"status": "success"}
    else:
        return {"status": "error", "error": "Delete failed (see logs for details)"}

def get_card_registry():
    """Get the card registry, handling file not found gracefully."""
    registry_path = Config.get_registry_path()
    return handle_file_operation(registry_path, operation='read')

def save_card_registry(registry):
    """Save the card registry to file."""
    registry_path = Config.get_registry_path()
    return handle_file_operation(registry_path, operation='write', data=registry)

# Create a global instance
card_manager = CardManager()