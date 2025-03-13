from flask import Flask, render_template, jsonify
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

# Configuration
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

app.secret_key = config.SECRET_KEY
app.debug = config.DEBUG

# Logging setup
def setup_logging():
    logger = logging.getLogger('smarty')
    logger.setLevel(config.LOG_LEVEL)

    file_handler = RotatingFileHandler(
        config.LOG_FILE, 
        maxBytes=10*1024*1024,
        backupCount=5
    )
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(config.LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    file_handler.setLevel(config.LOG_LEVEL)
    console_handler.setLevel(config.LOG_LEVEL if config.DEBUG else logging.WARNING)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()

# Register Blueprints
app.register_blueprint(routes_bp)

# Server management functions
def manage_server(action, host=None, port=None):
    host = host or config.SERVER_HOST
    port = port or config.SERVER_PORT
    
    try:
        if action == 'start':
            success = run_server(app, host, port)
            if success and config.DEFAULT_READER:
                from card_utils import select_reader, poll_card_presence
                select_reader(config.DEFAULT_READER)
                poll_card_presence()
            return success, "Server started"
        elif action == 'stop':
            stop_server()
            return True, "Server stopped"
        else:
            return False, "Invalid action"
    except Exception as e:
        logger.error(f"Exception occurred during {action}: {e}")
        return False, f"Internal server error: {str(e)}"

# Routes
@app.route('/')
def index():
    try:
        reader_list = [str(r) for r in readers()]
        return render_template('index.html', readers=reader_list)
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return render_template('error.html', error_message="Failed to load the main page.")

@app.route('/start_server', methods=['POST'], endpoint='app_start_server')
def start_server_route():
    success, message = manage_server('start')
    status_code = 200 if success else 500
    return jsonify({"message": message}), status_code

@app.route('/stop_server', methods=['POST'], endpoint='app_stop_server')
def stop_server_route():
    success, message = manage_server('stop')
    status_code = 200 if success else 500
    return jsonify({"message": message}), status_code

# Error handling
@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Internal Server Error: {e}")
    return render_template('error.html', error_message="Internal server error"), 500

@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"Page Not Found: {e}")
    return render_template('error.html', error_message="Page not found"), 404

# Main execution
if __name__ == '__main__':
    success, message = manage_server('start')
    if success:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            manage_server('stop')
            sys.exit(0)
    else:
        logger.error(message)
        sys.exit(1)