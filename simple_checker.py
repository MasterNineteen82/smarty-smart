import os
import sys
import json
from pathlib import Path

def check_path(path_str, is_file=False, message=""):
    """Check if path exists and display appropriate message"""
    path = Path(path_str)
    exists = path.exists()
    
    type_str = "File" if is_file else "Directory"
    status = "OK" if exists else "MISSING"
    print(f"{type_str}: {path_str} - {status}")
    
    if message and not exists:
        print(f"  Info: {message}")
    
    return exists

def check_config_content(path):
    """Check if config file has required keys"""
    try:
        with open(path, 'r') as f:
            config = json.load(f)
        
        required_keys = ['app_name', 'debug', 'log_level', 'port']
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            print(f"Config file is missing keys: {', '.join(missing_keys)}")
            return False
        else:
            print("Config file has all required keys")
            return True
    except Exception as e:
        print(f"Error checking config content: {str(e)}")
        return False

def check_app_structure():
    """Check critical application components"""
    print("\n=== Application Structure Check ===")
    
    # Essential directories
    essential_dirs = {
        "app": "Main application directory",
        "app/data": "Data storage directory",
        "app/logs": "Log files directory",
        "static": "Static assets directory",
        "templates": "HTML templates directory",
        "app/utils": "Utility modules directory"
    }
    
    # Essential files
    essential_files = {
        "config.json": "Application configuration",
        "app/data/registered_cards.json": "Card registry",
        "app/__init__.py": "Python package initializer",
        "app/main.py": "Main application entry point", 
        "app/routes.py": "API routes definition",
        "app/smart.py": "Application entry script",
        "requirements.txt": "Python dependencies"
    }

    # Optional but expected files
    optional_files = {
        ".env": "Environment variables", 
        "app/card_utils.py": "Card utility functions",
        "app/config.py": "Configuration loader"
    }
    
    # Check directories
    print("\nChecking essential directories:")
    all_dirs_exist = True
    for dir_path, description in essential_dirs.items():
        if not check_path(dir_path, is_file=False, message=description):
            all_dirs_exist = False
    
    # Check essential files
    print("\nChecking essential files:")
    all_files_exist = True
    for file_path, description in essential_files.items():
        if not check_path(file_path, is_file=True, message=description):
            all_files_exist = False
    
    # Check optional files
    print("\nChecking optional files:")
    for file_path, description in optional_files.items():
        check_path(file_path, is_file=True, message=description)
    
    # Check config file content if it exists
    if os.path.exists("config.json"):
        print("\nChecking config.json content:")
        check_config_content("config.json")
    
    # Final outcome
    print("\n=== Structure Check Result ===")
    if all_dirs_exist and all_files_exist:
        print("All essential components found - Structure OK")
        return True
    else:
        if not all_dirs_exist:
            print("ERROR: Missing essential directories")
        if not all_files_exist:
            print("ERROR: Missing essential files")
        print("Please create the missing components")
        return False

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    success = check_app_structure()
    
    # Exit with appropriate code
    print("\nCheck completed.")
    if not success:
        print("RESULT: FAILED - Missing essential components")
        sys.exit(1)
    else:
        print("RESULT: PASSED - All components found")
        sys.exit(0)