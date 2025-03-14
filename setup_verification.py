"""
Verify application setup and create necessary files/directories
"""
import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("setup_checker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('setup_verification')

def check_system():
    """Check system requirements"""
    logger.info("Checking system requirements...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        logger.error(f"Python 3.8+ required. Found: {sys.version}")
        return False
    logger.info(f"Python version OK: {sys.version}")
    
    # Check virtual environment
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        logger.warning("Not running in a virtual environment")
    else:
        logger.info(f"Virtual environment detected: {sys.prefix}")
    
    return True

def check_directories():
    """Check and create necessary directories"""
    logger.info("Checking directory structure...")
    required_dirs = ["app/data", "app/logs", "static", "templates"]
    
    for directory in required_dirs:
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.info(f"Creating missing directory: {directory}")
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                return False
    
    logger.info("Directory structure OK")
    return True

def check_config_file():
    """Check if config.json exists and is valid"""
    logger.info("Checking config file...")
    config_path = Path("config.json")
    
    if not config_path.exists():
        logger.info("Creating default config.json file")
        default_config = {
            "app_name": "Smart Card Manager",
            "debug": True,
            "log_level": "INFO",
            "port": 5000,
            "card_data_path": "app/data/registered_cards.json"
        }
        try:
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to create config file: {e}")
            return False
    
    # Verify config file is valid JSON
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info("Config file is valid JSON")
    except json.JSONDecodeError as e:
        logger.error(f"Config file contains invalid JSON: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reading config file: {e}")
        return False
    
    return True

def check_card_registry():
    """Check if card registry exists and is valid"""
    logger.info("Checking card registry file...")
    
    # Get registry path from config if possible
    registry_path = "app/data/registered_cards.json"
    if os.path.exists("config.json"):
        try:
            with open("config.json", 'r') as f:
                config = json.load(f)
                if "card_data_path" in config:
                    registry_path = config["card_data_path"]
        except:
            pass
    
    registry_path = Path(registry_path)
    
    # Create parent directories if needed
    if not registry_path.parent.exists():
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created parent directory: {registry_path.parent}")
    
    if not registry_path.exists():
        logger.info(f"Creating empty card registry: {registry_path}")
        try:
            with open(registry_path, 'w') as f:
                json.dump({}, f)
        except Exception as e:
            logger.error(f"Failed to create card registry: {e}")
            return False
    else:
        # Verify the registry is valid JSON
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
            logger.info("Card registry is valid JSON")
        except json.JSONDecodeError:
            logger.warning("Card registry contains invalid JSON, recreating it")
            try:
                with open(registry_path, 'w') as f:
                    json.dump({}, f)
            except Exception as e:
                logger.error(f"Failed to recreate card registry: {e}")
                return False
        except Exception as e:
            logger.error(f"Error reading card registry: {e}")
            return False
    
    return True

def create_env_file():
    """Create or update .env file"""
    logger.info("Creating/updating .env file...")
    
    env_vars = {
        "PYTHONPATH": os.getcwd(),
        "DEBUG": "true",
        "APP_DATA_DIR": os.path.join(os.getcwd(), "app", "data"),
        "LOG_LEVEL": "INFO"
    }
    
    try:
        with open('.env', 'w') as env_file:
            for key, value in env_vars.items():
                env_file.write(f"{key}={value}\n")
        logger.info(".env file created/updated successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create .env file: {e}")
        return False

def main():
    logger.info("Starting setup verification")
    
    checks = [
        ("System requirements", check_system),
        ("Directory structure", check_directories),
        ("Configuration file", check_config_file),
        ("Card registry", check_card_registry),
        ("Environment file", create_env_file)
    ]
    
    all_passed = True
    for name, check_func in checks:
        logger.info(f"Running check: {name}")
        if check_func():
            logger.info(f"✓ {name} check passed")
        else:
            logger.error(f"✗ {name} check failed")
            all_passed = False
    
    if all_passed:
        logger.info("All checks passed! The application should be ready to run.")
        return 0
    else:
        logger.error("Some checks failed. Please check the log for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())