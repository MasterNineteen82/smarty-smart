from flask import Flask
from routes import bp
import logging

def create_app():
    app = Flask(__name__)
    
    # Configure logging
    handler = logging.FileHandler('smarty.log')
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    # Register blueprint
    app.register_blueprint(bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=True)