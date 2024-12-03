# OdooAPI/__init__.py

from flask import Flask
from .config import Config
from .logging_config import setup_logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    setup_logging(app)
    
    with app.app_context():
        # Import parts of our application
        from .routes import bp
        # Register Blueprints
        app.register_blueprint(bp)
        
    return app
