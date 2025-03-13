from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
import os

# Use lazy imports to avoid circular dependencies
def get_models():
    from . import models
    return models

def get_api():
    from . import api
    return api

def get_core():
    from . import core
    return core

# Define __all__ to control which modules are imported with "from app import *"
__all__ = ["get_models", "get_api", "get_core"]

app = FastAPI()

def configure_logging():
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = configure_logging()

def load_configuration():
    config = {
        "SECRET_KEY": os.environ.get("SECRET_KEY", "dev_key"),
        # Add other default configs here, e.g., DATABASE_URL
    }
    return config

app.state.config = load_configuration()

def register_routes():
    try:
        from .routes import router
        app.include_router(router)
    except ImportError as e:
        logger.error(f"Failed to import routes: {e}")
        print(f"Error: {e}. Ensure 'routes.py' exists and has a router named 'router'. Also, check dependencies.")

register_routes()

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handles HTTP exceptions, returning JSON responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "description": exc.detail},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handles all other exceptions, logging them and returning a generic error."""
    logger.exception(f"An unexpected error occurred: {exc}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "description": "Internal Server Error"},
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)