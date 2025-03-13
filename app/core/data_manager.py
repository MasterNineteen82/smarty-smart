import json
import logging
import os
import threading
import time
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional, Tuple, Union

import schedule

# Setup logging with proper format
logging.basicConfig(
    filename="smartcard_module.log", 
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
)
logger = logging.getLogger(__name__)

class DataError(Exception):
    """Base exception for data manager errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ValidationError(DataError):
    """Exception raised when data validation fails"""
    pass


class StorageError(DataError):
    """Exception raised when storage operations (read/write/access) fail"""
    pass


class OperationError(DataError):
    """Exception raised when a data operation fails for reasons other than validation/storage"""
    pass


class ResponseStatus(Enum):
    """
    Standardized response status codes for consistent API responses
    
    These status codes are used throughout the application to provide
    consistent status reporting for all data operations.
    """
    SUCCESS = "success"        # Operation completed successfully
    ERROR = "error"            # General error occurred
    NOT_FOUND = "not_found"    # Requested resource doesn't exist
    VALIDATION_ERROR = "validation_error"  # Input validation failed
    STORAGE_ERROR = "storage_error"        # File/storage operation failed
    UNAUTHORIZED = "unauthorized"          # Operation not permitted
    CONFLICT = "conflict"      # Resource conflict (e.g., duplicate entries)

class SmartcardDataManager:
    def __init__(self, data_file: str = "smartcard_data.json"):
        """
        Initializes the data manager with the given JSON file.
        
        Args:
            data_file: Name of the JSON file to store data
        """
        self.data_file = Path(__file__).resolve().parent.parent / 'data' / data_file
        self.data: Dict[str, Dict[str, Any]] = {}
        self._schedule_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._data_lock = Lock()  # For thread safety
        
        # Ensure data directory exists
        try:
            if not os.path.exists(self.data_file.parent):
                os.makedirs(self.data_file.parent)
            self.data = self.load_data()
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to initialize data directory: {e}")
            raise StorageError(f"Cannot access data directory: {e}")

    def load_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads structured smartcard/NFC data from a JSON file.
        
        Returns:
            Dictionary containing the loaded data
            
        Raises:
            StorageError: If file operations fail
        """
        try:
            if not os.path.exists(self.data_file):
                logger.warning(f"Data file {self.data_file} not found. Initializing with empty data.")
                return {}
                
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Data loaded successfully from {self.data_file}")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.data_file}: {e}")
            raise StorageError(f"Invalid JSON format in data file: {e}")
        except (IOError, PermissionError) as e:
            logger.error(f"Error reading from {self.data_file}: {e}")
            raise StorageError(f"Cannot read data file: {e}")

    def save_data(self) -> None:
        """
        Saves data back to the JSON file.
        
        Raises:
            StorageError: If file operations fail
        """
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            logger.info(f"Data saved successfully to {self.data_file}")
        except (IOError, PermissionError) as e:
            logger.error(f"Error saving data to {self.data_file}: {e}")
            raise StorageError(f"Cannot write to data file: {e}")

    def add_entry(self, category: str, key: str, value: Any) -> Dict[str, Any]:
        """
        Adds a new entry under a specific category.
        
        Args:
            category: The category to add the entry to
            key: The key for the entry
            value: The value to store
            
        Returns:
            Response dictionary with status and message
            
        Raises:
            ValidationError: If inputs are invalid
        """
        try:
            if not isinstance(category, str) or not isinstance(key, str):
                raise ValidationError("Category and key must be strings")

            with self._data_lock:
                if category not in self.data:
                    self.data[category] = {}
                    
                is_update = key in self.data[category]
                self.data[category][key] = value
                self.save_data()
                
                action = "updated" if is_update else "added"
                logger.info(f"Entry {action} - Category: {category}, Key: {key}")
                
                return {
                    "status": ResponseStatus.SUCCESS.value,
                    "message": f"Entry {action} successfully",
                    "data": {key: value}
                }
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except StorageError as e:
            logger.error(f"Storage error: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in add_entry: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": f"An unexpected error occurred: {e}"}

    def get_entry(self, category: str, key: str) -> Dict[str, Any]:
        """
        Retrieves an entry by category and key.
        
        Args:
            category: Category to search in
            key: Key to look for
            
        Returns:
            Response dictionary with status and data
        """
        try:
            if not isinstance(category, str) or not isinstance(key, str):
                raise ValidationError("Category and key must be strings")
                
            with self._data_lock:
                if category not in self.data:
                    logger.warning(f"Category '{category}' not found")
                    return {
                        "status": ResponseStatus.NOT_FOUND.value,
                        "message": f"Category '{category}' not found"
                    }
                    
                if key not in self.data[category]:
                    logger.warning(f"Key '{key}' not found in category '{category}'")
                    return {
                        "status": ResponseStatus.NOT_FOUND.value,
                        "message": f"Entry not found"
                    }
                    
                entry = self.data[category][key]
                logger.info(f"Retrieved entry - Category: {category}, Key: {key}")
                return {
                    "status": ResponseStatus.SUCCESS.value,
                    "data": entry
                }
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in get_entry: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": f"An unexpected error occurred: {e}"}

    def search_data(self, category: str, search_term: str) -> Dict[str, Any]:
        """
        Performs a partial match search across a specific category.
        
        Args:
            category: Category to search in
            search_term: Term to search for
            
        Returns:
            Response dictionary with matching entries
        """
        try:
            if not isinstance(category, str) or not isinstance(search_term, str):
                raise ValidationError("Category and search term must be strings")
                
            with self._data_lock:
                if category not in self.data:
                    logger.info(f"Category '{category}' not found for search term '{search_term}'")
                    return {
                        "status": ResponseStatus.NOT_FOUND.value,
                        "message": f"Category '{category}' not found"
                    }
                    
                results = {k: v for k, v in self.data.get(category, {}).items() 
                          if search_term.lower() in k.lower()}
                
                if not results:
                    logger.info(f"No matches found in category '{category}' for term '{search_term}'")
                    return {
                        "status": ResponseStatus.NOT_FOUND.value,
                        "message": "No matches found"
                    }
                    
                logger.info(f"Found {len(results)} matches in category '{category}' for term '{search_term}'")
                return {
                    "status": ResponseStatus.SUCCESS.value,
                    "data": results
                }
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error in search_data: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": f"An unexpected error occurred: {e}"}

    def update_from_source(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates the data from an external source.
        
        Args:
            new_data: Dictionary containing new data
            
        Returns:
            Response dictionary with status
        """
        try:
            if not isinstance(new_data, dict):
                raise ValidationError("New data must be a dictionary")
                
            with self._data_lock:
                self.data.update(new_data)
                self.save_data()
                logger.info("Database updated successfully from external source")
                
                return {
                    "status": ResponseStatus.SUCCESS.value,
                    "message": "Data updated successfully"
                }
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except StorageError as e:
            logger.error(f"Storage error during update: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": str(e)}
        except Exception as e:
            logger.error(f"Error during update: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": f"An unexpected error occurred: {e}"}

    def schedule_data_updates(self, interval: int = 24) -> Dict[str, Any]:
        """
        Schedules data updates to run at a specified interval.
        
        Args:
            interval: Update interval in hours
            
        Returns:
            Response dictionary with status
        """
        try:
            if self._schedule_thread is not None and self._schedule_thread.is_alive():
                logger.info("Data updates already scheduled")
                return {
                    "status": ResponseStatus.SUCCESS.value, 
                    "message": "Updates already scheduled"
                }
                
            # Reset stop event
            self._stop_event.clear()
            
            def run_scheduled_updates():
                logger.info(f"Starting scheduled updates every {interval} hours")
                schedule.every(interval).hours.do(self._perform_update)
                
                while not self._stop_event.is_set():
                    schedule.run_pending()
                    self._stop_event.wait(60)  # Check every minute but allow for clean exit
                
                logger.info("Scheduled update thread terminated")

            self._schedule_thread = threading.Thread(target=run_scheduled_updates)
            self._schedule_thread.daemon = True
            self._schedule_thread.start()
            logger.info(f"Data updates scheduled to run every {interval} hours")
            
            return {
                "status": ResponseStatus.SUCCESS.value,
                "message": f"Updates scheduled every {interval} hours"
            }
        except Exception as e:
            logger.error(f"Error setting up scheduled updates: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": f"Failed to schedule updates: {e}"}

    def _perform_update(self) -> None:
        """Performs the actual update operation"""
        try:
            logger.info("Running scheduled data update...")
            # Simulate fetching data from an external source
            # Replace this with your actual data fetching logic
            new_data = self._fetch_data_from_api()
            self.update_from_source(new_data)
            logger.info("Scheduled update completed successfully")
        except Exception as e:
            logger.error(f"Error during scheduled update: {e}")

    def _fetch_data_from_api(self) -> Dict[str, Any]:
        """Fetches data from an external API."""
        # Replace this with your actual API fetching logic
        # This is just a placeholder
        return {"API_Data": {"timestamp": time.time()}}

    def stop_scheduled_updates(self) -> Dict[str, Any]:
        """
        Stops the scheduled data updates.
        
        Returns:
            Response dictionary with status
        """
        if self._schedule_thread is None or not self._schedule_thread.is_alive():
            logger.info("No active scheduled updates to stop")
            return {
                "status": ResponseStatus.SUCCESS.value,
                "message": "No active scheduled updates"
            }
            
        try:
            # Signal thread to stop
            self._stop_event.set()
            schedule.clear()
            
            # Wait for thread to terminate (with timeout)
            self._schedule_thread.join(timeout=2.0)
            self._schedule_thread = None
            
            logger.info("Scheduled data updates stopped")
            return {
                "status": ResponseStatus.SUCCESS.value,
                "message": "Scheduled updates stopped"
            }
        except Exception as e:
            logger.error(f"Error stopping scheduled updates: {e}")
            return {"status": ResponseStatus.ERROR.value, "message": f"Failed to stop updates: {e}"}