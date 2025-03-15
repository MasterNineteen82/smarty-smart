from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional, Dict, Any, List
from fastapi.responses import JSONResponse

import logging
from pydantic import BaseModel, validator

# Update this line to include SecurityManager
# from app.security_manager import AuthenticationError, get_security_manager, SecurityManager
from app.db import session_scope, User
from sqlalchemy.orm import Session
# Import response utilities from the common module
from app.utils.response_utils import standard_response, error_response

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Define a Pydantic model for user data
class User(BaseModel):
    id: int
    username: str
    email: Optional[str] = None

    class Config:
        from_attributes = True

# Pydantic models for request and response data
class Token(BaseModel):
    access_token: str
    token_type: str


# Dependency to get database session
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


#"""
# Route for user login
#@router.post("/token")
#async def login(
#    form_data: OAuth2PasswordRequestForm = Depends(),
#    security_manager: SecurityManager = Depends(get_security_manager),
#):
#    """
#    User login route.
#    """
#    try:
#        if await security_manager.authenticate_user(
#            form_data.username, form_data.password
#        ):
#            access_token = "test_token"
#            return standard_response(
#                message="Login successful",
#                data={"access_token": access_token, "token_type": "bearer"}
#            )
#        else:
#            return JSONResponse(
#                status_code=status.HTTP_401_UNAUTHORIZED,
#                content=error_response(
#                    message="Incorrect username or password",
#                    error_type="AuthenticationError"
#                ),
#                headers={"WWW-Authenticate": "Bearer"}
#            )
#    except AuthenticationError as e:
#        raise HTTPException(
#            status_code=status.HTTP_401_UNAUTHORIZED,
#            detail=str(e),
#            headers={"WWW-Authenticate": "Bearer"},
#        )
#    except Exception as e:
#        logger.error(f"Login failed: {e}")
#        raise HTTPException(
#            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#            detail="Internal server error",
#        )
#"""


# Route for user registration
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: User, db: Session = Depends(get_db)):
    """
    User registration route.
    """
    try:
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message="Username already taken",
                    error_type="UserExistsError",
                    suggestion="Please choose a different username"
                )
            )

        db_user = User(username=user.username, email=user.email)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Convert to dict for response
        user_data = {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email
        }
        
        return standard_response(
            message="User registered successfully",
            data=user_data
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to register user",
                error_type="ServerError",
                suggestion="Please try again later or contact support"
            )
        )