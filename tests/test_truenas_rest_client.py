"""Tests for TrueNAS REST API client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.truenas_rest_client import TrueNASRestClient, TrueNASAPIError


class TestTrueNASRestClient:
    """Test TrueNAS REST API client functionality."""
    
    def test_init(self):
        """Test client initialization."""
        client = TrueNASRestClient(host="localhost", port=443, use_ssl=True)
        assert client.host == "localhost"
        assert client.port == 443
        assert client.use_ssl is True
        assert client._access_token is None
    
    def test_get_api_url(self):
        """Test API URL building."""
        client = TrueNASRestClient(host="nas", port=8080, use_ssl=False)
        url = client._get_api_url("/user")
        assert url == "http://nas:8080/api/v2.0/user"
        
        client_ssl = TrueNASRestClient(host="nas", port=443, use_ssl=True)
        url_ssl = client_ssl._get_api_url("/auth/generate_token")
        assert url_ssl == "https://nas:443/api/v2.0/auth/generate_token"
    
    @patch('app.truenas_rest_client.requests.Session.get')
    def test_connect_success(self, mock_get):
        """Test successful connection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        client = TrueNASRestClient(host="localhost")
        client.connect()  # Should not raise
    
    @patch('app.truenas_rest_client.requests.Session.get')
    def test_connect_failure(self, mock_get):
        """Test connection failure."""
        mock_get.side_effect = Exception("Connection refused")
        
        client = TrueNASRestClient(host="localhost")
        with pytest.raises(TrueNASAPIError):
            client.connect()
    
    @patch('app.truenas_rest_client.requests.Session.post')
    def test_login_success(self, mock_post):
        """Test successful login."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token_12345"}
        mock_post.return_value = mock_response
        
        client = TrueNASRestClient(host="localhost")
        result = client.login("admin", "password")
        
        assert result is True
        assert client._access_token == "test_token_12345"
        assert "Authorization" in client._session.headers
        assert client._session.headers["Authorization"] == "Bearer test_token_12345"
    
    @patch('app.truenas_rest_client.requests.Session.post')
    def test_login_invalid_credentials(self, mock_post):
        """Test login with invalid credentials."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        client = TrueNASRestClient(host="localhost")
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.login("admin", "wrongpassword")
        
        assert "Invalid username or password" in str(excinfo.value)
    
    @patch('app.truenas_rest_client.requests.Session.post')
    def test_login_server_error(self, mock_post):
        """Test login with server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        client = TrueNASRestClient(host="localhost")
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.login("admin", "password")
        
        assert "Authentication failed" in str(excinfo.value)
    
    @patch('app.truenas_rest_client.requests.Session.post')
    def test_login_network_error(self, mock_post):
        """Test login with network error."""
        mock_post.side_effect = Exception("Connection timeout")
        
        client = TrueNASRestClient(host="localhost")
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.login("admin", "password")
        
        assert "request failed" in str(excinfo.value)
    
    @patch('app.truenas_rest_client.requests.Session.get')
    @patch('app.truenas_rest_client.requests.Session.put')
    def test_set_password_success(self, mock_put, mock_get):
        """Test successful password change."""
        # Mock user list response
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [
            {"id": 1, "username": "admin"},
            {"id": 2, "username": "testuser"}
        ]
        mock_get.return_value = mock_get_response
        
        # Mock password update response
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put.return_value = mock_put_response
        
        client = TrueNASRestClient(host="localhost")
        client._access_token = "test_token"
        
        result = client.set_password("testuser", "newpassword")
        assert result is True
    
    @patch('app.truenas_rest_client.requests.Session.get')
    def test_set_password_not_authenticated(self, mock_get):
        """Test password change without authentication."""
        client = TrueNASRestClient(host="localhost")
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.set_password("testuser", "newpassword")
        
        assert "Not authenticated" in str(excinfo.value)
    
    @patch('app.truenas_rest_client.requests.Session.get')
    def test_set_password_user_not_found(self, mock_get):
        """Test password change for non-existent user."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "username": "admin"}
        ]
        mock_get.return_value = mock_response
        
        client = TrueNASRestClient(host="localhost")
        client._access_token = "test_token"
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.set_password("nonexistent", "newpassword")
        
        assert "not found" in str(excinfo.value)
    
    @patch('app.truenas_rest_client.requests.Session.get')
    @patch('app.truenas_rest_client.requests.Session.put')
    def test_set_password_update_failed(self, mock_put, mock_get):
        """Test password change update failure."""
        # Mock user list response
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [
            {"id": 2, "username": "testuser"}
        ]
        mock_get.return_value = mock_get_response
        
        # Mock failed update response
        mock_put_response = Mock()
        mock_put_response.status_code = 400
        mock_put_response.text = "Invalid password"
        mock_put.return_value = mock_put_response
        
        client = TrueNASRestClient(host="localhost")
        client._access_token = "test_token"
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.set_password("testuser", "")
        
        assert "Password change failed" in str(excinfo.value)
    
    def test_disconnect(self):
        """Test disconnection."""
        client = TrueNASRestClient(host="localhost")
        client._access_token = "test_token"
        
        client.disconnect()
        
        assert client._access_token is None
    
    def test_error_exception(self):
        """Test TrueNASAPIError exception."""
        error = TrueNASAPIError("Test error", code=123, reason="test")
        
        assert error.message == "Test error"
        assert error.code == 123
        assert error.reason == "test"
        assert str(error) == "Test error"


class TestRestClientIntegration:
    """Integration tests for REST client (mocked)."""
    
    @patch('app.truenas_rest_client.requests.Session.get')
    @patch('app.truenas_rest_client.requests.Session.post')
    @patch('app.truenas_rest_client.requests.Session.put')
    def test_full_auth_and_password_change(self, mock_put, mock_post, mock_get):
        """Test full authentication and password change flow."""
        # Setup mocks
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"access_token": "token123"}
        mock_post.return_value = mock_post_response
        
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [
            {"id": 1, "username": "testuser"}
        ]
        mock_get.return_value = mock_get_response
        
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put.return_value = mock_put_response
        
        # Perform operations
        client = TrueNASRestClient(host="nas.local", port=443, use_ssl=True)
        client.connect()
        
        assert client.login("testuser", "oldpass") is True
        assert client._access_token == "token123"
        
        assert client.set_password("testuser", "newpass") is True
        
        client.disconnect()
        assert client._access_token is None
