"""Unit tests for WTForms form definitions."""

import pytest
from werkzeug.datastructures import MultiDict

from app.forms import LoginForm, PasswordChangeForm


class TestLoginForm:
    """Test cases for LoginForm."""
    
    def test_valid_login_form(self):
        """Test form validation with valid data."""
        form = LoginForm(MultiDict([
            ('username', 'testuser'),
            ('password', 'testpass123')
        ]))
        
        assert form.validate() is True
        assert form.username.data == 'testuser'
        assert form.password.data == 'testpass123'
    
    def test_missing_username(self):
        """Test form validation fails without username."""
        form = LoginForm(MultiDict([
            ('username', ''),
            ('password', 'testpass123')
        ]))
        
        assert form.validate() is False
        assert 'Username is required' in form.username.errors
    
    def test_missing_password(self):
        """Test form validation fails without password."""
        form = LoginForm(MultiDict([
            ('username', 'testuser'),
            ('password', '')
        ]))
        
        assert form.validate() is False
        assert 'Password is required' in form.password.errors
    
    def test_username_too_long(self):
        """Test form validation fails with username over 64 characters."""
        long_username = 'a' * 65
        form = LoginForm(MultiDict([
            ('username', long_username),
            ('password', 'testpass123')
        ]))
        
        assert form.validate() is False
        assert any('64 characters' in error for error in form.username.errors)
    
    def test_empty_form(self):
        """Test form validation fails with empty form."""
        form = LoginForm(MultiDict([]))
        
        assert form.validate() is False
        assert len(form.username.errors) > 0
        assert len(form.password.errors) > 0


class TestPasswordChangeForm:
    """Test cases for PasswordChangeForm."""
    
    def test_valid_password_change_form(self):
        """Test form validation with valid data."""
        form = PasswordChangeForm(MultiDict([
            ('current_password', 'oldpass123'),
            ('new_password', 'newpass456'),
            ('confirm_password', 'newpass456')
        ]))
        
        assert form.validate() is True
        assert form.current_password.data == 'oldpass123'
        assert form.new_password.data == 'newpass456'
        assert form.confirm_password.data == 'newpass456'
    
    def test_missing_current_password(self):
        """Test form validation fails without current password."""
        form = PasswordChangeForm(MultiDict([
            ('current_password', ''),
            ('new_password', 'newpass456'),
            ('confirm_password', 'newpass456')
        ]))
        
        assert form.validate() is False
        assert 'Current password is required' in form.current_password.errors
    
    def test_missing_new_password(self):
        """Test form validation fails without new password."""
        form = PasswordChangeForm(MultiDict([
            ('current_password', 'oldpass123'),
            ('new_password', ''),
            ('confirm_password', 'newpass456')
        ]))
        
        assert form.validate() is False
        assert 'New password is required' in form.new_password.errors
    
    def test_missing_confirm_password(self):
        """Test form validation fails without confirm password."""
        form = PasswordChangeForm(MultiDict([
            ('current_password', 'oldpass123'),
            ('new_password', 'newpass456'),
            ('confirm_password', '')
        ]))
        
        assert form.validate() is False
        assert 'Please confirm your new password' in form.confirm_password.errors
    
    def test_passwords_do_not_match(self):
        """Test form validation fails when passwords don't match."""
        form = PasswordChangeForm(MultiDict([
            ('current_password', 'oldpass123'),
            ('new_password', 'newpass456'),
            ('confirm_password', 'differentpass789')
        ]))
        
        assert form.validate() is False
        assert 'Passwords must match' in form.confirm_password.errors
    
    def test_empty_form(self):
        """Test form validation fails with empty form."""
        form = PasswordChangeForm(MultiDict([]))
        
        assert form.validate() is False
        assert len(form.current_password.errors) > 0
        assert len(form.new_password.errors) > 0
        assert len(form.confirm_password.errors) > 0
