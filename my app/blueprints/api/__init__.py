# blueprints/api/__init__.py
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

from . import routes

# Register sub-blueprints
from .preferences import preferences_bp
api_bp.register_blueprint(preferences_bp)
