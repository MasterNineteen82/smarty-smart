"""Card manager module."""
import os
import json
import asyncio
import logging
import shutil
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime

from app.db import session_scope, Card, Session

# Configuration & Constants
class Config:
    """Centralized configuration management."""
    MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))
    RETRY_DELAY = float(os.environ.get("RETRY_DELAY", 0.5))
    REGISTRY_SUBDIR = os.environ.get("REGISTRY_SUBDIR", "data")
    REGISTRY_FILENAME = os.environ.get("REGISTRY_FILENAME", "card_registry.json")
    BACKUP_SUBDIR = os.environ.get("BACKUP_SUBDIR", "backups")
    
    @classmethod
    def get_registry_path(cls) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, cls.REGISTRY_SUBDIR, cls.REGISTRY_FILENAME)
    
    @classmethod
    def get_backup_dir(cls) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, cls.BACKUP_SUBDIR)

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
        return {} if operation == 'read' else False
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
    """Manages smart card interactions."""
    def __init__(self):
        self.readers = []
        self.current_reader = None
        self.smart_card = None
        self.recovery_mode = False
        self.refresh_readers()
        logger.debug("CardManager initialized.")

    def refresh_readers(self):
        try:
            self.readers = list_readers()
            logger.info(f"Found {len(self.readers)} smart card readers." if self.readers else "No smart card readers found.")
        except Exception as e:
            logger.error(f"Error refreshing readers: {e}")
            self.readers = []

    def get_readers(self) -> List[str]:
        return self.readers

    def set_reader(self, reader_name: str) -> None:
        if reader_name in self.readers:
            self.current_reader = reader_name
            logger.info(f"Current reader set to: {reader_name}")
        else:
            logger.error(f"Reader not found: {reader_name}")
            raise ValueError(f"Reader not found: {reader_name}")

    def connect_card(self) -> None:
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
        try:
            if self.smart_card:
                self.smart_card.disconnect()
                self.smart_card = None
                logger.info("Disconnected from card.")
        except Exception as e:
            logger.error(f"Error disconnecting from card: {e}")
            raise SmartCardError(f"Error disconnecting from card: {e}")

    def get_atr(self) -> Optional[str]:
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
        try:
            if not self.smart_card:
                raise CardConnectionError("Not connected to card.")
            # Placeholder authentication
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
                result = await operation_func(*args, **kwargs)
                if isinstance(result, tuple):
                    success, message, *extra = result
                    extra_data = extra[0] if extra else None
                    return success, message, extra_data
                else:
                    return result, "Operation successful", None
                    
            except Exception as e:
                logger.error(f"Operation {self.last_operation} failed: {e}")
                retries += 1
                
                if retries < Config.MAX_RETRIES:
                    logger.info(f"Retrying operation (attempt {retries+1}/{Config.MAX_RETRIES})...")
                    await asyncio.sleep(Config.RETRY_DELAY)
                else:
                    return False, f"Operation failed after {Config.MAX_RETRIES} attempts: {str(e)}", None
        
        return False, "Operation failed with unknown error", None
    
    def _db_operation(self, operation: Callable, atr: str, **kwargs) -> Tuple[bool, str]:
        """Generic database operation handler for card operations."""
        try:
            with session_scope() as db:
                # Check if card exists for most operations
                existing_card = db.query(Card).filter(Card.atr == atr).first()
                
                # Call the specific operation function
                return operation(db, existing_card, **kwargs)
                
        except Exception as e:
            operation_name = operation.__name__
            logger.error(f"Error in {operation_name}: {e}")
            return False, f"Error in {operation_name}: {str(e)}"
    
    def register_new_card(self, atr: str, user_id: str) -> Tuple[bool, str]:
        """Register a new card."""
        def operation(db, existing_card, **kwargs):
            if existing_card:
                return False, "Card already registered"
            new_card = Card(atr=atr, user_id=kwargs['user_id'], status=CardStatus.REGISTERED.value)
            db.add(new_card)
            db.commit()
            return True, "Card registered successfully"
            
        return self._db_operation(operation, atr, user_id=user_id)
    
    def unregister_existing_card(self, atr: str) -> Tuple[bool, str]:
        """Unregister a card."""
        def operation(db, existing_card, **kwargs):
            if not existing_card:
                return False, "Card not registered"
            db.delete(existing_card)
            db.commit()
            return True, "Card unregistered successfully"
            
        return self._db_operation(operation, atr)
    
    # Other card operations follow the same pattern...
    
    def create_backup(self) -> Tuple[bool, str, Optional[str]]:
        """Create a backup of card data."""
        try:
            backup_dir = Config.get_backup_dir()
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f'card_db_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sqlite')
            from app.db import DATABASE_URL
            shutil.copy2(DATABASE_URL.replace("sqlite:///", ""), backup_path)
            return True, "Database backed up successfully", backup_path
        except Exception as e:
            logger.error(f"Create backup failed: {e}")
            return False, f"Create backup encountered an error: {str(e)}", None
    
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

# Registry operations
def backup_registry(backup_path=None):
    """Backup the card registry to a file."""
    if backup_path is None:
        backup_dir = Config.get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f'card_registry_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    
    result = handle_file_operation(backup_path, operation='write', data=get_card_registry())
    return {"status": "success", "path": backup_path} if result else {"status": "error", "error": "Backup failed"}

def get_card_registry():
    """Get the card registry, handling file not found gracefully."""
    return handle_file_operation(Config.get_registry_path(), operation='read')

# Create a global instance
card_manager = CardManager()
