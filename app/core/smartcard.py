import logging
from smartcard.System import readers
from smartcard.CardConnection import CardConnection
from smartcard.util import toHexString

logger = logging.getLogger(__name__)

class SmartCardError(Exception):
    """
    Custom exception for smart card related errors.

    Attributes:
        message (str): Explanation of the error.
        card_id (int, optional): The ID of the card involved. Defaults to None.
        reader_name (str, optional): The name of the reader involved. Defaults to None.
        atr (str, optional): ATR of the card, if available. Defaults to None.
    """
    def __init__(self, message, card_id=None, reader_name=None, atr=None):
        super().__init__(message)
        self.message = message
        self.card_id = card_id
        self.reader_name = reader_name
        self.atr = atr

    def __str__(self):
        details = []
        if self.card_id is not None:
            details.append(f"Card ID: {self.card_id}")
        if self.reader_name is not None:
            details.append(f"Reader: {self.reader_name}")
        if self.atr is not None:
            details.append(f"ATR: {self.atr}")
        if details:
            return f"{self.message} ({', '.join(details)})"
        return self.message


class CardConnectionError(SmartCardError):
    """Exception for connection related issues."""
    def __init__(self, message, card_id=None, reader_name=None, atr=None, reader_status=None):
        super().__init__(message, card_id, reader_name, atr)
        self.reader_status = reader_status

    def __str__(self):
        details = super().__str__()
        status_details = []
        if self.reader_status:
            status_details.append(f"Reader Status: {self.reader_status}")

        if status_details:
            return f"{details} ({', '.join(status_details)})"
        return details


class CardDataError(SmartCardError):
    """Exception for data reading/writing issues."""
    def __init__(self, message, card_id=None, reader_name=None, atr=None, sw1=None, sw2=None):
        super().__init__(message, card_id, reader_name, atr)
        self.sw1 = sw1
        self.sw2 = sw2

    def __str__(self):
        details = super().__str__()
        status_details = []
        if self.sw1 is not None:
            status_details.append(f"SW1: {self.sw1:02X}")
        if self.sw2 is not None:
            status_details.append(f"SW2: {self.sw2:02X}")

        if status_details:
            return f"{details} (Status: {', '.join(status_details)})"
        return details


class CardAuthenticationError(SmartCardError):
    """Exception for authentication failures."""
    def __init__(self, message, card_id=None, reader_name=None, atr=None, sw1=None, sw2=None):
        super().__init__(message, card_id, reader_name, atr)
        self.sw1 = sw1
        self.sw2 = sw2

    def __str__(self):
        details = super().__str__()
        status_details = []
        if self.sw1 is not None:
            status_details.append(f"SW1: {self.sw1:02X}")
        if self.sw2 is not None:
            status_details.append(f"SW2: {self.sw2:02X}")

        if status_details:
            return f"{details} (Status: {', '.join(status_details)})"
        return details

def read_smart_card_data(card_id: int, command: list = None):
    """
    Reads data from a conventional smart card using pyscard.

    Args:
        card_id (int): The ID of the smart card.
        command (list, optional): The command to send to the card. Defaults to a standard read command.

    Returns:
        dict: A dictionary containing the card ID, type, and data read from the card.

    Raises:
        SmartCardError: If there is an error reading the card data.
    """
    if not isinstance(card_id, int):
        logger.error("Card ID must be an integer.")
        raise ValueError("Card ID must be an integer.")

    if card_id <= 0:
        logger.warning("Card ID should be a positive integer.")

    reader = None
    connection = None
    try:
        # Get the list of readers
        reader_list = readers()
        if not reader_list:
            raise CardConnectionError("No smart card readers found.")

        # Use the first reader
        reader = reader_list[0]
        logger.info(f"Using reader: {reader}")

        # Establish a connection to the card
        try:
            connection = reader.createConnection()
            connection.connect()
            logger.info("Connected to smart card.")
        except Exception as e:
            raise CardConnectionError(f"Failed to connect to smart card: {e}")

        # Send a command to read data from the card (replace with your actual command)
        if command is None:
            command = [0x00, 0xC0, 0x00, 0x00, 0x08]  # Default command to read 8 bytes
        if not isinstance(command, list):
            raise ValueError("Command must be a list of integers.")

        try:
            response, sw1, sw2 = connection.transmit(command)
        except Exception as e:
            raise CardDataError(f"Failed to transmit command: {e}")

        if sw1 == 0x90 and sw2 == 0x00:
            card_data = {"card_id": card_id, "type": "smartcard", "data": toHexString(response)}
            logger.info(f"Read data: {card_data}")
            return card_data
        elif sw1 == 0x6C:
            error_message = f"Incorrect length provided in command. Expected length: {sw2}"
            logger.error(error_message)
            raise CardDataError(error_message)
        else:
            error_message = f"Failed to read card data. Status: {sw1:02X} {sw2:02X}"
            logger.error(error_message)
            raise CardDataError(error_message)

    except (CardConnectionError, CardDataError, ValueError) as e:
        logger.error(f"Failed to read smart card data for ID {card_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading smart card data for ID {card_id}: {e}")
        raise SmartCardError(f"An unexpected error occurred: {e}")
    finally:
        if connection:
            try:
                connection.disconnect()
                logger.info("Disconnected from smart card.")
            except Exception as e:
                logger.error(f"Failed to disconnect from smart card: {e}")

def authenticate_smart_card(card_id: int, pin: str, command: list = None):
    """
    Authenticates a conventional smart card using pyscard.

     Args:
        card_id (int): The ID of the smart card.
        pin (str): The PIN code for authentication.
        command (list, optional): The command to send to the card. Defaults to a PIN authentication command.

    Returns:
        bool: True if authentication is successful, False otherwise.

    Raises:
        SmartCardError: If there is an error during authentication.
    """
    if not isinstance(card_id, int):
        logger.error("Card ID must be an integer.")
        raise ValueError("Card ID must be an integer.")

    if not isinstance(pin, str):
        logger.error("PIN must be a string.")
        raise ValueError("PIN must be a string.")

    if not pin:
        logger.error("PIN cannot be empty.")
        raise ValueError("PIN cannot be empty.")

    reader = None
    connection = None

    try:
        # Get the list of readers
        reader_list = readers()
        if not reader_list:
            raise CardConnectionError("No smart card readers found.")

        # Use the first reader
        reader = reader_list[0]
        logger.info(f"Using reader: {reader}")

        # Establish a connection to the card
        try:
            connection = reader.createConnection()
            connection.connect()
            logger.info("Connected to smart card.")
        except Exception as e:
            raise CardConnectionError(f"Failed to connect to smart card: {e}")

        # Send a command to authenticate the card (replace with your actual command)
        if command is None:
            command = [0x00, 0x20, 0x00, 0x00, len(pin)] + [ord(c) for c in pin]
        if not isinstance(command, list):
            raise ValueError("Command must be a list of integers.")
        try:
            response, sw1, sw2 = connection.transmit(command)
        except Exception as e:
            raise CardDataError(f"Failed to transmit command: {e}")

        if sw1 == 0x90 and sw2 == 0x00:
            logger.info("Authentication successful.")
            return True
        elif sw1 == 0x63:
            error_message = f"Authentication failed. Incorrect PIN. Status: {sw1:02X} {sw2:02X}"
            logger.warning(error_message)
            return False
        else:
            error_message = f"Authentication failed. Status: {sw1:02X} {sw2:02X}"
            logger.warning(error_message)
            raise CardAuthenticationError(error_message)

    except (CardConnectionError, CardDataError, CardAuthenticationError, ValueError) as e:
        logger.error(f"Failed to authenticate smart card with ID {card_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while authenticating smart card with ID {card_id}: {e}")
        raise SmartCardError(f"An unexpected error occurred: {e}")
    finally:
        if connection:
            try:
                connection.disconnect()
                logger.info("Disconnected from smart card.")
            except Exception as e:
                logger.error(f"Failed to disconnect from smart card: {e}")