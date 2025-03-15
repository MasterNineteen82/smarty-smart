import os
import sys
import logging
import argparse
import inspect
import socket
from pathlib import Path
from typing import Optional, List

# Configure logging
LOG_FILE = "debug_startup.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),  # Overwrite the log file on each run
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DebugStartup")

# Define parent_dir globally
parent_dir = Path(__file__).resolve().parent

def import_module(module_path: str):
    """
    Dynamically imports a module from a given path.

    Args:
        module_path: The path to the module.

    Returns:
        The imported module, or None if import fails.
    """
    try:
        module_path = os.path.abspath(module_path)  # Convert to absolute path
        module_dir = os.path.dirname(module_path)  # Get the directory of the module
        if module_dir not in sys.path:  # Check if the directory is already in sys.path
            sys.path.insert(0, module_dir)  # Add the directory to sys.path
        module_name = os.path.basename(module_path).replace(".py", "")
        module = __import__(module_name)
        # sys.path.pop(0)  # Remove the directory from sys.path after importing - DON'T DO THIS
        logger.info(f"Successfully imported module: {module_name} from {module_path}")
        return module
    except ImportError as e:
        logger.error(f"Failed to import module {module_path}: {e}", exc_info=True)  # Include traceback
        return None
    except Exception as e:
        logger.error(f"Unexpected error during import of {module_path}: {e}", exc_info=True)
        return None

def analyze_routes(app):
    """
    Analyzes the routes defined in a FastAPI app.

    Args:
        app: The FastAPI application instance.
    """
    if not hasattr(app, "routes"):
        logger.warning("The app object does not have a 'routes' attribute. Skipping route analysis.")
        return

    logger.info("Analyzing routes...")
    try:
        for route in app.routes:
            logger.info({
                "path": route.path,
                "methods": route.methods,
                "name": route.name,
                "endpoint": route.endpoint.__name__ if hasattr(route, "endpoint") else None
            })

            if hasattr(route, "endpoint"):
                endpoint = route.endpoint
                logger.debug(f"  Endpoint: {endpoint.__name__}")
                logger.debug(f"  Signature: {inspect.signature(endpoint)}")
                logger.debug(f"  Docstring: {endpoint.__doc__}")
    except Exception as e:
        logger.error(f"Failed to analyze routes: {e}", exc_info=True)

def check_dependencies(module):
    """
    Checks the dependencies of a module.

    Args:
        module: The module to check.
    """
    logger.info(f"Checking dependencies for module: {module.__name__}")
    try:
        for name, value in inspect.getmembers(module):
            if inspect.isclass(value) or inspect.isfunction(value):
                logger.debug(f"  Dependency: {name} - {type(value)}")
    except Exception as e:
        logger.error(f"Failed to check dependencies for module {module.__name__}: {e}", exc_info=True)

def is_port_in_use(port: int) -> bool:
    """
    Checks if a port is currently in use.

    Args:
        port: The port number to check.

    Returns:
        True if the port is in use, False otherwise.
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except socket.error:
            return True

def find_available_port(start_port: int = 8765, max_attempts: int = 100) -> Optional[int]:
    """
    Finds an available port starting from a given port.

    Args:
        start_port: The port number to start searching from.
        max_attempts: The maximum number of ports to check.

    Returns:
        An available port number, or None if no port is available.
    """
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            logger.info(f"Found available port: {port}")
            return port
    logger.warning(f"Could not find an available port in the range {start_port} to {start_port + max_attempts}")
    return None

class Args:
    def __init__(self, port: int, frontend_port: int, log_level: str, open_browser: bool):
        self.port = port
        self.frontend_port = frontend_port
        self.log_level = log_level
        self.open_browser = open_browser

def simulate_startup(smart_module, args: Args):
    """
    Simulates the startup process of the Smart Card Manager application.

    Args:
        smart_module: The imported smart.py module.
        args: The parsed command-line arguments.
    """
    logger.info("Simulating startup process...")

    try:
        # 1. Setup environment
        logger.info("Setting up environment...")
        if hasattr(smart_module, "setup_environment") and callable(smart_module.setup_environment):
            smart_module.setup_environment()
        else:
            logger.warning("setup_environment function not found in smart_module. Skipping.")

        # 2. Run setup verification (dummy)
        logger.info("Running setup verification (dummy)...")
        setup_ok = True
        if hasattr(smart_module, "run_setup_verification") and callable(smart_module.run_setup_verification):
            setup_ok = smart_module.run_setup_verification()
            if not setup_ok:
                logger.warning("Setup verification failed (dummy). Continuing anyway.")
            else:
                logger.info("Setup verification passed (dummy).")
        else:
            logger.warning("run_setup_verification function not found in smart_module. Assuming setup is OK.")

        # 3. Parse arguments
        logger.info("Parsing arguments...")
        # Create a dummy parser for testing
        parser = argparse.ArgumentParser(description="Smart Card Manager Application")
        parser.add_argument("--port", type=int, default=8765, help="Port to run on (default: 8765)")
        parser.add_argument("--frontend-port", type=int, default=3000, help="Port where frontend is running (default: 3000)")
        parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (default: INFO)")
        parser.add_argument("--open-browser", action="store_true", help="Open browser on startup")

        # Simulate parsing arguments (replace with actual arguments if needed)
        parsed_args = parser.parse_args(["--port", str(args.port), "--frontend-port", str(args.frontend_port), "--log-level", args.log_level])

        # 4. Configure logging
        logger.info("Configuring logging...")
        log_level = getattr(logging, parsed_args.log_level.upper(), logging.INFO)  # Default to INFO if invalid
        logger.setLevel(log_level)
        logger.info(f"Log level set to: {logging.getLevelName(log_level)}")

        # 5. Find available port (if needed)
        logger.info("Finding available port...")
        port = parsed_args.port
        if is_port_in_use(port):
            logger.warning(f"Port {port} is in use. Attempting to find an available port.")
            port = find_available_port()
            if port is None:
                logger.error("Could not find an available port. Startup aborted.")
                return
        logger.info(f"Using port: {port}")

        # 6. Print links
        logger.info("Printing links...")
        if hasattr(smart_module, "print_links") and callable(smart_module.print_links):
            smart_module.print_links(port, parsed_args.frontend_port)
        else:
            logger.warning("print_links function not found in smart_module. Skipping.")

        # 7. Update CORS settings
        logger.info("Updating CORS settings...")
        origins = [
            f"http://localhost:{parsed_args.frontend_port}",
            "http://localhost",
            "http://localhost:8080",
            f"http://127.0.0.1:{parsed_args.frontend_port}",
            "http://127.0.0.1",
        ]
        # This part is difficult to simulate without modifying the actual app
        logger.info(f"CORS origins: {origins}")

        # 8. Database initialization (dummy)
        logger.info("Initializing database (dummy)...")
        # In a real scenario, you would call create_db_and_tables() here

        logger.info("Startup simulation complete.")

    except Exception as e:
        logger.error(f"Error during startup simulation: {e}", exc_info=True)

def main(args: Args):
    """
    Main function to run the debugging script.

    Args:
        args: The parsed command-line arguments.
    """
    logger.info("Starting debugging script...")

    # Print sys.path *before* importing smart.py
    logger.info(f"sys.path: {sys.path}")

    try:
        # 1. Import smart.py
        logger.info("Importing smart.py...")
        smart_path = os.path.join(parent_dir, "smart.py")
        smart_module = import_module(smart_path)
        if not smart_module:
            logger.error("Failed to import smart.py. Exiting.")
            sys.exit(1)

        # 2. Analyze smart.py
        logger.info("Analyzing smart.py...")
        check_dependencies(smart_module)

        # 3. Analyze routes
        logger.info("Analyzing routes...")
        if hasattr(smart_module, "app"):
            analyze_routes(smart_module.app)
        else:
            logger.warning("smart.py does not have an 'app' attribute. Skipping route analysis.")

        # 4. Simulate startup
        simulate_startup(smart_module, args)

        logger.info("Debugging script complete. Check debug_startup.log for details.")

    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Card Manager Debugging Script")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on (default: 8765)")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Port where frontend is running (default: 3000)")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (default: INFO)")
    parser.add_argument("--open-browser", action="store_true", help="Open browser on startup")

    args = parser.parse_args()

    if args.port < 1 or args.port > 65535:
        parser.error("Port number must be between 1 and 65535")

    # Create an instance of Args
    class Args:
        def __init__(self, port: int, frontend_port: int, log_level: str, open_browser: bool):
            self.port = port
            self.frontend_port = frontend_port
            self.log_level = log_level
            self.open_browser = open_browser

    args_obj = Args(port=args.port, frontend_port=args.frontend_port, log_level=args.log_level, open_browser=args.open_browser)

    main(args_obj)