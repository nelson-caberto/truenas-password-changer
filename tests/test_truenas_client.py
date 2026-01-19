"""Unit tests for TrueNAS API client."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.truenas_client import TrueNASClient, TrueNASAPIError, create_client


class TestTrueNASClient:
    """Test cases for TrueNASClient class."""
    
    def test_init_default_values(self):
        """Test client initialization with default values."""
        client = TrueNASClient("truenas.local")
        
        assert client.host == "truenas.local"
        assert client.port == 443
        assert client.use_ssl is True
        assert client._ws is None
        assert client._auth_token is None
    
    def test_init_custom_values(self):
        """Test client initialization with custom values."""
        client = TrueNASClient("192.168.1.100", port=80, use_ssl=False)
        
        assert client.host == "192.168.1.100"
        assert client.port == 80
        assert client.use_ssl is False
    
    def test_get_ws_url_with_ssl(self):
        """Test WebSocket URL generation with SSL."""
        client = TrueNASClient("truenas.local", port=443, use_ssl=True)
        
        assert client._get_ws_url() == "wss://truenas.local:443/websocket"
    
    def test_get_ws_url_without_ssl(self):
        """Test WebSocket URL generation without SSL."""
        client = TrueNASClient("truenas.local", port=80, use_ssl=False)
        
        assert client._get_ws_url() == "ws://truenas.local:80/websocket"
    
    def test_get_next_id_increments(self):
        """Test message ID increments correctly."""
        client = TrueNASClient("truenas.local")
        
        assert client._get_next_id() == 1
        assert client._get_next_id() == 2
        assert client._get_next_id() == 3
    
    def test_is_connected_when_not_connected(self):
        """Test is_connected returns False when not connected."""
        client = TrueNASClient("truenas.local")
        
        assert client.is_connected is False
    
    def test_is_authenticated_when_not_authenticated(self):
        """Test is_authenticated returns False when not authenticated."""
        client = TrueNASClient("truenas.local")
        
        assert client.is_authenticated is False
    
    @patch('app.truenas_client.websocket.create_connection')
    def test_connect_success(self, mock_create_connection):
        """Test successful connection to TrueNAS."""
        mock_ws = MagicMock()
        mock_ws.recv.return_value = json.dumps({"msg": "connected"})
        mock_create_connection.return_value = mock_ws
        
        client = TrueNASClient("truenas.local")
        client.connect()
        
        assert client._ws is mock_ws
        mock_create_connection.assert_called_once()
    
    @patch('app.truenas_client.websocket.create_connection')
    def test_connect_failure_bad_response(self, mock_create_connection):
        """Test connection failure when WebSocket connection fails."""
        mock_ws = MagicMock()
        mock_ws.connected = False  # Simulate connection failure
        mock_create_connection.return_value = mock_ws
        
        client = TrueNASClient("truenas.local")
        
        with pytest.raises(TrueNASAPIError) as exc_info:
            client.connect()
        
        assert "Failed to establish connection" in str(exc_info.value)
    
    @patch('app.truenas_client.websocket.create_connection')
    def test_connect_websocket_exception(self, mock_create_connection):
        """Test connection failure on WebSocket exception."""
        import websocket
        mock_create_connection.side_effect = websocket.WebSocketException("Connection refused")
        
        client = TrueNASClient("truenas.local")
        
        with pytest.raises(TrueNASAPIError) as exc_info:
            client.connect()
        
        assert "WebSocket connection failed" in str(exc_info.value)
    
    def test_disconnect_clears_state(self):
        """Test disconnect clears connection state."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        client._auth_token = "test_token"
        
        client.disconnect()
        
        assert client._ws is None
        assert client._auth_token is None
    
    def test_call_without_connection(self):
        """Test _call raises error when not connected."""
        client = TrueNASClient("truenas.local")
        
        with pytest.raises(TrueNASAPIError) as exc_info:
            client._call("test.method")
        
        assert "Not connected" in str(exc_info.value)
    
    def test_call_success(self):
        """Test successful API call."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        client._ws.recv.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"success": True}
        })
        
        result = client._call("test.method", ["param1", "param2"])
        
        assert result == {"success": True}
        client._ws.send.assert_called_once()
        
        # Verify the sent message format
        sent_data = json.loads(client._ws.send.call_args[0][0])
        assert sent_data["method"] == "test.method"
        assert sent_data["params"] == ["param1", "param2"]
        assert sent_data["jsonrpc"] == "2.0"
    
    def test_call_with_error_response(self):
        """Test _call handles error responses correctly."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        client._ws.recv.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32001,
                "message": "method call error",
                "data": {
                    "error": 403,
                    "errname": "PermissionError",
                    "reason": "User not authenticated"
                }
            }
        })
        
        with pytest.raises(TrueNASAPIError) as exc_info:
            client._call("test.method")
        
        assert exc_info.value.code == 403
        assert exc_info.value.reason == "User not authenticated"
    
    def test_login_success(self):
        """Test successful login."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        client._ws.recv.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": True
        })
        
        result = client.login("admin", "password123")
        
        assert result is True
        assert client.is_authenticated is True
    
    def test_login_with_otp(self):
        """Test login with OTP token."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        client._ws.recv.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": True
        })
        
        client.login("admin", "password123", otp_token="123456")
        
        sent_data = json.loads(client._ws.send.call_args[0][0])
        assert sent_data["params"] == ["admin", "password123", "123456"]
    
    def test_login_failure(self):
        """Test login failure with invalid credentials."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        client._ws.recv.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": False
        })
        
        with pytest.raises(TrueNASAPIError) as exc_info:
            client.login("admin", "wrongpassword")
        
        assert "Authentication failed" in str(exc_info.value)
    
    def test_set_password_success(self):
        """Test successful password change."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        client._auth_token = "authenticated"
        client._ws.recv.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": True
        })
        
        result = client.set_password("testuser", "newpassword123")
        
        assert result is True
        
        sent_data = json.loads(client._ws.send.call_args[0][0])
        assert sent_data["method"] == "user.set_password"
        assert sent_data["params"] == ["testuser", "newpassword123"]
    
    def test_set_password_without_auth(self):
        """Test set_password fails when not authenticated."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        
        with pytest.raises(TrueNASAPIError) as exc_info:
            client.set_password("testuser", "newpassword")
        
        assert "Not authenticated" in str(exc_info.value)
    
    def test_get_current_user_success(self):
        """Test getting current user information."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        client._auth_token = "authenticated"
        client._ws.recv.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "username": "admin",
                "uid": 0,
                "groups": ["wheel"]
            }
        })
        
        result = client.get_current_user()
        
        assert result["username"] == "admin"
        assert result["uid"] == 0
    
    def test_get_current_user_without_auth(self):
        """Test get_current_user fails when not authenticated."""
        client = TrueNASClient("truenas.local")
        client._ws = MagicMock()
        
        with pytest.raises(TrueNASAPIError) as exc_info:
            client.get_current_user()
        
        assert "Not authenticated" in str(exc_info.value)


class TestTrueNASAPIError:
    """Test cases for TrueNASAPIError exception."""
    
    def test_error_basic(self):
        """Test basic error creation."""
        error = TrueNASAPIError("Test error")
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.code is None
        assert error.reason is None
    
    def test_error_with_code_and_reason(self):
        """Test error with code and reason."""
        error = TrueNASAPIError("Test error", code=403, reason="Permission denied")
        
        assert error.code == 403
        assert error.reason == "Permission denied"


class TestCreateClientFactory:
    """Test cases for create_client factory function."""
    
    def test_create_client_default(self):
        """Test create_client with defaults."""
        client = create_client("truenas.local")
        
        assert isinstance(client, TrueNASClient)
        assert client.host == "truenas.local"
        assert client.port == 443
        assert client.use_ssl is True
    
    def test_create_client_custom(self):
        """Test create_client with custom values."""
        client = create_client("192.168.1.100", port=8080, use_ssl=False)
        
        assert client.host == "192.168.1.100"
        assert client.port == 8080
        assert client.use_ssl is False
