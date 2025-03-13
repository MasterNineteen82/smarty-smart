import logging
from smartcard.System import readers
from smartcard.CardConnection import CardConnection
from smartcard.util import toHexString

logger = logging.getLogger(__name__)

class SmartCardError(Exception):
    """Custom exception for smart card related errors."""
    pass

def read_smart_card_data(card_id: int):
    """
    Reads data from a conventional smart card using pyscard.
    """
    if not isinstance(card_id, int):
        logger.error("Card ID must be an integer.")
        raise SmartCardError("Invalid card ID format.")

    if card_id <= 0:
        logger.warning("Card ID should be a positive integer.")

    try:
        # Get the list of readers
        reader_list = readers()
        if not reader_list:
            raise SmartCardError("No smart card readers found.")

        # Use the first reader
        reader = reader_list[0]
        logger.info(f"Using reader: {reader}")

        # Establish a connection to the card
        connection = reader.createConnection()
        connection.connect()
        logger.info("Connected to smart card.")

        # Send a command to read data from the card (replace with your actual command)
        command = [0x00, 0xC0, 0x00, 0x00, 0x08]  # Example command to read 8 bytes
        response, sw1, sw2 = connection.transmit(command)

        if sw1 == 0x90 and sw2 == 0x00:
            card_data = {"card_id": card_id, "type": "smartcard", "data": toHexString(response)}
            logger.info(f"Read data: {card_data}")
            return card_data
        else:
            raise SmartCardError(f"Failed to read card data. Status: {sw1:02X} {sw2:02X}")

    except Exception as e:
        logger.error(f"Failed to read smart card data for ID {card_id}: {e}")
        raise SmartCardError(f"Failed to read card data: {e}")
    finally:
        if 'connection' in locals():
            connection.disconnect()
            logger.info("Disconnected from smart card.")

def authenticate_smart_card(card_id: int, pin: str):
    """
    Authenticates a conventional smart card using pyscard.
    """
    if not isinstance(card_id, int):
        logger.error("Card ID must be an integer.")
        raise SmartCardError("Invalid card ID format.")

    if not isinstance(pin, str):
        logger.error("PIN must be a string.")
        raise SmartCardError("Invalid PIN format.")

    if not pin:
        logger.error("PIN cannot be empty.")
        raise SmartCardError("PIN cannot be empty.")

    try:
        # Get the list of readers
        reader_list = readers()
        if not reader_list:
            raise SmartCardError("No smart card readers found.")

        # Use the first reader
        reader = reader_list[0]
        logger.info(f"Using reader: {reader}")

        # Establish a connection to the card
        connection = reader.createConnection()
        connection.connect()
        logger.info("Connected to smart card.")

        # Send a command to authenticate the card (replace with your actual command)
        command = [0x00, 0x20, 0x00, 0x00, len(pin)] + [ord(c) for c in pin]
        response, sw1, sw2 = connection.transmit(command)

        if sw1 == 0x90 and sw2 == 0x00:
            logger.info("Authentication successful.")
            return True
        else:
            logger.warning(f"Authentication failed. Status: {sw1:02X} {sw2:02X}")
            return False

    except Exception as e:
        logger.error(f"Failed to authenticate smart card with ID {card_id}: {e}")
        raise SmartCardError(f"Failed to authenticate card: {e}")
    finally:
        if 'connection' in locals():
            connection.disconnect()
            logger.info("Disconnected from smart card.")