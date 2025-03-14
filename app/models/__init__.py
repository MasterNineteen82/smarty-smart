from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import logging

app = FastAPI()
router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@router.get("/test")
async def test_route():
    try:
        # Simulate some processing
        result = {"message": "Test route working"}
        logger.info("Test route accessed successfully")
        return result
    except Exception as e:
        logger.error(f"Error in test_route: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Serve frontend static files
@app.get("/{file_path:path}")
async def serve_frontend(file_path: str):
    try:
        file_location = f"frontend/{file_path}"
        return FileResponse(file_location)
    except Exception as e:
        logger.error(f"Error serving file {file_path}: {e}")
        raise HTTPException(status_code=404, detail="File not found")

app.include_router(router)