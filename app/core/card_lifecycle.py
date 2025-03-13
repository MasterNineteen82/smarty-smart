"""
Card lifecycle management module for Smart Card and NFC Manager.
Handles card/device lifecycle state transitions with validation and edge case handling.
"""

import logging
from typing import List, Tuple, Optional, Any, Dict, Union
from enum import Enum, auto
from dataclasses import dataclass
from app.core.card_manager import CardManager
from app.core.nfc_manager import NFCManager
from app.utils.exceptions import CardError, NFCError, ConnectionTimeoutError, AuthenticationError

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """Defines the type of device being managed."""
    SMARTCARD = auto()
    NFC = auto()

class CardStatus(Enum):
    """Enumerates possible card/device statuses."""
    UNKNOWN = 0
    CONNECTED = 1
    UNREGISTERED = 2
    REGISTERED = 3
    ACTIVE = 4
    BLOCKED = 5
    DEACTIVATED = 6
    SUSPENDED = 7  # Added for temporary suspension
    EXPIRED = 8    # Added for expired cards/tokens

@dataclass
class DeviceInfo:
    """Store device information."""
    device_id: str  # ATR for cards, UID for NFC
    device_type: DeviceType
    status: CardStatus
    user_id: Optional[str] = None
    metadata: Optional[Dict] = None

class DeviceLifecycleManager:
    """
    Manages card and NFC device lifecycle state transitions with validation and edge case handling.
    """

    def __init__(self, card_manager: CardManager, nfc_manager: Optional[NFCManager] = None):
        """
        Initializes the DeviceLifecycleManager with required managers.

        Args:
            card_manager: An instance of CardManager.
            nfc_manager: An optional instance of NFCManager.
        """
        self.card_manager = card_manager
        self.nfc_manager = nfc_manager
        self.recovery_mode = False  # To bypass state checks (for admin use only)
        self._timeout = 30  # Default timeout in seconds

    @property
    def timeout(self) -> int:
        """Get the current operation timeout."""
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        """Set the operation timeout."""
        if value <= 0:
            raise ValueError("Timeout must be positive")
        self._timeout = value

    def get_device_status(self, device_id: str, device_type: DeviceType) -> CardStatus:
        """
        Get the current status of a device.
        
        Args:
            device_id: The ID of the device (ATR for cards, UID for NFC)
            device_type: Type of the device (SMARTCARD or NFC)
            
        Returns:
            The current CardStatus of the device
        
        Raises:
            CardError: If there's an issue with a smartcard
            NFCError: If there's an issue with an NFC device
            ConnectionTimeoutError: If the operation times out
        """
        try:
            if device_type == DeviceType.SMARTCARD:
                return self.card_manager.get_card_status(device_id)
            elif device_type == DeviceType.NFC:
                if not self.nfc_manager:
                    raise NFCError("NFC manager not initialized")
                return self.nfc_manager.get_device_status(device_id)
            else:
                raise ValueError(f"Unsupported device type: {device_type}")
        except TimeoutError:
            raise ConnectionTimeoutError(f"Timed out while getting status for {device_type.name} {device_id}")
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            raise

    def handle_operation(self, operation_func, *args, **kwargs) -> Tuple[bool, str, Optional[Any]]:
        """
        Handles operations with retry logic and timeout.

        Args:
            operation_func: The function to execute.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            A tuple containing:
                - A boolean indicating success or failure.
                - A message describing the outcome.
                - Optional extra data.
        """
        max_retries = kwargs.pop('max_retries', 1)
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                result = operation_func(*args, **kwargs)
                return True, "Operation completed successfully", result
            except (CardError, NFCError, ConnectionTimeoutError) as e:
                logger.warning(f"Operation attempt {retry_count + 1} failed: {e}")
                if retry_count < max_retries:
                    retry_count += 1
                    continue
                return False, f"Operation failed after {max_retries + 1} attempts: {e}", None
            except Exception as e:
                logger.error(f"Unexpected error during operation: {e}")
                return False, f"Unexpected error: {e}", None

    def lifecycle_transition(self, device_id: str, device_type: DeviceType,
                             from_states: List[CardStatus], to_state: CardStatus,
                             operation_func, *args, **kwargs) -> Tuple[bool, str, Optional[Any]]:
        """
        Handles lifecycle state transitions with validation and edge case handling.

        Args:
            device_id: The ID of the device (ATR for cards, UID for NFC)
            device_type: Type of the device (SMARTCARD or NFC)
            from_states: A list of valid states to transition from.
            to_state: The state to transition to.
            operation_func: The function to execute.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            A tuple containing:
                - A boolean indicating success or failure.
                - A message describing the outcome.
                - Optional extra data.
        """
        try:
            current_status = self.get_device_status(device_id, device_type)
            
            if current_status not in from_states and not self.recovery_mode:
                valid_states = [state.name for state in from_states]
                return False, f"Invalid state transition. Device must be in one of these states: {', '.join(valid_states)}", None

            success, message, extra = self.handle_operation(operation_func, *args, **kwargs)

            if success:
                device_type_name = "card" if device_type == DeviceType.SMARTCARD else "NFC device"
                logger.info(f"Transition of {device_type_name} {device_id} to {to_state.name} successful: {message}")
                return True, f"Transition to {to_state.name} successful: {message}", extra
            else:
                return False, f"Transition to {to_state.name} failed: {message}", None
                
        except ConnectionTimeoutError as e:
            return False, f"Connection timed out: {e}", None
        except (CardError, NFCError) as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Unexpected error in lifecycle transition: {e}")
            return False, f"Unexpected error in lifecycle transition: {e}", None

    async def register_device(self, device_type: str, device_id: str, user_id: str) -> bool:
        """
        Registers a new smart card or NFC device.

        Args:
            device_type: The type of device (e.g., "smartcard", "nfc").
            device_id: The unique identifier of the device.
            user_id: The ID of the user who owns the device.

        Returns:
            True if the device was registered successfully, False otherwise.
        """
        try:
            # Simulate registering a device
            logger.info(f"Successfully registered device: {device_type} - {device_id} - {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return False

    def block_device(self, device_id: str, device_type: DeviceType, reason: str = None) -> Tuple[bool, str]:
        """
        Blocks an existing device with edge case handling.

        Args:
            device_id: The ID of the device to block.
            device_type: Type of the device (SMARTCARD or NFC)
            reason: Optional reason for blocking

        Returns:
            A tuple containing:
                - A boolean indicating success or failure.
                - A message describing the outcome.
        """
        try:
            if device_type == DeviceType.SMARTCARD:
                operation = self.card_manager.block_card
            else:
                if not self.nfc_manager:
                    return False, "NFC manager not initialized"
                operation = self.nfc_manager.block_device
            
            success, message, _ = self.lifecycle_transition(
                device_id, device_type,
                [CardStatus.ACTIVE, CardStatus.REGISTERED],
                CardStatus.BLOCKED,
                operation, device_id, reason=reason
            )
            return success, message
        except Exception as e:
            logger.error(f"Error blocking device: {e}")
            return False, f"Error blocking device: {e}"

    def activate_device(self, device_id: str, device_type: DeviceType) -> Tuple[bool, str]:
        """
        Activates an existing device with edge case handling.

        Args:
            device_id: The ID of the device to activate.
            device_type: Type of the device (SMARTCARD or NFC)

        Returns:
            A tuple containing:
                - A boolean indicating success or failure.
                - A message describing the outcome.
        """
        try:
            if device_type == DeviceType.SMARTCARD:
                operation = self.card_manager.activate_card
            else:
                if not self.nfc_manager:
                    return False, "NFC manager not initialized"
                operation = self.nfc_manager.activate_device
            
            success, message, _ = self.lifecycle_transition(
                device_id, device_type,
                [CardStatus.BLOCKED, CardStatus.REGISTERED, CardStatus.DEACTIVATED, CardStatus.SUSPENDED],
                CardStatus.ACTIVE,
                operation, device_id
            )
            return success, message
        except Exception as e:
            logger.error(f"Error activating device: {e}")
            return False, f"Error activating device: {e}"

    def deactivate_device(self, device_id: str, device_type: DeviceType) -> Tuple[bool, str]:
        """
        Deactivates an existing device with edge case handling.

        Args:
            device_id: The ID of the device to deactivate.
            device_type: Type of the device (SMARTCARD or NFC)

        Returns:
            A tuple containing:
                - A boolean indicating success or failure.
                - A message describing the outcome.
        """
        try:
            if device_type == DeviceType.SMARTCARD:
                operation = self.card_manager.deactivate_card
            else:
                if not self.nfc_manager:
                    return False, "NFC manager not initialized"
                operation = self.nfc_manager.deactivate_device
            
            success, message, _ = self.lifecycle_transition(
                device_id, device_type,
                [CardStatus.ACTIVE, CardStatus.BLOCKED, CardStatus.SUSPENDED],
                CardStatus.DEACTIVATED,
                operation, device_id
            )
            return success, message
        except Exception as e:
            logger.error(f"Error deactivating device: {e}")
            return False, f"Error deactivating device: {e}"

    def suspend_device(self, device_id: str, device_type: DeviceType, 
                       duration_days: int = None) -> Tuple[bool, str]:
        """
        Temporarily suspends a device.

        Args:
            device_id: The ID of the device to suspend.
            device_type: Type of the device (SMARTCARD or NFC)
            duration_days: Optional number of days to suspend the device

        Returns:
            A tuple containing:
                - A boolean indicating success or failure.
                - A message describing the outcome.
        """
        try:
            if device_type == DeviceType.SMARTCARD:
                operation = self.card_manager.suspend_card
            else:
                if not self.nfc_manager:
                    return False, "NFC manager not initialized"
                operation = self.nfc_manager.suspend_device
            
            success, message, _ = self.lifecycle_transition(
                device_id, device_type,
                [CardStatus.ACTIVE, CardStatus.REGISTERED],
                CardStatus.SUSPENDED,
                operation, device_id, duration_days=duration_days
            )
            return success, message
        except Exception as e:
            logger.error(f"Error suspending device: {e}")
            return False, f"Error suspending device: {e}"

# Create singleton instance
device_lifecycle_manager = DeviceLifecycleManager(CardManager())