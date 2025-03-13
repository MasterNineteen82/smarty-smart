"""
Database integration module for the Smartcard Manager application.

This module uses SQLAlchemy to handle the database connection and define the database models.
"""

import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy.pool import QueuePool

from app.config import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW
from app.core.config_utils import config  # Import the config object

# Get the database URL from the environment or use a default
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./test.db")

# Configure logging
logger = logging.getLogger(__name__)

# Database engine with connection pooling
try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True  # Verify connections before using them
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Base class for declarative models
Base = declarative_base()

# Session factory
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()

class User(Base):
    """
    Represents a user in the database.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password = Column(String(256), nullable=False)  # Store hashed passwords
    email = Column(String(120), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationship with cards
    cards = relationship("Card", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

class Card(Base):
    """
    Represents a smart card in the database.
    """
    __tablename__ = 'cards'

    id = Column(Integer, primary_key=True)
    atr = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    is_blocked = Column(Boolean, default=False)
    last_used = Column(DateTime, nullable=True)
    
    # Relationship with user
    user = relationship("User", back_populates="cards")

    def __repr__(self):
        return f"<Card(id={self.id}, atr='{self.atr}', user_id={self.user_id})>"

def init_db():
    """
    Initializes the database by creating the tables.
    """
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

# Initialize database only if this module is executed directly
if __name__ == "__main__":
    init_db()