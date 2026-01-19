"""Unit tests for Flask application factory."""

import pytest
from unittest.mock import patch

from app import create_app


class TestCreateApp:
    """Test cases for Flask application factory."""
    
    def test_create_app_default_config(self):
        """Test app creation with default configuration."""
        app = create_app()
        
        assert app is not None
        # Config values should exist (may be overridden by .env)
        assert app.config['SECRET_KEY'] is not None
        assert app.config['TRUENAS_HOST'] is not None
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


class TestDotEnvLoading:
    """Test cases for .env file loading."""
    
    def test_dotenv_module_imported(self):
        """Test that dotenv is imported in app module."""
        from app import load_dotenv
        assert load_dotenv is not None
    
    def test_config_class_reads_env_variables(self):
        """Test that Config class reads environment variables."""
        from app.config import Config
        
        # Config class has env variable attributes
        assert hasattr(Config, 'SECRET_KEY')
        assert hasattr(Config, 'TRUENAS_HOST')
        assert hasattr(Config, 'TRUENAS_PORT')
        assert hasattr(Config, 'TRUENAS_USE_SSL')
    
    def test_config_has_defaults(self):
        """Test that Config class has sensible defaults."""
        from app.config import Config
        
        # Defaults should be set
        assert Config.SECRET_KEY is not None
        assert Config.TRUENAS_HOST is not None
        assert Config.TRUENAS_PORT is not None
        assert isinstance(Config.TRUENAS_USE_SSL, bool)
    
    def test_create_app_uses_defaults_when_env_not_set(self):
        """Test that app uses default config when env variables not set."""
        import os
        
        # Save original env vars
        original_host = os.environ.get('TRUENAS_HOST')
        original_port = os.environ.get('TRUENAS_PORT')
        original_ssl = os.environ.get('TRUENAS_USE_SSL')
        original_secret = os.environ.get('SECRET_KEY')
        
        try:
            # Clear environment variables
            os.environ.pop('TRUENAS_HOST', None)
            os.environ.pop('TRUENAS_PORT', None)
            os.environ.pop('TRUENAS_USE_SSL', None)
            os.environ.pop('SECRET_KEY', None)
            
            app_instance = create_app()
            
            # Should use defaults from config (or values from .env if it exists)
            # Just verify the app is configured without errors
            assert app_instance is not None
            assert app_instance.config['TRUENAS_PORT'] == 443
            assert app_instance.config['TRUENAS_USE_SSL'] is True
        finally:
            # Restore original env vars
            if original_host:
                os.environ['TRUENAS_HOST'] = original_host
            if original_port:
                os.environ['TRUENAS_PORT'] = original_port
            if original_ssl:
                os.environ['TRUENAS_USE_SSL'] = original_ssl
            if original_secret:
                os.environ['SECRET_KEY'] = original_secret
    
    def test_config_override_takes_precedence(self):
        """Test that config_override takes precedence over env variables."""
        import os
        
        # Set environment variables
        os.environ['TRUENAS_HOST'] = 'env-host.local'
        
        try:
            app_instance = create_app({
                'TRUENAS_HOST': 'override-host.local',
            })
            
            # Override should take precedence
            assert app_instance.config['TRUENAS_HOST'] == 'override-host.local'
        
        finally:
            os.environ.pop('TRUENAS_HOST', None)

