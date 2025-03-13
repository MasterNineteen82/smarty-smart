from flask import Flask, jsonify, Blueprint
import logging
import os
from werkzeug.exceptions import HTTPException

def create_app(config_override=None):
    app = Flask(__name__)
    configure_app(app, config_override)
    configure_logging(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_health_check(app)
    return app

def configure_app(app, config_override=None):
    """Configures the Flask app with default settings and overrides."""
    # Load default configuration from a file or environment variables
    app.config.from_object('config.DefaultConfig')

    # Optionally apply environment variables
    app.config.from_envvar('APP_CONFIG_FILE', silent=True)

    # Apply overrides from the config_override dictionary
    if config_override:
        app.config.from_mapping(config_override)

def configure_logging(app):
    """Configures logging for the Flask app."""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    try:
        log_level = getattr(logging, log_level)
    except AttributeError:
        log_level = logging.INFO
        app.logger.warning(f"Invalid log level specified. Defaulting to INFO.")

    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)

def register_blueprints(app):
    """Registers blueprints for different parts of the application."""
    try:
        from .routes import bp
    except ImportError as e:
        app.logger.error(f"Failed to import routes: {e}")
        print(f"Error: {e}. Ensure 'routes.py' exists and has a blueprint named 'bp'. Also, check dependencies.")
        return  # Exit if routes blueprint cannot be loaded

    app.register_blueprint(bp)

def register_error_handlers(app):
    """Registers global error handlers for the Flask app."""
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handles HTTP exceptions, returning JSON responses."""
        app.logger.error(f"HTTP Exception: {e.code} - {e.description}")
        response = jsonify({'code': e.code, 'description': str(e)})  # Ensure description is a string
        response.status_code = e.code
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """Handles all other exceptions, logging them and returning a generic error."""
        app.logger.exception("An unexpected error occurred: %s", e)
        response = jsonify({'code': 500, 'description': 'Internal Server Error'})
        response.status_code = 500
        return response

def register_health_check(app):
    """Registers a health check endpoint."""
    @app.route('/health')
    def health_check():
        """Returns a simple health status."""
        return jsonify({"status": "ok"})

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)