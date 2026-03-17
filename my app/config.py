# config.py
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-for-dev'
    
    # Database Configuration (PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://softeng2_db_user:ZpQr8FErKxXR412nZOMTBbKhTv7lF0LL@dpg-d6n73675gffc73bsk9f0-a/softeng2_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    
    # Security Settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # CSRF tokens don't expire (adjust if needed)
    WTF_CSRF_SSL_STRICT = False  # Set to True in production with HTTPS
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']  # Methods that require CSRF
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']  # Header names to check
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULTS = ["200 per day", "50 per hour"]
    RATELIMIT_STORAGE_URI = "memory://"  # Use Redis in production for distributed systems
    
    # Password Policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = False  # Optional: require special characters
    
    # Session Settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # Sessions expire after 8 hours of inactivity

    # Forecasting Settings
    DEFAULT_FORECAST_DAYS = 7
    ACCURACY_THRESHOLD = 0.80 # Target accuracy for top 10 sellers
    RESTOCK_THRESHOLD_DAYS = 7 # Stock must cover at least this many days of forecast
    
    # Pagination
    ITEMS_PER_PAGE = 50
    
    # Upload Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv', 'zip'}

    # JWT Settings (for mobile API)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-dev-secret-change-in-prod'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    # Higher rate limits for local development/testing
    RATELIMIT_DEFAULTS = ["2000 per day", "500 per hour"]

    # Fix for older Render connection strings in local .env files
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)
    
    # CORS Configuration - Allow localhost and local network for development and mobile testing
    CORS_ORIGINS = [
        "http://localhost:5000",
        "http://localhost:3000",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:3000",
        # Regex patterns for local network IPs (192.168.x.x, 10.x.x.x) for mobile testing
        r"http://192\.168\.\d{1,3}\.\d{1,3}:\d+",
        r"http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+"
    ]


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # Override with secure settings – validated lazily so importing this
    # module in development mode doesn't raise errors.
    SECRET_KEY = os.environ.get('SECRET_KEY', '')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '')
    
    # Keep DB connections alive; recycle before Render's idle timeout
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    
    # CORS Configuration - Only allow your Render deployment and optional frontend
    CORS_ORIGINS = [
        "https://vapecrib.onrender.com",
        os.environ.get('FRONTEND_URL', 'https://vapecrib.onrender.com')
    ]

    # Fix for Render: Replace postgres:// with postgresql://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    @classmethod
    def init_app(cls, app):
        """Validate required env vars when actually used in production."""
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable must be set in production")
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise ValueError("DATABASE_URL environment variable must be set in production")
    
    # Security settings
    WTF_CSRF_SSL_STRICT = True  # Enforce HTTPS for CSRF
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']  # Methods that require CSRF
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']  # Header names to check
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Rate Limiting - Use Redis for distributed rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get('REDIS_URL', 'memory://')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory SQLite is fine for unit tests
    SQLALCHEMY_ENGINE_OPTIONS = {}  # Disable pool options for in-memory SQLite
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}