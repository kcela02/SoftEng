# blueprints/auth/routes.py
from flask import request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from models import db, User
from utils import ActivityLogger
from . import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
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
        if user and user.check_password(password):
            login_user(user)
            
            # Log successful login
            ActivityLogger.log(ActivityLogger.USER_LOGIN, user_id=user.id, details=f"Username: {username}")
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login successful', 'redirect': url_for('main.dashboard')})
            return redirect(url_for('main.dashboard'))
        else:
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
    return redirect(url_for('main.home'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
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
            return redirect(url_for('auth.register'))

        # Prevent privilege escalation: only an already authenticated admin can set roles
        if not (current_user.is_authenticated and getattr(current_user, 'role', None) == 'admin'):
            # Force plain registrations to 'user' role regardless of submitted value
            role = 'user'

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Log user registration
        ActivityLogger.log(ActivityLogger.USER_REGISTER, user_id=user.id, details=f"Username: {username}, Role: {role}")

        if request.is_json:
            return jsonify({'success': True, 'message': 'Registration successful'})
        flash('Registration successful')
        return redirect(url_for('auth.login'))
    return render_template('register.html')
