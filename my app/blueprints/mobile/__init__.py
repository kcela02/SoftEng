# blueprints/mobile/__init__.py
from flask import Blueprint

mobile_bp = Blueprint('mobile', __name__, url_prefix='/api/mobile')

from . import routes
