from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os

app = FastAPI()

# Logging Configuration
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
try:
    log_level = getattr(logging, log_level)
except AttributeError:
    log_level = logging.INFO
    logging.warning("Invalid log level specified. Defaulting to INFO.")

logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Custom Middleware Example (can be expanded)
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status code: {response.status_code}")
        return response

# Register Middleware
app = FastAPI(middleware=[Middleware(LoggingMiddleware)])

# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.exception(exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "description": str(exc.detail)},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.exception(exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "description": str(exc)},
    )

# Health Check Endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Include your routes
# from . import card_routes
# from . import auth_routes
# from .routes import router
# app.include_router(router)
# from . import config_routes # Remove config routes
