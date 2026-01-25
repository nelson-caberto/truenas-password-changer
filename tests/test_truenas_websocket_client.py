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
        # TrueNAS returns connected message after connect handshake
        mock_ws.recv.return_value = '{"msg": "connected", "session": "test-session"}'
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost")
        client.connect()
        
        mock_create_conn.assert_called_once()
        assert client._ws is not None
        assert client._session_id == "test-session"
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_connect_with_api_key(self, mock_create_conn):
        """Test connection with API key authentication."""
        mock_ws = Mock()
        # First call returns connected, second returns auth result
        mock_ws.recv.side_effect = [
            '{"msg": "connected", "session": "test-session"}',
            '{"id": "1", "msg": "result", "result": true}'
        ]
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client.connect()
        
        # Should have sent connect and auth requests
        assert mock_ws.send.call_count == 2
    
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
        # TrueNAS middleware returns msg: result
        mock_ws.recv.return_value = '{"id": "1", "msg": "result", "result": {"key": "value"}}'
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
        # TrueNAS middleware error format
        mock_ws.recv.return_value = '{"id": "1", "msg": "error", "error": {"error": -1, "reason": "Test error"}}'
        mock_create_conn.return_value = mock_ws
        
        client = TrueNASWebSocketClient(host="localhost")
        client._ws = mock_ws
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client._call("test.method")
        assert "Test error" in str(excinfo.value)
    
    @patch('app.truenas_websocket_client.sha512_crypt.verify')
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_login_success(self, mock_create_conn, mock_verify):
        """Test successful login using hash verification."""
        mock_ws = Mock()
        # Return user query response in middleware format
        mock_ws.recv.return_value = '{"id": "1", "msg": "result", "result": [{"username": "admin", "unixhash": "$6$hash", "twofactor_auth_configured": false, "smb": false}]}'
        mock_create_conn.return_value = mock_ws
        
        # Mock passlib verify to return True
        mock_verify.return_value = True
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client._ws = mock_ws
        
        result = client.login("admin", "password")
        assert result is True
    
    @patch('app.truenas_websocket_client.sha512_crypt.verify')
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_login_invalid_credentials(self, mock_create_conn, mock_verify):
        """Test login with invalid credentials."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"id": "1", "msg": "result", "result": [{"username": "admin", "unixhash": "$6$hash", "twofactor_auth_configured": false, "smb": false}]}'
        mock_create_conn.return_value = mock_ws
        
        # Mock passlib verify to return False
        mock_verify.return_value = False
        
        client = TrueNASWebSocketClient(host="localhost", api_key="test_key")
        client._ws = mock_ws
        
        with pytest.raises(TrueNASAPIError) as excinfo:
            client.login("admin", "wrongpassword")
        assert "Invalid username or password" in str(excinfo.value)
    
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_login_otp_required(self, mock_create_conn):
        """Test login when OTP is required."""
        mock_ws = Mock()
        mock_ws.recv.return_value = '{"id": "1", "msg": "result", "result": [{"username": "admin", "unixhash": "$6$hash", "twofactor_auth_configured": true, "smb": false}]}'
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
        mock_ws.recv.return_value = '{"id": "1", "msg": "result", "result": []}'
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
            '{"id": "1", "msg": "result", "result": [{"id": 1, "username": "testuser"}]}',
            '{"id": "2", "msg": "result", "result": {"id": 1}}'
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
        mock_ws.recv.return_value = '{"id": "1", "msg": "result", "result": []}'
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
    
    @patch('app.truenas_websocket_client.sha512_crypt.verify')
    @patch('app.truenas_websocket_client.websocket.create_connection')
    def test_full_auth_and_password_change(self, mock_create_conn, mock_verify):
        """Test full authentication and password change flow."""
        mock_ws = Mock()
        
        # Mock passlib verify to return True
        mock_verify.return_value = True
        
        # Setup responses for: connect, auth, user query (login), user query (set_password), user update
        mock_ws.recv.side_effect = [
            '{"msg": "connected", "session": "test-session"}',  # connect handshake
            '{"id": "1", "msg": "result", "result": true}',  # auth.login_with_api_key
            '{"id": "2", "msg": "result", "result": [{"id": 1, "username": "testuser", "unixhash": "$6$hash", "twofactor_auth_configured": false, "smb": false}]}',  # user.query for login
            '{"id": "3", "msg": "result", "result": [{"id": 1, "username": "testuser"}]}',  # user.query for set_password
            '{"id": "4", "msg": "result", "result": {"id": 1}}'  # user.update
        ]
        mock_create_conn.return_value = mock_ws
        
        # Perform operations
        client = TrueNASWebSocketClient(host="nas.local", port=443, use_ssl=True, api_key="test_api_key")
        client.connect()
        
        assert client.login("testuser", "oldpass") is True
        assert client.set_password("testuser", "newpass") is True
        
        client.disconnect()
        assert client._ws is None
