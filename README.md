# TrueNAS Password Manager

A simple Flask web application that allows TrueNAS users to change their own passwords through a web interface.

## Features

- User authentication against TrueNAS
- Self-service password change
- Simple, clean web interface
- No password requirements enforced (TrueNAS handles validation)
- **Dual API Support**: Works with both REST API and WebSocket JSON-RPC APIs
- Comprehensive testing (102 tests, 94% coverage)

## Requirements

- Python 3.10+
- Pipenv
- Access to a TrueNAS server

## Installation

1. Clone or download this repository:
   ```bash
   cd truenas-web-password
   ```

2. Install dependencies with pipenv:
   ```bash
   pipenv install
   ```

3. For development, install dev dependencies:
   ```bash
   pipenv install --dev
   ```

## Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your TrueNAS server details:

```
TRUENAS_HOST=192.168.1.100
TRUENAS_PORT=443
TRUENAS_USE_SSL=true
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
TRUENAS_CLIENT=rest
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TRUENAS_HOST` | TrueNAS server hostname or IP | `localhost` |
| `TRUENAS_PORT` | TrueNAS API port | `443` |
| `TRUENAS_USE_SSL` | Use SSL for connection | `true` |
| `SECRET_KEY` | Flask secret key for sessions | `change-this-secret-key-in-production` |
| `FLASK_ENV` | Environment mode (`development`, `production`, `testing`) | `development` |
| `TRUENAS_CLIENT` | API client to use (`rest` or `websocket`) | `rest` |

## API Client Selection

### REST API (Recommended)
- **Status**: ✅ Fully functional and tested
- **Use**: `TRUENAS_CLIENT=rest`
- **Advantages**:
  - Standard HTTP protocol
  - Better error handling
  - No WebSocket compatibility issues
  - Token-based authentication
  - Well-documented in TrueNAS

### WebSocket JSON-RPC (Legacy)
- **Status**: ⚠️ Tested but may have compatibility issues with some TrueNAS versions
- **Use**: `TRUENAS_CLIENT=websocket`
- **Note**: If you encounter WebSocket connection errors, see [WEBSOCKET_DIAGNOSIS.md](WEBSOCKET_DIAGNOSIS.md)

The application defaults to REST API. Switch to WebSocket if needed:
```bash
export TRUENAS_CLIENT=websocket
```

## Running the Application

### Development Mode

```bash
pipenv run python run.py
```

The application will be available at `http://localhost:5000`

### Production Mode

For production, use a WSGI server like Gunicorn:

```bash
pipenv install gunicorn
pipenv run gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'
```

## Running Tests

Run all tests with coverage:
```bash
pipenv run pytest --cov=app --cov-report=term-missing
```

Run tests verbosely:
```bash
pipenv run pytest -v
```

Current test results:
- **102 tests** (87 unit + 15 integration/REST tests)
- **94% code coverage**
- All client implementations tested

## Project Structure

```
truenas-web-password/
├── app/
│   ├── __init__.py              # Flask application factory
│   ├── config.py                 # Configuration classes
│   ├── forms.py                  # WTForms form definitions
│   ├── truenas_client.py         # TrueNAS WebSocket API client
│   ├── truenas_rest_client.py    # TrueNAS REST API client (recommended)
│   ├── utils.py                  # Shared utility functions
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py               # Login/logout routes
│   │   └── password.py           # Password change routes
│   └── templates/
│       ├── base.html             # Base template
│       ├── login.html            # Login page
│       └── change_password.html  # Password change page
├── tests/
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration and fixtures
│   ├── test_app.py               # Application factory tests
│   ├── test_auth_routes.py       # Authentication route tests
│   ├── test_forms.py             # Form validation tests
│   ├── test_password_routes.py   # Password change route tests
│   ├── test_truenas_client.py    # WebSocket client tests
│   ├── test_truenas_rest_client.py  # REST client tests
│   └── test_utils.py             # Utility function tests
├── Pipfile                       # Pipenv dependencies
├── Pipfile.lock
├── pytest.ini                    # Pytest configuration
├── run.py                        # Application entry point
├── .env.example                  # Example environment configuration
├── WEBSOCKET_DIAGNOSIS.md        # WebSocket troubleshooting guide
├── REST_API_MIGRATION.md         # REST API implementation notes
└── README.md
```

## How It Works

1. User visits the web interface and logs in with their TrueNAS credentials
2. The application authenticates against TrueNAS (via REST API by default)
3. User enters current password and new password
4. The application calls the password change API
5. User receives confirmation of successful password change

## Troubleshooting

### WebSocket Connection Errors

If you encounter WebSocket connection errors:
1. Check [WEBSOCKET_DIAGNOSIS.md](WEBSOCKET_DIAGNOSIS.md) for detailed diagnostics
2. Try switching to REST API: `export TRUENAS_CLIENT=rest`
3. Verify TrueNAS is accessible: `curl -k https://your-truenas-host/api/v2.0/system/info`

### Invalid Credentials

- Verify the credentials work on the TrueNAS web UI
- Check user permissions (some TrueNAS users may have restricted access)
- Ensure the user account exists on the TrueNAS instance

## Limitations

- Only works with local TrueNAS accounts (not LDAP/Active Directory users)
- Runs over HTTP by default (use a reverse proxy for HTTPS in production)

## License

MIT License
