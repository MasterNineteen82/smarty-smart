import logging
from typing import Optional, Dict, Any

"""
Custom exceptions for the Smartcard Manager application.

This module provides a hierarchy of custom exceptions used throughout the
application to ensure consistent error handling and reporting.
"""

# Configure logging for exceptions
logger = logging.getLogger(__name__)

class SmartcardBaseException(Exception):
    """Base exception class for all application exceptions."""
    
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, log_level: int = logging.ERROR):
        """
        Initialize the exception with a message and optional details.
        
        Args:
            message: Human-readable error description
            code: Machine-readable error code
            details: Additional context about the error
            log_level: Logging level for the exception (default: ERROR)
        """
        self.message = message
        self.code = code
        self.details = details or {}
        self.log_level = log_level
        self.log()  # Log the exception when it's created
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for API responses."""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'code': self.code,
            'details': self.details
        }

    def log(self):
        """Log the exception with relevant details."""
        log_message = f"{self.__class__.__name__}: {self.message}"
        if self.code:
            log_message += f" (Code: {self.code})"
        if self.details:
            log_message += f" - Details: {self.details}"

        logger.log(self.log_level, log_message, exc_info=True)  # Include traceback


class DataError(SmartcardBaseException):
    """Base class for data-related exceptions."""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, log_level: int = logging.WARNING):
        super().__init__(message, code, details, log_level)


class DataUpdateError(DataError):
    """Exception raised when a data update operation fails."""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, log_level: int = logging.WARNING):
        super().__init__(message, code, details, log_level)


class StorageError(DataError):
    """Exception raised when there is an error with data storage operations."""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, log_level: int = logging.ERROR):
        super().__init__(message, code, details, log_level)


class ValidationError(DataError):
    """Exception raised when data validation fails."""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, log_level: int = logging.WARNING):
        super().__init__(message, code, details, log_level)


class CardError(SmartcardBaseException):
    """Custom exception for card-related errors."""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, log_level: int = logging.ERROR):
        super().__init__(message, code, details, log_level)


class InvalidInputError(SmartcardBaseException):
    """Custom exception for invalid input errors."""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, log_level: int = logging.WARNING):
        super().__init__(message, code, details, log_level)


class ModuleIntegratorError(SmartcardBaseException):
    """Base exception for ModuleIntegrator errors."""
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None, log_level: int = logging.ERROR):
        super().__init__(message, code, details, log_level)

class AuthenticationError(Exception):
    pass

class AuthorizationError(Exception):
    pass

class EncryptionError(Exception):
    pass