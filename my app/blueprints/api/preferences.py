"""
API routes for user preferences management.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, UserPreference
from datetime import datetime
from utils.activity_logger import ActivityLogger

preferences_bp = Blueprint('preferences', __name__, url_prefix='/api/preferences')


@preferences_bp.route('/', methods=['GET'])
@login_required
def get_all_preferences():
    """Get all preferences for the current user."""
    preferences = UserPreference.query.filter_by(user_id=current_user.id).all()
    
    # Convert to dictionary for easier frontend consumption
    prefs_dict = {
        pref.preference_key: pref.preference_value 
        for pref in preferences
    }
    
    return jsonify(prefs_dict), 200


@preferences_bp.route('/<key>', methods=['GET'])
@login_required
def get_preference(key):
    """Get a specific preference by key."""
    preference = UserPreference.query.filter_by(
        user_id=current_user.id,
        preference_key=key
    ).first()
    
    if not preference:
        return jsonify({'error': 'Preference not found'}), 404
    
    return jsonify({
        'key': preference.preference_key,
        'value': preference.preference_value
    }), 200


@preferences_bp.route('/', methods=['POST'])
@login_required
def set_preferences():
    """Set multiple preferences at once."""
    data = request.get_json()
    
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid request data'}), 400
    
    try:
        updated_count = 0
        for key, value in data.items():
            # Check if preference exists
            preference = UserPreference.query.filter_by(
                user_id=current_user.id,
                preference_key=key
            ).first()
            
            if preference:
                # Update existing
                preference.preference_value = str(value)
                preference.updated_at = datetime.utcnow()
            else:
                # Create new
                preference = UserPreference(
                    user_id=current_user.id,
                    preference_key=key,
                    preference_value=str(value)
                )
                db.session.add(preference)
            updated_count += 1
        
        db.session.commit()
        
        # Log the settings update
        ActivityLogger.log(
            action_type=ActivityLogger.SETTINGS,
            user_id=current_user.id,
            action=f'Updated {updated_count} preferences',
            details=', '.join([f'{k}={v}' for k, v in data.items()])
        )
        
        return jsonify({'message': 'Preferences updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@preferences_bp.route('/<key>', methods=['PUT'])
@login_required
def update_preference(key):
    """Update a specific preference."""
    data = request.get_json()
    
    if not data or 'value' not in data:
        return jsonify({'error': 'Missing value in request'}), 400
    
    try:
        preference = UserPreference.query.filter_by(
            user_id=current_user.id,
            preference_key=key
        ).first()
        
        if preference:
            preference.preference_value = str(data['value'])
            preference.updated_at = datetime.utcnow()
        else:
            preference = UserPreference(
                user_id=current_user.id,
                preference_key=key,
                preference_value=str(data['value'])
            )
            db.session.add(preference)
        
        db.session.commit()
        return jsonify({'message': f'Preference {key} updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@preferences_bp.route('/<key>', methods=['DELETE'])
@login_required
def delete_preference(key):
    """Delete a specific preference."""
    preference = UserPreference.query.filter_by(
        user_id=current_user.id,
        preference_key=key
    ).first()
    
    if not preference:
        return jsonify({'error': 'Preference not found'}), 404
    
    try:
        db.session.delete(preference)
        db.session.commit()
        return jsonify({'message': f'Preference {key} deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Common preference keys and their expected values
PREFERENCE_SCHEMA = {
    'default_forecast_days': '7|14|30',  # Default number of days for forecasting
    'chart_theme': 'light|dark',  # Chart theme preference
    'default_tab': 'overview|forecasting|products|reports|settings',  # Default dashboard tab
    'items_per_page': '10|25|50|100',  # Items per page in tables
    'alert_notifications': 'true|false',  # Enable/disable alert notifications
    'auto_refresh': 'true|false',  # Auto-refresh dashboard
    'refresh_interval': '30|60|120',  # Refresh interval in seconds
}


@preferences_bp.route('/schema', methods=['GET'])
def get_preference_schema():
    """Get the preference schema for frontend validation."""
    return jsonify(PREFERENCE_SCHEMA), 200
