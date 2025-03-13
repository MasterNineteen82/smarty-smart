import os
import sys
import logging

# Adjust Python path
venv_path = os.path.join(os.getcwd(), 'venv', 'lib', 'site-packages')
python_path = [venv_path] + sys.path
sys.path = list(set(python_path))  # Remove duplicates by converting to a set

logger = logging.getLogger('app')
logger.setLevel(logging.DEBUG)  # Set the minimum log level

# Create a console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(ch)

logger.debug(f"venv_path: {venv_path}")
logger.debug(f"Python path: {sys.path}")

try:
    from app.api import card_routes  # Import the card routes
    from app.api import auth_routes
    # from app.api import config_routes # Import config routes - REMOVED
except ImportError as e:
    logger.error(f"Failed to import routes: {e}")
    print(f"Error: {e}. Ensure 'routes.py' exists and has a router named 'router'. Also, check dependencies.")
    sys.exit(1)

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import argparse
import uvicorn
# from app.api import logs_routes # Import logs routes - REMOVED
from app.core.card_manager import card_manager  # Import card manager
from app.core.card_utils import config  # Import config
from app.db import init_db
from contextlib import asynccontextmanager

# Initialize security manager outside lifespan
security_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global security_manager
    # Startup event
    logger.info("Starting up the application...")
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Initialize SecurityManager here, after env vars are loaded
    from app.security_manager import SecurityManager, get_security_manager  # Use get_security_manager instead
    security_manager = get_security_manager()

    # Persist key if it was generated
    if os.environ.get("SMARTCARD_ENCRYPTION_KEY") is None:
        security_manager.persist_key()

    yield

    # Shutdown event
    logger.info("Shutting down the application...")
    # Perform cleanup tasks here
    logger.info("Application shutdown completed.")

app = FastAPI(
    title="Smart Card Manager API",
    description="API for managing smart cards",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# app.include_router(logs_routes.router, prefix="/logs", tags=["logs"]) # Include logs routes - REMOVED
app.include_router(card_routes.router, prefix="/cards", tags=["cards"])  # Include card routes
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])  # Include auth routes

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
    return JSONResponse(status_code=500, content={"message": exc.detail})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Card Manager API")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)