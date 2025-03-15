import os
import sys
import logging
import argparse
import inspect
import socket
import asyncio
import site
import importlib.util
import time
import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List, Set
import traceback
import json

# Logging setup
LOG_FILE = "debug_startup.log"
log_levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

def get_log_level_from_env() -> int:
    """
    Retrieves the log level from the environment variable DEBUG_STARTUP_LOG_LEVEL.
    Defaults to INFO if the environment variable is not set or invalid.
    """
    log_level_str = os.environ.get("DEBUG_STARTUP_LOG_LEVEL", "INFO").upper()
    return log_levels.get(log_level_str, logging.INFO)

def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Custom exception handler to log unhandled exceptions.
    """
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

# Set up logging
log_level = get_log_level_from_env()
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Set custom exception handler
sys.excepthook = exception_hook
logger = logging.getLogger("DebugStartup")

def format_extra(extra: Optional[dict]) -> str:
    """Formats the extra dictionary for logging."""
    if extra is None:
        return ""
    try:
        return json.dumps(extra, indent=2, default=str)
    except Exception as e:
        return f"Error formatting extra: {e}. Original: {extra}"

def log_info(message: str, extra: Optional[dict] = None):
    """Logs an info message with optional extra context."""
    extra_str = format_extra(extra)
    if extra_str:
        logger.info(f"{message} Extra: {extra_str}")
    else:
        logger.info(message)

def log_debug(message: str, extra: Optional[dict] = None):
    """Logs a debug message with optional extra context."""
    extra_str = format_extra(extra)
    if extra_str:
        logger.debug(f"{message} Extra: {extra_str}")
    else:
        logger.debug(message)

def log_warning(message: str, extra: Optional[dict] = None):
    """Logs a warning message with optional extra context."""
    extra_str = format_extra(extra)
    if extra_str:
        logger.warning(f"{message} Extra: {extra_str}")
    else:
        logger.warning(message)

def log_error(message: str, extra: Optional[dict] = None):
    """Logs an error message with optional extra context."""
    extra_str = format_extra(extra)
    if extra_str:
        logger.error(f"{message} Extra: {extra_str}")
    else:
        logger.error(message)

def log_exception(message: str, exc_info: bool = True, extra: Optional[dict] = None):
    """Logs an error message with exception info and optional extra context."""
    extra_str = format_extra(extra)
    if extra_str:
        logger.exception(f"{message} Extra: {extra_str}", exc_info=exc_info)
    else:
        logger.exception(message, exc_info=exc_info)

# Environment checks
log_info("--- Environment Information ---")
log_info(f"Operating System: {sys.platform}")
log_info(f"VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', 'Not in a virtual environment')}")
log_info(f"CONDA_DEFAULT_ENV: {os.environ.get('CONDA_DEFAULT_ENV', 'Not in a conda environment')}")
log_info(f"PATH: {os.environ.get('PATH', 'PATH not set')}")
log_info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'PYTHONPATH not set')}")
log_info(f"Current User: {os.getlogin() if hasattr(os, 'getlogin') else 'N/A'}")

log_info("\n--- Python Information ---")
log_info(f"sys.executable: {sys.executable}")
log_info(f"sys.version: {sys.version}")
log_info(f"sys.version_info: {sys.version_info}")
log_info(f"sys.prefix: {sys.prefix}")
log_info(f"sys.base_prefix: {getattr(sys, 'base_prefix', 'N/A')}")
log_info(f"sys.real_prefix: {getattr(sys, 'real_prefix', 'N/A')}")
log_info(f"site.getsitepackages(): {site.getsitepackages()}")
log_info(f"site.getusersitepackages(): {site.getusersitepackages()}")

log_info("\n--- Encoding Information ---")
log_info(f"sys.getdefaultencoding(): {sys.getdefaultencoding()}")
log_info(f"sys.getfilesystemencoding(): {sys.getfilesystemencoding()}")
log_info(f"locale.getpreferredencoding(): {__import__('locale').getpreferredencoding() if 'locale' in sys.modules else 'locale module not imported'}")

log_info("\n--- Module Search Path ---")
log_info(f"sys.path: {sys.path}")

def check_common_issues():
    log_info("\n--- Check for common issues ---")
    cwd = os.getcwd()
    if cwd not in sys.path:
        log_warning(f"Current working directory '{cwd}' is not in sys.path. This may cause import issues.")
    else:
        log_info(f"Current working directory '{cwd}' is in sys.path.")

    if sys.executable.lower().endswith(".zip"):
        log_warning("Running from a zip file may cause issues with some libraries.")

    try:
        test_file = os.path.join(site.getsitepackages()[0], "__test_write__.txt")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        log_info("Write permissions to site-packages: OK")
    except Exception as e:
        log_error(f"Write permissions to site-packages: FAILED ({e})")

    if "PYTHONHOME" in os.environ:
        log_warning("PYTHONHOME is set. This can interfere with Python's module search path.")
        log_debug(f"PYTHONHOME value: {os.environ['PYTHONHOME']}")
    if "PYTHONUSERBASE" in os.environ:
        log_warning("PYTHONUSERBASE is set. This can interfere with user-specific package installations.")
        log_debug(f"PYTHONUSERBASE value: {os.environ['PYTHONUSERBASE']}")

check_common_issues()

parent_dir = Path(__file__).resolve().parent

import importlib.util

async def import_module_async(module_path: str, imported_modules: Optional[Set[str]] = None, import_stack: Optional[List[str]] = None):
    """
    Asynchronously imports a module from a given path with enhanced error checking and diagnostics.

    Args:
        module_path: Path to the module file.
        imported_modules: Set of already imported module paths to detect circular dependencies.
        import_stack: List tracking the import chain for circular dependency diagnostics.

    Returns:
        The imported module object or None if import fails.
    """
    module_name = os.path.basename(module_path).replace(".py", "")
    module_dir = os.path.dirname(module_path)

    if imported_modules is None:
        imported_modules = set()
    if import_stack is None:
        import_stack = []

    # Start timing the import process
    start_time = time.time()

    # Check for circular dependencies
    if module_path in imported_modules:
        import_stack.append(module_path)
        log_warning(f"Circular dependency detected", extra={
            "module": module_path,
            "import_chain": import_stack
        })
        return None

    import_stack.append(module_path)
    
    try:
        log_debug(f"Attempting to import module from path: {module_path}", extra={"import_stack": import_stack})

        # File existence and type checks
        if not os.path.exists(module_path):
            log_error(f"Module path does not exist: {module_path}")
            return None
        if not os.path.isfile(module_path):
            log_error(f"Module path is not a file: {module_path}")
            return None

        # Permission check
        if not os.access(module_path, os.R_OK):
            log_error(f"No read permission for module: {module_path}")
            return None

        # File size and emptiness check
        file_size = os.path.getsize(module_path)
        if file_size == 0:
            log_warning(f"Module file is empty: {module_path}")
            return None
        if file_size > 1024 * 1024:  # Warn if larger than 1MB
            log_warning(f"Large module file detected: {file_size / 1024:.2f} KB", extra={"path": module_path})

        # Hash file for integrity check
        with open(module_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        log_debug(f"Module file hash: {file_hash}", extra={"path": module_path})

        # Add module directory to sys.path
        added_to_sys_path = False
        if module_dir not in sys.path:
            sys.path.insert(0, module_dir)
            added_to_sys_path = True
            log_debug(f"Added module directory to sys.path: {module_dir}")
        else:
            log_debug(f"Module directory already in sys.path: {module_dir}")

        # Create module specification
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            log_error(f"Failed to create module specification for {module_path}")
            return None

        module = importlib.util.module_from_spec(spec)
        if module is None:
            log_error(f"Failed to create module from spec for {module_path}")
            return None

        # Execute module with timing and error handling
        imported_modules.add(module_path)
        log_debug(f"Executing module: {module_path}")
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            log_exception(f"Syntax error in {module_path}", extra={
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text
            })
            return None
        except ModuleNotFoundError as e:
            log_exception(f"Module not found error while executing {module_path}: {e}")
            if "No module named 'smartcard.System'" in str(e):
                log_error("The 'smartcard.System' module could not be found. Ensure 'pyscard' is installed.")
                relevant_files = [
                    os.path.join(parent_dir, "smart.py"),
                    os.path.join(parent_dir, "app", "api", "__init__.py"),
                    os.path.join(parent_dir, "app", "api", "card_routes.py"),
                    os.path.join(parent_dir, "app", "core", "card_manager.py"),
                    os.path.join(parent_dir, "app", "core", "card_utils.py"),
                    os.path.join(parent_dir, "app", "utils", "smartcard.py"),
                ]
                for filepath in relevant_files:
                    if os.path.exists(filepath):
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                contents = f.readlines()
                            log_debug(f"Contents of {filepath}:\n" + "".join(contents))

                            log_debug(f"Running debug checks on {filepath}:")
                            for i, line in enumerate(contents):
                                line = line.strip()
                                if "import *" in line:
                                    log_warning(f"  {filepath}:{i+1}: Wildcard import detected")
                                elif "print(" in line and not line.startswith("#"):
                                    log_warning(f"  {filepath}:{i+1}: Print statement detected")
                                elif "os.system" in line and not line.startswith("#"):
                                    log_warning(f"  {filepath}:{i+1}: os.system call detected")
                                elif "try:" in line:
                                    next_line = contents[i+1].strip() if i+1 < len(contents) else ""
                                    if not next_line.startswith("except"):
                                        log_warning(f"  {filepath}:{i+1}: 'try' without immediate 'except'")
                                elif "except Exception" in line:
                                    log_warning(f"  {filepath}:{i+1}: Broad 'Exception' catch")
                                elif "TODO" in line.upper() or "FIXME" in line.upper():
                                    log_info(f"  {filepath}:{i+1}: TODO/FIXME comment found")
                        except UnicodeDecodeError:
                            log_error(f"  {filepath}: Encoding issue - not UTF-8 compatible")
                        except Exception as inspect_e:
                            log_error(f"Failed to inspect {filepath}: {inspect_e}")
                    else:
                        log_warning(f"Relevant file not found: {filepath}")
            return None
        except ImportError as e:
            log_exception(f"Import error in {module_path}: {e}", extra={
                "traceback": traceback.format_exc()
            })
            return None
        except AttributeError as e:
            log_exception(f"Attribute error during import of {module_path}: {e}", extra={
                "traceback": traceback.format_exc()
            })
            return None
        except Exception as e:
            log_exception(f"Unexpected error executing {module_path}: {e}", extra={
                "traceback": traceback.format_exc()
            })
            return None

        # Post-import validation
        if not hasattr(module, "__file__") or module.__file__ != module_path:
            log_warning(f"Module __file__ attribute mismatch: expected {module_path}, got {getattr(module, '__file__', 'N/A')}")

        # Check for imported modules
        if hasattr(module, "__spec__") and module.__spec__.submodule_search_locations:
            log_debug(f"Module has submodules: {module.__spec__.submodule_search_locations}")

        # Measure import time
        import_time = time.time() - start_time
        if import_time > 1.0:  # Warn if import takes more than 1 second
            log_warning(f"Slow import detected: {import_time:.2f} seconds", extra={"module": module_path})

        log_info(f"Successfully imported module: {module_name} from {module_path}", extra={
            "import_time": f"{import_time:.2f} seconds"
        })
        return module

    except Exception as e:
        log_exception(f"Failed to import module {module_path}: {e}", extra={
            "traceback": traceback.format_exc()
        })
        return None
    finally:
        # Clean up sys.path if we modified it
        if added_to_sys_path and module_dir in sys.path:
            sys.path.remove(module_dir)
            log_debug(f"Removed module directory from sys.path: {module_dir}")
        import_stack.pop()
        
def analyze_routes(app):
    """Analyzes the routes defined in a FastAPI app."""
    if not hasattr(app, "routes"):
        log_warning("The app object does not have a 'routes' attribute. Skipping route analysis.")
        return

    log_info("Analyzing routes...")
    try:
        for route in app.routes:
            log_info("", extra={
                "path": route.path,
                "methods": route.methods,
                "name": route.name,
                "endpoint": route.endpoint.__name__ if hasattr(route, "endpoint") else None
            })
            if hasattr(route, "endpoint"):
                endpoint = route.endpoint
                log_debug(f"  Endpoint: {endpoint.__name__}")
                log_debug(f"  Signature: {inspect.signature(endpoint)}")
                log_debug(f"  Docstring: {endpoint.__doc__}")
    except Exception as e:
        log_exception(f"Failed to analyze routes: {e}")

def check_dependencies(module):
    """Checks the dependencies of a module."""
    log_info(f"Checking dependencies for module: {module.__name__}")
    try:
        for name, value in inspect.getmembers(module):
            if inspect.isclass(value) or inspect.isfunction(value):
                log_debug(f"  Dependency: {name} - {type(value)}")
    except Exception as e:
        log_exception(f"Failed to check dependencies for module {module.__name__}: {e}")

def is_port_in_use(port: int) -> bool:
    """Checks if a port is currently in use."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('localhost', port))
        s.close()
        return False
    except socket.error:
        return True

def find_available_port(start_port: int = 8765, max_attempts: int = 100) -> Optional[int]:
    """Finds an available port starting from a given port."""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            log_info(f"Found available port: {port}")
            return port
    log_warning(f"Could not find an available port in range {start_port} to {start_port + max_attempts}")
    return None

class Args:
    def __init__(self, port: int, frontend_port: int, log_level: str, open_browser: bool):
        self.port = port
        self.frontend_port = frontend_port
        self.log_level = log_level
        self.open_browser = open_browser

async def simulate_startup(smart_module, args: Args):
    """Asynchronously simulates the startup process."""
    log_info("Simulating startup process...")
    try:
        log_info("Setting up environment...")
        if hasattr(smart_module, "setup_environment") and callable(smart_module.setup_environment):
            smart_module.setup_environment()
        else:
            log_warning("setup_environment function not found in smart_module. Skipping.")

        log_info("Running setup verification (dummy)...")
        setup_ok = True
        if hasattr(smart_module, "run_setup_verification") and callable(smart_module.run_setup_verification):
            setup_ok = smart_module.run_setup_verification()
            if not setup_ok:
                log_warning("Setup verification failed (dummy). Continuing anyway.")
            else:
                log_info("Setup verification passed (dummy).")
        else:
            log_warning("run_setup_verification function not found in smart_module. Assuming setup is OK.")

        log_info("Parsing arguments...")
        parser = argparse.ArgumentParser(description="Smart Card Manager Application")
        parser.add_argument("--port", type=int, default=8765, help="Port to run on (default: 8765)")
        parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend port (default: 3000)")
        parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (default: INFO)")
        parser.add_argument("--open-browser", action="store_true", help="Open browser on startup")
        parsed_args = parser.parse_args(["--port", str(args.port), "--frontend-port", str(args.frontend_port), "--log-level", args.log_level])

        log_info("Configuring logging...")
        log_level = getattr(logging, parsed_args.log_level.upper(), logging.INFO)
        logger.setLevel(log_level)
        log_info(f"Log level set to: {logging.getLevelName(log_level)}")

        log_info("Finding available port...")
        port = parsed_args.port
        if is_port_in_use(port):
            log_warning(f"Port {port} is in use. Finding available port...")
            port = find_available_port()
            if port is None:
                log_error("Could not find an available port. Startup aborted.")
                return
        log_info(f"Using port: {port}")

        log_info("Printing links...")
        if hasattr(smart_module, "print_links") and callable(smart_module.print_links):
            smart_module.print_links(port, parsed_args.frontend_port)
        else:
            log_warning("print_links function not found in smart_module. Skipping.")

        log_info("Updating CORS settings...")
        origins = [
            f"http://localhost:{parsed_args.frontend_port}",
            "http://localhost",
            "http://localhost:8080",
            f"http://127.0.0.1:{parsed_args.frontend_port}",
            "http://127.0.0.1",
        ]
        log_info(f"CORS origins: {origins}")

        log_info("Initializing database (dummy)...")
        log_info("Startup simulation complete.")

    except Exception as e:
        log_exception(f"Error during startup simulation: {e}")

async def main(args: Args):
    """Main function to run the debugging script."""
    log_info("Starting debugging script...")
    app_dir = os.path.join(parent_dir, "app")
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    utils_dir = os.path.join(app_dir, "utils")
    if utils_dir not in sys.path:
        sys.path.insert(0, utils_dir)

    log_info(f"sys.path: {sys.path}")
    imported_modules: Set[str] = set()

    try:
        log_info("Importing smart.py...")
        smart_path = os.path.join(parent_dir, "smart.py")
        smart_module = await import_module_async(smart_path, imported_modules)
        if not smart_module:
            log_error("Failed to import smart.py. Exiting.")
            sys.exit(1)

        log_info("Analyzing smart.py, routes, and simulating startup concurrently...")
        tasks = [
            asyncio.to_thread(check_dependencies, smart_module),
            asyncio.to_thread(analyze_routes, smart_module.app if hasattr(smart_module, "app") else None),
            simulate_startup(smart_module, args)
        ]
        await asyncio.gather(*tasks)

        log_info("Debugging script complete. Check debug_startup.log for details.")

    except Exception as e:
        log_exception(f"Unhandled exception in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Card Manager Debugging Script")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on (default: 8765)")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend port (default: 3000)")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (default: INFO)")
    parser.add_argument("--open-browser", action="store_true", help="Open browser on startup")

    args = parser.parse_args()
    if args.port < 1 or args.port > 65535:
        parser.error("Port number must be between 1 and 65535")

    args_obj = Args(
        port=args.port,
        frontend_port=args.frontend_port,
        log_level=args.log_level,
        open_browser=args.open_browser
    )
    asyncio.run(main(args_obj))