import logging
import nfc

logger = logging.getLogger(__name__)

class NFCError(Exception):
    """Custom exception for NFC related errors."""
    pass

def read_nfc_card_data(card_id: int):
    """
    Reads data from an NFC card.
    """
    try:
        logger.info(f"Attempting to read data from NFC card with ID: {card_id}")
        with nfc.ContactlessFrontend('usb') as clf:
            # Wait for a tag to be discovered
            tag = clf.connect(rdwr={'on-connect': lambda tag: tag.dump()})  # Attempt to read all data

            if not tag:
                raise NFCError("No NFC tag found within timeout.")

            # Extract relevant data from the tag (example)
            card_data = {
                "card_id": card_id,
                "type": "nfc",
                "tag_type": str(type(tag)),  # Include tag type
                "data": str(tag),  # String representation of the tag
            }
            logger.info(f"Successfully read data from NFC card {card_id}.")
            return card_data

    except nfc.clf.CommunicationError as e:
        logger.error(f"Communication error during NFC read: {e}")
        raise NFCError(f"Communication error with NFC card: {e}")
    except NFCError as e:
        raise e  # Re-raise NFCError to maintain consistent error handling
    except Exception as e:
        logger.exception(f"Unexpected error reading NFC card data: {e}")
        raise NFCError(f"Unexpected error reading NFC card: {e}")


def write_nfc_card_data(card_id: int, data: str):
    """
    Writes data to an NFC card.
    """
    try:
        logger.info(f"Attempting to write data to NFC card with ID: {card_id}")
        with nfc.ContactlessFrontend('usb') as clf:
            tag = clf.connect(rdwr={'on-connect': lambda tag: False})

            if not tag:
                raise NFCError("No NFC tag found within timeout.")

            #  Write data to the tag (replace with actual writing logic)
            #  This is a placeholder; actual writing depends on the tag type and data format.
            try:
                #  Example:  Writing text to a Mifare tag (requires specific tag and data formatting)
                # tag.write(data)  # Replace with appropriate write command
                logger.warning("NFC write functionality is a placeholder. Implement actual writing logic.")
                logger.info(f"Data to be written: {data}") # Log the data
                pass # Remove pass when implementing
            except Exception as e:
                 logger.error(f"Error writing data to NFC tag: {e}")
                 raise NFCError(f"Error writing data to NFC tag: {e}")


            logger.info(f"Data written to NFC card {card_id} successfully (placeholder).")
            return {"message": f"Data written to NFC card {card_id} successfully (placeholder)"}

    except nfc.clf.CommunicationError as e:
        logger.error(f"Communication error during NFC write: {e}")
        raise NFCError(f"Communication error with NFC card: {e}")
    except NFCError as e:
        raise e  # Re-raise NFCError
    except Exception as e:
        logger.exception(f"Unexpected error writing NFC card data: {e}")
        raise NFCError(f"Unexpected error writing NFC card: {e}")