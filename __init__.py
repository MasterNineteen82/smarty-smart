from flask import Flask
import logging

def create_app(config=None):
    app = Flask(__name__)
    
    # Configure logging
    app.logger.setLevel(logging.INFO)
    # Add handlers if needed:
    # handler = logging.FileHandler('app.log')
    # app.logger.addHandler(handler)
    
    # Load configuration
    if config:
        app.config.from_mapping(config)
    
    # Register blueprint
    from .routes import bp
    app.register_blueprint(bp)
    
    return app

# If this is the main script
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)