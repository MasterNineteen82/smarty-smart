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
        self.config_path = self._resolve_config_path(config_file)
        self.config: Dict[str, Dict[str, Any]] = {}
        self.defaults: Dict[str, Dict[str, Any]] = {}
        self._setup_defaults()
        self.load()
    
    def _resolve_config_path(self, config_file: str) -> str:
        """Determine the absolute path to the configuration file."""
        if not isinstance(config_file, str):
            raise TypeError("config_file must be a string")

        if os.path.isabs(config_file):
            return config_file

        try:
            app_root = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(app_root, config_file)
        except NameError:
            logger.warning("__file__ is not defined, using current working directory.")
            return os.path.join(os.getcwd(), config_file)
        except Exception as e:
            logger.error(f"Error determining app root: {e}")
            return config_file  # Fallback to the provided relative path

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
            self.config = deepcopy(self.defaults)
            if os.path.exists(self.config_path):
                self._load_from_file()
            else:
                self.save()
                logger.info(f"Created new configuration file at {self.config_path}")
        except Exception as e:
            logger.exception(f"Unexpected error loading configuration: {e}")
            self.config = deepcopy(self.defaults)
    
    def _load_from_file(self) -> None:
        """Load configuration from the JSON file, merging with defaults."""
        try:
            with open(self.config_path, 'r') as f:
                try:
                    file_config = json.load(f)
                    self._merge_config(file_config)
                except json.JSONDecodeError as e:
                    logger.error(f"JSONDecodeError: Invalid JSON format in {self.config_path}: {e}")
        except IOError as e:
            logger.error(f"IOError: Could not open or read file {self.config_path}: {e}")

    def _merge_config(self, file_config: Dict[str, Any]) -> None:
         """Merge the loaded configuration with the default configuration."""
         if not isinstance(file_config, dict):
             logger.error("Invalid config file format. Expected a dictionary at the root.")
             return

         for section, settings in file_config.items():
             if not isinstance(section, str):
                 logger.warning(f"Invalid section name '{section}' (expected string); skipping.")
                 continue

             if section in self.config and isinstance(settings, dict):
                 for key, value in settings.items():
                     if not isinstance(key, str):
                         logger.warning(f"Invalid key name '{key}' in section '{section}' (expected string); skipping.")
                         continue
                     if key in self.config[section]:
                         self.config[section][key] = value
                     else:
                         logger.warning(f"Unknown key '{key}' in section '{section}'; skipping.")
             else:
                 logger.warning(f"Unknown section '{section}' found in config file; skipping.")
    
    def save(self) -> bool:
        """Save configuration to file"""
        try:
            self._ensure_directory_exists()
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except (OSError, TypeError, IOError, Exception) as e:
            logger.exception(f"Error saving configuration: {e}")
            return False
    
    def _ensure_directory_exists(self) -> None:
        """Ensure that the directory for the config file exists."""
        dir_path = os.path.dirname(os.path.abspath(self.config_path))
        os.makedirs(dir_path, exist_ok=True)
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        if not self._validate_section_and_key(section, key):
            return default

        try:
            return self.config[section][key]
        except KeyError:
            logger.warning(f"Configuration key '{key}' not found in section '{section}'. Returning default.")
            return default
        except Exception as e:
            logger.exception(f"Unexpected error getting configuration: {e}")
            return default
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """Set a configuration value"""
        if not self._validate_section_and_key(section, key, check_valid=False):
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
                self.config = deepcopy(self.defaults)
                logger.info("Configuration reset to defaults.")
                return True
            elif section in self.defaults:
                if key is None:
                    self.config[section] = deepcopy(self.defaults[section])
                    logger.info(f"Section '{section}' reset to defaults.")
                    return True
                elif key in self.defaults[section]:
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

    def _validate_section_and_key(self, section: str, key: str, check_valid: bool = True) -> bool:
        """Validate section and key, logging errors if invalid."""
        if not isinstance(section, str):
            logger.error("Section must be a string.")
            return False
        if not isinstance(key, str):
            logger.error("Key must be a string.")
            return False

        if check_valid and not self.is_valid_section(section):
            logger.error(f"Section '{section}' is not a valid configuration section.")
            return False
        if check_valid and not self.is_valid_key(section, key):
            logger.error(f"Key '{key}' is not a valid configuration key in section '{section}'.")
            return False
        return True

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
