import os
import json
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from card_utils import (
    establish_connection, close_connection, safe_globals,
    detect_card_type, detect_reader_type, is_card_registered,
    register_card, unregister_card, activate_card, deactivate_card,
    block_card, unblock_card, backup_card_data, restore_card_data,
    secure_dispose_card, card_info, card_status, CardStatus,
    CHERRY_ST_IDENTIFIER, ACR122U_IDENTIFIER
)
from smartcard.util import toHexString

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('card_manager')

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

class CardManager:
    """High-level card management class handling lifecycle operations with better error handling"""
    
    def __init__(self):
        self.last_operation = None
        self.last_operation_time = None
        self.recovery_mode = False
    
    def handle_operation(self, operation_func, *args, **kwargs) -> Tuple[bool, str, Optional[Any]]:
        """Execute card operation with retry logic and error handling"""
        retries = 0
        self.last_operation = operation_func.__name__
        self.last_operation_time = datetime.now()
        
        while retries < MAX_RETRIES:
            try:
                # Attempt operation
                if "backup_card" in self.last_operation:
                    success, message, extra = operation_func(*args, **kwargs)
                    return success, message, extra
                else:
                    success, message = operation_func(*args, **kwargs)
                    return success, message, None
                    
            except Exception as e:
                logger.error(f"Operation {self.last_operation} failed: {e}")
                retries += 1
                
                if retries < MAX_RETRIES:
                    logger.info(f"Retrying operation (attempt {retries+1}/{MAX_RETRIES})...")
                    time.sleep(RETRY_DELAY)
                else:
                    return False, f"Operation failed after {MAX_RETRIES} attempts: {str(e)}", None
        
        return False, "Operation failed with unknown error", None
    
    def lifecycle_transition(self, from_states: List[CardStatus], to_state: CardStatus, 
                             operation_func, *args, **kwargs) -> Tuple[bool, str, Optional[Any]]:
        """Handle lifecycle state transitions with validation and edge case handling"""
        try:
            current_status = card_status()
            if current_status not in from_states and not self.recovery_mode:
                valid_states = [state.name for state in from_states]
                return False, f"Invalid state transition. Card must be in one of these states: {', '.join(valid_states)}", None
            
            success, message, extra = self.handle_operation(operation_func, *args, **kwargs)
            
            if success:
                # Update card status if operation was successful
                card_status(to_state)
                return True, f"Transition to {to_state.name} successful: {message}", extra
            else:
                return False, f"Transition to {to_state.name} failed: {message}", extra
        
        except Exception as e:
            logger.error(f"Lifecycle transition failed: {e}")
            return False, f"Lifecycle transition encountered an error: {str(e)}", None
    def register_new_card(self, name: str, user_id: str, 
                         custom_data: Optional[Dict] = None) -> Tuple[bool, str]:
        """Register a new card with edge case handling"""
        try:
            if is_card_registered():
                return False, "Card is already registered"
            
            success, message, _ = self.lifecycle_transition(
                [CardStatus.UNKNOWN, CardStatus.CONNECTED, CardStatus.UNREGISTERED],
                CardStatus.REGISTERED,
                register_card, name, user_id, custom_data
            )
            return success, message
        except Exception as e:
            logger.error(f"Register new card failed: {e}")
            return False, f"Register new card encountered an error: {str(e)}"
    
    def unregister_existing_card(self) -> Tuple[bool, str]:
        """Unregister a card with edge case handling"""
        try:
            if not is_card_registered():
                return False, "Card is not registered"
            
            success, message, _ = self.lifecycle_transition(
                [CardStatus.REGISTERED, CardStatus.ACTIVE, CardStatus.INACTIVE],
                CardStatus.UNREGISTERED,
                unregister_card
            )
            return success, message
        except Exception as e:
            logger.error(f"Unregister existing card failed: {e}")
            return False, f"Unregister existing card encountered an error: {str(e)}"
    
    def activate_inactive_card(self) -> Tuple[bool, str]:
        """Activate a card with edge case handling"""
        try:
            if not is_card_registered():
                return False, "Card is not registered"
            
            success, message, _ = self.lifecycle_transition(
                [CardStatus.REGISTERED, CardStatus.INACTIVE],
                CardStatus.ACTIVE,
                activate_card
            )
            return success, message
        except Exception as e:
            logger.error(f"Activate inactive card failed: {e}")
            return False, f"Activate inactive card encountered an error: {str(e)}"
    
    def deactivate_active_card(self) -> Tuple[bool, str]:
        """Deactivate a card with edge case handling"""
        try:
            if not is_card_registered():
                return False, "Card is not registered"
            
            success, message, _ = self.lifecycle_transition(
                [CardStatus.ACTIVE, CardStatus.REGISTERED],
                CardStatus.INACTIVE,
                deactivate_card
            )
            return success, message
        except Exception as e:
            logger.error(f"Deactivate active card failed: {e}")
            return False, f"Deactivate active card encountered an error: {str(e)}"
    
    def block_active_card(self) -> Tuple[bool, str]:
        """Block a card with edge case handling"""
        try:
            if not is_card_registered():
                return False, "Card is not registered"
            
            success, message, _ = self.lifecycle_transition(
                [CardStatus.ACTIVE, CardStatus.INACTIVE, CardStatus.REGISTERED],
                CardStatus.BLOCKED,
                block_card
            )
            return success, message
        except Exception as e:
            logger.error(f"Block active card failed: {e}")
            return False, f"Block active card encountered an error: {str(e)}"
    
    def unblock_blocked_card(self) -> Tuple[bool, str]:
        """Unblock a card with edge case handling"""
        try:
            if not is_card_registered():
                return False, "Card is not registered"
            
            success, message, _ = self.lifecycle_transition(
                [CardStatus.BLOCKED],
                CardStatus.INACTIVE,
                unblock_card
            )
            return success, message
        except Exception as e:
            logger.error(f"Unblock blocked card failed: {e}")
            return False, f"Unblock blocked card encountered an error: {str(e)}"
    
    def create_backup(self) -> Tuple[bool, str, Optional[str]]:
        """Create a backup of card data with edge case handling"""
        try:
            if not is_card_registered():
                return False, "Card is not registered", None
            
            success, message, backup_id = self.handle_operation(backup_card_data)
            return success, message, backup_id
        except Exception as e:
            logger.error(f"Create backup failed: {e}")
            return False, f"Create backup encountered an error: {str(e)}", None
    
    def restore_from_backup(self, backup_id: str) -> Tuple[bool, str]:
        """Restore card from a backup with edge case handling"""
        try:
            if not is_card_registered():
                return False, "Card is not registered"
            
            success, message, _ = self.handle_operation(restore_card_data, backup_id)
            return success, message
        except Exception as e:
            logger.error(f"Restore from backup failed: {e}")
            return False, f"Restore from backup encountered an error: {str(e)}"
    
    def securely_dispose(self) -> Tuple[bool, str]:
        """Securely dispose of a card with edge case handling"""
        try:
            if not is_card_registered():
                return False, "Card is not registered"
            
            success, message, _ = self.lifecycle_transition(
                [CardStatus.ACTIVE, CardStatus.INACTIVE, CardStatus.BLOCKED, CardStatus.REGISTERED, CardStatus.UNREGISTERED],
                CardStatus.DISPOSED,
                secure_dispose_card
            )
            return success, message
        except Exception as e:
            logger.error(f"Securely dispose card failed: {e}")
            return False, f"Securely dispose card encountered an error: {str(e)}"
    
    def get_device_card_compatibility(self) -> Dict:
        """Check compatibility between current reader and card"""
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
                atr = toHexString(conn.getATR())
                card_type = detect_card_type(atr)
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
                    "atr": atr
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
        """Enable recovery mode to bypass state checks (for admin use only)"""
        if not self.recovery_mode:
            self.recovery_mode = True
            logger.warning("Recovery mode enabled! State transitions will not be validated.")
        else:
            logger.info("Recovery mode is already enabled.")
    
    def disable_recovery_mode(self) -> None:
        """Disable recovery mode"""
        if self.recovery_mode:
            self.recovery_mode = False
            logger.info("Recovery mode disabled. State transitions will be validated.")
        else:
            logger.info("Recovery mode is already disabled.")


# Create a global instance
card_manager = CardManager()