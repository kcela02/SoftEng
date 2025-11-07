# utils/activity_logger.py
"""
Centralized activity logging utility for tracking user actions across the application.
This provides a consistent interface for logging all user activities to the database.
"""

from models import db, Log
from flask_login import current_user
from datetime import datetime


class ActivityLogger:
    """Centralized logging utility for user activities."""
    
    # Activity type constants
    USER_LOGIN = "User login"
    USER_LOGOUT = "User logout"
    USER_REGISTER = "User registration"
    
    PRODUCT_CREATE = "Product created"
    PRODUCT_UPDATE = "Product updated"
    PRODUCT_DELETE = "Product deleted"
    
    INVENTORY_ADJUST = "Inventory adjusted"
    INVENTORY_ADD = "Stock added"
    INVENTORY_REMOVE = "Stock removed"
    
    CSV_UPLOAD_SALES = "CSV uploaded: Sales"
    CSV_UPLOAD_PRODUCTS = "CSV uploaded: Products"
    CSV_UPLOAD_INVENTORY = "CSV uploaded: Inventory"
    CSV_UPLOAD_FAILED = "CSV upload failed"
    
    FORECAST_GENERATE = "Forecast generated"
    FORECAST_VIEW = "Forecast viewed"
    
    ALERT_ACKNOWLEDGE = "Alert acknowledged"
    ALERT_TRIGGER = "Low stock alert triggered"
    
    SETTINGS_UPDATE = "Settings updated"
    PREFERENCE_UPDATE = "Preferences updated"
    
    @staticmethod
    def log(action: str, user_id: int = None, details: str = None):
        """
        Log an activity to the database.
        
        Args:
            action (str): The action being performed (use class constants)
            user_id (int, optional): ID of the user performing the action. 
                                    Defaults to current_user if authenticated.
            details (str, optional): Additional details about the action
        
        Returns:
            Log: The created log entry
        """
        try:
            # Use current user if not specified
            if user_id is None and current_user and current_user.is_authenticated:
                user_id = current_user.id
            
            # Build action string with details if provided
            full_action = action
            if details:
                full_action = f"{action}: {details}"
            
            # Create log entry
            log_entry = Log(
                user_id=user_id,
                action=full_action,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
            return log_entry
            
        except Exception as e:
            print(f"[ActivityLogger] Error logging activity: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def log_product_action(action_type: str, product_name: str, details: str = None):
        """Helper for logging product-related actions."""
        action = f"{action_type}: {product_name}"
        if details:
            action = f"{action} ({details})"
        return ActivityLogger.log(action)
    
    @staticmethod
    def log_csv_upload(file_type: str, filename: str, rows_processed: int, 
                       rows_skipped: int = 0, rows_failed: int = 0):
        """Helper for logging CSV upload activities."""
        details = f"{filename} - {rows_processed} rows processed"
        if rows_skipped > 0:
            details += f", {rows_skipped} skipped"
        if rows_failed > 0:
            details += f", {rows_failed} failed"
        
        action_map = {
            'sales': ActivityLogger.CSV_UPLOAD_SALES,
            'products': ActivityLogger.CSV_UPLOAD_PRODUCTS,
            'inventory': ActivityLogger.CSV_UPLOAD_INVENTORY
        }
        
        action = action_map.get(file_type, f"CSV uploaded: {file_type}")
        return ActivityLogger.log(action, details=details)
    
    @staticmethod
    def log_inventory_adjustment(product_name: str, operation: str, quantity: int, reason: str = None):
        """Helper for logging inventory adjustments."""
        action = ActivityLogger.INVENTORY_ADJUST
        details = f"{product_name}: {operation} {quantity} units"
        if reason:
            details += f" - {reason}"
        return ActivityLogger.log(action, details=details)
    
    @staticmethod
    def log_forecast(product_name: str, forecast_date: str, quantity: int):
        """Helper for logging forecast generation."""
        details = f"{product_name} for {forecast_date}: {quantity} units"
        return ActivityLogger.log(ActivityLogger.FORECAST_GENERATE, details=details)
