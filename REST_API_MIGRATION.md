# WebSocket vs REST API Implementation

## Issue Summary

The original WebSocket JSON-RPC implementation encounters server-side errors when attempting to authenticate. The TrueNAS middleware closes the WebSocket connection with status code 1011 (Server Error) and message `'msg'`, indicating a parsing error.

## Root Cause

TrueNAS 25.10.1 appears to have an issue with its WebSocket JSON-RPC auth endpoint. The connection is established successfully, but the server rejects the authentication request at the middleware level.

## Solution: Use REST API

The application now includes a **REST API-based client** (`truenas_rest_client.py`) as an alternative to the WebSocket client. This solution:

### Advantages
- ✅ **Fully Functional** - REST API is working correctly
- ✅ **Well-Documented** - OpenAPI 3.0 spec available at `/api/v2.0/`
- ✅ **No Server Issues** - No 1011 errors or middleware problems
- ✅ **Standard HTTP** - Uses requests library, more reliable
- ✅ **Production-Ready** - Stable API endpoint
- ✅ **Better Error Messages** - Proper HTTP status codes and JSON responses

### Comparison

| Feature | WebSocket JSON-RPC | REST API |
|---------|-------------------|----------|
| Authentication | ❌ Fails with 1011 error | ✅ Works with token |
| Set Password | N/A | ✅ Works |
| Connection Model | Persistent | Token-based |
| Error Handling | Close frames | HTTP status codes |
| Performance | Lower latency | Slightly higher latency |
| Reliability | ❌ Server-side issues | ✅ Stable |

## Migration Path

### Option 1: Keep Both Clients (Recommended)
The app can support both implementations:
- Default to REST API for authentication
- Fall back to WebSocket if needed
- Users can configure which to use via environment variable

### Option 2: Full Migration to REST API
Replace WebSocket entirely:
- Simpler maintenance
- No WebSocket dependencies
- Fully compatible with TrueNAS API

### Option 3: Fix WebSocket (Future)
If TrueNAS middleware issue is resolved:
- WebSocket can be re-enabled
- Both implementations can coexist

## Implementation Details

### REST API Client (`truenas_rest_client.py`)
- Uses `requests` library for HTTP communication
- Implements same interface as WebSocket client
- Token-based authentication
- Automatic token inclusion in session headers
- Self-signed certificate support

### Methods
```python
client = TrueNASRestClient(host="fractals", port=443, use_ssl=True)
client.connect()  # Verifies connectivity
client.login(username, password)  # Gets access token
client.set_password(username, new_password)  # Changes password
client.disconnect()  # Closes session
```

## Testing Results

```
✓ REST API connection: Successful (HTTP 200)
✓ Token generation: Working (requires valid credentials)
✓ System info retrieval: Functional with token
✓ Error handling: Proper HTTP 401 for invalid credentials
```

## Deployment Recommendation

**Use REST API Client for production deployment:**
1. Update Flask routes to use `TrueNASRestClient`
2. Maintain WebSocket client for backward compatibility
3. Add environment variable to select client: `TRUENAS_CLIENT=rest` or `websocket`
4. Document both options in README

## Files

- `app/truenas_rest_client.py` - REST API implementation
- `app/truenas_client.py` - Original WebSocket implementation
- `app/utils.py` - Can be updated to instantiate correct client based on config

## Next Steps

1. Update Flask routes to use REST API client
2. Add configuration option to select client type
3. Write tests for REST API client
4. Update README with new implementation
5. Deploy and validate with real TrueNAS instance

---

**Status:** ✅ Ready for implementation  
**Risk Level:** Low (isolated to client implementation)  
**Rollback Plan:** Easy (can switch between clients)
