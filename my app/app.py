# app.py - Application Factory Pattern
from flask import Flask, jsonify, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config
from models import db, User
import os

# Initialize SocketIO (will be attached to app in create_app)
socketio = None


def create_app(config_name=None):
    """
    Application factory for creating Flask app instances.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
                    If None, uses FLASK_ENV environment variable or defaults to 'development'
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize CSRF Protection
    csrf = CSRFProtect(app)
    
    # Initialize Rate Limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=app.config.get('RATELIMIT_DEFAULTS', ["200 per day", "50 per hour"]),
        storage_uri=app.config.get('RATELIMIT_STORAGE_URI', 'memory://'),
        strategy='fixed-window'
    )
    
    # Store limiter in app for access in blueprints
    app.limiter = limiter
    
    # Initialize CORS with environment-specific allowed origins
    cors_origins = app.config.get('CORS_ORIGINS', [])
    CORS(app, origins=cors_origins, supports_credentials=True)
    
    # Initialize SocketIO with CORS support using same origins
    global socketio
    socketio = SocketIO(app, cors_allowed_origins=cors_origins)
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.index'  # Redirect to index instead of login page
    login_manager.login_message = None  # Disable flash message for cleaner UX
    
    # Custom unauthorized handler for API calls
    @login_manager.unauthorized_handler
    def unauthorized():
        """Return JSON for API requests, redirect for HTML pages."""
        from flask import request
        # Check if this is an API call
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Unauthorized - please log in first'}), 401
        # For non-API requests, redirect to index page with login modal
        return redirect(url_for('main.index'))
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    # Inject git commit hash as a template global so CSS/JS cache busts on every deploy
    import subprocess
    try:
        _ver = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=os.path.dirname(__file__),
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        _ver = str(int(os.getenv('DEPLOY_TS', '1')))
    app.jinja_env.globals['static_ver'] = _ver
    
    # Register WebSocket event handlers
    from websocket_events import register_socketio_events
    register_socketio_events(socketio)
    
    # Create database tables and default admin user
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin123')
            admin.force_password_change = True  # Security: Force password change on first login
            db.session.add(admin)
            db.session.commit()
            print("[SECURITY WARNING] Default admin user created (username: admin, password: admin123)")
            print("[ACTION REQUIRED] Please change the admin password immediately after first login!")
    
    return app


if __name__ == '__main__':
    app = create_app()
    # Get configuration from environment
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.getenv('FLASK_PORT', 5000))
    
    print(f"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║  Predictive Sales & Restocking Dashboard - Flask Server      ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  Environment: {os.getenv('FLASK_ENV', 'development').upper():<48}║
    ║  Server:      http://127.0.0.1:{port:<42}║
    ║  Debug Mode:  {str(debug_mode):<48}║
    ║  Auto-Reload: {'Enabled' if debug_mode else 'Disabled':<48}║
    ║  WebSocket:   Enabled (Socket.IO)                            ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  Login:       admin / admin123                                ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Use socketio.run with auto-reload enabled in debug mode
    # The reloader will automatically restart the server when files change
    socketio.run(app, debug=debug_mode, port=port, use_reloader=debug_mode)
