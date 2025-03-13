import sys
import os

# Add the virtual environment's site-packages directory to the Python path
venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "lib", "site-packages")
print(f"venv_path: {venv_path}")  # Print the venv_path for verification
sys.path.insert(0, venv_path)

print(f"Python path: {sys.path}")  # Print the Python path for verification

import os
import logging
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import argparse
import uvicorn
from app.api import card_routes  # Import the card routes
from app.api import config_routes # Import config routes
from app.api import logs_routes # Import logs routes
from app.core.card_manager import card_manager # Import card manager
from app.core.config_utils import config # Import config
from app.db import create_db_and_tables

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Card Manager API",
    description="API for managing smart cards",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(card_routes.router, prefix="/cards", tags=["cards"]) # Include card routes
app.include_router(config_routes.router, prefix="/config", tags=["config"]) # Include config routes
app.include_router(logs_routes.router, prefix="/logs", tags=["logs"]) # Include logs routes

app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency to simulate database interaction
async def fake_dependency():
    try:
        logger.info("Simulating database dependency...")
        yield
    except Exception as e:
        logger.error(f"Dependency failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database dependency failed: {e}",
        )

@app.get("/", tags=["root"])
async def read_root(dependency=Depends(fake_dependency)):
    try:
        return {"message": "Welcome to Smart Card Manager API"}
    except Exception as e:
        logger.exception("Error in read_root")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Generic Exception: {type(exc).__name__} - {exc}")
    return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the application...")
    # Initialize the card manager on startup
    await card_manager.initialize()
    # Create database tables
    create_db_and_tables()
    logger.info("Application startup completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Card Manager API")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)