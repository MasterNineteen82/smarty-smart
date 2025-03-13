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

# Required packages list
REQUIRED_PACKAGES = [
    "pyscard",
    "flask",
    "werkzeug",
    "cryptography",
    "pyopenssl",
    "python-dateutil"
]

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(message):
    """Print a formatted header"""
    print(f"{Colors.HEADER}{Colors.BOLD}\n{'=' * 60}\n{message}\n{'=' * 60}{Colors.ENDC}\n")

def print_success(message):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.WARNING}! {message}{Colors.ENDC}")

def print_error(message):
    """Print an error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_info(message):
    """Print an info message"""
    print(f"{Colors.BLUE}i {message}{Colors.ENDC}")

def is_package_installed(package_name):
    """Check if a package is installed"""
    return importlib.util.find_spec(package_name) is not None

def install_package(package_name):
    """Install a package using pip"""
    print_info(f"Installing {package_name}...")
    try:
        # Use --quiet flag and redirect stdout/stderr to suppress messages
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package_name, "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        print_error(f"Failed to install {package_name}")
        return False

def check_python_version():
    """Check if the Python version is sufficient"""
    required_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version >= required_version:
        print_success(f"Python version {sys.version.split()[0]} detected (required: 3.8+)")
        return True
    else:
        print_error(f"Python version {sys.version.split()[0]} is not supported (required: 3.8+)")
        return False

def check_pip():
    """Check if pip is installed and working"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print_success("pip is installed and working")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("pip is not installed or not working")
        return False

def check_required_packages():
    """Check for and install required packages"""
    print_header("Checking Required Packages")
    
    all_packages_installed = True
    for package in REQUIRED_PACKAGES:
        if is_package_installed(package):
            print_success(f"{package} is installed")  # Consistent format
        else:
            print_warning(f"{package} is not installed. Attempting to install...")
            if install_package(package):
                print_success(f"{package} was successfully installed")  # Consistent format
            else:
                print_error(f"Could not install {package}")
                all_packages_installed = False
    
    return all_packages_installed

def check_pcsc_service():
    """Check if PC/SC service is running"""
    print_header("Checking PC/SC Service")
    
    if platform.system() == "Windows":
        try:
            output = subprocess.check_output(["sc", "query", "SCardSvr"], 
                                            stderr=subprocess.STDOUT, 
                                            universal_newlines=True)
            if "RUNNING" in output:
                print_success("PC/SC service (SCardSvr) is running")
                return True
            else:
                print_warning("PC/SC service (SCardSvr) is not running")
                print_info("Trying to start PC/SC service...")
                try:
                    subprocess.check_call(["sc", "start", "SCardSvr"], 
                                         stdout=subprocess.DEVNULL, 
                                         stderr=subprocess.DEVNULL)
                    print_success("PC/SC service started successfully")
                    return True
                except subprocess.CalledProcessError:
                    print_error("Failed to start PC/SC service. Try starting it manually.")
                    return False
        except subprocess.CalledProcessError:
            print_error("Failed to check PC/SC service status")
            return False
            
    elif platform.system() == "Linux":
        try:
            output = subprocess.check_output(["systemctl", "is-active", "pcscd"], 
                                           stderr=subprocess.STDOUT, 
                                           universal_newlines=True)
            if "active" in output:
                print_success("PC/SC service (pcscd) is running")
                return True
            else:
                print_warning("PC/SC service (pcscd) is not running")
                print_info("Trying to start PC/SC service...")
                try:
                    subprocess.check_call(["sudo", "systemctl", "start", "pcscd"], 
                                         stdout=subprocess.DEVNULL, 
                                         stderr=subprocess.DEVNULL)
                    print_success("PC/SC service started successfully")
                    return True
                except subprocess.CalledProcessError:
                    print_error("Failed to start PC/SC service. Try: sudo systemctl start pcscd")
                    return False
        except subprocess.CalledProcessError:
            print_error("Failed to check PC/SC service status")
            return False
            
    else:  # macOS or other
        print_info(f"PC/SC service check not implemented for {platform.system()}")
        print_info("Please ensure PCSC service is running on your system")
        return True  # Assume service is running on macOS (it usually is)

def check_card_readers():
    """Check for connected card readers"""
    print_header("Checking for Card Readers")
    
    try:
        # First make sure pyscard is installed
        if not is_package_installed("smartcard"):
            print_warning("pyscard module not available to check readers")
            return True  # Don't fail the overall check for this
            
        # Import after checking to avoid import errors
        from smartcard.System import readers
        
        reader_list = readers()
        if reader_list:
            print_success(f"Found {len(reader_list)} card reader(s):")
            for i, reader in enumerate(reader_list):
                print_info(f"  {i+1}. {reader}")
            return True
        else:
            print_warning("No card readers detected")
            print_info("Please connect a supported card reader and try again")
            return True  # Don't fail the overall check for this
    except Exception as e:
        print_warning(f"Error checking card readers: {e}")
        print_info("This doesn't prevent startup, but check your reader connection")
        return True  # Don't fail the overall check for this

def create_directories():
    """Create required directories if they don't exist"""
    directories = ["logs", "data", os.path.join("logs", "backups")]
    
    print_header("Setting Up Directories")
    
    for directory in directories:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print_success(f"Created directory: {directory}")
            except Exception as e:
                print_error(f"Failed to create directory {directory}: {e}")
        else:
            print_info(f"Directory already exists: {directory}")
    
    return True

def main():
    """Main function to check and set up the environment"""
    print_header("Smart Card Manager Setup Checker")
    print(f"System: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check Python version first
    if not check_python_version():
        return 1
        
    # Check pip next, as we need it to install packages
    if not check_pip():
        return 1
    
    # Check and create directories
    create_directories()
    
    # Check for required packages
    packages_ok = check_required_packages()
    
    # Check PC/SC service
    pcsc_ok = check_pcsc_service()
    
    # Check for card readers
    readers_ok = check_card_readers()
    
    # Summary
    print_header("Setup Check Summary")
    if packages_ok and pcsc_ok:
        print_success("All critical checks passed! The application should start correctly.")
        if not readers_ok:
            print_warning("No readers detected, but you can still start the application.")
        print_info("Starting Smart Card Manager...")
        return 0
    else:
        print_error("Some critical checks failed. Please resolve the issues above.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nSetup check interrupted.")
        sys.exit(1)
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        sys.exit(1)