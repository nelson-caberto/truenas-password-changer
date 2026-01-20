"""WTForms form definitions for authentication and password change."""

from wtforms import Form, StringField, PasswordField, validators


class LoginForm(Form):
    """Login form for TrueNAS authentication."""
    
    username = StringField('Username', [
        validators.DataRequired(message='Username is required'),
        validators.Length(min=1, max=64, message='Username must be between 1 and 64 characters')
    ])
    
    password = PasswordField('Password', [
        validators.DataRequired(message='Password is required')
    ])


class PasswordChangeForm(Form):
    """Form for changing user password."""
    
    current_password = PasswordField('Current Password', [
        validators.DataRequired(message='Current password is required')
    ])
    
    new_password = PasswordField('New Password', [
        validators.DataRequired(message='New password is required')
    ])
    
    confirm_password = PasswordField('Confirm New Password', [
        validators.DataRequired(message='Please confirm your new password'),
        validators.EqualTo('new_password', message='Passwords must match')
    ])
