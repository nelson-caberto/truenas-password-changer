"""Shared utilities for the Flask application."""

import os
from functools import wraps
from flask import session, flash, redirect, url_for, current_app

from app.truenas_client import TrueNASClient
from app.truenas_rest_client import TrueNASRestClient


def get_truenas_client():
    """Create a TrueNAS client from app configuration.
    
    Supports both WebSocket (legacy) and REST API (recommended) clients.
    Configured via TRUENAS_CLIENT environment variable or config.
    
    Returns:
        Configured TrueNASClient or TrueNASRestClient instance.
    """
    # Determine which client to use (default to REST API)
    client_type = os.getenv('TRUENAS_CLIENT', 'rest').lower()
    
    config = {
        'host': current_app.config['TRUENAS_HOST'],
        'port': current_app.config['TRUENAS_PORT'],
        'use_ssl': current_app.config['TRUENAS_USE_SSL']
    }
    
    if client_type == 'websocket':
        return TrueNASClient(**config)
    else:
        # Default to REST API client
        return TrueNASRestClient(**config)


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
