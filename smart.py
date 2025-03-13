from flask import Flask, render_template
import os
import sys
import logging
import time
from logging.handlers import RotatingFileHandler
import config
from routes import bp as routes_bp
from server_utils import run_server, stop_server
from smartcard.System import readers

app = Flask(__name__, template_folder='templates', static_folder='static')

# Ensure backup directory exists
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Register Blueprints
app.register_blueprint(routes_bp)

# Update logging configuration
logger = logging.getLogger('smarty')
logger.setLevel(config.LOG_LEVEL)

# Create handlers
file_handler = RotatingFileHandler(
    config.LOG_FILE, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
console_handler = logging.StreamHandler()

# Set log levels
file_handler.setLevel(config.LOG_LEVEL)
console_handler.setLevel(config.LOG_LEVEL if config.DEBUG else logging.WARNING)

# Create formatter
formatter = logging.Formatter(config.LOG_FORMAT)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Update app configuration
app.secret_key = config.SECRET_KEY
app.debug = config.DEBUG

# Update server start function to use config
def start_server(host=None, port=None):
    host = host or config.SERVER_HOST
    port = port or config.SERVER_PORT
    try:
        success = run_server(app, host, port)
        if success and config.DEFAULT_READER:
            # Import here to avoid circular import
            from card_utils import select_reader, poll_card_presence
            select_reader(config.DEFAULT_READER)
            poll_card_presence()
        return success
    except Exception as e:
        logger.error(f"Exception occurred while starting server: {e}")
        return False

@app.route('/')
def index():
    return render_template('index.html', readers=[str(r) for r in readers()])

@app.route('/start_server', methods=['POST'], endpoint='app_start_server')  # Added unique endpoint
def start_server_route():
    try:
        if start_server():
            return {"message": "Server started"}, 200
        else:
            return {"message": "Failed to start server"}, 500
    except Exception as e:
        logger.error(f"Exception occurred while starting server: {e}")
        return {"message": "Internal server error"}, 500

@app.route('/stop_server', methods=['POST'], endpoint='app_stop_server')  # Added unique endpoint
def stop_server_route():
    try:
        stop_server()
        return {"message": "Server stopped"}, 200
    except Exception as e:
        logger.error(f"Exception occurred while stopping server: {e}")
        return {"message": "Internal server error"}, 500

if __name__ == '__main__':
    if start_server():
        try:
            while True:
                time.sleep(1)  # Keep main thread alive
        except KeyboardInterrupt:
            stop_server()
            sys.exit(0)
    else:
        logger.error("Failed to start the server. Exiting.")
        sys.exit(1)