# TrueNAS Password Changer

A simple Flask web application that allows TrueNAS users to change their own passwords through a web interface.

## Features

- **Universal Authentication**: Works for ALL users (admin and non-admin accounts)
- **Dual Authentication Methods**: 
  - SMB authentication (preferred for SMB-enabled users)
  - Unix password hash verification (fallback for all users)
- Self-service password change
- Simple, clean web interface
- No password requirements enforced (TrueNAS handles validation)
- **WebSocket API** (TrueNAS 26.04+ compatible)
- Comprehensive testing (84 tests, 95%+ coverage)

## Compatibility

**Developed and Tested For:**
- **TrueNAS SCALE 25.10.1** (primary target)
- **TrueNAS SCALE 26.04+** (ready for WebSocket-only API)
- TrueNAS WebSocket Middleware Protocol

**Expected to work with:**
- TrueNAS SCALE 24.x and newer
- TrueNAS SCALE 26.04+ (REST API removed, WebSocket required)

**Note:** This application uses the TrueNAS WebSocket API with its custom middleware protocol (DDP-like), which is the only supported API in TrueNAS 26.04+. The deprecated REST API was removed in that release. Authentication uses standard Unix mechanisms (SMB and password hashes) that are platform-independent.

**⚠️ Migration Notice:** If upgrading from an older version of this app that used the REST API, simply update to this version - no configuration changes needed. The WebSocket API uses the same ports and API keys.

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

> **🔒 Security Best Practice**: Create a dedicated service account instead of using your main admin account. This follows the principle of least privilege and limits potential security exposure.

#### Option A: Use Existing Admin Account (Quick Start)

1. Log in to your TrueNAS web interface
2. Click on the user icon (top right) or go to **Credentials > Local Users**
3. Click on your admin user (e.g., `truenas_admin` or `admin`)
4. Scroll down to the **API Keys** section
5. Click **Add** to create a new API key
6. Give it a name (e.g., "Password Changer")
7. Click **Save** or **Add**
8. **Important**: Copy the API key immediately - it will only be shown once!

#### Option B: Create Dedicated Service Account (Recommended)

For better security, create a dedicated account with minimal privileges:

1. Go to **Credentials > Local Users** → **Add**

2. Configure the user:
   | Field | Value |
   |-------|-------|
   | **Username** | `password-changer-service` |
   | **Full Name** | `Password Changer Service Account` |
   | **Email** | (optional) |
   | **Password** | Generate a strong random password |
   | **User ID** | (auto-generate) |
   | **Home Directory** | `/nonexistent` |
   | **Shell** | `nologin` |
   | **Samba Authentication** | ❌ Disabled |
   | **Sudo Access** | ❌ Disabled |

3. After creating, edit the user and go to **Roles**:
   - Click **Add**
   - Select role: **SHARING_ADMIN** (allows managing user accounts)
   - Or create a custom role with only: `ACCOUNT_READ`, `ACCOUNT_WRITE`

4. Generate API Key:
   - Scroll to **API Keys** section
   - Click **Add**
   - Name: `Password Changer Service`
   - Click **Add**
   - Copy the API key immediately

5. **Disable Password Login** (optional but recommended):
   - This account should only use API key, not password login
   - Set **Lock User** or use a very strong random password

**Why use a dedicated account?**
- ✅ Limits blast radius if API key is compromised
- ✅ Easier to audit (all actions by this app show as one user)
- ✅ Can be disabled independently without affecting admin access
- ✅ Follows principle of least privilege

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
   - Fetches user's Unix password hash via WebSocket API using the API key
   - Verifies password locally using `passlib` library
   - Supports SHA-512, SHA-256, and MD5 hash formats
   - Works for ALL users regardless of admin status or SMB access

### Why This Approach?

TrueNAS SCALE restricts API authentication to users with admin roles. Regular users (with `roles: []`) cannot authenticate via traditional API methods even with correct passwords. This dual approach solves that limitation:

- **SMB auth**: Preferred for speed when available
- **Hash verification**: Universal fallback using API key privileges
- **Result**: Any TrueNAS user can log in and change their password

## API Client Selection

### WebSocket Middleware Protocol (Current)
- **Status**: ✅ Fully functional and tested
- **Why WebSocket**: TrueNAS deprecated the REST API and removed it in version 26.04
- **Protocol**: TrueNAS uses a custom DDP-like middleware protocol over WebSocket:
  - Connect handshake: `{"msg": "connect", "version": "1", "support": ["1"]}`
  - Method calls: `{"id": "N", "msg": "method", "method": "...", "params": [...]}`
  - Responses: `{"id": "N", "msg": "result", "result": ...}`
- **Advantages**:
  - Future-proof (required for TrueNAS 26.04+)
  - Real-time bidirectional communication
  - Token-based authentication with API key
  - Works with hash verification method
- **Documentation**: https://api.truenas.com/v25.10/jsonrpc.html

### REST API (Deprecated/Removed)
- **Status**: ❌ Removed from this application
- **Reason**: TrueNAS removed REST API support in version 26.04
- **Note**: If you need REST API support for older TrueNAS versions, use commits before the WebSocket migration

## Deployment Options

Choose the deployment method that best fits your environment:

| Option | Best For | Difficulty | Status |
|--------|----------|------------|--------|
| [1. Standalone Flask](#option-1-standalone-flask-server) | Testing, simple setups | Easy | ✅ **Tested** |
| [2. Apache Integration](#option-2-integrate-with-existing-apache) | Existing Apache servers | Medium | ⚠️ Untested |
| [3. Nginx Integration](#option-3-integrate-with-existing-nginx) | Existing Nginx servers | Medium | ⚠️ Untested |
| [4. TrueNAS App](#option-4-install-as-truenas-app) | TrueNAS SCALE users | Easy | ⚠️ Untested |

---

### Option 1: Standalone Flask Server

✅ **Tested and verified**

Best for testing or simple deployments without an existing web server.

#### Development Mode

```bash
# Install dependencies
pipenv install

# Run the development server
pipenv run python run.py
```

Access at `http://localhost:5000`

#### Production Mode (Gunicorn)

```bash
# Install gunicorn
pipenv install gunicorn

# Run with gunicorn (4 workers)
pipenv run gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'
```

#### Auto-start with Systemd

Create `/etc/systemd/system/truenas-password-changer.service`:

```ini
[Unit]
Description=TrueNAS Password Changer
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/truenas-password-changer
Environment="PATH=/opt/truenas-password-changer/.venv/bin"
EnvironmentFile=/opt/truenas-password-changer/.env
ExecStart=/opt/truenas-password-changer/.venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable truenas-password-changer
sudo systemctl start truenas-password-changer
```

---

### Option 2: Integrate with Existing Apache

⚠️ **Untested - provided as reference configuration**

If you already have Apache running, add this as a virtual host.

#### Prerequisites

```bash
# Enable required modules
sudo a2enmod proxy proxy_http ssl headers
sudo systemctl restart apache2
```

#### Step 1: Install the Application

```bash
# Clone to /opt
cd /opt
git clone https://github.com/yourusername/truenas-web-password.git truenas-password-changer
cd truenas-password-changer

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn

# Configure
cp .env.example .env
nano .env  # Add your TRUENAS_HOST, TRUENAS_API_KEY, SECRET_KEY
```

#### Step 2: Create Systemd Service

Create `/etc/systemd/system/truenas-password-changer.service`:

```ini
[Unit]
Description=TrueNAS Password Changer
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/truenas-password-changer
Environment="PATH=/opt/truenas-password-changer/.venv/bin"
EnvironmentFile=/opt/truenas-password-changer/.env
ExecStart=/opt/truenas-password-changer/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 'app:create_app()'
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable truenas-password-changer
sudo systemctl start truenas-password-changer
```

#### Step 3: Apache Virtual Host

Create `/etc/apache2/sites-available/password-changer.conf`:

```apache
<VirtualHost *:80>
    ServerName password.yourdomain.com
    Redirect permanent / https://password.yourdomain.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName password.yourdomain.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/password.yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/password.yourdomain.com/privkey.pem
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1

    # Security headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"

    # Proxy to Flask app
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    ProxyTimeout 60
</VirtualHost>
```

```bash
sudo a2ensite password-changer
sudo systemctl reload apache2
```

---

### Option 3: Integrate with Existing Nginx

⚠️ **Untested - provided as reference configuration**

If you already have Nginx running, add this as a server block.

#### Step 1: Install the Application

```bash
# Clone to /opt
cd /opt
git clone https://github.com/yourusername/truenas-web-password.git truenas-password-changer
cd truenas-password-changer

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn

# Configure
cp .env.example .env
nano .env  # Add your TRUENAS_HOST, TRUENAS_API_KEY, SECRET_KEY
```

#### Step 2: Create Systemd Service

Create `/etc/systemd/system/truenas-password-changer.service`:

```ini
[Unit]
Description=TrueNAS Password Changer
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/truenas-password-changer
Environment="PATH=/opt/truenas-password-changer/.venv/bin"
EnvironmentFile=/opt/truenas-password-changer/.env
ExecStart=/opt/truenas-password-changer/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 'app:create_app()'
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable truenas-password-changer
sudo systemctl start truenas-password-changer
```

#### Step 3: Nginx Server Block

Create `/etc/nginx/sites-available/password-changer`:

```nginx
server {
    listen 80;
    server_name password.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name password.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/password.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/password.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/password-changer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### Option 4: Install as TrueNAS App

⚠️ **Untested - provided as reference configuration**

Deploy directly on your TrueNAS SCALE server using Docker.

#### Method A: Docker Compose (Simple)

1. SSH into your TrueNAS or use a dataset:
   ```bash
   cd /mnt/your-pool/apps/password-changer
   ```

2. Create `docker-compose.yml`:
   ```yaml
   version: '3.8'
   services:
     password-changer:
       image: ghcr.io/yourusername/truenas-password-changer:latest
       # Or build locally:
       # build: .
       ports:
         - "5000:5000"
       environment:
         - TRUENAS_HOST=10.0.0.100  # Your TrueNAS IP
         - TRUENAS_PORT=443
         - TRUENAS_USE_SSL=true
         - TRUENAS_API_KEY=your-api-key-here
         - SECRET_KEY=generate-random-string
       restart: unless-stopped
   ```

3. Run:
   ```bash
   docker-compose up -d
   ```

4. Access at `http://your-truenas-ip:5000`

#### Method B: TrueNAS Custom App

1. Go to **Apps** → **Discover Apps** → **Custom App**

2. Configure:
   | Setting | Value |
   |---------|-------|
   | Application Name | `password-changer` |
   | Image Repository | `ghcr.io/yourusername/truenas-password-changer` |
   | Image Tag | `latest` |

3. Add Environment Variables:
   | Name | Value |
   |------|-------|
   | `TRUENAS_HOST` | Your TrueNAS IP (NOT localhost!) |
   | `TRUENAS_PORT` | `443` |
   | `TRUENAS_USE_SSL` | `true` |
   | `TRUENAS_API_KEY` | Your API key |
   | `SECRET_KEY` | Random string |

4. Configure Networking:
   - Container Port: `5000`
   - Node Port: `30500` (or any available)

5. Deploy and access at `http://your-truenas-ip:30500`

#### Method C: Helm Chart (Advanced)

```bash
helm install password-changer ./chart \
  --set truenas.host=10.0.0.100 \
  --set truenas.apiKey=your-api-key \
  --set truenas.port=443
```

#### Important Notes for TrueNAS Deployment

⚠️ **Use the TrueNAS host IP** (e.g., `10.0.0.100`), NOT `localhost`. The container runs in its own network namespace.

⚠️ **Ensure ports are accessible** from the container:
- Port 443 (WebSocket API) - Required for WebSocket JSON-RPC calls
- Port 445 (SMB) - Required for SMB authentication (if used)

---

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
- **84 tests** (all passing)
- **95%+ code coverage**
- Comprehensive unit and integration tests

## Project Structure

```
truenas-web-password/
├── app/
│   ├── __init__.py              # Flask application factory
│   ├── config.py                 # Configuration classes
│   ├── forms.py                  # WTForms form definitions
│   ├── truenas_websocket_client.py  # TrueNAS WebSocket JSON-RPC 2.0 client
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
│   ├── test_truenas_websocket_client.py  # WebSocket client tests
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
2. Check firewall settings (port 443 for WebSocket API, port 445 for SMB)
3. Verify `TRUENAS_HOST` in `.env` is correct
4. Check SSL certificate settings (use `TRUENAS_USE_SSL=false` for HTTP)
5. Ensure WebSocket connections are not blocked by proxies/firewalls

### Invalid Credentials

- Verify the credentials work on the TrueNAS web UI or via SSH
- Check that the user account exists on the TrueNAS instance
- For SMB users: Verify SMB service is enabled and running
- Check TrueNAS logs for authentication failures

## Limitations

- Requires a TrueNAS API key with admin privileges
- Only works with local TrueNAS accounts (not LDAP/Active Directory users)
- SMB authentication requires port 445 access
- Runs over HTTP by default (use a reverse proxy for HTTPS in production)

## Dependencies

- Flask 3.x - Web framework
- WTForms - Form validation
- python-dotenv - Environment configuration
- pysmb - SMB authentication (used for SMB users)
- websocket-client - WebSocket client for TrueNAS API
- passlib - Password hash verification (SHA-512, SHA-256, MD5)

## License

MIT License
