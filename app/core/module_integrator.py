import logging
import re
from typing import Any, Dict, Optional, Union

from app.core.data_manager import SmartcardDataManager, ResponseStatus, ValidationError

logger = logging.getLogger(__name__)

class ModuleIntegratorError(Exception):
    """Base exception for ModuleIntegrator errors."""
    pass

class ModuleIntegrator:
    """
    Integrates the SmartcardDataManager with other modules, such as card validation and transaction processing.
    
    This class serves as a bridge between different components of the system, ensuring
    consistent data flow and error handling across modules.
    """

    def __init__(self, data_manager: SmartcardDataManager):
        """
        Initializes the ModuleIntegrator with a SmartcardDataManager instance.

        Args:
            data_manager: An instance of SmartcardDataManager.
            
        Raises:
            TypeError: If data_manager is not an instance of SmartcardDataManager.
        """
        if not isinstance(data_manager, SmartcardDataManager):
            logger.error("Invalid data manager type provided")
            raise TypeError("data_manager must be an instance of SmartcardDataManager")
        self.data_manager = data_manager
        logger.info("ModuleIntegrator initialized successfully")

    def _create_response(self, status: ResponseStatus, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Creates a standardized response dictionary.
        
        Args:
            status: Response status enum value.
            message: Response message.
            data: Optional data to include in the response.
            
        Returns:
            A standardized response dictionary.
        """
        response = {
            "status": status.value,
            "message": message
        }
        if data is not None:
            response["data"] = data
        return response

    def link_to_card_validation(self, atr: str) -> Dict[str, Any]:
        """
        Links an ATR (Answer To Reset) to a card validation process.

        Args:
            atr: The ATR string to link.

        Returns:
            A dictionary containing the status and message of the operation.
        """
        try:
            if not isinstance(atr, str):
                raise ValidationError("ATR must be a string")

            # Simulate card validation process (replace with actual validation logic)
            # Here you would call the card validation module
            # For example: card_validation_module.validate_card(atr)
            validation_data = {"card_valid": True, "validation_date": "2024-01-01"}
            self.data_manager.add_entry("CardValidation", atr, validation_data)
            logger.info(f"Linked ATR '{atr}' to card validation process")
            return self._create_response(ResponseStatus.SUCCESS, f"Successfully linked ATR '{atr}' to card validation", validation_data)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return self._create_response(ResponseStatus.ERROR, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in link_to_card_validation: {e}")
            return self._create_response(ResponseStatus.ERROR, f"An unexpected error occurred: {e}")

    def link_to_transaction_module(self, apdu_code: str) -> Dict[str, Any]:
        """
        Links an APDU (Application Protocol Data Unit) response code to a transaction processing module.

        Args:
            apdu_code: The APDU response code to link (format: hexadecimal string).

        Returns:
            A dictionary containing the status, message, and transaction data if successful.
            
        Raises:
            ValidationError: If the APDU code format is invalid.
        """
        try:
            # Validate input
            if not isinstance(apdu_code, str):
                raise ValidationError("APDU code must be a string")
            if not apdu_code:
                raise ValidationError("APDU code cannot be empty")
            
            # Validate APDU format (typically a hexadecimal string)
            if not re.match(r'^[0-9A-Fa-f]+$', apdu_code):
                raise ValidationError("APDU code must be a hexadecimal string")

            # Simulate linking to a transaction processing module (replace with actual linking logic)
            transaction_data = {"transaction_module": "TransactionModule1", "description": "Handles standard transactions"}
            self.data_manager.add_entry("TransactionModules", apdu_code, transaction_data)
            logger.info(f"Linked APDU code '{apdu_code}' to transaction module")
            
            return self._create_response(
                ResponseStatus.SUCCESS,
                f"Successfully linked APDU code '{apdu_code}' to transaction module",
                transaction_data
            )
            
        except ValidationError as e:
            logger.error(f"Validation error in link_to_transaction_module: {e}")
            return self._create_response(ResponseStatus.ERROR, str(e))
            
        except Exception as e:
            logger.exception(f"Unexpected error in link_to_transaction_module with code '{apdu_code}'")
            return self._create_response(ResponseStatus.ERROR, f"An unexpected error occurred: {e}")