"""Tests for TrueNAS WebSocket JSON-RPC 2.0 client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.truenas_websocket_client import TrueNASWebSocketClient, TrueNASAPIError


class TestTrueNASWebSocketClient:
    """Test TrueNAS WebSocket client functionality."""
    
    def test_init(self):
        """Test client initialization."""
        client = TrueNASWebSocketClient(host="localhost", port=443, use_ssl=True)
        assert client.host == "localhost"
        assert client.port == 443
        assert client.use_ssl is True
        assert client._api_key is None
    
    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        assert client._api_key == "test_key"
    
    def test_get_ws_url_ssl(self):
        """Test WebSocket URL building with SSL."""
        client = TrueNASWebSocketClient(host="nas", port=443, use_ssl=True)
        url = client._get_ws_url()
        assert url == "wss://nas:443/websocket"
    
    def test_get_ws_url_no_ssl(self):
        """Test WebSocket URL building without SSL."""
        client = TrueNASWebSocketClient(host="nas", port=80, use_ssl=False)
        url = client._get_ws_url()
        assert url == "ws://nas:80/websocket"
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_connect_success(self, mock_create_conn):
        """Test successful connection."""
        mock_ws = Mock()
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost")
        client.connect()
        
        mock_create_conn.assert_called_once()
        assert client._ws is not None
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_connect_with_api_key(self, mock_create_conn):
        """Test connection with API key authentication."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": true}'
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client.connect()
        
        # Should have sent auth request
        mock_ws.send.assert_called()
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_connect_failure(self, mock_create_conn):
        """Test connection failure."""
        mock_create_conn.side_effect = Exception("Connection refused")
        
        client = TrueNASWebSocketClient(host="localhost")
        with pytest.raises(TrueNASAPIError):
            client.connect()
    
    def test_call_not_connected(self):
        """Test API call when not connected."""
        client = TrueNASWebSocketClient(host="localhost")
        with pytest.raises(TrueNASAPIError) as excinfo:
            client._call("test.method")
        assert "Not connected" in str(excinfo.value)
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_call_success(self, mock_create_conn):
        """Test successful API call."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": {"key": "value"}}'
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost")
        client._ws = mock_ws
        
        result = client._call("test.method", ["param1"])
        
        assert result == {"key": "value"}
        mock_ws.send.assert_called()
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_call_error_response(self, mock_create_conn):
        """Test API call with error response."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "error": {"code": -1, "message": "Test error"}}'
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost")
        client._ws = mock_ws
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client._call("test.method")
        assert "Test error" in str(excinfo.value)
    
    @patch('app.truenas_websocket_client.crypt.crypt')
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_login_success(self, mock_create_conn, mock_crypt):
        """Test successful login using hash verification."""
        mock_ws = Mock()
        # Return user query response
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": [{"username": "admin", "unixhash": "$6$hash", "twofactor_auth_configured": false, "smb": false}]}'
        mock_create_conn.return_value = mock_ws
        
        # Mock crypt to return matching hash
        mock_crypt.return_value = "$6$hash"
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client._ws = mock_ws
        
        result = client.login("admin", "password")
        assert result is True
    
    @patch('app.truenas_websocket_client.crypt.crypt')
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_login_invalid_credentials(self, mock_create_conn, mock_crypt):
        """Test login with invalid credentials."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": [{"username": "admin", "unixhash": "$6$hash", "twofactor_auth_configured": false, "smb": false}]}'
        mock_create_conn.return_value = mock_ws
        
        # Mock crypt to return non-matching hash
        mock_crypt.return_value = "$6$wronghash"
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client._ws = mock_ws
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.login("admin", "wrongpassword")
        assert "Invalid username or password" in str(excinfo.value)
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_login_otp_required(self, mock_create_conn):
        """Test login when OTP is required."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": [{"username": "admin", "unixhash": "$6$hash", "twofactor_auth_configured": true, "smb": false}]}'
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client._ws = mock_ws
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.login("admin", "password")
        assert "OTP" in str(excinfo.value)
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_login_user_not_found(self, mock_create_conn):
        """Test login with non-existent user."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": []}'
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client._ws = mock_ws
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.login("nonexistent", "password")
        assert "Invalid username or password" in str(excinfo.value)
    
    def test_login_requires_api_key(self):
        """Test login requires API key."""
        client = TrueNASWebSocketClient(host="localhost")
        client._ws = Mock()
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.login("admin", "password")
        assert "API key required" in str(excinfo.value)
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_set_password_success(self, mock_create_conn):
        """Test successful password change."""
        mock_ws = Mock()
        # First call: user query, second call: user update
        mock_ws.recv.side_effect = [
            '{"jsonrpc": "2.0", "id": "1", "result": [{"id": 1, "username": "testuser"}]}',
            '{"jsonrpc": "2.0", "id": "2", "result": {"id": 1}}'
        ]
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client._ws = mock_ws
        
        result = client.set_password("testuser", "newpassword")
        assert result is True
    
    def test_set_password_not_authenticated(self):
        """Test password change without API key."""
        client = TrueNASWebSocketClient(host="localhost")
        client._ws = Mock()
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.set_password("testuser", "newpassword")
        assert "API key required" in str(excinfo.value)
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_set_password_user_not_found(self, mock_create_conn):
        """Test password change for non-existent user."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": []}'
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client._ws = mock_ws
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.set_password("nonexistent", "newpassword")
        assert "not found" in str(excinfo.value)
    
    def test_disconnect(self):
        """Test disconnection."""
        client = TrueNASWebSocketClient(host="localhost")
        mock_ws = Mock()
        client._ws = mock_ws
        
        client.disconnect()
        
        mock_ws.close.assert_called_once()
        assert client._ws is None
    
    def test_disconnect_not_connected(self):
        """Test disconnection when not connected."""
        client = TrueNASWebSocketClient(host="localhost")
        # Should not raise
        client.disconnect()
    
    def test_error_exception(self):
        """Test TrueNASAPIError exception."""
        error = TrueNASAPIError("Test error", code=123, reason="test")
        
        assert error.message == "Test error"
        assert error.code == 123
        assert error.reason == "test"
        assert str(error) == "Test error"


class TestWebSocketClientIntegration:
    """Integration tests for WebSocket client (mocked)."""
    
    @patch('app.truenas_websocket_client.crypt.crypt')
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_full_auth_and_password_change(self, mock_create_conn, mock_crypt):
        """Test full authentication and password change flow."""
        mock_ws = Mock()
        
        # Mock crypt to return matching hash for login
        mock_crypt.return_value = "$6$hash"
        
        # Setup responses for: auth, user query (login), user query (set_password), user update
        mock_ws.recv.side_effect = [
            '{"jsonrpc": "2.0", "id": "1", "result": true}',  # auth.login_with_api_key
            '{"jsonrpc": "2.0", "id": "2", "result": [{"id": 1, "username": "testuser", "unixhash": "$6$hash", "twofactor_auth_configured": false, "smb": false}]}',  # user.query for login
            '{"jsonrpc": "2.0", "id": "3", "result": [{"id": 1, "username": "testuser"}]}',  # user.query for set_password
            '{"jsonrpc": "2.0", "id": "4", "result": {"id": 1}}'  # user.update
        ]
        mock_create_conn.return_value = mock_ws
        
        # Perform operations
        client = TrueNASWebSocketClient(host="nas.local", port=443, use_ssl=True, api_key="test_api_key")
        client.connect()
        
        assert client.login("testuser", "oldpass") is True
        assert client.set_password("testuser", "newpass") is True
        
        client.disconnect()
        assert client._ws is None
