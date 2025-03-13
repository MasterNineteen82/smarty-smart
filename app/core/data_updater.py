import logging
import time
import schedule
import threading
from typing import Any, Dict, Callable, Optional
import functools
from datetime import datetime

from app.core.data_manager import SmartcardDataManager, ResponseStatus
from app.utils.exceptions import DataUpdateError  # Assuming this exists or needs to be created

logger = logging.getLogger(__name__)

class DataUpdater:
    """
    Handles automated data updates for the SmartcardDataManager.
    """

    def __init__(
        self, 
        data_manager: SmartcardDataManager, 
        update_function: Callable[[], Dict[str, Any]],
        max_retries: int = 3,
        retry_delay: int = 60,
        data_source_name: str = "External Source",  # Add data source name
    ):
        """
        Initializes the DataUpdater with a SmartcardDataManager instance and an update function.

        Args:
            data_manager: An instance of SmartcardDataManager.
            update_function: A callable that fetches and returns new data as a dictionary.
            max_retries: Maximum number of retry attempts for failed updates.
            retry_delay: Delay between retries in seconds.
            data_source_name: A descriptive name for the data source.
        """
        if not isinstance(data_manager, SmartcardDataManager):
            raise TypeError("data_manager must be an instance of SmartcardDataManager")
        if not callable(update_function):
            raise TypeError("update_function must be callable")

        self.data_manager = data_manager
        self.update_function = update_function
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.data_source_name = data_source_name  # Store data source name
        self._schedule_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.last_update_time = None
        self.last_update_status = None
        logger.info(f"DataUpdater initialized successfully for {self.data_source_name}")

    def _fetch_and_update_data(self) -> Dict[str, Any]:
        """
        Fetches new data using the provided update function and updates the SmartcardDataManager.
        
        Returns:
            Dict containing update status and details.
        
        Raises:
            DataUpdateError: If update ultimately fails after retries.
        """
        result = {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "message": "",
            "retry_count": 0
        }
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching new data from external source (attempt {attempt+1}/{self.max_retries})...")
                new_data = self.update_function()
                
                if not isinstance(new_data, dict):
                    raise ValueError("Update function must return a dictionary")
                
                if not new_data:
                    logger.warning("Update function returned empty data")
                
                with self._lock:
                    response = self.data_manager.update_from_source(new_data)
                
                if response["status"] == ResponseStatus.SUCCESS.value:
                    logger.info("Data updated successfully from external source")
                    result["success"] = True
                    result["message"] = "Update successful"
                    self.last_update_time = datetime.now()
                    self.last_update_status = "SUCCESS"
                    return result
                else:
                    error_msg = f"Failed to update data: {response['message']}"
                    logger.error(error_msg)
                    result["message"] = error_msg
                    
            except Exception as e:
                error_msg = f"Error during data update: {str(e)}"
                logger.error(error_msg, exc_info=True)
                result["message"] = error_msg
                result["retry_count"] = attempt + 1
                
            if attempt < self.max_retries - 1:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        
        self.last_update_status = "FAILED"
        return result

    def schedule_data_updates(self, interval: int = 24) -> None:
        """
        Schedules data updates to run at a specified interval (in hours).

        Args:
            interval: The interval between updates in hours (default is 24).
        """
        with self._lock:
            if self._schedule_thread is not None and self._schedule_thread.is_alive():
                logger.info("Data updates already scheduled.")
                return

            self._stop_event.clear()

        def run_scheduled_updates():
            logger.info(f"Starting scheduled updates every {interval} hours")
            # Run initial update immediately
            self._fetch_and_update_data()
            
            schedule.every(interval).hours.do(self._fetch_and_update_data)
            
            while not self._stop_event.is_set():
                schedule.run_pending()
                # Check for stop event every 15 seconds to allow for responsive shutdown
                self._stop_event.wait(timeout=15)

        self._schedule_thread = threading.Thread(target=run_scheduled_updates, name="DataUpdaterThread")
        self._schedule_thread.daemon = True
        self._schedule_thread.start()
        logger.info(f"Data updates scheduled to run every {interval} hours.")

    def stop_scheduled_updates(self, timeout: int = 30) -> bool:
        """
        Stops the scheduled data updates.
        
        Args:
            timeout: Maximum time to wait for thread termination in seconds.
            
        Returns:
            bool: True if successfully stopped, False if timeout occurred.
        """
        with self._lock:
            if self._schedule_thread is None or not self._schedule_thread.is_alive():
                logger.info("No active scheduled updates to stop.")
                return True

            logger.info("Stopping scheduled data updates...")
            self._stop_event.set()
            schedule.clear()
            
        # Wait for thread to terminate
        self._schedule_thread.join(timeout=timeout)
        is_stopped = not self._schedule_thread.is_alive()
        
        if is_stopped:
            logger.info("Scheduled data updates stopped successfully.")
            self._schedule_thread = None
        else:
            logger.warning(f"Scheduled data updates thread did not terminate within {timeout} seconds.")
        
        return is_stopped
    
    def get_status(self) -> Dict[str, Any]:
        """
        Returns the current status of the data updater.
        
        Returns:
            Dict containing status information.
        """
        return {
            "active": self._schedule_thread is not None and self._schedule_thread.is_alive(),
            "last_update_time": self.last_update_time.isoformat() if self.last_update_time else None,
            "last_update_status": self.last_update_status
        }

    def force_update(self) -> Dict[str, Any]:
        """
        Forces an immediate data update, regardless of schedule.
        
        Returns:
            Dict containing update result.
        """
        logger.info("Forcing immediate data update")
        return self._fetch_and_update_data()