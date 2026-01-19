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
