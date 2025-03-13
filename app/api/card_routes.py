from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional, Dict, Any, List
import logging
from pydantic import BaseModel, validator
import psycopg
from app.core import smartcard, nfc
from app.core.card_manager import CardManager, card_manager
from app.core.card_validation import CardValidator, card_validator
from app.db import session_scope, Card
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
            raise ValueError(f'Status must be one of: {valid_statuses}')
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

# Database connection parameters (replace with your actual credentials)
DATABASE_URL = "postgresql://user:password@host:port/database"

# Dependency to get database connection
async def get_db():
    conn = None
    try:
        conn = psycopg.connect(DATABASE_URL)
        logger.info("Database connection established")
        yield conn
    except psycopg.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database connection failed")
    finally:
        if conn:
            try:
                await conn.close()
                logger.info("Database connection closed")
            except psycopg.Error as e:
                logger.error(f"Error closing database connection: {e}")

async def execute_query(db, query, params=None):
    try:
        with db.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()  # Use fetchall for SELECT queries
            else:
                return None
    except psycopg.Error as e:
        logger.error(f"Database query failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database query failed")

@router.get("/{card_id}", response_model=Card, tags=["cards"])
async def read_card(card_id: int, db=Depends(get_db)):
    """
    Retrieve card information by ID.
    """
    try:
        logger.info(f"Fetching card information for card ID: {card_id}")
        rows = await execute_query(db, "SELECT card_id, status, balance, card_type, data FROM cards WHERE card_id = %s", (card_id,))

        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Card with ID {card_id} not found")

        card = rows[0]
        card_data = Card(card_id=card[0], status=card[1], balance=card[2], card_type=card[3], data=card[4])

        # Read additional data based on card type
        if card_data.card_type == "smartcard":
            try:
                smartcard_data = smartcard.read_smart_card_data(card_id)
                card_data.data = smartcard_data
            except smartcard.SmartCardError as e:
                logger.error(f"Error reading smartcard data: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read smartcard data: {e}")
            except Exception as e:
                logger.error(f"Unexpected error reading smartcard data: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error reading smartcard data")
        elif card_data.card_type == "nfc":
            try:
                nfc_data = nfc.read_nfc_card_data(card_id)
                card_data.data = nfc_data
            except nfc.NFCError as e:
                logger.error(f"Error reading NFC data: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read NFC data: {e}")
            except Exception as e:
                logger.error(f"Unexpected error reading NFC data: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error reading NFC data")

        return card_data

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in read_card: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred")

@router.post("/", response_model=Card, status_code=status.HTTP_201_CREATED, tags=["cards"])
async def create_card(card: Card, db=Depends(get_db)):
    """
    Create a new card.
    """
    try:
        logger.info("Creating a new card...")
        await execute_query(db, "INSERT INTO cards (card_id, status, balance, card_type, data) VALUES (%s, %s, %s, %s, %s)",
                            (card.card_id, card.status, card.balance, card.card_type, card.data))
        db.commit()
        return card
    except psycopg.errors.UniqueViolation as e:
        logger.error(f"Unique constraint violation in create_card: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card with this ID already exists")
    except Exception as e:
        logger.error(f"Error in create_card: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/{card_id}", response_model=Card, tags=["cards"])
async def update_card(card_id: int, card_update: Card, db=Depends(get_db)):
    """
    Update card information by ID.
    """
    try:
        logger.info(f"Updating card information for card ID: {card_id}")
        rows = await execute_query(db, "UPDATE cards SET status = %s, balance = %s, card_type = %s, data = %s WHERE card_id = %s RETURNING card_id",
                            (card_update.status, card_update.balance, card_update.card_type, card_update.data, card_id))
        db.commit()
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Card with ID {card_id} not found")
        return card_update
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in update_card: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{card_id}", response_model=Dict[str, str], tags=["cards"])
async def delete_card(card_id: int, db=Depends(get_db)):
    """
    Delete card by ID.
    """
    try:
        logger.info(f"Deleting card with card ID: {card_id}")
        rows = await execute_query(db, "DELETE FROM cards WHERE card_id = %s RETURNING card_id", (card_id,))
        db.commit()
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Card with ID {card_id} not found")
        return {"message": f"Card {card_id} deleted successfully"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in delete_card: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{card_id}/authenticate", tags=["cards"])
async def authenticate_card(card_id: int, pin: str):
    """
    Authenticate a smart card.
    """
    try:
        # Authenticate the smart card
        logger.info(f"Authenticating smart card with ID: {card_id}")
        is_authenticated = smartcard.authenticate_smart_card(card_id, pin)
        if is_authenticated:
            return {"message": "Authentication successful"}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")
    except smartcard.SmartCardError as e:
        logger.error(f"Error authenticating smart card: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error in authenticate_card: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/register", response_model=CardResponse)
async def register_card(card_create: CardCreate, db: Session = Depends(session_scope)):
    """Register a new card."""
    try:
        # Validate input data
        if not card_create.atr or not card_create.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ATR and user_id are required")

        # Check if card already exists
        existing_card = db.query(Card).filter_by(atr=card_create.atr).first()
        if existing_card:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card already registered")

        # Create new card
        new_card = Card(atr=card_create.atr, user_id=card_create.user_id, card_type=card_create.card_type)
        db.add(new_card)
        db.commit()
        db.refresh(new_card)

        return new_card
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/cards", response_model=List[CardResponse])
async def list_cards(db: Session = Depends(session_scope)):
    """List all registered cards."""
    try:
        cards = db.query(Card).all()
        return cards
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(card_id: int, db: Session = Depends(session_scope)):
    """Get a specific card by ID."""
    try:
        card = db.query(Card).filter_by(id=card_id).first()
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        return card
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/cards/{card_id}", response_model=CardResponse)
async def update_card_by_id(card_id: int, card_update: CardCreate, db: Session = Depends(session_scope)):
    """Update a specific card by ID."""
    try:
        card = db.query(Card).filter_by(id=card_id).first()
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

        card.atr = card_update.atr
        card.user_id = card_update.user_id
        card.card_type = card_update.card_type
        db.commit()
        db.refresh(card)

        return card
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: int, db: Session = Depends(session_scope)):
    """Delete a specific card by ID."""
    try:
        card = db.query(Card).filter_by(id=card_id).first()
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

        db.delete(card)
        db.commit()
        return
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))