from flask import Flask, render_template, jsonify, request
import os
import sys
import logging
import time
from logging.handlers import RotatingFileHandler
import config
from routes import bp as routes_bp
from server_utils import run_server, stop_server
from smartcard.System import readers

def create_app():
    app = Flask(__name__)

    # Load configuration
    try:
        app.config.from_object('app.config')
        app.secret_key = app.config.get('SECRET_KEY')  # Access SECRET_KEY from app.config
        app.debug = app.config.get('DEBUG', False)  # Access DEBUG from app.config, default to False
    except Exception as e:
        print(f"Error loading configuration: {e}")
        raise

    # Configure logging
    configure_logging(app)

    # Register blueprints
    register_blueprints(app)

    return app

def register_blueprints(app):
    try:
        app.register_blueprint(routes_bp)
    except Exception as e:
        app.logger.error(f"Failed to register blueprint: {e}")
        raise

def configure_logging(app):
    """Configure logging for the application."""
    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    log_file = app.config.get('LOG_FILE', 'app.log')
    log_format = app.config.get('LOG_FORMAT', '%(asctime)s - %(levelname)s - %(message)s')

    logger = logging.getLogger('smarty')
    logger.setLevel(log_level)

    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
        console_handler = logging.StreamHandler()

        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        file_handler.setLevel(log_level)
        console_handler.setLevel(log_level if app.debug else logging.WARNING)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"Error configuring logging: {e}")
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.error(f"Fallback logging due to configuration error: {e}")

    app.logger = logger  # Attach the logger to the app instance
    return logger

app = create_app()
logger = app.logger  # Get the logger from the app instance

# Configuration
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
try:
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
except OSError as e:
    logger.error(f"Failed to create backup directory {BACKUP_DIR}: {e}")

# Server management functions
def manage_server(action, host=None, port=None):
    host = host or app.config.get('SERVER_HOST')
    port = port or app.config.get('SERVER_PORT')

    try:
        if action == 'start':
            success = run_server(app, host, int(port))  # Ensure port is an integer
            if not success:
                return False, "Failed to start server."

            if app.config.get('DEFAULT_READER'):
                from card_utils import select_reader, poll_card_presence
                try:
                    select_reader(app.config.get('DEFAULT_READER'))
                    poll_card_presence()
                except Exception as e:
                    logger.error(f"Error during reader selection/polling: {e}")
                    return False, f"Failed to initialize card reader: {str(e)}"
            return True, "Server started"

        elif action == 'stop':
            stop_server()
            return True, "Server stopped"
        else:
            return False, "Invalid action"
    except ValueError as ve:
        logger.error(f"Invalid host or port: {ve}")
        return False, "Invalid host or port specified."
    except Exception as e:
        logger.exception(f"Exception occurred during {action}: {e}")
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
    try:
        success, message = manage_server('start')
        status_code = 200 if success else 500
        return jsonify({"message": message}), status_code
    except Exception as e:
        logger.exception("Exception in start_server_route")
        return jsonify({"message": f"Internal server error: {str(e)}"}), 500

@app.route('/stop_server', methods=['POST'], endpoint='app_stop_server')
def stop_server_route():
    try:
        success, message = manage_server('stop')
        status_code = 200 if success else 500
        return jsonify({"message": message}), status_code
    except Exception as e:
        logger.exception("Exception in stop_server_route")
        return jsonify({"message": f"Internal server error: {str(e)}"}), 500

# Improved Error handling
@app.errorhandler(500)
def internal_server_error(e):
    logger.exception("Internal Server Error")
    return render_template('error.html', error_message="Internal server error"), 500

@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"Page Not Found: {request.path}")
    return render_template('error.html', error_message="Page not found"), 404

@app.errorhandler(Exception)
def unhandled_exception(e):
    logger.exception("Unhandled Exception")
    return render_template('error.html', error_message="An unexpected error occurred."), 500

# Main execution
if __name__ == '__main__':
    try:
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
    except Exception as e:
        logger.exception("Unhandled exception during server startup")
        sys.exit(1)