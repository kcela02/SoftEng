# app.py - Application Factory Pattern
from dotenv import load_dotenv
load_dotenv(override=True)  # Load .env before anything reads os.environ

from flask import Flask, jsonify, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config
from models import db, User
import os


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
    # Trust one level of reverse proxy (Render, nginx). This makes
    # request.remote_addr and request.url reflect the real client values.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)

    # JWT for mobile API
    JWTManager(app)
    
    # Gzip compress HTML/JSON/CSS responses (big win on slow connections)
    from flask_compress import Compress
    Compress(app)
    
    # Initialize CSRF Protection
    csrf = CSRFProtect(app)
    
    # Initialize Rate Limiter
    # ProxyFix (above) already unwraps X-Forwarded-For into request.remote_addr,
    # so get_remote_address now returns each real client's IP instead of the
    # shared Render proxy IP.
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
    from blueprints.mobile import mobile_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(mobile_bp)
    # Exempt mobile API from CSRF — mobile apps use JWT tokens, not browser cookies
    csrf.exempt(mobile_bp)
    # Exempt mobile API from IP-based rate limiting — mobile clients make many
    # burst requests on startup (pagination, dashboard, forecasts) from the same
    # IP and hit the default limit fast.  JWT auth already protects these endpoints.
    limiter.exempt(mobile_bp)
    
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
    
    # Create database tables and default admin user
    with app.app_context():
        db.create_all()
        
        # Auto-migrate missing columns
        try:
            from sqlalchemy import text
            engine = db.engine
            db_type = engine.dialect.name
            
            # Add used_for_training column to sale table if missing
            try:
                if db_type == 'postgresql':
                    db.session.execute(text("""
                        DO $$ 
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.columns 
                                WHERE table_name = 'sale' 
                                AND column_name = 'used_for_training'
                            ) THEN
                                ALTER TABLE sale ADD COLUMN used_for_training BOOLEAN DEFAULT 0;
                            END IF;
                        END $$;
                    """))
                else:
                    # SQLite
                    result = db.session.execute(text("PRAGMA table_info(sale)"))
                    columns = [row[1] for row in result]
                    if 'used_for_training' not in columns:
                        db.session.execute(text(
                            "ALTER TABLE sale ADD COLUMN used_for_training BOOLEAN DEFAULT 0"
                        ))
                db.session.commit()
                print("[OK] Database schema up to date")
            except Exception as e:
                print(f"[OK] Schema check: {e}")
                db.session.rollback()
        except Exception as e:
            print(f"[OK] Auto-migration skipped: {e}")
        
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
    ╠═══════════════════════════════════════════════════════════════╣
    ║  Login:       admin / admin123                                ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Run Flask development server with auto-reload
        # Only run the development server if not in production
    if __name__ == "__main__":
            app.run(debug=debug_mode, port=port, use_reloader=debug_mode)