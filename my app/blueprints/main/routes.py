# blueprints/main/routes.py
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from . import main_bp


@main_bp.route('/')
def home():
    """Homepage - redirect to dashboard if authenticated"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard accessible to all logged-in users"""
    # Only 'admin' and 'manager' roles may edit/control the system
    user_role = getattr(current_user, 'role', 'user')
    can_edit = user_role in ('admin', 'manager')
    return render_template('admin.html', can_edit=can_edit)


@main_bp.route('/forecasting')
@login_required
def forecasting():
    """Forecasting page"""
    user_role = getattr(current_user, 'role', 'user')
    can_edit = user_role in ('admin', 'manager')
    return render_template('forecasting.html', can_edit=can_edit)


@main_bp.route('/products')
@login_required
def products_page():
    """Products page"""
    user_role = getattr(current_user, 'role', 'user')
    can_edit = user_role in ('admin', 'manager')
    return render_template('products.html', can_edit=can_edit)


@main_bp.route('/reports')
@login_required
def reports():
    """Reports page accessible to all logged-in users"""
    from datetime import datetime
    version = datetime.now().timestamp()
    return render_template('reports.html', v=version)


@main_bp.route('/settings')
@login_required
def settings():
    """Settings page accessible to all logged-in users"""
    from datetime import datetime
    version = datetime.now().timestamp()
    return render_template('settings.html', v=version)


@main_bp.route('/websocket-test')
@login_required
def websocket_test():
    """WebSocket test page for real-time features"""
    return render_template('websocket_test.html')


@main_bp.route('/init-db-once', methods=['POST'])
def init_db_once():
    """One-time database initialization endpoint (call once after deployment, then delete)"""
    import os
    from models import db, User
    
    # Security: only allow this in production with a check
    # This endpoint should only be called ONCE and should be deleted after
    
    try:
        # Create tables
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            return {
                'status': 'success',
                'message': 'Database initialized successfully',
                'admin_created': True,
                'username': 'admin',
                'password': 'admin123'
            }, 201
        else:
            return {
                'status': 'success',
                'message': 'Database already initialized',
                'admin_created': False
            }, 200
    except Exception as e:
        db.session.rollback()
        return {
            'status': 'error',
            'message': f'Initialization failed: {str(e)}'
        }, 500

