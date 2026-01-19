# TrueNAS Password Manager

A simple Flask web application that allows TrueNAS users to change their own passwords through a web interface.

## Features

- User authentication against TrueNAS
- Self-service password change
- Simple, clean web interface
- No password requirements enforced (TrueNAS handles validation)

## Requirements

- Python 3.10+
- Pipenv
- Access to a TrueNAS server with WebSocket API enabled

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
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TRUENAS_HOST` | TrueNAS server hostname or IP | `localhost` |
| `TRUENAS_PORT` | TrueNAS WebSocket API port | `443` |
| `TRUENAS_USE_SSL` | Use SSL for WebSocket connection | `true` |
| `SECRET_KEY` | Flask secret key for sessions | `change-this-secret-key-in-production` |
| `FLASK_ENV` | Environment mode (`development`, `production`, `testing`) | `development` |

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

## Project Structure

```
truenas-web-password/
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── config.py             # Configuration classes
│   ├── forms.py              # WTForms form definitions
│   ├── truenas_client.py     # TrueNAS WebSocket API client
│   ├── utils.py              # Shared utility functions
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py           # Login/logout routes
│   │   └── password.py       # Password change routes
│   └── templates/
│       ├── base.html         # Base template
│       ├── login.html        # Login page
│       └── change_password.html  # Password change page
├── tests/
│   ├── __init__.py
│   ├── test_app.py           # Application factory tests
│   ├── test_auth_routes.py   # Authentication route tests
│   ├── test_forms.py         # Form validation tests
│   ├── test_password_routes.py   # Password change route tests
│   ├── test_truenas_client.py    # TrueNAS client tests
│   └── test_utils.py         # Utility function tests
├── Pipfile                   # Pipenv dependencies
├── Pipfile.lock
├── pytest.ini                # Pytest configuration
├── run.py                    # Application entry point
└── README.md
```

## How It Works

1. User visits the web interface and logs in with their TrueNAS credentials
2. The application authenticates against TrueNAS via WebSocket JSON-RPC API
3. User enters current password and new password
4. The application calls `user.set_password` API to change the password
5. User receives confirmation of successful password change

## Limitations

- Only works with local TrueNAS accounts (not LDAP/Active Directory users)
- Requires WebSocket API access to TrueNAS
- Runs over HTTP (no HTTPS by default)

## License

MIT License
