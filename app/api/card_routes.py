from fastapi import APIRouter, Depends, status
from typing import Optional, Dict, Any, List
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
# Renamed import to avoid confusion
from app.models.card import Card as CardModel 
from pydantic import BaseModel, validator
#from app.core.card_manager import CardManager, card_manager
#from app.security_manager import SecurityManager, get_security_manager  # Updated import statement
from app.db import session_scope, Card, Session
#from app.utils.exceptions import CardError, InvalidInputError
# Import response utils
from fastapi.responses import JSONResponse
from app.utils.response_utils import standard_response, error_response

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic model for API
class Card(BaseModel):
    id: int
    atr: str
    user_id: int
    status: str

    class Config:
        from_attributes = True

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

# Helper function for consistent card model conversion
def card_model_to_dict(db_card):
    """Convert CardModel to dict for API response"""
    return {
        "id": db_card.id,
        "atr": db_card.atr,
        "user_id": db_card.user_id,
        "status": db_card.status
    }

# Dependency to get database session
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()

# Important: Define specific routes before parameterized routes
@router.get("/status", tags=["cards"])
async def get_card_status():
    """Get the status of card services without accessing DB"""
    try:
        # Keep existing logic
        return standard_response(
            message="Card status retrieved successfully",
            data={
                "status": "ready", 
                "timestamp": str(datetime.now()),
                "services": {
                    "card_manager": True,
                    "database": True
                }
            }
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to get card status",
                error_type="CardStatusError",
                suggestion="Please try again or contact support"
            )
        )

# # Route for registering a new card
# @router.post("/register", status_code=status.HTTP_201_CREATED)
# async def register_card(card: Card, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
#     """Register a new card."""
#     logger.info(f"Registering new card with ATR: {card.atr}")
#     try:
#         # Keep existing logic
#         success, message = card_manager.register_new_card(card.atr, card.user_id)
#         if success:
#             logger.info(f"Card registered successfully: {card.atr}")
#             db_card = db.query(CardModel).filter(CardModel.atr == card.atr).first()
#             
#             # Convert to dict for response
#             card_data = card_model_to_dict(db_card)
#             
#             return standard_response(
#                 message="Card registered successfully",
#                 data=card_data
#             )
#         else:
#             logger.warning(f"Card registration failed: {message}")
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content=error_response(
#                     message=message,
#                     error_type="CardRegistrationError",
#                     suggestion="Please check the card parameters and try again"
#                 )
#             )
#     except Exception as e:
#         logger.error(f"Registration failed: {e}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content=error_response(
#                 message="Card registration failed",
#                 error_type="ServerError",
#                 suggestion="Please try again later or contact support"
#             )
#         )

# Now this won't match '/status' anymore
@router.get("/{atr}")
async def get_card(atr: str, db: Session = Depends(get_db)):
    """Get a card by ATR."""
    try:
        # Debug the specific exception
        logger.info(f"Attempting to query card with ATR: {atr}")
        
        # Add logging to see what's happening in the database
        logger.debug(f"Database session valid: {db is not None}")
        
        # Use a more robust query approach with error details
        try:
            # Try a simpler query first to test DB connectivity
            count = db.query(CardModel).count()
            logger.debug(f"Total cards in database: {count}")
            
            # Now try the specific query
            db_card = db.query(CardModel).filter(CardModel.atr == atr).first()
            # Continue with existing logic...
            
        except Exception as db_error:
            logger.error(f"Database query error: {str(db_error)}")
            raise db_error
            
        if db_card:
            logger.info(f"Card found: {atr}")
            
            # Convert to dict for response using helper function
            card_data = card_model_to_dict(db_card)
            
            return standard_response(
                message="Card found successfully",
                data=card_data
            )
        else:
            logger.warning(f"Card not found: {atr}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message="Card not found",
                    error_type="NotFoundError",
                    suggestion="Check the ATR and try again"
                )
            )
    except Exception as e:
        logger.error(f"Failed to get card: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to retrieve card information",
                error_type="ServerError",
                suggestion="Please try again later"
            )
        )

# # Route for activating a card
# @router.post("/{atr}/activate")
# async def activate_card(atr: str, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
#     """Activate a card."""
#     logger.info(f"Activating card with ATR: {atr}")
#     try:
#         # Activate the card using the CardManager
#         success, message = card_manager.activate_inactive_card(atr)
#         if success:
#             logger.info(f"Card activated successfully: {atr}")
#             # Retrieve the activated card from the database
#             db_card = db.query(CardModel).filter(CardModel.atr == atr).first()
#             
#             # Convert to dict for response
#             card_data = card_model_to_dict(db_card)
#             
#             return standard_response(
#                 message="Card activated successfully",
#                 data=card_data
#             )
#         else:
#             logger.warning(f"Card activation failed: {message}")
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content=error_response(
#                     message=message,
#                     error_type="CardActivationError",
#                     suggestion="Check if the card is in the correct state for activation"
#                 )
#             )
#     except Exception as e:
#         logger.error(f"Activation failed: {e}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content=error_response(
#                 message="Failed to activate card",
#                 error_type="ServerError",
#                 suggestion="Please try again later or contact support"
#             )
#         )
# 
# # Route for deactivating a card
# @router.post("/{atr}/deactivate")
# async def deactivate_card(atr: str, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
#     """Deactivate a card."""
#     logger.info(f"Deactivating card with ATR: {atr}")
#     try:
#         # Deactivate the card using the CardManager
#         success, message = card_manager.deactivate_active_card(atr)
#         if success:
#             logger.info(f"Card deactivated successfully: {atr}")
#             # Retrieve the deactivated card from the database
#             db_card = db.query(CardModel).filter(CardModel.atr == atr).first()
#             
#             # Convert to dict for response
#             card_data = card_model_to_dict(db_card)
#             
#             return standard_response(
#                 message="Card deactivated successfully",
#                 data=card_data
#             )
#         else:
#             logger.warning(f"Card deactivation failed: {message}")
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content=error_response(
#                     message=message,
#                     error_type="CardDeactivationError",
#                     suggestion="Check if the card is in the correct state for deactivation"
#                 )
#             )
#     except Exception as e:
#         logger.error(f"Deactivation failed: {e}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content=error_response(
#                 message="Failed to deactivate card",
#                 error_type="ServerError",
#                 suggestion="Please try again later or contact support"
#             )
#         )
# 
# # Route for blocking a card
# @router.post("/{atr}/block")
# async def block_card(atr: str, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
#     """Block a card."""
#     logger.info(f"Blocking card with ATR: {atr}")
#     try:
#         # Block the card using the CardManager
#         success, message = card_manager.block_active_card(atr)
#         if success:
#             logger.info(f"Card blocked successfully: {atr}")
#             # Retrieve the blocked card from the database
#             db_card = db.query(CardModel).filter(CardModel.atr == atr).first()
#             
#             # Convert to dict for response
#             card_data = card_model_to_dict(db_card)
#             
#             return standard_response(
#                 message="Card blocked successfully",
#                 data=card_data
#             )
#         else:
#             logger.warning(f"Card blocking failed: {message}")
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content=error_response(
#                     message=message,
#                     error_type="CardBlockError",
#                     suggestion="Check if the card is in the correct state for blocking"
#                 )
#             )
#     except Exception as e:
#         logger.error(f"Blocking failed: {e}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content=error_response(
#                 message="Failed to block card",
#                 error_type="ServerError",
#                 suggestion="Please try again later or contact support"
#             )
#         )
# 
# # Route for unblocking a card
# @router.post("/{atr}/unblock")
# async def unblock_card(atr: str, db: Session = Depends(get_db), card_manager: CardManager = Depends(lambda: card_manager)):
#     """Unblock a card."""
#     logger.info(f"Unblocking card with ATR: {atr}")
#     try:
#         # Unblock the card using the CardManager
#         success, message = card_manager.unblock_blocked_card(atr)
#         if success:
#             logger.info(f"Card unblocked successfully: {atr}")
#             # Retrieve the unblocked card from the database
#             db_card = db.query(CardModel).filter(CardModel.atr == atr).first()
#             
#             # Convert to dict for response
#             card_data = card_model_to_dict(db_card)
#             
#             return standard_response(
#                 message="Card unblocked successfully",
#                 data=card_data
#             )
#         else:
#             logger.warning(f"Card unblocking failed: {message}")
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content=error_response(
#                     message=message,
#                     error_type="CardUnblockError",
#                     suggestion="Check if the card is in the correct state for unblocking"
#                 )
#             )
#     except Exception as e:
#         logger.error(f"Unblocking failed: {e}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content=error_response(
#                 message="Failed to unblock card",
#                 error_type="ServerError",
#                 suggestion="Please try again later or contact support"
#             )
#         )