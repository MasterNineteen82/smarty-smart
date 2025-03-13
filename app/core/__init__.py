from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
import os

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
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev_key'),
    }
    return config

app.state.config = load_configuration()

@app.exception_handler(HTTPException)
async def handle_http_exception(request, exc):
    logger.error(f"HTTPException: {exc.detail} (status code: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "description": exc.detail},
    )

@app.exception_handler(Exception)
async def handle_generic_exception(request, exc):
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
