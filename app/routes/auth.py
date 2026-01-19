"""Authentication routes for login and logout."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.forms import LoginForm
from app.truenas_client import TrueNASAPIError
from app.utils import get_truenas_client

bp = Blueprint('auth', __name__)


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
            import sys
            print(f'Connection attempt to {client._get_ws_url()}', file=sys.stderr)
        except Exception as e:
            flash(f'Connection error: {str(e)}', 'error')
            import sys
            print(f'Connection attempt to {client._get_ws_url()}: {str(e)}', file=sys.stderr)
        finally:
            client.disconnect()
    
    return render_template('login.html', form=form)


@bp.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
