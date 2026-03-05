# blueprints/auth/routes.py
from flask import request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_user, login_required, logout_user, current_user
from models import db, User
from utils import ActivityLogger, get_safe_redirect_url, get_safe_endpoint_url
from datetime import datetime, timedelta
import re
from . import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with rate limiting and account lockout protection."""
    if request.method == 'POST':
        # Check if this is an AJAX request
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        
        # Check if account is locked
        if user and user.is_account_locked():
            lockout_time = user.account_locked_until
            remaining = (lockout_time - datetime.utcnow()).total_seconds() / 60
            error_msg = f'Account locked due to too many failed attempts. Try again in {int(remaining)} minutes.'
            
            # Log lockout attempt
            ActivityLogger.log(ActivityLogger.USER_LOGIN, user_id=user.id, 
                             details=f"Login attempt while locked: {username}")
            
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 403
            flash(error_msg)
            return render_template('login.html')
        
        # Validate credentials
        if user and user.check_password(password):
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user)
            session.permanent = True  # Enforce PERMANENT_SESSION_LIFETIME expiry
            
            # Log successful login
            ActivityLogger.log(ActivityLogger.USER_LOGIN, user_id=user.id, details=f"Username: {username}")
            
            # Check if password change is required
            if user.force_password_change:
                if request.is_json:
                    return jsonify({
                        'success': True, 
                        'force_password_change': True,
                        'message': 'Password change required',
                        'redirect': url_for('auth.change_password')
                    })
                flash('You must change your password before continuing', 'warning')
                return redirect(url_for('auth.change_password'))
            
            # Get safe redirect URL (validate any redirect parameter)
            next_page = request.args.get('next')
            redirect_url = get_safe_redirect_url(next_page, fallback='main.dashboard')
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login successful', 'redirect': redirect_url})
            return redirect(redirect_url)
        else:
            # Track failed login attempt
            if user:
                user.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts for 15 minutes
                if user.failed_login_attempts >= 5:
                    user.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
                    db.session.commit()
                    
                    # Log account lockout
                    ActivityLogger.log(ActivityLogger.USER_LOGIN, user_id=user.id,
                                     details=f"Account locked after {user.failed_login_attempts} failed attempts")
                    
                    error_msg = 'Account locked due to too many failed attempts. Try again in 15 minutes.'
                    if request.is_json:
                        return jsonify({'success': False, 'message': error_msg}), 403
                    flash(error_msg)
                    return render_template('login.html')
                
                db.session.commit()
                
                # Log failed attempt
                ActivityLogger.log(ActivityLogger.USER_LOGIN, user_id=user.id,
                                 details=f"Failed login attempt ({user.failed_login_attempts}/5): {username}")
            
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
            flash('Invalid username or password')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    # Log logout before actually logging out
    ActivityLogger.log(ActivityLogger.USER_LOGOUT, details=f"Username: {current_user.username}")
    
    logout_user()
    # Use safe endpoint URL for redirect
    return redirect(get_safe_endpoint_url('main.home'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration - first user can register without login"""
    if request.method == 'POST':
        # Check if this is an AJAX request
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            role = data.get('role', 'user')
        else:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role', 'user')

        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({'success': False, 'message': 'Username already exists'}), 400
            flash('Username already exists')
            return redirect(get_safe_endpoint_url('auth.register'))
        
        # Validate password strength
        is_valid, error_msg = User.validate_password_strength(password)
        if not is_valid:
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return render_template('register.html')

        # Check if this is the first user - if so, make them admin and owner
        user_count = db.session.query(User).count()
        is_owner = False
        if user_count == 0:
            # First user becomes admin and is marked as the protected owner
            role = 'admin'
            is_owner = True
        else:
            # Only existing admins can create other admins
            if not (current_user.is_authenticated and getattr(current_user, 'role', None) == 'admin'):
                role = 'user'

        user = User(username=username, email=email, role=role, is_owner=is_owner)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Log user registration
        ActivityLogger.log(ActivityLogger.USER_REGISTER, user_id=user.id, details=f"Username: {username}, Role: {role}")

        if request.is_json:
            return jsonify({'success': True, 'message': 'Registration successful'})
        flash('Registration successful')
        return redirect(get_safe_endpoint_url('auth.login'))
    return render_template('register.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Force password change for users with weak default passwords."""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
        else:
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
        
        # Verify current password
        if not current_user.check_password(current_password):
            error_msg = 'Current password is incorrect'
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 401
            flash(error_msg)
            return render_template('change_password.html', force_change=current_user.force_password_change)
        
        # Check if new password matches confirmation
        if new_password != confirm_password:
            error_msg = 'New passwords do not match'
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return render_template('change_password.html', force_change=current_user.force_password_change)
        
        # Validate new password strength
        is_valid, error_msg = User.validate_password_strength(new_password)
        if not is_valid:
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg)
            return render_template('change_password.html', force_change=current_user.force_password_change)
        
        # Update password
        current_user.set_password(new_password)
        current_user.force_password_change = False
        db.session.commit()
        
        # Log password change
        ActivityLogger.log(ActivityLogger.USER_LOGIN, user_id=current_user.id,
                         details=f"Password changed: {current_user.username}")
        
        if request.is_json:
            return jsonify({
                'success': True, 
                'message': 'Password changed successfully',
                'redirect': url_for('main.dashboard')
            })
        flash('Password changed successfully', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('change_password.html', force_change=current_user.force_password_change)


@auth_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update current user profile (email)."""
    if not request.is_json:
        return jsonify({'success': False, 'message': 'JSON required'}), 400
    data = request.get_json() or {}
    new_email    = data.get('email', '').strip()
    new_username = data.get('username', '').strip()

    if new_username:
        if not re.match(r'^[A-Za-z0-9_]{3,32}$', new_username):
            return jsonify({'success': False, 'message': 'Username must be 3–32 characters: letters, numbers, underscores only.'}), 400
        existing = User.query.filter(User.username == new_username, User.id != current_user.id).first()
        if existing:
            return jsonify({'success': False, 'message': 'That username is already taken.'}), 409
        current_user.username = new_username
        db.session.commit()
        ActivityLogger.log(ActivityLogger.USER_LOGIN, user_id=current_user.id,
                           details=f"Profile username updated to: {new_username}")
        return jsonify({'success': True, 'message': 'Username updated successfully.'})

    if new_email:
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', new_email):
            return jsonify({'success': False, 'message': 'Invalid email address.'}), 400
        existing = User.query.filter(User.email == new_email, User.id != current_user.id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Email is already in use.'}), 409
        current_user.email = new_email
        db.session.commit()
        ActivityLogger.log(ActivityLogger.USER_LOGIN, user_id=current_user.id,
                           details=f"Profile email updated: {current_user.username}")
        return jsonify({'success': True, 'message': 'Email updated successfully.'})

    return jsonify({'success': False, 'message': 'Nothing to update.'}), 400
