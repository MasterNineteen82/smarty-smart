"""
Card validation module for the Smartcard Manager application.

This module validates smart cards by checking their ATR against a database of known cards.
"""

import logging
from typing import Optional

from app.db import session_scope, Card, Session  # Import Session
from sqlalchemy.orm import Session

# Configure logging
logger = logging.getLogger(__name__)

class CardValidator:
    """
    Validates smart card data against predefined rules and database records.
    """
    def __init__(self):
        """
        Initializes the CardValidator with necessary dependencies.
        """
        pass

    async def validate_card(self, atr: str, db: Session) -> Optional[Card]:
        """
        Validates if a card with the given ATR exists in the database.

        Args:
            atr (str): The Answer To Reset (ATR) string of the card.
            db (Session): The database session.

        Returns:
            Optional[Card]: The Card object if found, otherwise None.
        """
        try:
            # Query the database for a card with the given ATR
            card = db.query(Card).filter(Card.atr == atr).first()
            if card:
                logger.info(f"Card with ATR '{atr}' found in the database.")
                return card
            else:
                logger.warning(f"Card with ATR '{atr}' not found in the database.")
                return None
        except Exception as e:
            logger.error(f"Error validating card: {e}")
            return None

# Initialize CardValidator
card_validator = CardValidator()