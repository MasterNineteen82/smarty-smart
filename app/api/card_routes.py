from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional, Dict, Any, List

import logging
from pydantic import BaseModel, validator
from app.core.card_manager import CardManager, card_manager
from app.security_manager import SecurityManager, get_security_manager  # Updated import statement
from app.db import session_scope, Card, Session
from sqlalchemy.orm import Session
from app.utils.exceptions import CardError, InvalidInputError

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Define a Pydantic model for card data
class Card(BaseModel):
    id: int
    atr: str
    user_id: int
    status: str

    class Config:
        from_attributes = True  # Changed orm_mode to from_attributes

# Pydantic models for request and response data
class CardCreate(BaseModel):
    atr: str
    user_id: int
    card_type: str

class CardResponse(BaseModel):
    id: int
    atr: str
    user_id: int
    card_type: str

# Dependency to get database session
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()

# Route for registering a new card
@router.post("/register", response_model=Card, status_code=status.HTTP_201_CREATED)
async def register_card(card: Card, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
    """
    Register a new card.
    """
    logger.info(f"Registering new card with ATR: {card.atr}")
    try:
        # Register the card using the CardManager
        success, message = card_manager.register_new_card(card.atr, card.user_id)
        if success:
            logger.info(f"Card registered successfully: {card.atr}")
            # Retrieve the registered card from the database
            db_card = db.query(Card).filter(Card.atr == card.atr).first()
            return db_card
        else:
            logger.warning(f"Card registration failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

# Route for getting a card by ATR
@router.get("/{atr}", response_model=Card)
async def get_card(atr: str, db: Session = Depends(get_db)):
    """
    Get a card by ATR.
    """
    logger.info(f"Getting card with ATR: {atr}")
    try:
        # Retrieve the card from the database
        db_card = db.query(Card).filter(Card.atr == atr).first()
        if db_card:
            logger.info(f"Card found: {atr}")
            return db_card
        else:
            logger.warning(f"Card not found: {atr}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Card not found",
            )
    except Exception as e:
        logger.error(f"Failed to get card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

# Route for activating a card
@router.post("/{atr}/activate", response_model=Card)
async def activate_card(atr: str, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
    """
    Activate a card.
    """
    logger.info(f"Activating card with ATR: {atr}")
    try:
        # Activate the card using the CardManager
        success, message = card_manager.activate_inactive_card(atr)
        if success:
            logger.info(f"Card activated successfully: {atr}")
            # Retrieve the activated card from the database
            db_card = db.query(Card).filter(Card.atr == atr).first()
            return db_card
        else:
            logger.warning(f"Card activation failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
    except Exception as e:
        logger.error(f"Activation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

# Route for deactivating a card
@router.post("/{atr}/deactivate", response_model=Card)
async def deactivate_card(atr: str, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
    """
    Deactivate a card.
    """
    logger.info(f"Deactivating card with ATR: {atr}")
    try:
        # Deactivate the card using the CardManager
        success, message = card_manager.deactivate_active_card(atr)
        if success:
            logger.info(f"Card deactivated successfully: {atr}")
            # Retrieve the deactivated card from the database
            db_card = db.query(Card).filter(Card.atr == atr).first()
            return db_card
        else:
            logger.warning(f"Card deactivation failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
    except Exception as e:
        logger.error(f"Deactivation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

# Route for blocking a card
@router.post("/{atr}/block", response_model=Card)
async def block_card(atr: str, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
    """
    Block a card.
    """
    logger.info(f"Blocking card with ATR: {atr}")
    try:
        # Block the card using the CardManager
        success, message = card_manager.block_active_card(atr)
        if success:
            logger.info(f"Card blocked successfully: {atr}")
            # Retrieve the blocked card from the database
            db_card = db.query(Card).filter(Card.atr == atr).first()
            return db_card
        else:
            logger.warning(f"Card blocking failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
    except Exception as e:
        logger.error(f"Blocking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

# Route for unblocking a card
@router.post("/{atr}/unblock", response_model=Card)
async def unblock_card(atr: str, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
    """
    Unblock a card.
    """
    logger.info(f"Unblocking card with ATR: {atr}")
    try:
        # Unblock the card using the CardManager
        success, message = card_manager.unblock_blocked_card(atr)
        if success:
            logger.info(f"Card unblocked successfully: {atr}")
            # Retrieve the unblocked card from the database
            db_card = db.query(Card).filter(Card.atr == atr).first()
            return db_card
        else:
            logger.warning(f"Card unblocking failed: {message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
    except Exception as e:
        logger.error(f"Unblocking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )