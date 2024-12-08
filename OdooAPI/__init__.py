# OdooAPI/__init__.py

from flask import Flask
from .config import Config
from .logging_config import setup_logging
from OdooAPI.models import init_db
from OdooAPI.routes import bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    setup_logging(app)

    # Initialize the database (this creates tables if not exist)
    init_db(app)

    app.register_blueprint(bp)
    return app