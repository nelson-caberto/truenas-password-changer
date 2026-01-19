"""TrueNAS API client using REST API (alternative to WebSocket)."""

import json
import ssl
from typing import Any, Optional
import requests
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for self-signed certs
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class TrueNASAPIError(Exception):
    """Exception raised when TrueNAS API returns an error."""
    
    def __init__(self, message: str, code: int = None, reason: str = None):
        self.message = message
        self.code = code
        self.reason = reason
        super().__init__(self.message)


class TrueNASRestClient:
    """Alternative client for TrueNAS using REST API instead of WebSocket.
    
    This client uses the TrueNAS REST API (/api/v2.0/) instead of the WebSocket
    JSON-RPC API. This avoids WebSocket compatibility issues while maintaining
    full functionality.
    """
    
    def __init__(self, host: str, port: int = 443, use_ssl: bool = True, api_key: Optional[str] = None):
        """Initialize the TrueNAS REST client.
        
        Args:
            host: TrueNAS server hostname or IP address.
            port: REST API port (default 443 for SSL, 80 for non-SSL).
            use_ssl: Whether to use SSL/TLS for the connection.
            api_key: Optional API key for authentication. If provided, token-based auth is skipped.
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self._session = requests.Session()
        self._session.verify = False  # Allow self-signed certificates
        self._access_token: Optional[str] = None
        self._api_key = api_key
        
        # If API key is provided, use it immediately
        if self._api_key:
            self._session.headers.update({
                "Authorization": f"Bearer {self._api_key}"
            })
    
    def _get_api_url(self, endpoint: str = "") -> str:
        """Build the REST API URL.
        
        Args:
            endpoint: API endpoint path (e.g., '/auth/generate_token')
            
        Returns:
            Full URL string.
        """
        protocol = "https" if self.use_ssl else "http"
        base = f"{protocol}://{self.host}:{self.port}/api/v2.0"
        return base + endpoint
    
    def connect(self) -> None:
        """Verify connection to TrueNAS API.
        
        This is a no-op for REST client but kept for API compatibility.
        The actual connection test happens during login().
        
        Raises:
            TrueNASAPIError: If connection fails.
        """
        try:
            # Test connection by getting system info (doesn't require auth)
            response = self._session.get(
                self._get_api_url("/system/info"),
                timeout=10
            )
            if response.status_code not in (200, 401, 403):
                raise TrueNASAPIError(
                    f"Failed to connect to TrueNAS: HTTP {response.status_code}"
                )
        except TrueNASAPIError:
            raise
        except Exception as e:
            raise TrueNASAPIError(f"Connection failed: {str(e)}")
    
    def disconnect(self) -> None:
        """Close the session."""
        if self._session:
            self._session.close()
        self._access_token = None
    
    def login(self, username: str, password: str, otp_token: str = None) -> bool:
        """Authenticate with TrueNAS REST API.
        
        Args:
            username: TrueNAS username.
            password: TrueNAS password.
            otp_token: Optional OTP token for 2FA (not used in REST API).
            
        Returns:
            True if authentication succeeded.
            
        Raises:
            TrueNASAPIError: If authentication fails.
        """
        try:
            payload = {
                "username": username,
                "password": password
            }
            
            # Temporarily remove API key header for token generation if it exists
            # (API key auth will be used for actual operations, but we still need to
            # verify the user's credentials)
            auth_header = self._session.headers.pop("Authorization", None)
            
            try:
                response = self._session.post(
                    self._get_api_url("/auth/generate_token"),
                    json=payload,
                    timeout=30
                )
            finally:
                # Restore API key header if it was present
                if auth_header:
                    self._session.headers["Authorization"] = auth_header
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                if not self._access_token:
                    raise TrueNASAPIError("No access token in response")
                
                # If API key is NOT configured, add the token to headers for future requests
                # If API key IS configured, we'll continue using it for actual operations
                # but we've now verified the user's credentials
                if not self._api_key:
                    self._session.headers.update({
                        "Authorization": f"Bearer {self._access_token}"
                    })
                return True
            elif response.status_code == 401:
                raise TrueNASAPIError("Invalid username or password")
            else:
                raise TrueNASAPIError(
                    f"Authentication failed: HTTP {response.status_code}: {response.text}"
                )
                
        except TrueNASAPIError:
            raise
        except Exception as e:
            raise TrueNASAPIError(f"Authentication request failed: {str(e)}")
    
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
        if not self._access_token and not self._api_key:
            raise TrueNASAPIError("Not authenticated. Call login() first.")
        
        try:
            # First, get the user UID using /user endpoint
            response = self._session.get(
                self._get_api_url("/user"),
                timeout=30
            )
            
            if response.status_code != 200:
                raise TrueNASAPIError(
                    f"Failed to get user list: HTTP {response.status_code}"
                )
            
            users = response.json()
            user_id = None
            
            for user in users:
                if user.get("username") == username:
                    user_id = user.get("id")
                    break
            
            if user_id is None:
                raise TrueNASAPIError(f"User '{username}' not found")
            
            # Update the user's password
            payload = {
                "password": new_password
            }
            
            response = self._session.put(
                self._get_api_url(f"/user/id/{user_id}"),
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return True
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = str(error_data)
                except:
                    pass
                
                raise TrueNASAPIError(
                    f"Password change failed: HTTP {response.status_code}: {error_msg}"
                )
                
        except TrueNASAPIError:
            raise
        except Exception as e:
            raise TrueNASAPIError(f"Password change request failed: {str(e)}")
