"""
Server utility functions for Smart Card Manager
Contains shared server management functions
"""

from threading import Thread
from werkzeug.serving import make_server
import logging
from flask import Flask
from typing import Optional

# Global server variables
server: Optional[make_server] = None
server_thread: Optional[Thread] = None
logger = logging.getLogger('server_utils')

# Update the run_server function to have a default parameter if possible
def run_server(app=None):
    """
    Start the server.
    
    Args:
        app: Flask app to run. If None, tries to import from smart.py
    """
    global server_process, server_running
    
    if server_running:
        return {"status": "already_running"}
        
    try:
        # If no app provided, try to import it
        if app is None:
            try:
                from smart import app as smart_app
                app = smart_app
            except ImportError:
                import logging
                logging.error("No app provided and couldn't import from smart.py")
                return {"status": "error", "message": "No Flask app provided"}
        
        import threading
        
        def run_in_thread():
            app.run(host='localhost', port=5000, debug=False)
            
        server_thread = threading.Thread(target=run_in_thread)
        server_thread.daemon = True
        server_thread.start()
        
        server_process = server_thread
        server_running = True
        
        import logging
        logging.info("Server started on localhost:5000")
        return {"status": "success"}
    except Exception as e:
        import logging
        logging.error(f"Failed to start server: {str(e)}")
        return {"status": "error", "message": str(e)}

def stop_server() -> bool:
    """Stop the Flask server"""
    global server, server_thread
    try:
        if server and server_thread.is_alive():
            server.shutdown()
            server_thread.join(timeout=5)
            server = None
            server_thread = None
            logger.info("Server stopped")
            return True
        else:
            logger.warning("Server is not running")
            return False
    except Exception as e:
        logger.error(f"Failed to stop server: {e}", exc_info=True)
        return False

def detect_readers():
    """
    Detect and classify all available smart card readers.
    
    Returns:
        list: List of dict objects containing reader information
    """
    import smartcard.System as scard
    import logging
    
    readers = []
    try:
        # Get list of available readers
        available_readers = scard.readers()
        if not available_readers:
            logging.info("No readers detected")
            return []
            
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
        logging.error(f"Error detecting readers: {str(e)}")
        return []

def classify_reader_type(reader_name):
    """
    Classify a reader based on its name.
    
    Args:
        reader_name (str): Name of the reader
        
    Returns:
        str: Reader type ('ACS_ACR122U', 'CHERRY_SMART_TERMINAL', 'GENERIC')
    """
    reader_name = reader_name.upper() if reader_name else ""
    
    if not reader_name:
        return "UNKNOWN"
        
    if "ACR122U" in reader_name:
        return "ACS_ACR122U"
    elif "CHERRY" in reader_name and "TERMINAL" in reader_name:
        return "CHERRY_SMART_TERMINAL"
    elif any(keyword in reader_name for keyword in ["OMNIKEY", "HID", "GEMALTO"]):
        return "PROPRIETARY"
    else:
        return "GENERIC"  # Default to GENERIC instead of UNKNOWN for better compatibility

def get_reader_capabilities(reader_name):
    """
    Determine capabilities of a reader based on its type.
    
    Args:
        reader_name (str): Name of the reader
        
    Returns:
        dict: Dictionary of reader capabilities
    """
    reader_type = classify_reader_type(reader_name)
    
    # Base capabilities all readers should have
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
    
    # Adjust capabilities based on reader type
    if reader_type == "ACS_ACR122U":
        capabilities.update({
            "mifare_desfire": True,
            "felica": True,
            "iso_14443_type_b": True
        })
    elif reader_type == "CHERRY_SMART_TERMINAL":
        capabilities.update({
            "contact": True,
            "mifare_desfire": True,
            "iso_14443_type_b": True,
            "emv": True
        })
    elif reader_type == "PROPRIETARY":
        capabilities.update({
            "mifare_desfire": True,
            "iso_14443_type_b": True
        })
        
    return capabilities