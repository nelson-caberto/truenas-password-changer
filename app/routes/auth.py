"""Authentication routes for login and logout."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app

from app.forms import LoginForm
from app.truenas_client import TrueNASClient, TrueNASAPIError

bp = Blueprint('auth', __name__)


def get_truenas_client() -> TrueNASClient:
    """Create a TrueNAS client from app configuration.
    
    Returns:
        Configured TrueNASClient instance.
    """
    return TrueNASClient(
        host=current_app.config['TRUENAS_HOST'],
        port=current_app.config['TRUENAS_PORT'],
        use_ssl=current_app.config['TRUENAS_USE_SSL']
    )


@bp.route('/')
def index():
    """Redirect to login or password change based on session state."""
    if 'username' in session:
        return redirect(url_for('password.change'))
    return redirect(url_for('auth.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    form = LoginForm(request.form)
    
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = form.password.data
        
        client = get_truenas_client()
        
        try:
            client.connect()
            client.login(username, password)
            
            # Store user info in session
            session['username'] = username
            session['password'] = password  # Needed for password change verification
            
            client.disconnect()
            
            flash('Login successful!', 'success')
            return redirect(url_for('password.change'))
            
        except TrueNASAPIError as e:
            flash(f'Login failed: {e.reason or e.message}', 'error')
        except Exception as e:
            flash(f'Connection error: {str(e)}', 'error')
        finally:
            client.disconnect()
    
    return render_template('login.html', form=form)


@bp.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
