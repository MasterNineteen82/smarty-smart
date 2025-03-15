import logging
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union

from fastapi import HTTPException
from app.core.smartcard_utils import CardConnectionError, CardDataError, CardAuthenticationError, SmartCardError
from app.utils.response_utils import error_response
from app.utils.exceptions import AuthenticationError, AuthorizationError, EncryptionError  # Import custom exceptions

logger = logging.getLogger(__name__)

def handle_card_exceptions(f):
    """
    Decorator for API routes to handle card-related exceptions consistently.
    
    Catches specific exceptions and converts them to appropriate HTTP responses
    with standardized error payloads.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Value error in {f.__name__}: {e}")
            raise HTTPException(
                status_code=400, 
                detail=error_response("ValueError", str(e), "Check input values")
            )
        except KeyError as e:
            logger.warning(f"Key error in {f.__name__}: {e}")
            raise HTTPException(
                status_code=400, 
                detail=error_response("KeyError", str(e), "Check required parameters")
            )
        except CardConnectionError as e:
            logger.error(f"Card connection error in {f.__name__}: {e}")
            suggestion = "Ensure card is properly placed on reader"
            if hasattr(e, 'reader_status') and e.reader_status:
                suggestion = f"{suggestion}. Reader status: {e.reader_status}"
            raise HTTPException(
                status_code=500, 
                detail=error_response("CardConnectionError", str(e), suggestion)
            )
        except CardDataError as e:
            logger.error(f"Card data error in {f.__name__}: {e}")
            suggestion = "Card data may be corrupted or in an invalid format"
            raise HTTPException(
                status_code=400, 
                detail=error_response("CardDataError", str(e), suggestion)
            )
        except CardAuthenticationError as e:
            logger.error(f"Card authentication error in {f.__name__}: {e}")
            suggestion = "Check authentication credentials"
            raise HTTPException(
                status_code=401, 
                detail=error_response("CardAuthenticationError", str(e), suggestion)
            )
        except AuthenticationError as e:
            logger.warning(f"Authentication error in {f.__name__}: {e}")
            raise HTTPException(
                status_code=401,
                detail=error_response("AuthenticationError", str(e), "Invalid credentials")
            )
        except AuthorizationError as e:
            logger.warning(f"Authorization error in {f.__name__}: {e}")
            raise HTTPException(
                status_code=403,
                detail=error_response("AuthorizationError", str(e), "Insufficient permissions")
            )
        except EncryptionError as e:
            logger.error(f"Encryption error in {f.__name__}: {e}")
            raise HTTPException(
                status_code=500,
                detail=error_response("EncryptionError", str(e), "Encryption or decryption failed")
            )
        except SmartCardError as e:
            logger.error(f"Smart card error in {f.__name__}: {e}")
            raise HTTPException(
                status_code=500, 
                detail=error_response("SmartCardError", str(e), "Check card and reader")
            )
        except Exception as e:
            # Log the full traceback for unexpected exceptions
            logger.exception(f"Unexpected exception in {f.__name__}: {e}")
            
            # Provide a helpful suggestion based on error patterns
            suggestion = "Please contact support if the issue persists"
            error_str = str(e).lower()
            
            if "no card present" in error_str:
                suggestion = "Please place a card on the reader"
            elif "connection failed" in error_str or "timeout" in error_str:
                suggestion = "Check if reader is properly connected"
            elif "permission" in error_str:
                suggestion = "Check application permissions"
            
            raise HTTPException(
                status_code=500,
                detail=error_response(
                    e.__class__.__name__, 
                    str(e), 
                    suggestion,
                    {"traceback": traceback.format_exc().splitlines()[-3:]}
                )
            )
    
    return decorated_function