"""Unit tests for password change routes."""

import pytest
from unittest.mock import patch, MagicMock

from app import create_app
from app.truenas_client import TrueNASAPIError


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


@pytest.fixture
def logged_in_client(client):
    """Create a test client with an authenticated session."""
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
        sess['password'] = 'currentpass123'
    return client


class TestLoginRequired:
    """Test cases for login_required decorator."""
    
    def test_password_change_requires_login(self, client):
        """Test password change page requires authentication."""
        response = client.get('/change-password')
        
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_password_change_accessible_when_logged_in(self, logged_in_client):
        """Test password change page accessible when logged in."""
        response = logged_in_client.get('/change-password')
        
        assert response.status_code == 200
        assert b'Change Password' in response.data


class TestPasswordChangeRoute:
    """Test cases for password change route."""
    
    def test_password_change_page_renders(self, logged_in_client):
        """Test password change page renders correctly."""
        response = logged_in_client.get('/change-password')
        
        assert response.status_code == 200
        assert b'Change Password' in response.data
        assert b'Current Password' in response.data
        assert b'New Password' in response.data
        assert b'Confirm New Password' in response.data
        assert b'testuser' in response.data
    
    def test_password_change_shows_logout_link(self, logged_in_client):
        """Test password change page has logout link."""
        response = logged_in_client.get('/change-password')
        
        assert response.status_code == 200
        assert b'Logout' in response.data
    
    def test_password_change_empty_form(self, logged_in_client):
        """Test password change fails with empty form."""
        response = logged_in_client.post('/change-password', data={
            'current_password': '',
            'new_password': '',
            'confirm_password': ''
        })
        
        assert response.status_code == 200
        assert b'Current password is required' in response.data
    
    def test_password_change_mismatched_passwords(self, logged_in_client):
        """Test password change fails when new passwords don't match."""
        response = logged_in_client.post('/change-password', data={
            'current_password': 'currentpass123',
            'new_password': 'newpass456',
            'confirm_password': 'differentpass789'
        })
        
        assert response.status_code == 200
        assert b'Passwords must match' in response.data
    
    @patch('app.utils.TrueNASRestClient')
    def test_password_change_wrong_current_password(self, mock_client_class, logged_in_client):
        """Test password change fails with wrong current password."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.login.side_effect = TrueNASAPIError("Invalid username or password")
        
        response = logged_in_client.post('/change-password', data={
            'current_password': 'wrongcurrentpass',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        
        assert response.status_code == 200
        assert b'Current password is incorrect' in response.data
    
    @patch('app.utils.TrueNASRestClient')
    def test_password_change_success(self, mock_client_class, logged_in_client):
        """Test successful password change."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        response = logged_in_client.post('/change-password', data={
            'current_password': 'currentpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Password changed successfully' in response.data
        
        mock_client.connect.assert_called_once()
        mock_client.login.assert_called_once_with('testuser', 'currentpass123')
        mock_client.set_password.assert_called_once_with('testuser', 'newpass456')
        mock_client.disconnect.assert_called()
    
    @patch('app.utils.TrueNASRestClient')
    def test_password_change_updates_session(self, mock_client_class, logged_in_client):
        """Test successful password change updates session password."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        with logged_in_client:
            logged_in_client.post('/change-password', data={
                'current_password': 'currentpass123',
                'new_password': 'newpass456',
                'confirm_password': 'newpass456'
            })
            
            from flask import session
            assert session['password'] == 'newpass456'
    
    @patch('app.utils.TrueNASRestClient')
    def test_password_change_api_error(self, mock_client_class, logged_in_client):
        """Test password change handles TrueNAS API errors."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.set_password.side_effect = TrueNASAPIError(
            "Password change failed",
            reason="Account is locked"
        )
        
        response = logged_in_client.post('/change-password', data={
            'current_password': 'currentpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        
        assert response.status_code == 200
        assert b'Account is locked' in response.data
    
    @patch('app.utils.TrueNASRestClient')
    def test_password_change_connection_error(self, mock_client_class, logged_in_client):
        """Test password change handles connection errors."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.side_effect = TrueNASAPIError("Connection refused")
        
        response = logged_in_client.post('/change-password', data={
            'current_password': 'currentpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        
        assert response.status_code == 200
        assert b'Password change failed' in response.data
    
    @patch('app.utils.TrueNASRestClient')
    def test_password_change_generic_exception(self, mock_client_class, logged_in_client):
        """Test password change handles generic exceptions."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.connect.side_effect = Exception("Unexpected error")
        
        response = logged_in_client.post('/change-password', data={
            'current_password': 'currentpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        
        assert response.status_code == 200
        assert b'Error' in response.data
