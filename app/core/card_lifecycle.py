import logging
from typing import Tuple, Optional

from app.core.card_utils import CardStatus
from app.core.card_manager import card_manager
from app.db import session_scope, Card, Session

# Configure logging
logger = logging.getLogger(__name__)

class CardLifecycleManager:
    """
    Manages the lifecycle of a smart card, including registration, activation,
    deactivation, and blocking.
    """

    def __init__(self, card_manager=card_manager):
        """
        Initializes the CardLifecycleManager with a CardManager instance.
        """
        self.card_manager = card_manager

    def register_new_card(self, atr: str, user_id: str) -> Tuple[bool, str]:
        """
        Registers a new card with the given ATR and user ID.
        """
        return self.card_manager.register_new_card(atr, user_id)

    def unregister_existing_card(self, atr: str) -> Tuple[bool, str]:
        """
        Unregisters an existing card with the given ATR.
        """
        return self.card_manager.unregister_existing_card(atr)

    def activate_existing_card(self, atr: str) -> Tuple[bool, str]:
        """
        Activates an existing card with the given ATR.
        """
        return self.card_manager.activate_inactive_card(atr)

    def deactivate_existing_card(self, atr: str) -> Tuple[bool, str]:
        """
        Deactivates an existing card with the given ATR.
        """
        return self.card_manager.deactivate_active_card(atr)

    def block_existing_card(self, atr: str) -> Tuple[bool, str]:
        """
        Blocks an existing card with the given ATR.
        """
        return self.card_manager.block_active_card(atr)

    def unblock_existing_card(self, atr: str) -> Tuple[bool, str]:
        """
        Unblocks an existing card with the given ATR.
        """
        return self.card_manager.unblock_blocked_card(atr)

# Create a global instance
card_lifecycle_manager = CardLifecycleManager()