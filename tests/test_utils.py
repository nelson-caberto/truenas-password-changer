"""Unit tests for utility functions."""

import pytest
from unittest.mock import patch, MagicMock

from app import create_app
from app.utils import get_truenas_client, login_required


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'TRUENAS_HOST': 'test.truenas.local',
        'TRUENAS_PORT': 8443,
        'TRUENAS_USE_SSL': False,
    })
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestGetTruenasClient:
    """Test cases for get_truenas_client function."""
    
    def test_creates_client_with_config(self, app):
        """Test client is created with app configuration."""
        with app.app_context():
            truenas_client = get_truenas_client()
            
            assert truenas_client.host == 'test.truenas.local'
            assert truenas_client.port == 8443
            assert truenas_client.use_ssl is False
    
    def test_creates_client_with_ssl(self, app):
        """Test client is created with SSL when configured."""
        app.config['TRUENAS_USE_SSL'] = True
        
        with app.app_context():
            truenas_client = get_truenas_client()
            
            assert truenas_client.use_ssl is True


class TestLoginRequired:
    """Test cases for login_required decorator."""
    
    def test_allows_access_when_logged_in(self, app, client):
        """Test decorator allows access when user is logged in."""
        @app.route('/test-protected')
        @login_required
        def protected_route():
            return 'Success'
        
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/test-protected')
        
        assert response.status_code == 200
        assert b'Success' in response.data
    
    def test_redirects_when_not_logged_in(self, app, client):
        """Test decorator redirects when user is not logged in."""
        @app.route('/test-protected-2')
        @login_required
        def protected_route_2():
            return 'Success'
        
        response = client.get('/test-protected-2')
        
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_shows_flash_message_when_not_logged_in(self, app, client):
        """Test decorator shows flash message when user is not logged in."""
        @app.route('/test-protected-3')
        @login_required
        def protected_route_3():
            return 'Success'
        
        response = client.get('/test-protected-3', follow_redirects=True)
        
        assert b'Please log in' in response.data
