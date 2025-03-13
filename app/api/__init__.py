from flask import Flask, jsonify
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
    # Load default configuration from a file, if it exists
    app.config.from_object('config.DefaultConfig')

    # Load environment variables
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key')
    )

    # Optionally load configuration from a file specified by environment variable
    config_file = os.environ.get('APP_CONFIG_FILE')
    if config_file:
        try:
            app.config.from_pyfile(config_file)
        except FileNotFoundError:
            app.logger.warning(f"Config file not found: {config_file}")

    # Override with any passed-in configuration
    if config_override:
        app.config.from_mapping(config_override)

def configure_logging(app):
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
    try:
        from .routes import bp
        app.register_blueprint(bp)
    except ImportError as e:
        app.logger.error(f"Failed to import routes: {e}")
        print(f"Error: {e}. Ensure 'routes.py' exists and has a blueprint named 'bp'. Also, check dependencies.")

def register_error_handlers(app):
    def create_error_response(e, status_code):
        app.logger.exception(e)
        return jsonify({'code': status_code, 'description': str(e)}), status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return create_error_response(e, e.code)

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        return create_error_response(e, 500)

def register_health_check(app):
    @app.route('/health')
    def health_check():
        return jsonify({"status": "ok"})

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)