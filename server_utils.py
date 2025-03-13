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

def run_server(app: Flask, host: str = 'localhost', port: int = 5000) -> bool:
    """Start the Flask server"""
    global server, server_thread
    try:
        if server is None or not server_thread.is_alive():
            server = make_server(host, port, app, threaded=True)
            server_thread = Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            logger.info(f"Server started on {host}:{port}")
            return True
        else:
            logger.warning("Server is already running")
            return False
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return False

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