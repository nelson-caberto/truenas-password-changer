"""Flask application factory for TrueNAS Password Change Web Interface."""

from flask import Flask


def create_app(config=None):
    """Create and configure the Flask application.
    
    Args:
        config: Optional configuration dictionary to override defaults.
        
    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    
    # Default configuration
    app.config.update(
        SECRET_KEY='dev-key-change-in-production',
        TRUENAS_HOST='localhost',
        TRUENAS_PORT=443,
        TRUENAS_USE_SSL=True,
    )
    
    # Override with provided config
    if config:
        app.config.update(config)
    
    # Register blueprints
    from app.routes import auth, password
    app.register_blueprint(auth.bp)
    app.register_blueprint(password.bp)
    
    return app
