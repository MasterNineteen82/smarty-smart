"""
NFC module for the Smartcard Manager application.

This module handles NFC-related functionality, such as reading and writing NFC card data.
"""

from typing import Dict, Any, Optional, Union
import logging
import time
import nfc
from enum import Enum

logger = logging.getLogger(__name__)

class NFCErrorCode(Enum):
    """Error codes for NFC operations to facilitate frontend error handling."""
    NO_DEVICE = 1
    NO_TAG = 2
    COMMUNICATION_ERROR = 3
    WRITE_ERROR = 4
    READ_ERROR = 5
    TIMEOUT = 6
    INVALID_PARAM = 7
    UNKNOWN_ERROR = 99

class NFCError(Exception):
    """Custom exception for NFC related errors with structured information."""
    def __init__(self, message: str, error_code: NFCErrorCode = NFCErrorCode.UNKNOWN_ERROR):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class NFCManager:
    """
    Handles NFC-related functionality, such as reading and writing NFC card data.
    
    Attributes:
        device_path (str): Path to the NFC device
        timeout (float): Default timeout for NFC operations in seconds
        max_retries (int): Maximum number of retries for failed operations
    """

    def __init__(self, device_path: str = 'usb', timeout: float = 2.0, max_retries: int = 3):
        self.device_path = device_path
        self.timeout = timeout
        self.max_retries = max_retries
        
    def _connect_to_device(self) -> nfc.ContactlessFrontend:
        """
        Establishes connection with the NFC device.
        
        Returns:
            A ContactlessFrontend object connected to the NFC reader.
            
        Raises:
            NFCError: If no NFC device is found.
        """
        try:
            clf = nfc.ContactlessFrontend(self.device_path)
            return clf
        except Exception as e:
            logger.error(f"Failed to connect to NFC device: {e}")
            raise NFCError(f"No NFC device found: {e}", NFCErrorCode.NO_DEVICE)

    def read_nfc_data(self, card_id: int, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Reads data from an NFC card.
        
        Args:
            card_id: Identifier for the card
            timeout: Operation timeout in seconds (overrides default if provided)
            
        Returns:
            Dictionary containing the card data with standard fields:
            {
                "success": True/False,
                "card_id": int,
                "type": "nfc",
                "tag_type": str,
                "data": Any,
                "timestamp": float
            }
            
        Raises:
            NFCError: With appropriate error code if operation fails
        """
        if not isinstance(card_id, int) or card_id <= 0:
            raise NFCError(f"Invalid card ID: {card_id}", NFCErrorCode.INVALID_PARAM)
            
        timeout = timeout or self.timeout
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                logger.info(f"Attempting to read data from NFC card {card_id} (try {retries+1}/{self.max_retries+1})")
                with self._connect_to_device() as clf:
                    # Set timeout for tag discovery
                    tag = clf.connect(rdwr={'on-connect': lambda tag: tag.dump()}, 
                                     terminate=lambda: time.time() > time.time() + timeout)

                    if not tag:
                        raise NFCError("No NFC tag detected", NFCErrorCode.NO_TAG)

                    # Extract relevant data from the tag
                    card_data = {
                        "success": True,
                        "card_id": card_id,
                        "type": "nfc",
                        "tag_type": str(type(tag).__name__),
                        "data": self._extract_tag_data(tag),
                        "timestamp": time.time()
                    }
                    logger.info(f"Successfully read data from NFC card {card_id}")
                    return card_data

            except NFCError as e:
                last_error = e
                logger.warning(f"NFCError during read attempt {retries+1}: {e}")
            except nfc.clf.CommunicationError as e:
                last_error = NFCError(f"Communication error with NFC card: {e}", 
                                     NFCErrorCode.COMMUNICATION_ERROR)
                logger.error(f"Communication error during NFC read (try {retries+1}): {e}")
            except Exception as e:
                last_error = NFCError(f"Unexpected error reading NFC card: {e}", 
                                     NFCErrorCode.READ_ERROR)
                logger.exception(f"Unexpected error reading NFC card data (try {retries+1}): {e}")
            
            retries += 1
            if retries <= self.max_retries:
                time.sleep(0.5)  # Short delay between retries
        
        # All retries failed
        raise last_error or NFCError("Failed to read NFC card after multiple attempts", 
                                    NFCErrorCode.READ_ERROR)

    def _extract_tag_data(self, tag) -> Dict[str, Any]:
        """Extract and normalize data from different tag types"""
        try:
            # Handle different tag types appropriately
            if hasattr(tag, 'ndef') and tag.ndef:
                return {"ndef_records": [record.text for record in tag.ndef.records]}
            
            # For Mifare cards
            if hasattr(tag, 'dump'):
                return {"raw_dump": tag.dump()}
                
            # Fallback for unknown tag types
            return {"raw": str(tag)}
        except Exception as e:
            logger.warning(f"Error extracting tag data: {e}")
            return {"error": str(e), "raw": str(tag)}

    def write_nfc_data(self, card_id: int, data: Union[str, Dict[str, Any]], 
                      timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Writes data to an NFC card.

        Args:
            card_id: Identifier for the card
            data: The data to write to the NFC card (string or dictionary)
            timeout: Operation timeout in seconds (overrides default if provided)

        Returns:
            Dictionary with result information:
            {
                "success": True/False,
                "card_id": int,
                "message": str,
                "timestamp": float
            }
            
        Raises:
            NFCError: With appropriate error code if operation fails
        """
        if not isinstance(card_id, int) or card_id <= 0:
            raise NFCError(f"Invalid card ID: {card_id}", NFCErrorCode.INVALID_PARAM)
            
        if not data:
            raise NFCError("No data provided for writing", NFCErrorCode.INVALID_PARAM)
            
        timeout = timeout or self.timeout
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                logger.info(f"Attempting to write data to NFC card {card_id} (try {retries+1}/{self.max_retries+1})")
                with self._connect_to_device() as clf:
                    # Wait for a tag and connect to it
                    tag = clf.connect(rdwr={'on-connect': lambda tag: False},
                                    terminate=lambda: time.time() > time.time() + timeout)

                    if not tag:
                        raise NFCError("No NFC tag detected", NFCErrorCode.NO_TAG)

                    # Write data to the tag based on tag type
                    # TODO: Implement actual writing logic based on tag type
                    logger.warning("NFC write functionality is a placeholder. Implement actual writing logic.")
                    logger.info(f"Data to be written: {data}")
                    
                    # Simulating successful write for placeholder
                    result = {
                        "success": True,
                        "card_id": card_id,
                        "message": f"Data written to NFC card {card_id} successfully (placeholder)",
                        "timestamp": time.time()
                    }
                    return result

            except NFCError as e:
                last_error = e
                logger.warning(f"NFCError during write attempt {retries+1}: {e}")
            except nfc.clf.CommunicationError as e:
                last_error = NFCError(f"Communication error with NFC card: {e}", 
                                     NFCErrorCode.COMMUNICATION_ERROR)
                logger.error(f"Communication error during NFC write (try {retries+1}): {e}")
            except Exception as e:
                last_error = NFCError(f"Unexpected error writing to NFC card: {e}", 
                                     NFCErrorCode.WRITE_ERROR)
                logger.exception(f"Unexpected error writing NFC card data (try {retries+1}): {e}")
            
            retries += 1
            if retries <= self.max_retries:
                time.sleep(0.5)  # Short delay between retries
        
        # All retries failed
        raise last_error or NFCError("Failed to write to NFC card after multiple attempts", 
                                   NFCErrorCode.WRITE_ERROR)

# Singleton instance
nfc_manager = NFCManager()