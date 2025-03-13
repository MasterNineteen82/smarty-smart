"""
Transaction processing module for the Smartcard Manager application.

This module processes transactions, such as debiting and crediting card balances.
"""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from app.db import session_scope, Card, Transaction
from app.utils.exceptions import CardError, InsufficientBalanceError, TransactionError

logger = logging.getLogger(__name__)

class TransactionProcessor:
    """
    Processes transactions, such as debiting and crediting card balances.
    """

    def debit_card(self, atr, amount):
        """
        Debits a card by a specified amount.

        Args:
            atr: The ATR of the card to debit.
            amount: The amount to debit (must be positive).

        Returns:
            dict: Transaction details including updated balance and status.
            
        Raises:
            CardError: If the card cannot be found or general processing error.
            InsufficientBalanceError: If the card has insufficient balance.
            ValueError: If amount is invalid.
        """
        if not isinstance(amount, (int, float, Decimal)) or amount <= 0:
            logger.error(f"Invalid debit amount: {amount}")
            raise ValueError("Debit amount must be a positive number")
            
        try:
            with session_scope() as session:
                card = session.query(Card).filter_by(atr=atr).first()
                if not card:
                    logger.warning(f"Card with ATR {atr} not found.")
                    raise CardError(f"Card with ATR {atr} not found")
                
                if card.balance < amount:
                    logger.warning(f"Insufficient balance on card {atr}: {card.balance} < {amount}")
                    raise InsufficientBalanceError(f"Insufficient balance: {card.balance}")
                
                # Update card balance
                card.balance -= Decimal(str(amount))
                card.last_updated = datetime.now()
                
                # Record transaction
                transaction = Transaction(
                    card_id=card.id,
                    amount=-Decimal(str(amount)),
                    timestamp=datetime.now(),
                    type="debit"
                )
                session.add(transaction)
                
                logger.info(f"Debited card with ATR {atr} by {amount}. New balance: {card.balance}")
                return {
                    "success": True,
                    "card_id": card.id,
                    "balance": float(card.balance),
                    "transaction_id": transaction.id
                }
        except InsufficientBalanceError:
            # Re-raise this specific error for frontend handling
            raise
        except CardError:
            # Re-raise card errors
            raise
        except Exception as e:
            logger.error(f"Error debiting card: {e}", exc_info=True)
            raise CardError(f"Error processing debit transaction: {str(e)}")

    def credit_card(self, atr, amount):
        """
        Credits a card by a specified amount.

        Args:
            atr: The ATR of the card to credit.
            amount: The amount to credit (must be positive).

        Returns:
            dict: Transaction details including updated balance and status.
            
        Raises:
            CardError: If the card cannot be found or general processing error.
            ValueError: If amount is invalid.
        """
        if not isinstance(amount, (int, float, Decimal)) or amount <= 0:
            logger.error(f"Invalid credit amount: {amount}")
            raise ValueError("Credit amount must be a positive number")
            
        try:
            with session_scope() as session:
                card = session.query(Card).filter_by(atr=atr).first()
                if not card:
                    logger.warning(f"Card with ATR {atr} not found.")
                    raise CardError(f"Card with ATR {atr} not found")
                
                # Update card balance
                card.balance += Decimal(str(amount))
                card.last_updated = datetime.now()
                
                # Record transaction
                transaction = Transaction(
                    card_id=card.id,
                    amount=Decimal(str(amount)),
                    timestamp=datetime.now(),
                    type="credit"
                )
                session.add(transaction)
                
                logger.info(f"Credited card with ATR {atr} by {amount}. New balance: {card.balance}")
                return {
                    "success": True,
                    "card_id": card.id,
                    "balance": float(card.balance),
                    "transaction_id": transaction.id
                }
        except CardError:
            # Re-raise card errors
            raise
        except Exception as e:
            logger.error(f"Error crediting card: {e}", exc_info=True)
            raise CardError(f"Error processing credit transaction: {str(e)}")

    async def process_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Processes a transaction.

        Args:
            transaction_data: A dictionary containing the transaction data.

        Returns:
            True if the transaction was processed successfully, False otherwise.

        Raises:
            TransactionError: If an error occurs during the transaction processing.
        """
        try:
            # Simulate processing a transaction
            logger.info(f"Successfully processed transaction: {transaction_data}")
            return True
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
            raise TransactionError(f"Failed to process transaction: {str(e)}")

transaction_processor = TransactionProcessor()