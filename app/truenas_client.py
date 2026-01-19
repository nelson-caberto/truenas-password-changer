"""TrueNAS API client for WebSocket JSON-RPC communication."""

import json
import ssl
from typing import Any, Optional

import websocket


class TrueNASAPIError(Exception):
    """Exception raised when TrueNAS API returns an error."""
    
    def __init__(self, message: str, code: int = None, reason: str = None):
        self.message = message
        self.code = code
        self.reason = reason
        super().__init__(self.message)


class TrueNASClient:
    """Client for communicating with TrueNAS via WebSocket JSON-RPC API."""
    
    def __init__(self, host: str, port: int = 443, use_ssl: bool = True):
        """Initialize the TrueNAS client.
        
        Args:
            host: TrueNAS server hostname or IP address.
            port: WebSocket port (default 443 for SSL, 80 for non-SSL).
            use_ssl: Whether to use SSL/TLS for the connection.
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self._ws: Optional[websocket.WebSocket] = None
        self._message_id = 0
        self._auth_token: Optional[str] = None
    
    def _get_ws_url(self) -> str:
        """Build the WebSocket URL for TrueNAS API.
        
        Returns:
            WebSocket URL string.
        """
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}:{self.port}/websocket"
    
    def _get_next_id(self) -> int:
        """Get the next message ID for JSON-RPC requests.
        
        Returns:
            Incremented message ID.
        """
        self._message_id += 1
        return self._message_id
    
    def connect(self) -> None:
        """Establish WebSocket connection to TrueNAS.
        
        Raises:
            TrueNASAPIError: If connection fails.
        """
        try:
            ssl_opts = None
            if self.use_ssl:
                # Allow self-signed certificates (common in TrueNAS setups)
                ssl_opts = {"cert_reqs": ssl.CERT_NONE}
            
            self._ws = websocket.create_connection(
                self._get_ws_url(),
                sslopt=ssl_opts,
                timeout=30
            )
            
            # TrueNAS sends a connect message first
            response = self._ws.recv()
            data = json.loads(response)
            
            if data.get("msg") != "connected":
                raise TrueNASAPIError("Failed to establish connection with TrueNAS")
                
        except websocket.WebSocketException as e:
            raise TrueNASAPIError(f"WebSocket connection failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise TrueNASAPIError(f"Invalid response from TrueNAS: {str(e)}")
    
    def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._auth_token = None
    
    def _call(self, method: str, params: list = None) -> Any:
        """Make a JSON-RPC call to TrueNAS.
        
        Args:
            method: The API method to call.
            params: Optional list of parameters.
            
        Returns:
            The result from the API call.
            
        Raises:
            TrueNASAPIError: If the call fails or returns an error.
        """
        if not self._ws:
            raise TrueNASAPIError("Not connected to TrueNAS")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method,
        }
        
        if params is not None:
            request["params"] = params
        
        try:
            self._ws.send(json.dumps(request))
            response = self._ws.recv()
            data = json.loads(response)
            
            if "error" in data:
                error = data["error"]
                error_data = error.get("data", {})
                raise TrueNASAPIError(
                    message=error.get("message", "Unknown error"),
                    code=error_data.get("error"),
                    reason=error_data.get("reason", error_data.get("errname"))
                )
            
            return data.get("result")
            
        except websocket.WebSocketException as e:
            raise TrueNASAPIError(f"WebSocket error: {str(e)}")
        except json.JSONDecodeError as e:
            raise TrueNASAPIError(f"Invalid JSON response: {str(e)}")
    
    def login(self, username: str, password: str, otp_token: str = None) -> bool:
        """Authenticate with TrueNAS.
        
        Args:
            username: TrueNAS username.
            password: TrueNAS password.
            otp_token: Optional OTP token for 2FA.
            
        Returns:
            True if authentication succeeded.
            
        Raises:
            TrueNASAPIError: If authentication fails.
        """
        params = [username, password]
        if otp_token:
            params.append(otp_token)
        
        result = self._call("auth.login", params)
        
        if result:
            self._auth_token = result if isinstance(result, str) else username
            return True
        
        raise TrueNASAPIError("Authentication failed", reason="Invalid credentials")
    
    def set_password(self, username: str, new_password: str) -> bool:
        """Change a user's password.
        
        Args:
            username: Username whose password to change.
            new_password: The new password to set.
            
        Returns:
            True if password change succeeded.
            
        Raises:
            TrueNASAPIError: If password change fails.
        """
        if not self._auth_token:
            raise TrueNASAPIError("Not authenticated", reason="Must login first")
        
        result = self._call("user.set_password", [username, new_password])
        return result is True or result is None
    
    def get_current_user(self) -> dict:
        """Get information about the currently authenticated user.
        
        Returns:
            Dictionary with user information.
            
        Raises:
            TrueNASAPIError: If the call fails.
        """
        if not self._auth_token:
            raise TrueNASAPIError("Not authenticated", reason="Must login first")
        
        return self._call("auth.me")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to TrueNAS.
        
        Returns:
            True if WebSocket connection is active.
        """
        return self._ws is not None and self._ws.connected
    
    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated with TrueNAS.
        
        Returns:
            True if currently authenticated.
        """
        return self._auth_token is not None


def create_client(host: str, port: int = 443, use_ssl: bool = True) -> TrueNASClient:
    """Factory function to create a TrueNAS client.
    
    Args:
        host: TrueNAS server hostname or IP address.
        port: WebSocket port.
        use_ssl: Whether to use SSL/TLS.
        
    Returns:
        Configured TrueNASClient instance.
    """
    return TrueNASClient(host, port, use_ssl)
