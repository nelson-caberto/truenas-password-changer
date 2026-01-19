"""Integration tests for full application flow."""

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


class TestFullUserFlow:
    """Integration tests for complete user workflows."""
    
    @patch('app.routes.password.get_truenas_client')
    @patch('app.routes.auth.get_truenas_client')
    def test_login_change_password_logout_flow(self, mock_auth_client, mock_password_client, client):
        """Test complete user flow: login -> change password -> logout."""
        mock_client = MagicMock()
        mock_auth_client.return_value = mock_client
        mock_password_client.return_value = mock_client
        
        # Step 1: Login
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'oldpassword123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Change Password' in response.data
        assert b'testuser' in response.data
        
        # Verify login was called
        mock_client.connect.assert_called()
        mock_client.login.assert_called_with('testuser', 'oldpassword123')
        
        # Step 2: Change password
        response = client.post('/change-password', data={
            'current_password': 'oldpassword123',
            'new_password': 'newpassword456',
            'confirm_password': 'newpassword456'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Password changed successfully' in response.data
        
        # Verify set_password was called
        mock_client.set_password.assert_called_with('testuser', 'newpassword456')
        
        # Step 3: Logout
        response = client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'logged out' in response.data
        assert b'TrueNAS Login' in response.data
    
    @patch('app.routes.auth.get_truenas_client')
    def test_failed_login_redirects_back(self, mock_get_client, client):
        """Test that failed login stays on login page with error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.login.side_effect = TrueNASAPIError(
            "Authentication failed",
            reason="Invalid credentials"
        )
        
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        assert b'Invalid credentials' in response.data
        assert b'TrueNAS Login' in response.data
    
    @patch('app.routes.auth.get_truenas_client')
    def test_session_persists_across_requests(self, mock_get_client, client):
        """Test that session data persists across multiple requests."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Login
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Make multiple requests to password change page
        for _ in range(3):
            response = client.get('/change-password')
            assert response.status_code == 200
            assert b'testuser' in response.data
    
    def test_unauthenticated_access_redirects_to_login(self, client):
        """Test that unauthenticated users are redirected to login."""
        response = client.get('/change-password')
        
        assert response.status_code == 302
        assert '/login' in response.location
        
        # Follow redirect
        response = client.get('/change-password', follow_redirects=True)
        assert b'Please log in' in response.data
    
    @patch('app.routes.password.get_truenas_client')
    @patch('app.routes.auth.get_truenas_client')
    def test_password_change_with_connection_failure(self, mock_auth_client, mock_password_client, client):
        """Test password change gracefully handles connection failures."""
        mock_client = MagicMock()
        mock_auth_client.return_value = mock_client
        
        mock_client2 = MagicMock()
        mock_password_client.return_value = mock_client2
        
        # First call succeeds (login)
        # Then subsequent calls fail (password change)
        mock_client2.connect.side_effect = TrueNASAPIError("Connection refused")
        
        # Login first
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Try to change password - should fail gracefully
        response = client.post('/change-password', data={
            'current_password': 'testpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        })
        
        assert response.status_code == 200
        # Should show error but not crash
        assert b'Change Password' in response.data


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_empty_password_fields(self, client):
        """Test submitting empty password fields."""
        # Set up session
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.post('/change-password', data={
            'current_password': '',
            'new_password': '',
            'confirm_password': ''
        })
        
        assert response.status_code == 200
        assert b'required' in response.data
    
    def test_password_mismatch(self, client):
        """Test password confirmation mismatch."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.post('/change-password', data={
            'current_password': 'currentpass',
            'new_password': 'newpass1',
            'confirm_password': 'newpass2'
        })
        
        assert response.status_code == 200
        assert b'Passwords must match' in response.data
    
    @patch('app.routes.password.get_truenas_client')
    def test_wrong_current_password(self, mock_get_client, client):
        """Test entering wrong current password."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.login.side_effect = TrueNASAPIError("Invalid username or password")
        
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.post('/change-password', data={
            'current_password': 'wrongpass',
            'new_password': 'newpass',
            'confirm_password': 'newpass'
        })
        
        assert response.status_code == 200
        assert b'Current password is incorrect' in response.data
    
    def test_login_with_special_characters(self, client):
        """Test login with special characters in username."""
        response = client.post('/login', data={
            'username': 'test<script>user',
            'password': 'pass<script>word'
        })
        
        # Should not execute script, form should work normally
        assert response.status_code == 200
        # The special characters should be escaped in the response
        assert b'<script>' not in response.data or b'&lt;script&gt;' in response.data
    
    def test_index_redirect_not_logged_in(self, client):
        """Test index redirects to login when not authenticated."""
        response = client.get('/')
        
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_index_redirect_logged_in(self, client):
        """Test index redirects to password change when authenticated."""
        with client.session_transaction() as sess:
            sess['username'] = 'testuser'
        
        response = client.get('/')
        
        assert response.status_code == 302
        assert '/change-password' in response.location
