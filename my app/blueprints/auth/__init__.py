# blueprints/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from . import routes
