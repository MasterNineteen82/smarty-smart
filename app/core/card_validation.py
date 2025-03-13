"""
Card validation module for the Smartcard Manager application.

This module validates smart cards by checking their ATR against a database of known cards.
"""

import logging
from typing import Dict, Optional, Union
from sqlalchemy.exc import SQLAlchemyError
from app.db import session_scope, Card
from app.utils.exceptions import CardError, InvalidInputError

logger = logging.getLogger(__name__)

class CardValidator:
    """
    Validates smart cards by checking their ATR against a database of known cards.
    """

    async def validate_card(self, atr: str) -> Dict[str, Union[bool, Optional[str]]]:
        """
        Validates a smart card by checking its ATR against a database of known cards.

        Args:
            atr: The ATR of the smart card to validate.

        Returns:
            Dictionary containing validation result and optional card information.

        Raises:
            InvalidInputError: If the ATR is None or empty.
            CardError: If an error occurs during card validation.
        """
        # Input validation
        if not atr:
            logger.error("ATR cannot be None or empty")
            raise InvalidInputError("ATR cannot be None or empty")
            
        try:
            async with session_scope() as session:
                card = await session.query(Card).filter_by(atr=atr).first()
                if card:
                    logger.info(f"Card with ATR {atr} is valid")
                    return {
                        "valid": True,
                        "card_type": card.type,
                        "card_id": card.id
                    }
                else:
                    logger.warning(f"Card with ATR {atr} is not recognized in the system")
                    return {
                        "valid": False,
                        "reason": "Card not recognized"
                    }
        except SQLAlchemyError as e:
            logger.error(f"Database error during card validation: {str(e)}")
            raise CardError(f"Database error during card validation: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error validating card: {str(e)}")
            raise CardError(f"Unexpected error validating card: {str(e)}")

# Singleton instance for application-wide use
card_validator = CardValidator()