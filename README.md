# TrueNAS Password Manager

A simple Flask web application that allows TrueNAS users to change their own passwords through a web interface.

## Features

- **Universal Authentication**: Works for ALL users (admin and non-admin accounts)
- **Dual Authentication Methods**: 
  - SMB authentication (preferred for SMB-enabled users)
  - Unix password hash verification (fallback for all users)
- Self-service password change
- Simple, clean web interface
- No password requirements enforced (TrueNAS handles validation)
- REST API based (efficient and reliable)
- Comprehensive testing (104 tests, 95%+ coverage)

## Compatibility

**Developed and Tested For:**
- **TrueNAS SCALE 25.10.1** (primary target)
- TrueNAS API v2.0

**Expected to work with:**
- TrueNAS SCALE 24.x and newer
- Any TrueNAS version with REST API v2.0 support

**Note:** The application uses standard Unix authentication mechanisms (SMB and password hashes) that are platform-independent. While developed on SCALE 25.10.1, it should work with most TrueNAS SCALE and potentially TrueNAS CORE versions that support the REST API v2.0.

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

### Step 1: Get TrueNAS API Key

The application requires a TrueNAS API key to authenticate users and change passwords.

**To generate an API key:**

1. Log in to your TrueNAS web interface
2. Click on the user icon (top right) or go to **Credentials > Local Users**
3. Click on your admin user (e.g., `truenas_admin` or `admin`)
4. Scroll down to the **API Keys** section
5. Click **Add** to create a new API key
6. Give it a name (e.g., "Password Manager")
7. Click **Save** or **Add**
8. **Important**: Copy the API key immediately - it will only be shown once!

The API key will look something like:
```
1-AbCdEfGhIjKlMnOpQrStUvWxYz1234567890AbCdEfGhIjKlMnOpQrSt
```

### Step 2: Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your TrueNAS server details:

```
TRUENAS_HOST=192.168.1.100
TRUENAS_PORT=443
TRUENAS_USE_SSL=true
TRUENAS_API_KEY=1-YourActualAPIKeyHere
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TRUENAS_HOST` | TrueNAS server hostname or IP | `localhost` | ✅ Yes |
| `TRUENAS_PORT` | TrueNAS API port | `443` | No |
| `TRUENAS_USE_SSL` | Use SSL for connection | `true` | No |
| `TRUENAS_API_KEY` | TrueNAS API key (see above) | None | ✅ Yes |
| `SECRET_KEY` | Flask secret key for sessions | `change-this-secret-key-in-production` | ✅ Yes |
| `FLASK_ENV` | Environment mode (`development`, `production`, `testing`) | `development` | No |

## How Authentication Works

The application uses a **dual authentication approach** that works for ALL TrueNAS users:

### Authentication Flow

1. **User Login**: User enters their TrueNAS username and password
2. **Primary Method - SMB Authentication** (if user has SMB enabled):
   - Attempts SMB authentication against port 445
   - Fast and direct verification
   - Works for users with SMB access enabled
3. **Fallback Method - Hash Verification** (if SMB fails or unavailable):
   - Fetches user's Unix password hash using the API key
   - Verifies password locally using Python's `crypt` module
   - Works for ALL users regardless of admin status or SMB access

### Why This Approach?

TrueNAS SCALE restricts API authentication to users with admin roles. Regular users (with `roles: []`) cannot authenticate via traditional API methods even with correct passwords. This dual approach solves that limitation:

- **SMB auth**: Preferred for speed when available
- **Hash verification**: Universal fallback using API key privileges
- **Result**: Any TrueNAS user can log in and change their password

## API Client Selection

### REST API (Used)
- **Status**: ✅ Fully functional and tested
- **Advantages**:
  - Standard HTTP protocol
  - Better error handling
  - Token-based authentication with API key
  - Well-documented in TrueNAS
  - Works with hash verification method

### WebSocket JSON-RPC (Legacy/Removed)
- **Status**: ⚠️ Previously supported but removed
- **Limitation**: Only worked for admin users with roles
- **Note**: If you need WebSocket support, use older commits before hash verification implementation

## Running the Application

### Development Mode

```bash
pipenv run python run.py
```

The application will be available at `http://localhost:5000`

### Docker Deployment

#### Quick Start with Docker Compose

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your TrueNAS details:
   ```
   TRUENAS_HOST=your-truenas-ip
   TRUENAS_API_KEY=your-api-key
   SECRET_KEY=generate-a-random-string
   ```

3. Build and run:
   ```bash
   docker-compose up -d
   ```

4. Access at `http://localhost:5000`

#### Manual Docker Build

```bash
# Build the image
docker build -t truenas-password-manager .

# Run the container
docker run -d \
  -p 5000:5000 \
  -e TRUENAS_HOST=your-truenas-ip \
  -e TRUENAS_PORT=443 \
  -e TRUENAS_USE_SSL=true \
  -e TRUENAS_API_KEY=your-api-key \
  -e SECRET_KEY=your-secret-key \
  --name password-manager \
  truenas-password-manager
```

### TrueNAS SCALE App Deployment

The application includes a Helm chart for deploying as a TrueNAS SCALE custom app.

#### Option 1: Custom App (Recommended)

1. In TrueNAS SCALE, go to **Apps** → **Discover Apps** → **Custom App**

2. Configure the app:
   - **Application Name**: `password-manager`
   - **Image Repository**: `ghcr.io/yourusername/truenas-password-manager`
   - **Image Tag**: `latest`

3. Add environment variables:
   | Name | Value |
   |------|-------|
   | `TRUENAS_HOST` | Your TrueNAS IP (e.g., `10.0.0.100`) |
   | `TRUENAS_PORT` | `443` |
   | `TRUENAS_USE_SSL` | `true` |
   | `TRUENAS_API_KEY` | Your API key |
   | `SECRET_KEY` | Random string for sessions |

4. Configure networking:
   - **Port**: `5000`
   - **Node Port**: Choose an available port (e.g., `30500`)

5. Deploy and access at `http://your-truenas-ip:30500`

#### Option 2: Helm Chart

If you have a custom TrueNAS catalog or want to use Helm directly:

```bash
# Add your chart repository (if using one)
helm repo add my-charts https://your-chart-repo

# Install
helm install password-manager ./chart \
  --set truenas.host=your-truenas-ip \
  --set truenas.apiKey=your-api-key
```

#### Important Notes for TrueNAS Deployment

- **Use the TrueNAS host IP**, not `localhost` (the container runs in its own network)
- **Port 445 (SMB)** must be accessible from the container to TrueNAS for SMB authentication
- **Port 443 (API)** must be accessible for REST API calls
- Consider using **Ingress** or a **reverse proxy** for HTTPS in production

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
- **104 tests** (all passing)
- **95%+ code coverage**
- Comprehensive unit and integration tests

## Project Structure

```
truenas-web-password/
├── app/
│   ├── __init__.py              # Flask application factory
│   ├── config.py                 # Configuration classes
│   ├── forms.py                  # WTForms form definitions
│   ├── truenas_rest_client.py    # TrueNAS REST API client with dual auth
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
│   ├── test_integration.py       # Full user flow integration tests
│   ├── test_password_routes.py   # Password change route tests
│   ├── test_truenas_rest_client.py  # REST client tests
│   └── test_utils.py             # Utility function tests
├── Pipfile                       # Pipenv dependencies
├── Pipfile.lock
├── pytest.ini                    # Pytest configuration
├── run.py                        # Application entry point
├── .env.example                  # Example environment configuration
└── README.md
```

## How It Works

1. User visits the web interface and logs in with their TrueNAS credentials
2. The application authenticates via:
   - **First**: SMB authentication (if user has SMB enabled)
   - **Fallback**: Unix password hash verification using API key
3. After successful login, user can change their password
4. User enters current password and new password
5. The application calls the TrueNAS password change API using the API key
6. User receives confirmation of successful password change

## Security Notes

- **API Key**: Keep your TrueNAS API key secure - it has admin privileges
- **HTTPS**: Use HTTPS in production (reverse proxy recommended)
- **Session Security**: Flask sessions are signed with SECRET_KEY
- **Password Verification**: Passwords are verified locally, never stored
- **SMB Connection**: SMB authentication is attempted over port 445 (firewall may need configuration)

## Troubleshooting

### Missing API Key Error

If you see "API key required for password verification":
1. Generate an API key in TrueNAS (see Configuration section above)
2. Add it to your `.env` file as `TRUENAS_API_KEY=your-key-here`
3. Restart the application

### Connection Errors

If you cannot connect to TrueNAS:
1. Verify TrueNAS is accessible: `curl -k https://your-truenas-host/api/v2.0/system/info`
2. Check firewall settings (port 443 for API, port 445 for SMB)
3. Verify `TRUENAS_HOST` in `.env` is correct
4. Check SSL certificate settings (use `TRUENAS_USE_SSL=false` for HTTP)

### Invalid Credentials

- Verify the credentials work on the TrueNAS web UI or via SSH
- Check that the user account exists on the TrueNAS instance
- For SMB users: Verify SMB service is enabled and running
- Check TrueNAS logs for authentication failures

### Python Crypt Deprecation Warning

You may see a warning about the deprecated `crypt` module. This is expected and will be addressed in future Python versions. The application will continue to work normally.

## Limitations

- Requires a TrueNAS API key with admin privileges
- Only works with local TrueNAS accounts (not LDAP/Active Directory users)
- SMB authentication requires port 445 access
- Runs over HTTP by default (use a reverse proxy for HTTPS in production)

## Dependencies

- Flask 3.x - Web framework
- WTForms - Form validation
- python-dotenv - Environment configuration
- pysmb - SMB authentication (optional, used for SMB users)
- requests - HTTP client for REST API

## License

MIT License
