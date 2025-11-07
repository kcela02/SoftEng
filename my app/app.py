# app.py - Application Factory Pattern
from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_socketio import SocketIO
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
    CORS(app)
    
    # Initialize SocketIO with CORS support
    global socketio
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
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
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin user created (username: admin, password: admin123)")
    
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
