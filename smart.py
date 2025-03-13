from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import Optional
import logging

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

# Include other API routes
from app.api import card_routes
app.include_router(card_routes.router, prefix="/cards", tags=["cards"])

# Dependency to simulate database interaction (replace with actual database)
async def fake_dependency():
    try:
        # Simulate database connection or other setup
        logger.info("Simulating database dependency...")
        # Simulate potential failure during dependency setup
        if False:  # Simulate failure condition
            raise Exception("Simulated database connection error")
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
        logger.exception("Error in read_root")  # Log the full exception traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",  # Generic error message for security
        )

@app.get("/items/{item_id}", tags=["items"])
async def read_item(item_id: int, q: Optional[str] = None, dependency=Depends(fake_dependency)):
    try:
        if item_id < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item ID must be non-negative",
            )
        # Simulate item not found
        if item_id == 999:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        return {"item_id": item_id, "q": q}
    except HTTPException as http_exception:
        raise http_exception  # Re-raise HTTPExceptions
    except ValueError as ve:  # Catch potential ValueErrors, e.g., invalid item_id
        logger.warning(f"Invalid input: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid input"
        )
    except Exception as e:
        logger.exception(f"Error in read_item with item_id {item_id}")  # Log full traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",  # Generic error message
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

# Add a generic exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Generic Exception: {type(exc).__name__} - {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal Server Error"},
    )