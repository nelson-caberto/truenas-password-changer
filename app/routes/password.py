"""Password change routes."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.forms import PasswordChangeForm
from app.truenas_websocket_client import TrueNASAPIError
from app.utils import get_truenas_client, login_required

bp = Blueprint('password', __name__)


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change():
    """Handle password change form."""
    form = PasswordChangeForm(request.form)
    username = session.get('username')
    
    if request.method == 'POST' and form.validate():
        current_password = form.current_password.data
        new_password = form.new_password.data
        
        client = get_truenas_client()
        
        try:
            client.connect()
            # Try to login with current credentials to verify them
            try:
                client.login(username, current_password)
            except TrueNASAPIError as e:
                # If login fails but not due to wrong credentials, proceed with API key auth
                if "not found" not in str(e).lower() and "Invalid" not in str(e):
                    pass
                else:
                    raise
            
            client.set_password(username, new_password)
            client.disconnect()
            
            # Password changed successfully - log out user for security
            session.clear()
            flash('Password changed successfully! Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
            
        except TrueNASAPIError as e:
            if "Invalid username or password" in str(e) or "not found" in str(e).lower():
                flash('Current password is incorrect.', 'error')
            else:
                flash(f'Password change failed: {e.reason or e.message}', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        finally:
            client.disconnect()
    
    return render_template('change_password.html', form=form, username=username)
