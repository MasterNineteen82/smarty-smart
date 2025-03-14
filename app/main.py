import os
import logging
import webbrowser
from fastapi import FastAPI, Request
import traceback
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api import card_routes, auth_routes
from app.db import init_db
from app.utils.response_utils import error_response, standard_response

# Set logging level based on environment
log_level = logging.DEBUG if os.getenv("ENV") == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

app = FastAPI()

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
origins = [
    frontend_url,
    "http://localhost",
    "http://localhost:8080",
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

# Health check route
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint to verify API is operational"""
    return standard_response(
        message="API service is operational",
        data={
            "status": "ok",
            "version": "1.0.0",
            "uptime": "X hours"
        }
    )

# Global exception handler
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Standardize HTTP exceptions (like 404 Not Found)"""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(exc.detail),
            error_type=f"HTTP{exc.status_code}Error",
            suggestion="Please check your request and try again"
        )
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Standardize validation errors"""
    return JSONResponse(
        status_code=422,
        content=error_response(
            message="Request validation error",
            error_type="ValidationError",
            suggestion="Please check the request parameters and try again"
        )
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Catch-all handler for unhandled exceptions"""
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content=error_response(
            message="An unexpected error occurred",
            error_type="ServerError",
            suggestion="Please try again later or contact support"
        )
    )

@app.on_event("startup")
async def startup_event():
    logger.debug("Running startup initialization.")
    try:
        init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"DB init failed: {e}")
        return

    logger.info("App started.")
    if os.getenv("ENV") == "development":
        webbrowser.open("http://localhost:8000/app")
