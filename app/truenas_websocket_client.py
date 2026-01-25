"""TrueNAS API client using WebSocket.

Migration from deprecated REST API to WebSocket per TrueNAS 26.04 requirements.
TrueNAS uses a custom middleware protocol over WebSocket (DDP-like), not standard JSON-RPC 2.0.
Documentation: https://api.truenas.com/v25.10/jsonrpc.html
"""

import json
import ssl
import threading
from typing import Any, Optional
import websocket

# Use passlib for password hash verification (crypt deprecated in Python 3.13)
from passlib.hash import sha512_crypt, sha256_crypt, md5_crypt


class TrueNASAPIError(Exception):
    """Exception raised when TrueNAS API returns an error."""
    
    def __init__(self, message: str, code: int = None, reason: str = None):
        self.message = message
        self.code = code
        self.reason = reason
        super().__init__(self.message)


class TrueNASWebSocketClient:
    """Client for TrueNAS using WebSocket API.
    
    This client uses the TrueNAS WebSocket API, which replaces the deprecated
    REST API (removed in TrueNAS 26.04). TrueNAS uses a custom middleware
    protocol (DDP-like) with msg types: 'connect', 'method', 'result', 'error'.
    
    Authentication uses a dual approach to support ALL users (not just admins):
    1. SMB authentication (for users with SMB enabled)
    2. Unix password hash verification (fallback for all users)
    """
    
    def __init__(self, host: str, port: int = 443, use_ssl: bool = True, api_key: Optional[str] = None):
        """Initialize the TrueNAS WebSocket client.
        
        Args:
            host: TrueNAS server hostname or IP address.
            port: WebSocket API port (default 443 for WSS, 80 for WS).
            use_ssl: Whether to use SSL/TLS for the connection.
            api_key: API key for authentication (required for user operations).
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self._api_key = api_key
        self._ws: Optional[websocket.WebSocket] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._session_id: Optional[str] = None
    
    def _get_ws_url(self) -> str:
        """Build the WebSocket URL.
        
        Returns:
            WebSocket URL string.
        """
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}:{self.port}/websocket"
    
    def _call(self, method: str, params: Any = None) -> Any:
        """Make a method call using TrueNAS middleware protocol.
        
        TrueNAS uses a custom DDP-like protocol:
        - Request: {"id": "N", "msg": "method", "method": "...", "params": [...]}
        - Response: {"id": "N", "msg": "result", "result": ...}
        - Error: {"id": "N", "msg": "error", "error": {...}}
        
        Args:
            method: Method name (e.g., 'user.query')
            params: Method parameters (list)
            
        Returns:
            Result from the API call.
            
        Raises:
            TrueNASAPIError: If the call fails.
        """
        if not self._ws:
            raise TrueNASAPIError("Not connected. Call connect() first.")
        
        with self._lock:
            self._request_id += 1
            request_id = str(self._request_id)
        
        # Build TrueNAS middleware request
        payload = {
            "id": request_id,
            "msg": "method",
            "method": method,
            "params": params or []
        }
        
        try:
            self._ws.send(json.dumps(payload))
            
            # Read response (may need to skip notifications)
            while True:
                response_text = self._ws.recv()
                if not response_text:
                    raise TrueNASAPIError("Empty response from server")
                    
                response = json.loads(response_text)
                
                # Skip notifications and other messages without matching id
                if response.get("id") == request_id:
                    break
                # Also accept messages with msg type we care about
                if response.get("msg") in ("result", "error") and response.get("id") == request_id:
                    break
            
            # Check for error response
            if response.get("msg") == "error" or "error" in response:
                error = response.get("error", {})
                if isinstance(error, dict):
                    raise TrueNASAPIError(
                        error.get("reason", error.get("message", "Unknown error")),
                        code=error.get("error"),
                        reason=error.get("reason")
                    )
                else:
                    raise TrueNASAPIError(str(error))
            
            return response.get("result")
            
        except websocket.WebSocketException as e:
            raise TrueNASAPIError(f"WebSocket error: {str(e)}")
        except json.JSONDecodeError as e:
            raise TrueNASAPIError(f"Invalid JSON response: {str(e)}")
        except TrueNASAPIError:
            raise
        except Exception as e:
            raise TrueNASAPIError(f"API call failed: {str(e)}")
    
    def connect(self) -> None:
        """Establish WebSocket connection to TrueNAS API.
        
        TrueNAS requires a handshake before API calls:
        1. Connect to WebSocket endpoint
        2. Send connect message with version
        3. Authenticate with API key
        
        Raises:
            TrueNASAPIError: If connection fails.
        """
        try:
            sslopt = {"cert_reqs": ssl.CERT_NONE} if self.use_ssl else None
            
            self._ws = websocket.create_connection(
                self._get_ws_url(),
                sslopt=sslopt,
                timeout=30
            )
            
            # TrueNAS requires a connect handshake first
            connect_msg = {
                "msg": "connect",
                "version": "1",
                "support": ["1"]
            }
            self._ws.send(json.dumps(connect_msg))
            
            # Wait for connected response
            response_text = self._ws.recv()
            response = json.loads(response_text)
            
            if response.get("msg") != "connected":
                raise TrueNASAPIError(f"Connect handshake failed: {response}")
            
            self._session_id = response.get("session")
            
            # Authenticate with API key if provided
            if self._api_key:
                result = self._call("auth.login_with_api_key", [self._api_key])
                if not result:
                    raise TrueNASAPIError("API key authentication failed")
                
        except websocket.WebSocketException as e:
            raise TrueNASAPIError(f"Failed to connect: {str(e)}")
        except json.JSONDecodeError as e:
            raise TrueNASAPIError(f"Invalid response during connect: {str(e)}")
        except TrueNASAPIError:
            raise
        except Exception as e:
            raise TrueNASAPIError(f"Connection failed: {str(e)}")
    
    def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        self._ws = None
    
    def login(self, username: str, password: str, otp_token: str = None) -> bool:
        """Authenticate user by verifying password.
        
        Uses dual authentication to support ALL users (not just admins):
        1. Try SMB authentication (for SMB-enabled users)
        2. Fallback to hash verification using API key
        
        Args:
            username: TrueNAS username.
            password: TrueNAS password.
            otp_token: Optional OTP token for 2FA.
            
        Returns:
            True if authentication succeeded.
            
        Raises:
            TrueNASAPIError: If authentication fails.
        """
        if not self._api_key:
            raise TrueNASAPIError("API key required for password verification")
        
        try:
            # Query user data using WebSocket JSON-RPC
            users = self._call("user.query", [[["username", "=", username]]])
            
            if not users:
                raise TrueNASAPIError("Invalid username or password", reason="Invalid username or password")
            
            user = users[0]
            
            # Check if 2FA is required
            if user.get("twofactor_auth_configured") and not otp_token:
                raise TrueNASAPIError("OTP token required", reason="Two-factor authentication required")
            
            # Try SMB authentication first if user has SMB enabled
            if user.get("smb"):
                try:
                    from smb.SMBConnection import SMBConnection
                    conn = SMBConnection(username, password, 'client', self.host, use_ntlm_v2=True)
                    if conn.connect(self.host, 445, timeout=5):
                        conn.close()
                        return True
                except Exception:
                    # SMB auth failed, fall through to hash verification
                    pass
            
            # Fall back to hash verification
            stored_hash = user.get("unixhash")
            
            if not stored_hash:
                raise TrueNASAPIError("Invalid username or password", reason="Invalid username or password")
            
            # Verify password against stored hash using passlib
            # TrueNAS uses SHA-512 ($6$), SHA-256 ($5$), or MD5 ($1$) hashes
            if stored_hash.startswith("$6$"):
                is_valid = sha512_crypt.verify(password, stored_hash)
            elif stored_hash.startswith("$5$"):
                is_valid = sha256_crypt.verify(password, stored_hash)
            elif stored_hash.startswith("$1$"):
                is_valid = md5_crypt.verify(password, stored_hash)
            else:
                raise TrueNASAPIError("Unsupported hash format", reason="Unsupported password hash format")
            
            if is_valid:
                return True
            else:
                raise TrueNASAPIError("Invalid username or password", reason="Invalid username or password")
                
        except TrueNASAPIError:
            raise
        except Exception as e:
            raise TrueNASAPIError(f"Authentication failed: {str(e)}")
    
    def set_password(self, username: str, new_password: str) -> bool:
        """Change a user's password.
        
        Args:
            username: Username to change password for.
            new_password: New password.
            
        Returns:
            True if password change succeeded.
            
        Raises:
            TrueNASAPIError: If password change fails.
        """
        if not self._api_key:
            raise TrueNASAPIError("Not authenticated. API key required.")
        
        try:
            # Query user to get user ID
            users = self._call("user.query", [[["username", "=", username]]])
            
            if not users:
                raise TrueNASAPIError(f"User '{username}' not found")
            
            user_id = users[0].get("id")
            
            # Update password using user.update method
            self._call("user.update", [user_id, {"password": new_password}])
            
            return True
                
        except TrueNASAPIError:
            raise
        except Exception as e:
            raise TrueNASAPIError(f"Password change request failed: {str(e)}")
