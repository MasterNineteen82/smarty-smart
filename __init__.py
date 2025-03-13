from flask import Flask
import logging
import os

def create_app(config=None):
    app = Flask(__name__)
    
    # Configure logging with more detail
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    # Load configuration from environment or file
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
        # Add other default configs
    )
    
    if config:
        app.config.from_mapping(config)
    try:
        # Use relative import since we're in the package
        from .routes import bp
        app.register_blueprint(bp)
        app.register_blueprint(bp)
    except ImportError as e:
        app.logger.error(f"Failed to import routes: {e}")
        # Handle dependency errors gracefully
        print(f"Error: {e}. Make sure all required packages are installed.")
        
    @app.route('/health')
    def health_check():
        return {"status": "ok"}
    
    return app

# If this is the main script
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)