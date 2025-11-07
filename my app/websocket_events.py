"""
WebSocket event handlers for real-time features.
Handles Socket.IO connections, disconnections, and broadcasts.
"""
from flask import request
from flask_socketio import emit, disconnect
from flask_login import current_user
from models import db, WebSocketSession, DashboardMetrics, Alert, Product, Sale
from utils import ActivityLogger
from datetime import datetime
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


def register_socketio_events(socketio):
    """
    Register all WebSocket event handlers with the SocketIO instance.
    
    Args:
        socketio: Flask-SocketIO instance
    """
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        try:
            if current_user.is_authenticated:
                # Create WebSocket session record
                session = WebSocketSession(
                    user_id=current_user.id,
                    session_id=request.sid,
                    is_active=True
                )
                db.session.add(session)
                db.session.commit()
                
                logger.info(f"User {current_user.username} connected (session: {request.sid})")
                
                # Send initial metrics to the newly connected client
                metrics = get_current_metrics()
                emit('metrics_update', metrics)
                
                # Send active alerts
                alerts = get_active_alerts()
                emit('alerts_update', alerts)
                
                return True
            else:
                logger.warning(f"Unauthorized connection attempt (session: {request.sid})")
                disconnect()
                return False
        except Exception as e:
            logger.error(f"Error in connect handler: {str(e)}")
            return False
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        try:
            # Mark session as inactive
            session = WebSocketSession.query.filter_by(
                session_id=request.sid,
                is_active=True
            ).first()
            
            if session:
                session.is_active = False
                session.last_activity = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"User disconnected (session: {request.sid})")
        except Exception as e:
            logger.error(f"Error in disconnect handler: {str(e)}")
    
    @socketio.on('request_metrics')
    def handle_metrics_request():
        """Handle manual metrics request from client."""
        try:
            if current_user.is_authenticated:
                metrics = get_current_metrics()
                emit('metrics_update', metrics)
        except Exception as e:
            logger.error(f"Error in metrics request handler: {str(e)}")
            emit('error', {'message': 'Failed to fetch metrics'})
    
    @socketio.on('acknowledge_alert')
    def handle_alert_acknowledgment(data):
        """Handle alert acknowledgment from client."""
        try:
            if current_user.is_authenticated:
                alert_id = data.get('alert_id')
                alert = Alert.query.get(alert_id)
                
                if alert:
                    # Get product info before acknowledging for logging
                    product = Product.query.get(alert.product_id)
                    product_name = product.name if product else f"Product ID {alert.product_id}"
                    
                    alert.is_acknowledged = True
                    alert.acknowledged_by = current_user.id
                    alert.acknowledged_at = datetime.utcnow()
                    db.session.commit()
                    
                    # Log the alert acknowledgment
                    ActivityLogger.log(
                        ActivityLogger.ALERT_ACKNOWLEDGE,
                        details=f"{product_name} - {alert.message}"
                    )
                    
                    # Broadcast updated alert status to all clients
                    socketio.emit('alert_acknowledged', {
                        'alert_id': alert_id,
                        'acknowledged_by': current_user.username
                    })
                    
                    logger.info(f"Alert {alert_id} acknowledged by {current_user.username}")
        except Exception as e:
            logger.error(f"Error in alert acknowledgment handler: {str(e)}")
            emit('error', {'message': 'Failed to acknowledge alert'})


def get_current_metrics():
    """
    Calculate and return current dashboard metrics.
    
    Returns:
        dict: Current metrics including revenue, units sold, accuracy, alerts
    """
    try:
        from datetime import datetime, timedelta
        
        # Calculate last 7 days metrics
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # Total revenue (last 7 days) = sum(quantity * price)
        total_revenue = db.session.query(
            func.coalesce(func.sum(Sale.quantity * Sale.price), 0.0)
        ).filter(Sale.sale_date >= seven_days_ago).scalar() or 0.0
        
        # Total units sold (last 7 days)
        total_units = db.session.query(
            func.coalesce(func.sum(Sale.quantity), 0)
        ).filter(Sale.sale_date >= seven_days_ago).scalar() or 0
        
        # Number of active alerts
        active_alerts_count = Alert.query.filter_by(
            is_active=True,
            is_acknowledged=False
        ).count()
        
        # Critical alerts count
        critical_alerts_count = Alert.query.filter_by(
            is_active=True,
            is_acknowledged=False,
            severity='CRITICAL'
        ).count()
        
        # Average order value
        avg_order_value = total_revenue / total_units if total_units > 0 else 0
        
        # Number of products with low stock (threshold: 15 units)
        low_stock_products = db.session.query(func.count(Product.id)).filter(
            (Product.current_stock != None) & (Product.current_stock <= 15)
        ).scalar() or 0
        
        return {
            'total_revenue': float(total_revenue),
            'total_units_sold': int(total_units),
            'active_alerts': int(active_alerts_count),
            'critical_alerts': int(critical_alerts_count),
            'avg_order_value': float(avg_order_value),
            'low_stock_products': int(low_stock_products),
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error calculating metrics: {str(e)}")
        return {}


def get_active_alerts():
    """
    Get all active, unacknowledged alerts.
    
    Returns:
        list: Active alerts with product information
    """
    try:
        alerts = Alert.query.filter_by(
            is_active=True,
            is_acknowledged=False
        ).order_by(Alert.created_at.desc()).limit(10).all()
        
        return [{
            'id': alert.id,
            'product_id': alert.product_id,
            'product_name': alert.product.name if alert.product else 'Unknown',
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'message': alert.message,
            'recommended_order_qty': alert.recommended_order_qty,
            'created_at': alert.created_at.isoformat()
        } for alert in alerts]
    except Exception as e:
        logger.error(f"Error fetching alerts: {str(e)}")
        return []


def broadcast_metrics_update(socketio):
    """
    Broadcast metrics update to all connected clients.
    Call this function when data changes (new sale, inventory update, etc.)
    
    Args:
        socketio: Flask-SocketIO instance
    """
    try:
        metrics = get_current_metrics()
        socketio.emit('metrics_update', metrics, broadcast=True)
        logger.info("Broadcasted metrics update to all clients")
    except Exception as e:
        logger.error(f"Error broadcasting metrics: {str(e)}")


def broadcast_new_alert(socketio, alert):
    """
    Broadcast new alert to all connected clients.
    
    Args:
        socketio: Flask-SocketIO instance
        alert: Alert model instance
    """
    try:
        alert_data = {
            'id': alert.id,
            'product_id': alert.product_id,
            'product_name': alert.product.name if alert.product else 'Unknown',
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'message': alert.message,
            'recommended_order_qty': alert.recommended_order_qty,
            'created_at': alert.created_at.isoformat()
        }
        
        socketio.emit('new_alert', alert_data, broadcast=True)
        logger.info(f"Broadcasted new alert: {alert.message}")
    except Exception as e:
        logger.error(f"Error broadcasting alert: {str(e)}")


def broadcast_import_progress(socketio, progress_data):
    """
    Broadcast CSV import progress to all connected clients.
    
    Args:
        socketio: Flask-SocketIO instance
        progress_data: dict with keys: step, total_steps, message, percentage
    """
    try:
        socketio.emit('import_progress', progress_data, broadcast=True)
        logger.info(f"Broadcasted import progress: {progress_data['message']}")
    except Exception as e:
        logger.error(f"Error broadcasting import progress: {str(e)}")
