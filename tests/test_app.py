"""Unit tests for Flask application factory."""

import pytest

from app import create_app


class TestCreateApp:
    """Test cases for Flask application factory."""
    
    def test_create_app_default_config(self):
        """Test app creation with default configuration."""
        app = create_app()
        
        assert app is not None
        assert app.config['SECRET_KEY'] == 'dev-key-change-in-production'
        assert app.config['TRUENAS_HOST'] == 'localhost'
        assert app.config['TRUENAS_PORT'] == 443
        assert app.config['TRUENAS_USE_SSL'] is True
    
    def test_create_app_custom_config(self):
        """Test app creation with custom configuration."""
        custom_config = {
            'SECRET_KEY': 'custom-secret-key',
            'TRUENAS_HOST': 'custom.truenas.local',
            'TRUENAS_PORT': 8080,
            'TRUENAS_USE_SSL': False,
            'TESTING': True,
        }
        
        app = create_app(custom_config)
        
        assert app.config['SECRET_KEY'] == 'custom-secret-key'
        assert app.config['TRUENAS_HOST'] == 'custom.truenas.local'
        assert app.config['TRUENAS_PORT'] == 8080
        assert app.config['TRUENAS_USE_SSL'] is False
        assert app.config['TESTING'] is True
    
    def test_create_app_registers_auth_blueprint(self):
        """Test app registers auth blueprint."""
        app = create_app()
        
        assert 'auth' in app.blueprints
    
    def test_create_app_registers_password_blueprint(self):
        """Test app registers password blueprint."""
        app = create_app()
        
        assert 'password' in app.blueprints
    
    def test_create_app_has_login_route(self):
        """Test app has login route."""
        app = create_app()
        
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/login' in rules
    
    def test_create_app_has_logout_route(self):
        """Test app has logout route."""
        app = create_app()
        
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/logout' in rules
    
    def test_create_app_has_password_change_route(self):
        """Test app has password change route."""
        app = create_app()
        
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/change-password' in rules
    
    def test_create_app_has_index_route(self):
        """Test app has index route."""
        app = create_app()
        
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/' in rules
