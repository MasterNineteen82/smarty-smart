"""
Server utility functions for Smart Card Manager.
Contains shared server management functions.
"""

import logging
import threading
from typing import Optional

from flask import Flask
from smartcard import System as scard

# Constants
HOST = 'localhost'
PORT = 5000
SERVER_START_MESSAGE = f"Server started on {HOST}:{PORT}"
SERVER_STOPPED_MESSAGE = "Server stopped"
NO_READERS_DETECTED_MESSAGE = "No readers detected"
READER_TYPE_ACS = "ACS_ACR122U"
READER_TYPE_CHERRY = "CHERRY_SMART_TERMINAL"
READER_TYPE_PROPRIETARY = "PROPRIETARY"
READER_TYPE_GENERIC = "GENERIC"
UNKNOWN = "UNKNOWN"

# Global server variables
server_thread: Optional[threading.Thread] = None
server_running: bool = False  # Flag to track server status
logger = logging.getLogger('server_utils')


def run_server(app: Optional[Flask] = None) -> dict:
    """
    Start the Flask server in a separate thread.

    Args:
        app: Flask app instance. If None, attempts to import it from smart.py.

    Returns:
        A dictionary with the status of the server operation.
    """
    global server_thread, server_running

    if server_running:
        return {"status": "already_running", "message": "Server is already running."}

    if not app:
        try:
            from smart import app as smart_app
            app = smart_app
        except ImportError:
            logger.error("No app provided and couldn't import from smart.py")
            return {"status": "error", "message": "No Flask app provided and failed to import."}

    def run_in_thread():
        """Runs the Flask app."""
        try:
            app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Server thread failed: {e}", exc_info=True)
            return  # Exit thread if app.run fails

    try:
        server_thread = threading.Thread(target=run_in_thread)
        server_thread.daemon = True  # Allow the main program to exit even if the thread is running
        server_thread.start()
        server_running = True
        logger.info(SERVER_START_MESSAGE)
        return {"status": "success", "message": SERVER_START_MESSAGE}
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def stop_server() -> dict:
    """
    Stop the Flask server.

    Returns:
        A dictionary with the status of the server operation.
    """
    global server_thread, server_running

    if not server_running or not (server_thread and server_thread.is_alive()):
        logger.warning("Server is not running")
        return {"status": "warning", "message": "Server is not running."}

    try:
        # Use a simple flag to signal the thread to stop
        server_running = False
        # Attempt to join the server thread, allowing it to terminate gracefully
        server_thread.join(timeout=5)
        if server_thread.is_alive():
            logger.error("Failed to stop server thread gracefully.")
            return {"status": "error", "message": "Failed to stop server thread gracefully."}

        server_thread = None
        logger.info(SERVER_STOPPED_MESSAGE)
        return {"status": "success", "message": SERVER_STOPPED_MESSAGE}
    except Exception as e:
        logger.error(f"Failed to stop server: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def detect_readers() -> list:
    """
    Detect and classify all available smart card readers.

    Returns:
        A list of dictionaries, each containing information about a detected reader.
    """
    try:
        available_readers = scard.readers()
        if not available_readers:
            logger.info(NO_READERS_DETECTED_MESSAGE)
            return []

        readers = []
        for reader in available_readers:
            reader_name = str(reader)
            reader_info = {
                "name": reader_name,
                "type": classify_reader_type(reader_name),
                "connected": True,
                "capabilities": get_reader_capabilities(reader_name)
            }
            readers.append(reader_info)
        return readers
    except Exception as e:
        logger.error(f"Error detecting readers: {e}", exc_info=True)
        return []


def classify_reader_type(reader_name: str) -> str:
    """
    Classify a reader based on its name.

    Args:
        reader_name: The name of the reader.

    Returns:
        A string representing the reader type.
    """
    reader_name = reader_name.upper() if reader_name else ""

    if not reader_name:
        return UNKNOWN

    if "ACR122U" in reader_name:
        return READER_TYPE_ACS
    elif "CHERRY" in reader_name and "TERMINAL" in reader_name:
        return READER_TYPE_CHERRY
    elif any(keyword in reader_name for keyword in ["OMNIKEY", "HID", "GEMALTO"]):
        return READER_TYPE_PROPRIETARY
    else:
        return READER_TYPE_GENERIC


def get_reader_capabilities(reader_name: str) -> dict:
    """
    Determine capabilities of a reader based on its type.

    Args:
        reader_name: The name of the reader.

    Returns:
        A dictionary of reader capabilities.
    """
    reader_type = classify_reader_type(reader_name)

    capabilities = {
        "contactless": True,
        "contact": False,
        "mifare_classic": True,
        "mifare_ultralight": True,
        "mifare_desfire": False,
        "felica": False,
        "iso_14443_type_a": True,
        "iso_14443_type_b": False,
        "emv": False
    }

    if reader_type == READER_TYPE_ACS:
        capabilities.update({
            "mifare_desfire": True,
            "felica": True,
            "iso_14443_type_b": True
        })
    elif reader_type == READER_TYPE_CHERRY:
        capabilities.update({
            "contact": True,
            "mifare_desfire": True,
            "iso_14443_type_b": True,
            "emv": True
        })
    elif reader_type == READER_TYPE_PROPRIETARY:
        capabilities.update({
            "mifare_desfire": True,
            "iso_14443_type_b": True
        })

    return capabilities