"""Flask application factory for TrueNAS Password Change Web Interface."""

import os
from flask import Flask
from dotenv import load_dotenv

from app.config import config

# Load environment variables from .env file
load_dotenv()


def create_app(config_override=None):
    """Create and configure the Flask application.
    
    Args:
        config_override: Optional configuration dictionary to override defaults.
        
    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    
    # Load configuration from environment or default
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config.get(env, config['default']))
    
    # Override with provided config
    if config_override:
        app.config.update(config_override)
    
    # Register blueprints
    from app.routes import auth, password
    app.register_blueprint(auth.bp)
    app.register_blueprint(password.bp)
    
    return app
