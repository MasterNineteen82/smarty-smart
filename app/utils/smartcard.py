import logging
from typing import Optional, Dict, Any
from smartcard.System import readers
from smartcard.util import toHexString


logger = logging.getLogger(__name__)

class SmartCardError(Exception):
    """Custom exception for smart card related errors."""
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

class SmartCardUtils:
    """Utility class for smart card operations."""

    def __init__(self):
        self.reader = None
        self.connection = None

    def connect_to_reader(self):
        """Connect to the first available smart card reader."""
        try:
            available_readers = readers()
            if not available_readers:
                raise SmartCardError("No smart card readers found.")
            self.reader = available_readers[0]
            self.connection = self.reader.createConnection()
            self.connection.connect()
            logger.info(f"Connected to reader: {self.reader}")
        except Exception as e:
            raise SmartCardError(f"Failed to connect to reader: {e}")

    def get_card_info(self) -> Dict[str, Any]:
        """Retrieve information about the connected smart card."""
        try:
            atr = self.connection.getATR()
            atr_str = toHexString(atr)
            logger.info(f"Card ATR: {atr_str}")
            return {
                "atr": atr_str,
                "reader": self.reader.name
            }
        except Exception as e:
            raise SmartCardError(f"Failed to get card info: {e}")

    def read_card_data(self) -> Optional[str]:
        """Read data from the smart card."""
        try:
            apdu = [0x00, 0xB0, 0x00, 0x00, 0x10]  # Example APDU command
            response, sw1, sw2 = self.connection.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                data = toHexString(response)
                logger.info(f"Read data: {data}")
                return data
            else:
                raise SmartCardError(f"Failed to read card data: SW1={sw1}, SW2={sw2}")
        except Exception as e:
            raise SmartCardError(f"Error reading card data: {e}")

    def write_card_data(self, data: str):
        """Write data to the smart card."""
        try:
            apdu = [0x00, 0xD0, 0x00, 0x00, len(data)] + [ord(c) for c in data]  # Example APDU command
            response, sw1, sw2 = self.connection.transmit(apdu)
            if sw1 == 0x90 and sw2 == 0x00:
                logger.info("Data written successfully.")
            else:
                raise SmartCardError(f"Failed to write card data: SW1={sw1}, SW2={sw2}")
        except Exception as e:
            raise SmartCardError(f"Error writing card data: {e}")

    def disconnect(self):
        """Disconnect from the smart card reader."""
        try:
            if self.connection:
                self.connection.disconnect()
                logger.info("Disconnected from reader.")
        except Exception as e:
            raise SmartCardError(f"Error disconnecting from reader: {e}")

# Example usage
if __name__ == "__main__":
    sc_utils = SmartCardUtils()
    try:
        sc_utils.connect_to_reader()
        card_info = sc_utils.get_card_info()
        print(f"Card Info: {card_info}")
        data = sc_utils.read_card_data()
        print(f"Card Data: {data}")
        sc_utils.write_card_data("Hello, Smart Card!")
    except SmartCardError as e:
        logger.error(e)
    finally:
        sc_utils.disconnect()