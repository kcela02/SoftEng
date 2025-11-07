# blueprints/__init__.py
"""
Blueprints package for modular Flask application structure.

This package contains separate blueprint modules for:
- auth: Authentication routes (login, logout, register)
- main: Main page routes (home, dashboard, reports, settings)
- api: REST API endpoints for data operations
"""

from .auth import auth_bp
from .main import main_bp
from .api import api_bp

__all__ = ['auth_bp', 'main_bp', 'api_bp']
