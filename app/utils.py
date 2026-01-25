"""Shared utilities for the Flask application."""

import os
from functools import wraps
from flask import session, flash, redirect, url_for, current_app

from app.truenas_websocket_client import TrueNASWebSocketClient


def get_truenas_client():
    """Create a TrueNAS WebSocket client from app configuration.
    
    Returns:
        Configured TrueNASWebSocketClient instance.
    """
    api_key = os.getenv('TRUENAS_API_KEY')
    
    return TrueNASWebSocketClient(
        host=current_app.config['TRUENAS_HOST'],
        port=current_app.config['TRUENAS_PORT'],
        use_ssl=current_app.config['TRUENAS_USE_SSL'],
        api_key=api_key
    )


def login_required(f):
    """Decorator to require login for a route.
    
    Args:
        f: The view function to wrap.
        
    Returns:
        Wrapped function that checks for login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    
    return decorated_function
