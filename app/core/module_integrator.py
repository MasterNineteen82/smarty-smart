import logging
from typing import Any, Dict, Callable, Coroutine

from app.core.card_manager import CardManager
from app.core.nfc import NFCManager
from app.core.transaction_processor import TransactionProcessor

logger = logging.getLogger(__name__)

class ModuleIntegratorError(Exception):
    """Base exception for ModuleIntegrator errors."""
    pass

class ModuleIntegrator:
    """
    Integrates different modules of the application.
    """

    def __init__(self, card_manager: CardManager, nfc_manager: NFCManager, transaction_processor: TransactionProcessor):
        """
        Initializes the ModuleIntegrator with instances of the CardManager, NFCManager, and TransactionProcessor.
        """
        self.card_manager = card_manager
        self.nfc_manager = nfc_manager
        self.transaction_processor = transaction_processor

        self._operation_map: Dict[str, Callable[[Dict[str, Any]], Coroutine[Any, Any, Any]]] = {
            "register_card": self._register_card,
            "read_nfc_data": self._read_nfc_data,
            "process_transaction": self._process_transaction,
        }


    async def _register_card(self, data: Dict[str, Any]) -> Any:
        """Registers a card using the card manager."""
        return await self.card_manager.register_card(data["atr"], data["user_id"])

    async def _read_nfc_data(self, data: Dict[str, Any]) -> Any:
        """Reads NFC data using the NFC manager."""
        return await self.nfc_manager.read_nfc_data(data["uid"])

    async def _process_transaction(self, data: Dict[str, Any]) -> Any:
        """Processes a transaction using the transaction processor."""
        return await self.transaction_processor.process_transaction(data)


    async def perform_integrated_operation(self, operation_type: str, data: Dict[str, Any]) -> Any:
        """
        Performs an integrated operation based on the specified operation type.

        Args:
            operation_type: The type of operation to perform.
            data: A dictionary containing the data required for the operation.

        Returns:
            The result of the operation.

        Raises:
            ValueError: If an invalid operation type is specified.
        """
        operation = self._operation_map.get(operation_type)

        if operation:
            try:
                result = await operation(data)
                logger.info(f"Successfully performed integrated operation: {operation_type}")
                return result
            except Exception as e:
                logger.error(f"Error performing integrated operation {operation_type}: {e}")
                raise
        else:
            logger.warning(f"Invalid operation type requested: {operation_type}")
            raise ValueError(f"Invalid operation type: {operation_type}")