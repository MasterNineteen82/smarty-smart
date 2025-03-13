from typing import Optional, Dict, Any

"""
Custom exceptions for the Smartcard Manager application.

This module provides a hierarchy of custom exceptions used throughout the
application to ensure consistent error handling and reporting.
"""


class SmartcardBaseException(Exception):
    """Base exception class for all application exceptions."""
    
    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None):
        """
        Initialize the exception with a message and optional details.
        
        Args:
            message: Human-readable error description
            code: Machine-readable error code
            details: Additional context about the error
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for API responses."""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'code': self.code,
            'details': self.details
        }


class DataError(SmartcardBaseException):
    """Base class for data-related exceptions."""
    pass


class DataUpdateError(DataError):
    """Exception raised when a data update operation fails."""
    pass


class StorageError(DataError):
    """Exception raised when there is an error with data storage operations."""
    pass


class ValidationError(DataError):
    """Exception raised when data validation fails."""
    pass


class CardError(Exception):
    """Custom exception for card-related errors."""
    pass

class InvalidInputError(Exception):
    """Custom exception for invalid input errors."""
    pass


class ModuleIntegratorError(SmartcardBaseException):
    """Base exception for ModuleIntegrator errors."""
    pass