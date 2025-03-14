import os
import json
from pathlib import Path

def check_path(path, is_file=False, create_if_missing=True):
    """Check if a path exists and create it if specified"""
    path_obj = Path(path)
    
    if is_file:
        exists = path_obj.is_file()
        parent = path_obj.parent
        if create_if_missing and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {parent}")
    else:
        exists = path_obj.is_dir()
        if create_if_missing and not exists:
            path_obj.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {path_obj}")
    
    status = "✓" if exists else "✗"
    print(f"{status} {'File' if is_file else 'Directory'}: {path}")
    return exists

# Required directories
required_dirs = [
    "app",
    "app/data",
    "app/logs",
    "static",
    "templates"
]

# Required files
required_files = [
    "config.json",
    "app/data/registered_cards.json"
]

print("=== Checking Application Structure ===")

print("\nChecking required directories:")
for directory in required_dirs:
    check_path(directory)

print("\nChecking required files:")
for file_path in required_files:
    check_path(file_path, is_file=True)
    
    # If it's a JSON file that doesn't exist, create it with empty structure
    if not os.path.exists(file_path) and file_path.endswith('.json'):
        if file_path == "app/data/registered_cards.json":
            with open(file_path, 'w') as f:
                json.dump({}, f)
            print(f"  Created empty JSON file: {file_path}")
        elif file_path == "config.json":
            default_config = {
                "app_name": "Smart Card Manager",
                "debug": True,
                "log_level": "INFO",
                "port": 5000
            }
            with open(file_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"  Created default config file: {file_path}")

print("\nSetup verification complete.")
input("Press Enter to exit...")