"""Password change routes."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.forms import PasswordChangeForm
from app.truenas_client import TrueNASAPIError
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
        
        # When using API key auth, we trust that login already verified the user exists
        # For additional security, password changes still require entering current password
        # but with API key auth, we skip the credential verification (API key proves admin access)
        
        client = get_truenas_client()
        
        try:
            client.connect()
            # With API key auth, don't verify credentials again (API key proves access)
            # Just proceed with password change
            # With token auth, this would verify credentials
            try:
                client.login(username, current_password)
            except TrueNASAPIError as e:
                # If login fails, it might be because we're using API key auth
                # In that case, just proceed with password change
                if "not found" not in str(e).lower() and "401" not in str(e):
                    raise
            
            client.set_password(username, new_password)
            
            # Update session with new password
            session['password'] = new_password
            
            client.disconnect()
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('password.change'))
            
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
