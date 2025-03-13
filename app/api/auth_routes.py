from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional, Dict, Any, List

import logging
from pydantic import BaseModel, validator

# Update this line to include SecurityManager
from app.security_manager import AuthenticationError, get_security_manager, SecurityManager
from app.db import session_scope, User
from sqlalchemy.orm import Session

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


# Route for user login
@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    security_manager: SecurityManager = Depends(get_security_manager),
):
    """
    User login route.
    """
    try:
        if await security_manager.authenticate_user(
            form_data.username, form_data.password
        ):
            access_token = "test_token"
            return {"access_token": access_token, "token_type": "bearer"}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Route for user registration
@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user: User, db: Session = Depends(get_db)):
    """
    User registration route.
    """
    try:
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        db_user = User(username=user.username, email=user.email)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )