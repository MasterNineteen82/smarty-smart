from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
import argparse
import logging
import uvicorn

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

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Generic Exception: {type(exc).__name__} - {exc}")
    return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Card Manager API")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)