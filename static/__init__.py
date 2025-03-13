from flask import Flask, jsonify
import logging
import os
from werkzeug.exceptions import HTTPException

def create_app(config=None):
    app = Flask(__name__)
    configure_logging(app)
    load_configuration(app, config)
    register_blueprints(app)
    register_error_handlers(app)
    register_health_check(app)
    return app

def configure_logging(app):
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

def load_configuration(app, config):
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
        # Add other default configs here, e.g., DATABASE_URL
    )
    if config:
        app.config.from_mapping(config)

def register_blueprints(app):
    try:
        from .routes import bp
        app.register_blueprint(bp)
    except ImportError as e:
        app.logger.error(f"Failed to import routes: {e}")
        print(f"Error: {e}. Ensure 'routes.py' exists and has a blueprint named 'bp'. Also, check dependencies.")

def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handles HTTP exceptions, returning JSON responses."""
        response = jsonify({'code': e.code, 'description': e.description})
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
    @app.route('/health')
    def health_check():
        return jsonify({"status": "ok"})

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)