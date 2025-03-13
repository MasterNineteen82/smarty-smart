from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging

from app.api import card_routes, auth_routes
from app.db import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# CORS middleware
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",  # Add your frontend URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(card_routes.router, prefix="/cards", tags=["cards"])
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])

# Lifespan event handler
@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.
    """
    logger.info("Starting up application...")
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    logger.info("Application started successfully.")