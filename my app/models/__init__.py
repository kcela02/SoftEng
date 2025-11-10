# models/__init__.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    unit_cost = db.Column(db.Float)
    current_stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_fake = db.Column(db.Boolean, default=False)  # Flag for fake data

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_fake = db.Column(db.Boolean, default=False)  # Flag for fake data

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    operation = db.Column(db.String(50))  # 'add', 'remove'
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class InventoryBatch(db.Model):
    """Track inventory batches with FIFO and expiration dates."""
    __tablename__ = 'inventory_batches'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)  # e.g., "BATCH-2025-001"
    quantity = db.Column(db.Integer, nullable=False, default=0)
    original_quantity = db.Column(db.Integer, nullable=False)  # Initial quantity received
    expiration_date = db.Column(db.Date, nullable=False)
    received_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    unit_cost = db.Column(db.Float)  # Cost per unit for this batch
    supplier = db.Column(db.String(255))  # Optional supplier info
    notes = db.Column(db.Text)  # Additional notes
    is_expired = db.Column(db.Boolean, default=False)  # Auto-computed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    product = db.relationship('Product', backref='batches', lazy=True)
    
    # Composite unique constraint - prevent duplicate batch numbers per product
    __table_args__ = (
        db.UniqueConstraint('product_id', 'batch_number', name='_product_batch_uc'),
        db.Index('idx_batch_expiration', 'product_id', 'expiration_date'),
        db.Index('idx_batch_quantity', 'product_id', 'quantity'),
    )
    
    def days_until_expiry(self):
        """Calculate days until expiration."""
        from datetime import date
        if self.expiration_date:
            delta = self.expiration_date - date.today()
            return delta.days
        return None
    
    def is_expiring_soon(self, threshold_days=7):
        """Check if batch is expiring within threshold days."""
        days = self.days_until_expiry()
        return days is not None and 0 <= days <= threshold_days
    
    def urgency_level(self):
        """Get urgency level for expiration."""
        days = self.days_until_expiry()
        if days is None or days < 0:
            return 'EXPIRED'
        elif days <= 3:
            return 'CRITICAL'
        elif days <= 7:
            return 'HIGH'
        elif days <= 14:
            return 'MEDIUM'
        else:
            return 'OK'


class BatchTransaction(db.Model):
    """Track all batch transactions for audit trail."""
    __tablename__ = 'batch_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('inventory_batches.id'), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))  # Link to sale if applicable
    transaction_type = db.Column(db.String(50), nullable=False)  # 'sale', 'adjustment', 'expired', 'received'
    quantity_change = db.Column(db.Integer, nullable=False)  # Negative for deductions, positive for additions
    quantity_before = db.Column(db.Integer, nullable=False)
    quantity_after = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    batch = db.relationship('InventoryBatch', backref='transactions', lazy=True)
    sale = db.relationship('Sale', backref='batch_transactions', lazy=True)
    
    __table_args__ = (
        db.Index('idx_batch_trans', 'batch_id', 'created_at'),
    )


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ImportLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    rows_processed = db.Column(db.Integer, default=0)
    rows_failed = db.Column(db.Integer, default=0)
    rows_skipped = db.Column(db.Integer, default=0)  # NEW: Duplicate records skipped
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(50), default='processing')  # 'success', 'partial', 'failed'
    error_message = db.Column(db.Text)
    validation_errors = db.Column(db.Text)  # NEW: Schema validation errors
    data_type = db.Column(db.String(50))  # 'sales', 'products', 'inventory'

class Forecast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    forecast_date = db.Column(db.DateTime, nullable=False)
    predicted_quantity = db.Column(db.Integer)
    model_used = db.Column(db.String(50))  # 'ARIMA', 'LINEAR_REGRESSION', 'ENSEMBLE'
    accuracy = db.Column(db.Float)
    # Confidence intervals (80% prediction range)
    confidence_lower = db.Column(db.Float)  # Lower bound (10th percentile)
    confidence_upper = db.Column(db.Float)  # Upper bound (90th percentile)
    # Model performance metrics
    mae = db.Column(db.Float)  # Mean Absolute Error
    rmse = db.Column(db.Float)  # Root Mean Squared Error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    generated_at = db.Column(db.Date)  # When this forecast was generated (for backtesting)
    # Aggregation level for synchronized forecasting
    aggregation_level = db.Column(db.String(20))  # 'daily', 'weekly', 'monthly'
    period_key = db.Column(db.String(50))  # '2025-11-02' for daily, '2025-W44' for weekly
    
    __table_args__ = (
        db.Index('idx_forecast_period', 'product_id', 'aggregation_level', 'period_key'),
    )


# New models for architectural enhancements
class UserPreference(db.Model):
    """Store user-specific dashboard settings and preferences."""
    __tablename__ = 'user_preferences'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    preference_key = db.Column(db.String(100), nullable=False)
    preference_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'preference_key', name='_user_pref_uc'),)


class Alert(db.Model):
    """Store alerts for historical tracking and acknowledgment."""
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    alert_type = db.Column(db.String(50))  # 'low_stock', 'forecast_shortage', 'critical'
    severity = db.Column(db.String(20))  # 'CRITICAL', 'WARNING', 'INFO'
    message = db.Column(db.Text)
    recommended_order_qty = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    is_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    acknowledged_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    product = db.relationship('Product', backref='alerts', lazy=True)


class DashboardMetrics(db.Model):
    """Cache computed metrics for improved performance."""
    __tablename__ = 'dashboard_metrics'
    id = db.Column(db.Integer, primary_key=True)
    metric_date = db.Column(db.Date, nullable=False, unique=True)
    total_revenue = db.Column(db.Float, default=0)
    total_units_sold = db.Column(db.Integer, default=0)
    total_orders = db.Column(db.Integer, default=0)
    avg_order_value = db.Column(db.Float, default=0)
    top_product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    active_alerts = db.Column(db.Integer, default=0)
    forecast_accuracy = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WebSocketSession(db.Model):
    """Track active WebSocket connections for real-time features."""
    __tablename__ = 'websocket_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class ForecastSnapshot(db.Model):
    """Store historical forecasts for comparison with actual results."""
    __tablename__ = 'forecast_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    forecast_date = db.Column(db.Date, nullable=False)  # The date being forecasted
    predicted_quantity = db.Column(db.Float, nullable=False)
    actual_quantity = db.Column(db.Float)  # Filled when actual data arrives
    snapshot_created_at = db.Column(db.DateTime, default=datetime.utcnow)  # When forecast was made
    model_used = db.Column(db.String(50))
    forecast_horizon = db.Column(db.String(20))  # '1-day', '7-day', '30-day'
    accuracy = db.Column(db.Float)  # % accuracy (filled when actual arrives)
    error_percentage = db.Column(db.Float)  # Absolute error %
    confidence_lower = db.Column(db.Float)
    confidence_upper = db.Column(db.Float)
    mae = db.Column(db.Float)
    rmse = db.Column(db.Float)
    
    # Relationships
    product = db.relationship('Product', backref='forecast_history', lazy=True)
    
    __table_args__ = (
        db.Index('idx_snapshot_date', 'product_id', 'forecast_date'),
        db.Index('idx_snapshot_created', 'snapshot_created_at'),
    )