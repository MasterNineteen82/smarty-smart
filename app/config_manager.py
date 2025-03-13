"""
Configuration Manager for Smarty Application

Provides centralized configuration management with persistence, defaults, and validation.
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from copy import deepcopy

# Set up logger
logger = logging.getLogger(__name__)

# Singleton instance
_config_instance = None

class ConfigManager:
    """Manages application configuration settings"""
    
    def __init__(self, config_file: str = "config.json"):
        """Initialize configuration manager
        
        Args:
            config_file: Path to configuration file (relative to app root or absolute)
        """
        # Determine config file path
        if not isinstance(config_file, str):
            raise TypeError("config_file must be a string")

        if os.path.isabs(config_file):
            self.config_path = config_file
        else:
            # Use the app root directory
            try:
                app_root = os.path.dirname(os.path.abspath(__file__))
                self.config_path = os.path.join(app_root, config_file)
            except NameError as e:
                # Handle case where __file__ is not defined (e.g., interactive mode)
                logger.warning("__file__ is not defined, using current working directory.")
                self.config_path = os.path.join(os.getcwd(), config_file)
            except Exception as e:
                logger.error(f"Error determining app root: {e}")
                self.config_path = config_file  # Fallback to the provided relative path

        # Initialize configuration
        self.config: Dict[str, Dict[str, Any]] = {}
        self.defaults: Dict[str, Dict[str, Any]] = {}
        
        # Set up default configuration
        self._setup_defaults()
        
        # Load existing configuration
        self.load()
    
    def _setup_defaults(self) -> None:
        """Set up default configuration values"""
        self.defaults = {
            "general": {
                "app_name": "Smarty Card Manager",
                "server_host": "127.0.0.1",
                "server_port": 5000,
                "debug": False
            },
            "readers": {
                "default_reader": "",
                "auto_connect": True,
                "command_timeout": 5,
                "transaction_timeout": 30
            },
            "security": {
                "max_pin_attempts": 3,
                "session_timeout": 600,
                "secure_memory": True
            },
            "logging": {
                "log_level": "INFO",
                "log_dir": "logs",
                "log_file": "smarty.log",
                "log_format": "%(asctime)s - %(levelname)s - %(message)s",
                "console_logging": True
            },
            "advanced": {
                "recovery_mode": False,
                "debug_apdu": False
            }
        }
    
    def load(self) -> None:
        """Load configuration from file"""
        try:
            # Start with defaults
            self.config = deepcopy(self.defaults)
            
            # Load from file if it exists
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r') as f:
                        try:
                            file_config = json.load(f)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSONDecodeError: Invalid JSON format in {self.config_path}: {e}")
                            # Optionally, you could reset to defaults or re-raise
                            self.config = deepcopy(self.defaults)
                            return
                except IOError as e:
                    logger.error(f"IOError: Could not open or read file {self.config_path}: {e}")
                    self.config = deepcopy(self.defaults)
                    return
                
                # Merge with defaults (only known sections and keys)
                if isinstance(file_config, dict):  # Validate loaded config
                    for section, settings in file_config.items():
                        if isinstance(section, str) and section in self.config:
                            if isinstance(settings, dict):
                                for key, value in settings.items():
                                    if isinstance(key, str) and key in self.config[section]:
                                        self.config[section][key] = value
                            else:
                                logger.warning(f"Section '{section}' in config file has invalid settings format (expected dict).")
                        else:
                            logger.warning(f"Unknown section '{section}' found in config file.")
                else:
                    logger.error(f"Invalid config file format.  Expected a dictionary at the root.")
                    self.config = deepcopy(self.defaults)
            else:
                # Create config file with defaults
                self.save()
                logger.info(f"Created new configuration file at {self.config_path}")
        except Exception as e:
            logger.exception(f"Unexpected error loading configuration: {e}")  # Log full traceback
            # Ensure we have defaults if loading fails
            self.config = deepcopy(self.defaults)
    
    def save(self) -> bool:
        """Save configuration to file"""
        try:
            # Make sure directory exists
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            except OSError as e:
                logger.error(f"OSError: Could not create directory: {e}")
                return False
            
            try:
                with open(self.config_path, 'w') as f:
                    try:
                        json.dump(self.config, f, indent=4)
                    except TypeError as e:
                        logger.error(f"TypeError: Could not serialize config to JSON: {e}")
                        return False
            except IOError as e:
                logger.error(f"IOError: Could not open or write to file {self.config_path}: {e}")
                return False
            
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.exception(f"Unexpected error saving configuration: {e}") # Log full traceback
            return False
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        if not isinstance(section, str):
            logger.error("Section must be a string.")
            return default
        if not isinstance(key, str):
            logger.error("Key must be a string.")
            return default

        try:
            if section in self.config and key in self.config[section]:
                return self.config[section][key]
            else:
                logger.warning(f"Configuration key '{key}' not found in section '{section}'. Returning default.")
                return default
        except Exception as e:
            logger.exception(f"Unexpected error getting configuration: {e}")
            return default

def set(self, section: str, key: str, value: Any) -> bool:
    """Set a configuration value"""
    if not isinstance(section, str):
        logger.error("Section must be a string.")
        return False
    if not isinstance(key, str):
        logger.error("Key must be a string.")
        return False

    try:
        if section in self.config:
            self.config[section][key] = value
            return True
        else:
            logger.error(f"Section '{section}' not found in configuration.")
            return False
    except Exception as e:
        logger.exception(f"Unexpected error setting configuration: {e}")
        return False

def reset_to_defaults(self, section: Optional[str] = None, key: Optional[str] = None) -> bool:
    """Reset configuration to default values, either for a specific key, a section, or the entire config."""
    try:
        if section is None:
            # Reset entire config to defaults
            self.config = deepcopy(self.defaults)
            logger.info("Configuration reset to defaults.")
            return True
        elif section in self.defaults:
            if key is None:
                # Reset entire section to defaults
                self.config[section] = deepcopy(self.defaults[section])
                logger.info(f"Section '{section}' reset to defaults.")
                return True
            elif key in self.defaults[section]:
                # Reset specific key to default
                self.config[section][key] = deepcopy(self.defaults[section][key])
                logger.info(f"Key '{key}' in section '{section}' reset to default.")
                return True
            else:
                logger.error(f"Key '{key}' not found in default configuration for section '{section}'.")
                return False
        else:
            logger.error(f"Section '{section}' not found in default configuration.")
            return False
    except Exception as e:
        logger.exception(f"Unexpected error resetting configuration: {e}")
        return False

def is_valid_section(self, section: str) -> bool:
    """Check if a section is a valid configuration section."""
    if not isinstance(section, str):
        logger.error("Section must be a string.")
        return False
    return section in self.defaults

def is_valid_key(self, section: str, key: str) -> bool:
    """Check if a key is a valid configuration key within a section."""
    if not isinstance(section, str):
        logger.error("Section must be a string.")
        return False
    if not isinstance(key, str):
        logger.error("Key must be a string.")
        return False

    if not self.is_valid_section(section):
        return False
    return key in self.defaults[section]

def get_config() -> ConfigManager:
    """Get the singleton configuration manager instance"""
    global _config_instance

    try:
        if _config_instance is None:
            _config_instance = ConfigManager()
            logger.debug("ConfigManager instance created.")
        else:
            logger.debug("Using existing ConfigManager instance.")
        
        return _config_instance
    except Exception as e:
        logger.exception(f"Error getting ConfigManager instance: {e}")
        raise  # Re-raise the exception after logging