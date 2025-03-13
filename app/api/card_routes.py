from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional, Dict, Any, List

import logging
from pydantic import BaseModel, validator
from app.core.card_manager import CardManager, card_manager
from app.core.card_validation import CardValidator, card_validator
from app.db import session_scope, Card, Session
from sqlalchemy.orm import Session
from app.utils.exceptions import CardError, InvalidInputError

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Define a Pydantic model for card data
class Card(BaseModel):
    card_id: int
    status: str = "active"
    balance: float = 0.0
    card_type: str
    data: Optional[Dict[str, Any]] = None

    @validator('card_id')
    def card_id_must_be_positive(cls, value):
        if value <= 0:
            raise ValueError('Card ID must be a positive integer')
        return value

    @validator('status')
    def status_must_be_valid(cls, value):
        valid_statuses = ['active', 'inactive', 'blocked']
        if value not in valid_statuses:
            raise ValueError('Status must be one of: active, inactive, blocked')
        return value

    @validator('card_type')
    def card_type_must_be_valid(cls, value):
        valid_card_types = ['smartcard', 'nfc']
        if value not in valid_card_types:
            raise ValueError(f'Card type must be one of: {valid_card_types}')
        return value

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

# Route to create a new card
@router.post("/", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
async def create_card(card: CardCreate, db: Session = Depends(get_db)):
    """
    Create a new card in the database.
    """
    try:
        db_card = Card(atr=card.atr, user_id=card.user_id, card_type=card.card_type)
        db.add(db_card)
        db.commit()
        db.refresh(db_card)
        return db_card
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Route to get a card by ID
@router.get("/{card_id}", response_model=CardResponse)
async def get_card(card_id: int, db: Session = Depends(get_db)):
    """
    Get a card by its ID.
    """
    db_card = db.query(Card).filter(Card.id == card_id).first()
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return db_card

# Route to list all cards
@router.get("/", response_model=List[CardResponse])
async def list_cards(db: Session = Depends(get_db)):
    """
    List all cards in the database.
    """
    cards = db.query(Card).all()
    return cards

# Route to update a card
@router.put("/{card_id}", response_model=CardResponse)
async def update_card(card_id: int, card: CardCreate, db: Session = Depends(get_db)):
    """
    Update a card in the database.
    """
    db_card = db.query(Card).filter(Card.id == card_id).first()
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    db_card.atr = card.atr
    db_card.user_id = card.user_id
    db_card.card_type = card.card_type
    db.commit()
    db.refresh(db_card)
    return db_card

# Route to delete a card
@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: int, db: Session = Depends(get_db)):
    """
    Delete a card from the database.
    """
    db_card = db.query(Card).filter(Card.id == card_id).first()
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    db.delete(db_card)
    db.commit()
    return None