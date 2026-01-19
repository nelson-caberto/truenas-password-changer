"""Password change routes."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app

from app.forms import PasswordChangeForm
from app.truenas_client import TrueNASClient, TrueNASAPIError

bp = Blueprint('password', __name__)


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


def login_required(f):
    """Decorator to require login for a route.
    
    Args:
        f: The view function to wrap.
        
    Returns:
        Wrapped function that checks for login.
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    
    return decorated_function


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change():
    """Handle password change form."""
    form = PasswordChangeForm(request.form)
    username = session.get('username')
    
    if request.method == 'POST' and form.validate():
        current_password = form.current_password.data
        new_password = form.new_password.data
        
        # Verify current password matches session
        if current_password != session.get('password'):
            flash('Current password is incorrect.', 'error')
            return render_template('change_password.html', form=form, username=username)
        
        client = get_truenas_client()
        
        try:
            client.connect()
            client.login(username, current_password)
            client.set_password(username, new_password)
            
            # Update session with new password
            session['password'] = new_password
            
            client.disconnect()
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('password.change'))
            
        except TrueNASAPIError as e:
            flash(f'Password change failed: {e.reason or e.message}', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        finally:
            client.disconnect()
    
    return render_template('change_password.html', form=form, username=username)
