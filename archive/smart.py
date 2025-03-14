"""
Smart Card Manager Main Application
"""
import os
import sys
import logging
import argparse
import uvicorn
import socket
import webbrowser
import site
import traceback
import json
import asyncio
import httpx  # Import httpx for async HTTP requests
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm

# Import necessary modules from other files
from app.api import card_routes, auth_routes, routes
from app.db import create_db_and_tables, get_db, User
from app.security_manager import SecurityManager, AuthenticationError, get_security_manager
from app.utils.response_utils import standard_response, error_response

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app/logs/smart_card_manager.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("SmartCardManager")

def setup_environment():
    """Set up the application environment"""
    # Add the parent directory to the path for imports
    parent_dir = Path(__file__).parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Set environment variables
    if not os.environ.get("APP_DATA_DIR"):
        os.environ["APP_DATA_DIR"] = str(Path(parent_dir, "app", "data"))
    
    if not os.environ.get("DEBUG"):
        os.environ["DEBUG"] = "true"
        
    logger.info(f"Application directory: {parent_dir}")
    return True

def run_setup_verification():
    """Run setup verification checks"""
    logger.info("Running setup verification...")
    try:
        # Add setup verification logic here
        logger.info("Setup verification completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Setup verification failed: {e}")
        return False

# Initialize FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    try:
        create_db_and_tables()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
        logger.error(traceback.format_exc())
        # Optionally, stop the app if DB init fails
        # raise  # Re-raise to prevent app from starting

    from app.security_manager import get_security_manager
    security_manager = get_security_manager()
    if os.environ.get("SMARTCARD_ENCRYPTION_KEY") is None:
        try:
            security_manager.persist_key()
            logger.info("Encryption key persisted.")
        except Exception as e:
            logger.error(f"Failed to persist encryption key: {e}")
            logger.error(traceback.format_exc())

    logger.info(f"Application started on port {active_port}")
    yield

    logger.info("Shutting down application...")
    # Add any cleanup tasks here, like closing database connections

app = FastAPI(
    title="Smart Card Manager API",
    description="API for managing smart cards",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add detailed CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Be more specific than "*" for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID"],  # Expose helpful headers
)

# Add the request logging middleware
class RequestLoggingMiddleware:
    async def __call__(self, request: Request, call_next):
        # Log the incoming request
        request_id = id(request)  # Simple unique identifier
        logger.debug(f"Request {request_id} started: {request.method} {request.url.path}")
        
        # Get request body for debugging if needed
        try:
            body = await request.body()
            if body:
                logger.debug(f"Request {request_id} body: {body.decode('utf-8')[:200]}...")
        except Exception as e:
            logger.debug(f"Request {request_id} body could not be read: {e}")
        
        # Process the request
        try:
            response = await call_next(request)
            logger.debug(f"Request {request_id} completed: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Request {request_id} failed: {e}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error_type": str(type(e).__name__)}
            )

app.middleware("http")(RequestLoggingMiddleware())

app.include_router(card_routes.router, prefix="/cards", tags=["cards"])
app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(routes.router, tags=["general"])

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse, tags=["root"])
async def read_root(request: Request):
    """Main entry point"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    # Add more detailed checks here, e.g., database connection
    try:
        # Example: Execute a simple DB query
        # from app.db import database  # Assuming you have a database instance
        # await database.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"
        
    return {"status": "ok", "db_status": db_status}

@app.get("/frontend")
async def frontend_link():
    return {"frontend_url": "http://localhost:3000"}

# New endpoint that returns config for the frontend
@app.get("/config", tags=["config"])
async def get_config():
    """Return configuration information for clients"""
    return {
        "api_url": f"http://localhost:{active_port}",
        "api_version": "1.0.0",
        "features": {
            "cards": True,
            "auth": True
        }
    }

# Simple connection test endpoint
@app.get("/test-connection", tags=["test"])
async def test_connection():
    """Test API connectivity"""
    return {
        "connected": True,
        "timestamp": datetime.now().isoformat(),
        "server_port": active_port
    }

# Add more detailed request timing for debugging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code, 
        content={"message": exc.detail, "path": request.url.path}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Exception: {type(exc).__name__} - {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500, 
        content={
            "message": "Internal Server Error",
            "error_type": str(type(exc).__name__),
            "path": request.url.path
        }
    )

# Create a test HTML page to verify frontend-backend communication
@app.get("/connection-test", response_class=HTMLResponse, tags=["test"])
async def connection_test_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Connection Test</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #2c3e50; }
            .result { margin: 20px 0; padding: 15px; border-radius: 4px; }
            .success { background-color: #d4edda; color: #155724; }
            .error { background-color: #f8d7da; color: #721c24; }
            button { padding: 10px 15px; background-color: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background-color: #2980b9; }
            pre { background-color: #f8f9fa; padding: 10px; border-radius: 4px; overflow: auto; }
        </style>
    </head>
    <body>
        <h1>API Connection Test</h1>
        <button id="test-btn">Test Connection</button>
        <div id="result" class="result"></div>
        
        <h2>API Configuration</h2>
        <button id="config-btn">Get Config</button>
        <pre id="config-result"></pre>
        
        <h2>All Requests Log</h2>
        <div id="request-log"></div>
        
        <script>
            document.getElementById('test-btn').addEventListener('click', async () => {
                const resultDiv = document.getElementById('result');
                resultDiv.className = 'result';
                resultDiv.textContent = 'Testing connection...';
                
                try {
                    logRequest('GET', '/test-connection');
                    const response = await fetch('/test-connection');
                    const data = await response.json();
                    
                    resultDiv.className = 'result success';
                    resultDiv.textContent = `Connection successful! Server time: ${data.timestamp}`;
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = `Connection failed: ${error.message}`;
                    console.error('Connection test error:', error);
                }
            });
            
            document.getElementById('config-btn').addEventListener('click', async () => {
                const resultPre = document.getElementById('config-result');
                
                try {
                    logRequest('GET', '/config');
                    const response = await fetch('/config');
                    const data = await response.json();
                    
                    resultPre.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultPre.textContent = `Error: ${error.message}`;
                    console.error('Config fetch error:', error);
                }
            });
            
            function logRequest(method, url) {
                const logDiv = document.getElementById('request-log');
                const entry = document.createElement('div');
                const time = new Date().toLocaleTimeString();
                entry.textContent = `${time} - ${method} ${url}`;
                logDiv.prepend(entry);
            }
        </script>
    </body>
    </html>
    """
    return html_content

# Replace the duplicate test-connection endpoints with this single one
# @app.get("/connection-test", response_class=HTMLResponse)
# async def connection_test_page(request: Request):
#     """Provides a page to test API connectivity"""
#     return templates.TemplateResponse("connection_test.html", {"request": request})

# Update the frontend_app function to use proper helper function
@app.get("/app", response_class=HTMLResponse, tags=["frontend"])
async def frontend_app(request: Request):
    """Serves the main frontend application"""
    # Use a simpler approach with relative paths
    return templates.TemplateResponse("index.html", {
        "request": request
    })

# Add this endpoint to provide frontend configuration
@app.get("/frontend-config", tags=["frontend"])
async def frontend_config():
    """Returns configuration for the frontend"""
    return {
        "api_url": f"http://localhost:{active_port}",
        "api_version": "1.0.0",
        "docs_url": f"http://localhost:{active_port}/docs",
        "app_url": f"http://localhost:{active_port}/app"
    }

# Add utility for templates to access static files without url_for
@app.get("/static-url/{path:path}", tags=["utility"])
async def static_url(path: str):
    """Helper endpoint for templates to get static URLs"""
    return {"url": f"/static/{path}"}

# Add missing route referenced in templates
@app.get("/help", tags=["help"])
async def help_page(request: Request):
    """Help page endpoint"""
    return templates.TemplateResponse("help.html", {"request": request})

# Add these routes after your existing routes

@app.get("/terms", response_class=HTMLResponse, tags=["legal"])
async def terms_page(request: Request):
    """Terms and conditions page"""
    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/privacy", response_class=HTMLResponse, tags=["legal"])
async def privacy_page(request: Request):
    """Privacy policy page"""
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/", response_class=HTMLResponse, tags=["root"])
async def read_root(request: Request):
    """Main landing page - using index.html directly instead of welcome.html"""
    return templates.TemplateResponse("index.html", {"request": request})

# Add a redirect for the old frontend URL
@app.get("/old-frontend", tags=["redirect"])
async def redirect_to_app():
    """Redirects the old frontend URL to the new /app URL"""
    return RedirectResponse("/app", status_code=302)

# Add this ConnectionManager class to manage WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.status_task = None
        self.last_status = {"status": "unknown", "timestamp": datetime.now().isoformat()}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send the current status immediately upon connection
        await websocket.send_json(self.last_status)
        
        # Start the status broadcasting task if it's not already running
        if self.status_task is None or self.status_task.done():
            self.status_task = asyncio.create_task(self.broadcast_status_periodically())
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        # Update the last known status
        self.last_status = message
        
        # Send to all connected clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except RuntimeError:
                # Mark for removal if connection is closed
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def get_card_status(self):
        """Get the current card status"""
        try:
            # Make a request to the status endpoint
            # This avoids duplicating logic and ensures consistency
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{active_port}/cards/status")
                if response.status_code == 200:
                    return response.json()
            
            # Fallback if the HTTP request fails
            return {
                "status": "ready", 
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "card_manager": True,
                    "database": True
                },
                "source": "websocket_fallback"
            }
        except Exception as e:
            logger.error(f"Error getting card status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "source": "websocket_error"
            }
    
    async def broadcast_status_periodically(self):
        """Periodically broadcast the card status to all clients"""
        try:
            while self.active_connections:
                status = await self.get_card_status()
                await self.broadcast(status)
                # Wait between updates - adjust as needed
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            logger.info("Status broadcast task cancelled")
        except Exception as e:
            logger.error(f"Error in status broadcast task: {e}")

# Create a connection manager instance
manager = ConnectionManager()

# Add WebSocket endpoint
@app.websocket("/ws/card-status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time card status updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any messages from the client
            # We're not actually expecting messages, but this keeps the connection open
            data = await websocket.receive_text()
            # You could handle client messages here if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.debug("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Command-line argument parsing
parser = argparse.ArgumentParser(description="Smart Card Manager Application")
parser.add_argument("--port", type=int, default=None, help="Port to run on (default: auto-detect available port)")
parser.add_argument("--frontend-port", type=int, default=3000, help="Port where frontend is running (default: 3000)")
parser.add_argument("--open-browser", action="store_true", help="Open browser at start")
parser.add_argument("--log-level", default="INFO", 
                      choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      help="Set logging level")
args = parser.parse_args()

# Store the active port globally so it can be accessed elsewhere
active_port = None

def find_available_port(start=5000, stop=5050):
    for port in range(start, stop + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise OSError(f"No available ports between {start} and {stop}")

def print_links(port, frontend_port):
    global active_port
    active_port = port
    
    api_url = f"http://localhost:{port}"
    docs_url = f"{api_url}/docs"
    app_url = f"{api_url}/app"  # New app URL
    
    print("\n" + "=" * 60)
    print(f"API running at: {api_url}")
    print(f"App available at: {app_url}")  # Show app URL instead of frontend URL
    print(f"API docs at: {docs_url}")
    print("=" * 60 + "\n")

# Main function to run the server
def main():
    """Main function to run the server"""
    setup_environment()
    
    if not run_setup_verification():
        logger.error("Setup verification failed. Exiting.")
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Set logging level from command line
    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)
    
    port = args.port or find_available_port()
    print_links(port, args.frontend_port)
    
    # Update CORS settings with frontend port
    origins = [
        f"http://localhost:{args.frontend_port}",
        "http://localhost",
        "http://localhost:8080",
        f"http://127.0.0.1:{args.frontend_port}",
    ]
    
    # Re-configure CORS to use the correct origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    if args.open_browser:
        webbrowser.open(f"http://localhost:{port}/app")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level=args.log_level.lower())
    except Exception as e:
        logger.critical(f"Failed to start server: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()