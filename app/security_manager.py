import logging
import hashlib
import os
import secrets
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
from functools import wraps, lru_cache
from typing import Tuple, Optional

from app.core.card_utils import config  # Import the config object
from app.db import session_scope, User

# Configure logging
logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom exception for authentication failures."""
    pass

class AuthorizationError(Exception):
    """Custom exception for authorization failures."""
    pass

class EncryptionError(Exception):
    """Custom exception for encryption failures."""
    pass

class SecurityManager:
    """
    Manages security-related operations, including authentication, authorization,
    encryption, and PIN verification.
    """

    def __init__(self, key=None):
        """
        Initializes the SecurityManager with an optional encryption key.
        """
        self.encryption_key = key or self._load_or_generate_key()
        self.fernet = Fernet(self.encryption_key.encode())
        self.default_pin = config.get("DEFAULT_PIN")  # Access DEFAULT_PIN using config
        self.max_pin_attempts = config.get("MAX_PIN_ATTEMPTS")  # Access MAX_PIN_ATTEMPTS using config
        self.pin_attempts = 0

    def _load_or_generate_key(self) -> str:
        """
        Loads the encryption key from an environment variable or generates a new one.
        """
        key = os.environ.get("SMARTCARD_ENCRYPTION_KEY")
        if key:
            logger.info("Encryption key loaded from environment variable.")
            return key
        else:
            key = self._generate_encryption_key()
            logger.warning("No encryption key provided. Generated a new key. Ensure key persistence in production.")
            return key

    def _generate_encryption_key(self) -> str:
        """
        Generates a new encryption key.
        """
        key = Fernet.generate_key().decode()
        return key

    def persist_key(self):
        """
        Persists the encryption key to an environment variable.
        """
        os.environ["SMARTCARD_ENCRYPTION_KEY"] = self.encryption_key
        logger.info("Encryption key persisted to environment variable.")

    async def authenticate_user(self, username, password):
        """
        Authenticate a user by checking the provided credentials against stored credentials.
        """
        logger.info(f"Authenticating user {username}")
        try:
            with session_scope() as db:
                # Retrieve user from database based on username
                user = db.query(User).filter(User.username == username).first()

                if user is None:
                    logger.warning(f"Authentication failed for user {username}: user not found.")
                    raise AuthenticationError("Invalid credentials.")

                # Hash the provided password
                hashed_password = self._hash_password(password)

                # Compare the hashed password with the stored hash
                if hashed_password == user.password:
                    logger.info(f"User {username} authenticated successfully.")
                    return True
                else:
                    logger.warning(f"Authentication failed for user {username}: incorrect password.")
                    raise AuthenticationError("Invalid credentials.")
        except Exception as e:
            logger.error(f"Authentication failed for user {username}: {e}")
            raise AuthenticationError("Authentication failed.") from e

    async def authorize_user(self, username, permission):
        """
        Authorize a user to perform a specific action based on their roles and permissions.
        """
        logger.info(f"Authorizing user {username} for permission {permission}")
        try:
            # Retrieve user roles from database
            user_roles = await self._get_user_roles_from_db(username)

            # Check if user has the required permission based on their roles
            if self._check_permission(user_roles, permission):
                logger.info(f"User {username} authorized for permission {permission}.")
                return True
            else:
                logger.warning(f"User {username} not authorized for permission {permission}.")
                raise AuthorizationError("Unauthorized access.")
        except Exception as e:
            logger.error(f"Authorization failed for user {username}: {e}")
            raise AuthorizationError("Authorization failed.") from e

    async def _get_user_roles_from_db(self, username):
        """
        Retrieve user roles from the database.
        This is a placeholder; replace with actual database retrieval logic.
        """
        # Placeholder: Simulate fetching user roles from a database
        if username == "testuser":
            return ["admin"]
        else:
            return []

    def _check_permission(self, user_roles, permission):
        """
        Check if the user has the specified permission based on their roles.
        This is a placeholder; replace with actual permission checking logic.
        """
        # Placeholder: Simulate permission checking based on roles
        if "admin" in user_roles:
            return True  # Admins have all permissions
        if permission == "read" and "reader" in user_roles:
            return True  # Readers have read permission
        return False

    def generate_encryption_key(self):
        """
        Generate a new encryption key using Fernet.
        """
        logger.info("Generating a new encryption key")
        try:
            key = Fernet.generate_key()
            logger.info("Encryption key generated successfully.")
            return key
        except Exception as e:
            logger.error(f"Failed to generate encryption key: {e}")
            raise EncryptionError("Failed to generate encryption key.") from e

    def encrypt_data(self, data, key=None):
        """
        Encrypt data using Fernet.
        """
        logger.info("Encrypting data")
        try:
            if key is None:
                cipher = self.fernet
            else:
                cipher = Fernet(key)
            encrypted_data = cipher.encrypt(data.encode())
            logger.info("Data encrypted successfully.")
            return encrypted_data
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError("Encryption failed.") from e

    def decrypt_data(self, data, key=None):
        """
        Decrypt data using Fernet.
        """
        logger.info("Decrypting data")
        try:
            if key is None:
                cipher = self.fernet
            else:
                cipher = Fernet(key)
            decrypted_data = cipher.decrypt(data.decode()).decode()
            logger.info("Data decrypted successfully.")
            return decrypted_data
        except InvalidToken as e:
            logger.error(f"Decryption failed: Invalid token - {e}")
            raise EncryptionError("Decryption failed: Invalid token.") from e
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError("Decryption failed.") from e

    def verify_pin(self, pin: str) -> Tuple[bool, str]:
        """
        Verifies the provided PIN against the stored PIN.
        """
        if pin == self.default_pin:
            self.pin_attempts = 0
            return True, "PIN verified successfully"
        else:
            self.pin_attempts += 1
            if self.pin_attempts >= self.max_pin_attempts:
                return False, "PIN blocked due to too many incorrect attempts"
            else:
                return False, f"Incorrect PIN. Attempts remaining: {self.max_pin_attempts - self.pin_attempts}"

    def reset_pin_attempts(self) -> None:
        """
        Resets the PIN attempts counter.
        """
        self.pin_attempts = 0

    def _hash_password(self, password):
        """
        Hash the password using SHA-256.
        """
        # Use a salt for more secure hashing
        salt = os.urandom(16)  # Generate a random salt
        salted_password = salt + password.encode('utf-8')
        hashed_password = hashlib.sha256(salted_password).hexdigest()
        return hashed_password

    def _hash_pin(self, pin):
        """
        Hash the PIN using SHA-256.
        """
        hashed_pin = hashlib.sha256(pin.encode()).hexdigest()
        return hashed_pin

    def require_auth(self, permission):
        """
        Decorator to enforce authorization on a method.
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                username = kwargs.get('username')  # Assuming username is passed as a kwarg
                if not username:
                    raise ValueError("Username must be provided.")
                if not self.authorize_user(username, permission):
                    raise AuthorizationError(f"User {username} not authorized for {permission}.")
                return func(*args, **kwargs)
            return wrapper
        return decorator

@lru_cache(maxsize=1)
def get_security_manager():
    """
    Returns a singleton instance of the SecurityManager.
    """
    return SecurityManager()