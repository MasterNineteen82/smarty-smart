"""
Smart Card Manager Setup Checker
Verifies and installs required dependencies
"""

import os
import sys
import subprocess
import importlib.util
import platform
import time
import logging
import json
from pathlib import Path
import importlib
import pkg_resources

# Configure logging
LOG_DIR = os.path.join("logs", "setup")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "setup_checker.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def load_requirements(file_path="requirements.txt"):
    """Load required packages from a requirements.txt file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:  # Specify encoding
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return requirements
    except FileNotFoundError:
        print_warning("requirements.txt not found. Using default package list.")
        logging.warning("requirements.txt not found. Using default package list.")
        return [
            "pyscard",
            "fastapi",
            "uvicorn",
            "werkzeug",
            "cryptography",
            "pyopenssl",
            "python-dateutil"
        ]
    except Exception as e:
        print_error(f"Error reading requirements.txt: {e}. Using default package list.")
        logging.error(f"Error reading requirements.txt: {e}. Using default package list.")
        return [
            "pyscard",
            "fastapi",
            "uvicorn",
            "werkzeug",
            "cryptography",
            "pyopenssl",
            "python-dateutil"
        ]

# Load required packages from requirements.txt
REQUIRED_PACKAGES = load_requirements()

# Color codes and icons for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Icons
ICON_SUCCESS = "✅"  # Unicode check mark
ICON_WARNING = "⚠️"  # Unicode warning sign
ICON_ERROR = "❌"    # Unicode cross mark
ICON_INFO = "ℹ️"     # Unicode information icon
ICON_HEADER = "⚙️"   # Unicode gear/settings icon


def print_header(message):
    """Print a formatted header with icon and underline"""
    print(f"{Colors.HEADER}{Colors.BOLD}{ICON_HEADER} {Colors.UNDERLINE}{message}{Colors.ENDC}")
    logging.info(f"Header: {message}")

def print_success(message):
    """Print a success message with green color and check mark icon"""
    print(f"{Colors.OKGREEN}{ICON_SUCCESS} {message}{Colors.ENDC}")
    logging.info(f"Success: {message}")

def print_warning(message):
    """Print a warning message with yellow color and warning icon"""
    print(f"{Colors.WARNING}{ICON_WARNING} {message}{Colors.ENDC}")
    logging.warning(f"Warning: {message}")

def print_error(message):
    """Print an error message with red color and cross mark icon"""
    print(f"{Colors.FAIL}{ICON_ERROR} {message}{Colors.ENDC}")
    logging.error(f"Error: {message}")

def print_info(message):
    """Print an info message with blue color and information icon"""
    print(f"{Colors.OKBLUE}{ICON_INFO} {message}{Colors.ENDC}")
    logging.info(f"Info: {message}")

def check_virtual_environment():
    """Check if the script is running inside a virtual environment."""
    print_header("Checking Virtual Environment")
    if 'VIRTUAL_ENV' in os.environ:
        print_success("Running inside a virtual environment.")
        logging.info("Running inside a virtual environment.")
        return True
    else:
        print_warning("Not running inside a virtual environment.")
        logging.warning("Not running inside a virtual environment.")
        print_info("It is recommended to run this application within a virtual environment.")
        logging.info("It is recommended to run this application within a virtual environment.")
        return False

def is_package_installed(package_name):
    """Check if a package is installed using pkg_resources."""
    try:
        # Attempt to get the package distribution
        dist = pkg_resources.get_distribution(package_name)
        print_info(f"Package {package_name} found with version {dist.version} using pkg_resources")
        return True  # If get_distribution doesn't raise an exception, it's installed

    except pkg_resources.DistributionNotFound:
        print_warning(f"Package {package_name} not found using pkg_resources")
        return False  # Package not found

    except Exception as e:
        print_error(f"Error checking if package {package_name} is installed using pkg_resources: {e}")
        logging.exception(f"Error checking if package {package_name} is installed using pkg_resources: {e}")
        return False

def check_python_version():
    """Check if the Python version is sufficient"""
    print_header("Checking Python Version")
    required_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version >= required_version:
        print_success(f"Python version {sys.version.split()[0]} detected (required: 3.8+)")
        logging.info(f"Python version {sys.version.split()[0]} detected (required: 3.8+)")
        return True
    else:
        print_error(f"Python version {sys.version.split()[0]} is not supported (required: 3.8+)")
        logging.error(f"Python version {sys.version.split()[0]} is not supported (required: 3.8+)")
        return False

def check_pip():
    """Check if pip is installed and working"""
    print_header("Checking Pip Installation")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                 capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print_success("pip is installed and working")
            logging.info("pip is installed and working")
            return True
        else:
            print_error(f"pip is not working correctly. Error: {result.stderr}")
            logging.error(f"pip is not working correctly. Error: {result.stderr}")
            return False
    except FileNotFoundError:
        print_error("pip is not installed or not in your PATH.")
        logging.error("pip is not installed.")
        return False
    except subprocess.TimeoutExpired:
        print_error("pip check timed out.")
        logging.error("pip check timed out.")
        return False
    except Exception as e:
        print_error(f"An unexpected error occurred while checking pip: {e}")
        logging.exception(f"An unexpected error occurred while checking pip: {e}")
        return False

def check_required_packages():
    """Check for and install required packages"""
    print_header("Checking Required Packages")
    
    # Clear importlib and pkg_resources caches
    importlib.invalidate_caches()
    pkg_resources.working_set = pkg_resources.WorkingSet()
    
    all_packages_installed = True
    for package in REQUIRED_PACKAGES:
        print(f"Checking {package}...")
        try:
            if is_package_installed(package):
                print_success(f"{package} is installed")
            else:
                print_warning(f"{package} is not installed. Attempting to install...")
                if not install_package(package):
                    all_packages_installed = False
        except Exception as e:
            print_error(f"An unexpected error occurred while checking/installing {package}: {e}")
            logging.exception(f"An unexpected error occurred while checking/installing {package}: {e}")
            all_packages_installed = False
    
    if all_packages_installed:
        return True
    else:
        print_error("Not all required packages were successfully installed.")
        return False

def install_package(package_name):
    """Install a package using pip with enhanced error handling"""
    print_info(f"Installing {package_name}...")
    logging.info(f"Installing {package_name}...")
    try:
        # Attempt to install the package
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name, "--quiet"],
            capture_output=True,
            text=True,
            encoding='utf-8', # Ensure encoding is set
            timeout=60
        )

        if result.returncode == 0:
            print_success(f"{package_name} was successfully installed")
            logging.info(f"{package_name} was successfully installed")
            return True
        else:
            # Log the error output from pip
            print_error(f"Failed to install {package_name}.  Error: {result.stderr}")
            logging.error(f"Failed to install {package_name}. Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print_error(f"Installation of {package_name} timed out.")
        logging.error(f"Installation of {package_name} timed out.")
        return False
    except FileNotFoundError:
        print_error(f"Pip not found. Ensure pip is installed and in your PATH.")
        logging.error(f"Pip not found.")
        return False
    except Exception as e:
        print_error(f"An unexpected error occurred during installation of {package_name}: {e}")
        logging.exception(f"An unexpected error occurred during installation of {package_name}: {e}")
        return False

def check_pcsc_service():
    """Check if PC/SC service is running"""
    print_header("Checking PC/SC Service")
    
    if platform.system() == "Windows":
        service_name = "SCardSvr"
        check_command = ["sc", "query", service_name]
        start_command = ["sc", "start", service_name]
    elif platform.system() == "Linux":
        service_name = "pcscd"
        check_command = ["systemctl", "is-active", service_name]
        start_command = ["sudo", "systemctl", "start", service_name]
    else:
        print_info(f"PC/SC service check not implemented for {platform.system()}")
        logging.info(f"PC/SC service check not implemented for {platform.system()}")
        print_info("Please ensure PCSC service is running on your system")
        logging.info("Please ensure PCSC service is running on your system")
        return True
    
    try:
        output = subprocess.check_output(check_command, stderr=subprocess.STDOUT, universal_newlines=True, timeout=10)
        if "RUNNING" in output or "active" in output:
            print_success(f"PC/SC service ({service_name}) is running")
            logging.info(f"PC/SC service ({service_name}) is running")
            return True
        else:
            print_warning(f"PC/SC service ({service_name}) is not running")
            logging.warning(f"PC/SC service ({service_name}) is not running")
            print_info("Trying to start PC/SC service...")
            logging.info("Trying to start PC/SC service...")
            try:
                subprocess.check_call(start_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                print_success("PC/SC service started successfully")
                logging.info("PC/SC service started successfully")
                return True
            except subprocess.TimeoutExpired:
                print_error("Starting PC/SC service timed out.")
                logging.error("Starting PC/SC service timed out.")
                return False
            except subprocess.CalledProcessError as e:
                print_error(f"Failed to start PC/SC service. Try starting it manually: {e}")
                logging.error(f"Failed to start PC/SC service. Try starting it manually: {e}")
                return False
    except subprocess.TimeoutExpired:
        print_error("Checking PC/SC service status timed out.")
        logging.error("Checking PC/SC service status timed out.")
        return False
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to check PC/SC service status: {e}")
        logging.error(f"Failed to check PC/SC service status: {e}")
        return False
    except FileNotFoundError as e:
        print_error(f"Command not found (Likely 'sc' or 'systemctl'): {e}")
        logging.error(f"Command not found: {e}")
        return False
    except Exception as e:
        print_error(f"An unexpected error occurred while checking PC/SC service: {e}")
        logging.exception(f"An unexpected error occurred while checking PC/SC service: {e}")
        return False

def check_card_readers():
    """Check for connected card readers"""
    print_header("Checking for Card Readers")
    
    try:
        # First make sure pyscard is installed
        if not is_package_installed("smartcard"):
            print_warning("smartcard module not available to check readers")
            logging.warning("smartcard module not available to check readers")
            return False  # Return False to indicate that the check failed
        
        # Import after checking to avoid import errors
        try:
            from smartcard.System import readers
        except ImportError as e:
            print_error(f"Error importing smartcard.System: {e}")
            logging.error(f"Error importing smartcard.System: {e}")
            return False
        
        try:
            reader_list = readers()
            if reader_list:
                print_success(f"Found {len(reader_list)} card reader(s):")
                logging.info(f"Found {len(reader_list)} card reader(s):")
                
                acr122u_found = False
                st1144_found = False
                
                for i, reader in enumerate(reader_list):
                    print_info(f"  {i+1}. {reader}")
                    logging.info(f"  {i+1}. {reader}")
                    
                    if "ACR122U" in str(reader):
                        acr122u_found = True
                    if "ST1144" in str(reader):
                        st1144_found = True
                
                if acr122u_found:
                    print_success("ACR122U card reader detected.")
                    logging.info("ACR122U card reader detected.")
                if st1144_found:
                    print_success("Cherry ST1144 card reader detected.")
                    logging.info("Cherry ST1144 card reader detected.")
                
                return True
            else:
                print_warning("No card readers detected")
                logging.warning("No card readers detected")
                print_info("Please connect a supported card reader and try again")
                logging.info("Please connect a supported card reader and try again")
                return False  # Return False to indicate that no readers were found
        except Exception as e:
            print_warning(f"Error listing card readers: {e}")
            logging.warning(f"Error listing card readers: {e}")
            print_info("Check reader connection and drivers.")
            logging.info("Check reader connection and drivers.")
            return False  # Return False to indicate that the check failed
            
    except Exception as e:
        print_warning(f"Error checking card readers: {e}")
        logging.warning(f"Error checking card readers: {e}")
        print_info("This doesn't prevent startup, but check your reader connection")
        logging.info("This doesn't prevent startup, but check your reader connection")
        return False  # Return False to indicate that the check failed

def create_directories():
    """Create required directories if they don't exist"""
    print_header("Setting Up Directories")
    
    directories = ["logs", "data", os.path.join("logs", "backups")]
    
    success = True
    for directory in directories:
        try:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                    print_success(f"Created directory: {directory}")
                    logging.info(f"Created directory: {directory}")
                except OSError as e:
                    print_error(f"Failed to create directory {directory}: {e}")
                    logging.error(f"Failed to create directory {directory}: {e}")
                    success = False
            else:
                print_info(f"Directory already exists: {directory}")
                logging.info(f"Directory already exists: {directory}")
        except Exception as e:
            print_error(f"An unexpected error occurred while creating directories: {e}")
            logging.exception(f"An unexpected error occurred while creating directories: {e}")
            success = False
    
    return success

def check_file(file_path, required=True):
    """Check if a file exists and log result"""
    path = Path(file_path)
    exists = path.exists()
    
    status = "OK" if exists else "MISSING"
    mark = "✓" if exists else "✗"
    print(f"{mark} {file_path}: {status}")
    
    if required and not exists:
        return False
    return True

def check_files():
    """Check for required files"""
    print_header("Checking Required Files")
    
    # Define required files
    required_files = [
        "app/__init__.py",
        "app/routes.py",
        "app/main.py",
        "config.json",
        "requirements.txt"
    ]
    
    # Define the entry point file
    # This is the file that the batch file actually tries to run
    entry_point = "app/smart.py"
    if not os.path.exists(entry_point):
        # Check alternative locations
        alternative_paths = [
            "smart.py",
            "app/core/smart.py",
            "app/main.py"  # Fallback to main.py if smart.py doesn't exist
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                entry_point = alt_path
                break
    
    print(f"Using entry point: {entry_point}")
    required_files.append(entry_point)
    
    # Check each required file
    all_files_exist = True
    for file_path in required_files:
        if not check_file(file_path, required=True):
            all_files_exist = False
    
    return all_files_exist

def check_config_content():
    """Check for config.json content"""
    print_header("Verifying config.json Content")
    
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                
            required_keys = ["app_name", "port", "debug"]
            missing_keys = [key for key in required_keys if key not in config]
            
            if missing_keys:
                print_error(f"config.json is missing required keys: {', '.join(missing_keys)}")
                return False
            else:
                print_success("config.json has all required keys")
                return True
                
        except json.JSONDecodeError:
            print_error("config.json contains invalid JSON")
            return False
        except Exception as e:
            print_error(f"Error reading config.json: {e}")
            return False
    else:
        print_error("config.json is missing")
        return False

def main():
    """Run setup verification checks"""
    print_header("Smart Card Manager Setup Checker")
    print(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Log system information
    logging.info(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    logging.info(f"Python: {sys.version.split()[0]}")
    logging.info(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    overall_success = True
    
    # 1. Check Virtual Environment
    venv_ok = check_virtual_environment()
    if not venv_ok:
        print_warning("Running outside a virtual environment is not recommended.")
        logging.warning("Running outside a virtual environment is not recommended.")
    
    # 2. Check Python version
    if not check_python_version():
        overall_success = False
        print_error("Python version check failed. Please ensure Python 3.8 or higher is installed.")
        logging.error("Python version check failed. Please ensure Python 3.8 or higher is installed.")
    
    # 3. Check pip installation
    if not check_pip():
        overall_success = False
        print_error("pip check failed. Please ensure pip is installed and working correctly.")
        logging.error("pip check failed. Please ensure pip is installed and working correctly.")
    
    # 4. Check required files
    files_ok = check_files()
    if not files_ok:
        overall_success = False
        print_error("One or more required files are missing.")
        logging.error("One or more required files are missing.")
    
    # 5. Check config.json content
    config_ok = check_config_content()
    if not config_ok:
        overall_success = False
        print_error("config.json is missing or contains invalid content.")
        logging.error("config.json is missing or contains invalid content.")
    
    # 6. Create and check directories
    dirs_ok = create_directories()
    if not dirs_ok:
        overall_success = False
        print_error("Failed to create required directories. Please check permissions.")
        logging.error("Failed to create required directories. Please check permissions.")
    
    # 7. Check for required packages
    packages_ok = check_required_packages()
    if not packages_ok:
        overall_success = False
        print_error("Not all required packages were successfully installed.")
        logging.error("Not all required packages were successfully installed.")
    
    # 8. Check PC/SC service
    pcsc_ok = check_pcsc_service()
    if not pcsc_ok:
        overall_success = False
        print_error("PC/SC service is not running or could not be started.")
        logging.error("PC/SC service is not running or could not be started.")
    
    # 9. Check for card readers
    readers_ok = check_card_readers()
    if not readers_ok:
        print_warning("No card readers detected, but you can still start the application.")
        logging.warning("No card readers detected, but you can still start the application.")
    
    # Summary
    print_header("Setup Check Summary")
    if overall_success:
        print_success("All critical checks passed! The application should start correctly.")
        logging.info("All critical checks passed! The application should start correctly.")
        print_info("Starting Smart Card Manager...")
        logging.info("Starting Smart Card Manager...")
        return 0
    else:
        print_error("Some critical checks failed. Please resolve the issues above.")
        logging.error("Some critical checks failed. Please resolve the issues above.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nSetup check interrupted.")
        logging.warning("Setup check interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        logging.critical(f"An unexpected error occurred: {e}", exc_info=True)  # Log with traceback
        sys.exit(1)