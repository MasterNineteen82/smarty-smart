"""
Smart Card Manager Main Application
"""
import os
import sys
import logging
import argparse
import uvicorn
from pathlib import Path

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
    parent_dir = Path(__file__).parent.parent
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
        # Use simple checker to avoid Unicode issues
        import subprocess
        result = subprocess.run([sys.executable, "simple_checker.py"], 
                               capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error("Setup checker reported issues.")
            print("\nSetup checker reported issues. Please resolve before continuing.")
            input("Press any key to continue . . .")
            return False
        
        logger.info("Setup verification passed.")
        return True
    except Exception as e:
        logger.error(f"Error running setup verification: {e}")
        return False

def start_server(port=5000):
    """Start the FastAPI server"""
    logger.info(f"Starting server on port {port}...")
    
    try:
        # Import here to ensure environment is set up first
        from app.main import app
        
        # Start the server
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port,
            log_level=os.environ.get("LOG_LEVEL", "info").lower()
        )
        return True
    except ImportError as e:
        logger.error(f"Failed to import application: {e}")
        return False
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return False

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description="Smart Card Manager")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    args = parser.parse_args()
    
    # Set up the environment
    if not setup_environment():
        logger.error("Failed to set up environment.")
        return 1
    
    # Run setup verification
    if not run_setup_verification():
        logger.error("Setup verification failed.")
        return 1
        
    # Start the server
    if not start_server(args.port):
        logger.error("Failed to start server.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
