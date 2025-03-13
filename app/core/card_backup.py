"""
Card backup and restore module for Smart Card Manager.
Handles card data backup and restore operations for both smartcards and NFC devices.
"""

import logging
import os
import json
import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from pathlib import Path
from app.core.card_manager import CardManager
from app.utils.exceptions import CardError, BackupError, RestoreError

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """Enum for supported device types."""
    SMARTCARD = "smartcard"
    NFC = "nfc"

class CardBackupManager:
    """
    Handles card data backup and restore operations for both smartcards and NFC devices.
    """

    def __init__(self, card_manager: CardManager, backup_dir: str = "backups"):
        """
        Initializes the CardBackupManager with a CardManager instance and a backup directory.

        Args:
            card_manager: An instance of CardManager.
            backup_dir: The directory to store backup files.
        
        Raises:
            BackupError: If the backup directory cannot be created.
        """
        self.card_manager = card_manager
        self.backup_dir = backup_dir
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except PermissionError as e:
            logger.error(f"Permission denied when creating backup directory: {e}")
            raise BackupError(f"Cannot create backup directory: Permission denied")
        except OSError as e:
            logger.error(f"OS error when creating backup directory: {e}")
            raise BackupError(f"Cannot create backup directory: {str(e)}")

    def backup_card_data(self, 
                         identifier: str, 
                         device_type: DeviceType = DeviceType.SMARTCARD, 
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Backs up card data to a JSON file.

        Args:
            identifier: The ATR or UID of the card/device to backup.
            device_type: Type of device (SMARTCARD or NFC).
            metadata: Additional metadata to store with the backup.

        Returns:
            The path to the backup file.

        Raises:
            CardError: If the card/device cannot be found.
            BackupError: If an error occurs during backup process.
        """
        if not identifier:
            raise CardError("Card/device identifier cannot be empty")

        try:
            # Implement logic to fetch card data based on device type
            card_data: Dict[str, Any] = {
                "identifier": identifier,
                "device_type": device_type.value,
                "backup_date": datetime.datetime.now().isoformat(),
                "version": "1.0"
            }
            
            if metadata:
                card_data["metadata"] = metadata

            # Get actual card data based on device type
            if device_type == DeviceType.SMARTCARD:
                # Get smartcard data
                card_data["data"] = self._get_smartcard_data(identifier)
            elif device_type == DeviceType.NFC:
                # Get NFC data
                card_data["data"] = self._get_nfc_data(identifier)
                
            # Create filename with timestamp for uniqueness
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{device_type.value}_{identifier.replace(':', '_')}_{timestamp}.json"
            backup_file = os.path.join(self.backup_dir, filename)
            
            with open(backup_file, 'w') as f:
                json.dump(card_data, f, indent=4)

            logger.info(f"{device_type.value.capitalize()} data for {identifier} backed up to {backup_file}")
            return backup_file
            
        except CardError as e:
            # Re-raise card errors
            raise
        except PermissionError as e:
            logger.error(f"Permission denied when writing backup file: {e}")
            raise BackupError(f"Cannot write backup file: Permission denied")
        except Exception as e:
            logger.error(f"Error backing up card data: {e}")
            raise BackupError(f"Error backing up card data: {str(e)}")

    def restore_card_data(self, backup_file: str) -> Dict[str, Any]:
        """
        Restores card data from a JSON file.

        Args:
            backup_file: The path to the backup file.

        Returns:
            A dictionary containing restored card data and metadata.

        Raises:
            RestoreError: If the backup file cannot be found or is invalid.
            CardError: If an error occurs during the restore operation.
        """
        if not os.path.isfile(backup_file):
            raise RestoreError(f"Backup file not found: {backup_file}")
        
        try:
            with open(backup_file, 'r') as f:
                card_data = json.load(f)

            # Validate the backup file format
            self._validate_backup_data(card_data)
            
            identifier = card_data.get("identifier")
            device_type = card_data.get("device_type")
            
            # Apply the restore based on device type
            if device_type == DeviceType.SMARTCARD.value:
                result = self._restore_smartcard_data(identifier, card_data.get("data", {}))
            elif device_type == DeviceType.NFC.value:
                result = self._restore_nfc_data(identifier, card_data.get("data", {}))
            else:
                raise RestoreError(f"Unsupported device type: {device_type}")
                
            logger.info(f"{device_type.capitalize()} data for {identifier} restored from {backup_file}")
            return {
                "identifier": identifier,
                "device_type": device_type,
                "restore_date": datetime.datetime.now().isoformat(),
                "backup_date": card_data.get("backup_date"),
                "result": result
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in backup file: {e}")
            raise RestoreError(f"Invalid backup file format: {str(e)}")
        except (KeyError, ValueError) as e:
            logger.error(f"Malformed backup data: {e}")
            raise RestoreError(f"Malformed backup data: {str(e)}")
        except CardError as e:
            # Re-raise card errors
            raise
        except Exception as e:
            logger.error(f"Error restoring card data: {e}")
            raise RestoreError(f"Error restoring card data: {str(e)}")

    def list_backups(self, device_type: Optional[DeviceType] = None) -> List[Dict[str, Any]]:
        """
        Lists available backups.

        Args:
            device_type: Optional filter for device type.

        Returns:
            A list of dictionaries containing backup metadata.
        """
        backups = []
        try:
            for filename in os.listdir(self.backup_dir):
                if not filename.endswith('.json'):
                    continue
                    
                file_path = os.path.join(self.backup_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    if device_type and data.get('device_type') != device_type.value:
                        continue
                        
                    backups.append({
                        'filename': filename,
                        'path': file_path,
                        'device_type': data.get('device_type'),
                        'identifier': data.get('identifier'),
                        'backup_date': data.get('backup_date')
                    })
                except (json.JSONDecodeError, KeyError):
                    logger.warning(f"Skipping invalid backup file: {filename}")
                    
            return backups
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            raise BackupError(f"Error listing backups: {str(e)}")

    def _get_smartcard_data(self, atr: str) -> Dict[str, Any]:
        """
        Retrieve data from a smartcard.
        
        Args:
            atr: The ATR string of the smartcard.
            
        Returns:
            Dictionary containing smartcard data.
            
        Raises:
            CardError: If the card cannot be accessed or data retrieval fails.
        """
        try:
            # Implement actual smartcard data retrieval logic here
            # This would interact with the card_manager to read data
            return self.card_manager.get_smartcard_data(atr)
        except Exception as e:
            logger.error(f"Error reading smartcard data: {e}")
            raise CardError(f"Failed to read smartcard data: {str(e)}")

    def _get_nfc_data(self, uid: str) -> Dict[str, Any]:
        """
        Retrieve data from an NFC device.
        
        Args:
            uid: The UID of the NFC device.
            
        Returns:
            Dictionary containing NFC device data.
            
        Raises:
            CardError: If the NFC device cannot be accessed or data retrieval fails.
        """
        try:
            # Implement actual NFC data retrieval logic here
            return self.card_manager.get_nfc_data(uid)
        except Exception as e:
            logger.error(f"Error reading NFC data: {e}")
            raise CardError(f"Failed to read NFC data: {str(e)}")

    def _restore_smartcard_data(self, atr: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore data to a smartcard.
        
        Args:
            atr: The ATR string of the smartcard.
            data: The data to restore.
            
        Returns:
            Dictionary containing restore result.
            
        Raises:
            CardError: If the restore operation fails.
        """
        try:
            # Implement actual smartcard data restore logic here
            return self.card_manager.restore_smartcard_data(atr, data)
        except Exception as e:
            logger.error(f"Error restoring smartcard data: {e}")
            raise CardError(f"Failed to restore smartcard data: {str(e)}")

    def _restore_nfc_data(self, uid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore data to an NFC device.
        
        Args:
            uid: The UID of the NFC device.
            data: The data to restore.
            
        Returns:
            Dictionary containing restore result.
            
        Raises:
            CardError: If the restore operation fails.
        """
        try:
            # Implement actual NFC data restore logic here
            return self.card_manager.restore_nfc_data(uid, data)
        except Exception as e:
            logger.error(f"Error restoring NFC data: {e}")
            raise CardError(f"Failed to restore NFC data: {str(e)}")

    def _validate_backup_data(self, data: Dict[str, Any]) -> None:
        """
        Validates the structure and content of backup data.
        
        Args:
            data: The backup data to validate.
            
        Raises:
            RestoreError: If the backup data is invalid.
        """
        required_fields = ["identifier", "device_type", "backup_date", "data"]
        for field in required_fields:
            if field not in data:
                raise RestoreError(f"Invalid backup data: Missing required field '{field}'")
                
        if data["device_type"] not in [dt.value for dt in DeviceType]:
            raise RestoreError(f"Invalid device type: {data['device_type']}")

# Create an instance with proper handling of initialization failures
try:
    card_backup_manager = CardBackupManager(CardManager())
except BackupError as e:
    logger.critical(f"Failed to initialize CardBackupManager: {e}")
    card_backup_manager = None