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
