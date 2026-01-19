"""Unit tests for authentication routes."""

import pytest
from unittest.mock import patch, MagicMock

from app import create_app
from app.truenas_rest_client import TrueNASAPIError


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'TRUENAS_HOST': 'test.truenas.local',
        'TRUENAS_PORT': 443,
        'TRUENAS_USE_SSL': True,
    })
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestIndexRoute:
    """Test cases for index route."""
    
    def test_index_redirects_to_login_when_not_logged_in(self, client):
        """Test index redirects to login when user is not authenticated."""
        response = client.get('/')
        
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_index_redirects_to_password_change_when_logged_in(self, client):
        """Test index redirects to password change when user is authenticated."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/')
        
        assert response.status_code == 302
        assert '/change-password' in response.location


class TestLoginRoute:
    """Test cases for login route."""
    
    def test_login_page_renders(self, client):
        """Test login page renders correctly."""
        response = client.get('/login')
        
        assert response.status_code == 200
        assert b'TrueNAS Login' in response.data
        assert b'Username' in response.data
        assert b'Password' in response.data
    
    def test_login_with_empty_form(self, client):
        """Test login fails with empty form."""
        response = client.post('/login', data={
            'username': '',
            'password': ''
        })
        
        assert response.status_code == 200
        assert b'Username is required' in response.data
    
    @patch('app.routes.auth.get_truenas_client')
    def test_login_success(self, mock_client_class, client):
        """Test successful login."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=False)
        
        assert response.status_code == 302
        assert '/change-password' in response.location
        
        mock_client.connect.assert_called_once()
        mock_client.login.assert_called_once_with('testuser', 'testpass123')
        mock_client.disconnect.assert_called()
    
    @patch('app.routes.auth.get_truenas_client')
    def test_login_failure_invalid_credentials(self, mock_client_class, client):
        """Test login fails with invalid credentials."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.login.side_effect = TrueNASAPIError(
            "Authentication failed",
            reason="Invalid credentials"
        )
        
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        })
        
        assert response.status_code == 200
        assert b'Invalid credentials' in response.data
    
    @patch('app.routes.auth.get_truenas_client')
    def test_login_failure_connection_error(self, mock_client_class, client):
        """Test login fails with connection error."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.side_effect = TrueNASAPIError("Connection refused")
        
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        assert response.status_code == 200
        assert b'Login failed' in response.data
    
    @patch('app.routes.auth.get_truenas_client')
    def test_login_stores_session(self, mock_client_class, client):
        """Test login stores user info in session."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        with client:
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'testpass123'
            }, follow_redirects=False)
            
            from flask import session
            assert session['username'] == 'testuser'
            # Password should NOT be stored in session for security
            assert 'password' not in session


class TestLogoutRoute:
    """Test cases for logout route."""
    
    def test_logout_clears_session(self, client):
        """Test logout clears session and redirects to login."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/logout')
        
        assert response.status_code == 302
        assert '/login' in response.location
        
        with client.session_transaction() as sess:
            assert 'username' not in sess
            assert 'password' not in sess
    
    def test_logout_shows_message(self, client):
        """Test logout shows flash message."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/logout', follow_redirects=True)
        
        assert b'logged out' in response.data
