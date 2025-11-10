# blueprints/api/routes.py
from flask import request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, User, Product, Sale, Inventory, Log, Forecast, ImportLog, Alert, ForecastSnapshot
from models.regression import forecast_linear_regression
from utils import ActivityLogger
from utils.model_trainer import ForecastingPipeline
from datetime import datetime, timedelta
from sqlalchemy import func
import pandas as pd
import csv
import io
from . import api_bp


def trigger_metrics_broadcast():
    """Trigger a WebSocket broadcast of updated metrics."""
    try:
        from app import socketio
        from websocket_events import broadcast_metrics_update
        if socketio:
            broadcast_metrics_update(socketio)
    except Exception as e:
        # Silently fail if WebSocket not available
        pass


def check_low_stock_and_alert(product: Product):
    """Create intelligent restock alerts using multi-horizon forecasts (1-day, 7-day, 30-day).
    
    Urgency Levels:
    - CRITICAL: Stock < 1-day forecast (immediate action needed)
    - HIGH: Stock < 7-day forecast (order this week)
    - MEDIUM: Stock < 30-day forecast (plan ahead)
    
    Recommends order quantities with 20% safety margin.
    Avoids duplicates if an active, unacknowledged alert already exists.
    """
    try:
        from utils.model_trainer import ForecastingPipeline
        
        if product is None or product.current_stock is None:
            return
        
        # Get multi-horizon forecasts
        forecast_1day = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=1)
        forecast_7day = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=7)
        forecast_30day = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=30)
        
        # Determine urgency level and recommended order quantity
        severity = None
        message = None
        recommended_qty = None
        alert_type = 'forecast_shortage'
        
        current_stock = product.current_stock
        
        # CRITICAL: Stock insufficient for next day's demand
        if forecast_1day and current_stock < forecast_1day:
            severity = 'CRITICAL'
            shortage = forecast_1day - current_stock
            recommended_qty = int(forecast_7day * 1.2) if forecast_7day else int(shortage * 1.5)
            message = (
                f"🔴 CRITICAL: {product.name} stock ({current_stock}) below 1-day demand ({forecast_1day:.0f}). "
                f"Shortage: {shortage:.0f} units. Recommend ordering {recommended_qty} units immediately."
            )
        
        # HIGH: Stock insufficient for next 7 days
        elif forecast_7day and current_stock < forecast_7day:
            severity = 'HIGH'
            shortage = forecast_7day - current_stock
            recommended_qty = int(forecast_7day * 1.2) if forecast_7day else int(shortage * 1.5)
            message = (
                f"🟡 HIGH: {product.name} stock ({current_stock}) below 7-day demand ({forecast_7day:.0f}). "
                f"Shortage: {shortage:.0f} units. Recommend ordering {recommended_qty} units this week."
            )
        
        # MEDIUM: Stock insufficient for next 30 days
        elif forecast_30day and current_stock < forecast_30day:
            severity = 'MEDIUM'
            shortage = forecast_30day - current_stock
            recommended_qty = int(forecast_30day * 1.2) if forecast_30day else int(shortage * 1.5)
            message = (
                f"🟢 MEDIUM: {product.name} stock ({current_stock}) below 30-day demand ({forecast_30day:.0f}). "
                f"Shortage: {shortage:.0f} units. Recommend ordering {recommended_qty} units this month."
            )
        
        # No alert needed - stock is sufficient
        if severity is None:
            return
        
        # Check for existing active alert for this product
        existing = Alert.query.filter_by(
            product_id=product.id,
            alert_type=alert_type,
            is_active=True,
            is_acknowledged=False
        ).first()
        
        if existing:
            # Update if severity worsened or message changed significantly
            severity_levels = {'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}
            existing_level = severity_levels.get(existing.severity, 0)
            new_level = severity_levels.get(severity, 0)
            
            if new_level > existing_level:
                existing.severity = severity
                existing.message = message
                existing.recommended_order_qty = recommended_qty
                db.session.commit()
            return
        
        # Create new alert
        new_alert = Alert(
            product_id=product.id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            recommended_order_qty=recommended_qty,
            is_active=True,
            is_acknowledged=False,
        )
        db.session.add(new_alert)
        db.session.commit()
        
        # Broadcast to clients
        try:
            from app import socketio
            from websocket_events import broadcast_new_alert
            if socketio:
                broadcast_new_alert(socketio, new_alert)
        except Exception:
            pass
            
    except Exception as e:
        print(f"Error in check_low_stock_and_alert: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        # do not raise to avoid breaking the main flow


@api_bp.route('/metrics', methods=['GET'])
@login_required
def get_metrics():
    """Get comprehensive dashboard metrics from database with period comparisons and filtering."""
    today = datetime.now()
    
    # Get period parameter (7d, 30d, 3m, 6m, 1y, all, or custom)
    period = request.args.get('period', '7d')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Calculate date range based on period
    if start_date_str and end_date_str:
        # Custom date range
        try:
            from datetime import datetime as dt
            filter_start = dt.strptime(start_date_str, '%Y-%m-%d')
            filter_end = dt.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)  # Include end date
        except ValueError:
            filter_start = today - timedelta(days=6)
            filter_end = today + timedelta(days=1)
    else:
        # Preset period
        period_map = {
            '7d': 7,
            '30d': 30,
            '3m': 90,
            '6m': 180,
            '1y': 365,
            'all': None
        }
        days = period_map.get(period, 7)
        
        if days is None:
            # All time - no filter
            filter_start = None
            filter_end = None
        else:
            filter_start = today - timedelta(days=days-1)
            filter_end = today + timedelta(days=1)
    
    # Build base query with period filter
    def apply_date_filter(query, date_column):
        if filter_start and filter_end:
            return query.filter(date_column >= filter_start, date_column < filter_end)
        return query
    
    # Calculate total revenue (filtered by period)
    revenue_query = db.session.query(db.func.sum(Sale.quantity * Sale.price))
    revenue_query = apply_date_filter(revenue_query, Sale.sale_date)
    total_revenue = revenue_query.scalar() or 0
    
    # Calculate total units sold (filtered by period)
    units_query = db.session.query(db.func.sum(Sale.quantity))
    units_query = apply_date_filter(units_query, Sale.sale_date)
    total_units_sold = units_query.scalar() or 0
    
    # Count total products
    total_products = db.session.query(db.func.count(Product.id)).scalar() or 0
    
    # Count total inventory
    total_inventory = db.session.query(db.func.sum(Product.current_stock)).scalar() or 0
    
    # Calculate total inventory value (stock × unit cost)
    total_inventory_value = db.session.query(
        db.func.sum(Product.current_stock * Product.unit_cost)
    ).scalar() or 0
    
    # Check if dataset contains fake data
    fake_sales_count = Sale.query.filter_by(is_fake=True).count()
    has_fake_data = fake_sales_count > 0
    
    # Calculate forecast accuracy from ForecastSnapshot table with actual values
    from models import ForecastSnapshot
    snapshots_with_actual = db.session.query(ForecastSnapshot).filter(
        ForecastSnapshot.actual_quantity.isnot(None)
    )
    
    # Apply date filter to snapshots if specified
    if filter_start and filter_end:
        snapshots_with_actual = snapshots_with_actual.filter(
            ForecastSnapshot.forecast_date >= filter_start.date(),
            ForecastSnapshot.forecast_date < filter_end.date()
        )
    
    snapshots_with_actual = snapshots_with_actual.all()
    
    if len(snapshots_with_actual) > 0:
        # Calculate MAPE (Mean Absolute Percentage Error)
        errors = []
        for snapshot in snapshots_with_actual:
            if snapshot.actual_quantity and snapshot.actual_quantity > 0:
                error = abs(snapshot.predicted_quantity - snapshot.actual_quantity) / snapshot.actual_quantity
                errors.append(error)
        
        if errors:
            mape = sum(errors) / len(errors)
            accuracy = max(0, (1 - mape) * 100)  # Convert to accuracy percentage
        else:
            accuracy = 0.0
    else:
        accuracy = 0.0
    
    # Count active alerts (CRITICAL + HIGH severity only)
    alerts = Alert.query.filter(
        Alert.is_active == True,
        Alert.is_acknowledged == False,
        Alert.severity.in_(['CRITICAL', 'HIGH'])
    ).count()
    
    # Period comparison calculations (current 7 days vs previous 7 days)
    seven_days_ago = today - timedelta(days=6)
    fourteen_days_ago = today - timedelta(days=13)
    
    # Current period revenue (last 7 days)
    current_revenue = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
        Sale.sale_date >= seven_days_ago
    ).scalar() or 0
    
    # Previous period revenue (7-14 days ago)
    previous_revenue = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
        Sale.sale_date >= fourteen_days_ago,
        Sale.sale_date < seven_days_ago
    ).scalar() or 0
    
    # Current period units (last 7 days)
    current_units = db.session.query(db.func.sum(Sale.quantity)).filter(
        Sale.sale_date >= seven_days_ago
    ).scalar() or 0
    
    # Previous period units (7-14 days ago)
    previous_units = db.session.query(db.func.sum(Sale.quantity)).filter(
        Sale.sale_date >= fourteen_days_ago,
        Sale.sale_date < seven_days_ago
    ).scalar() or 0
    
    # Calculate percentage changes (only if previous period has data)
    revenue_change = None
    if previous_revenue > 0:
        revenue_change = ((current_revenue - previous_revenue) / previous_revenue) * 100
    
    units_change = None
    if previous_units > 0:
        units_change = ((current_units - previous_units) / previous_units) * 100
    
    # Get daily data for date range (for dashboard trend chart)
    # If custom date range, use that; otherwise use current month
    if filter_start and filter_end:
        chart_start = filter_start
        chart_end = filter_end - timedelta(days=1)  # Exclude the extra day added for filter
    else:
        chart_start = today.replace(day=1)
        chart_end = today
    
    # Calculate number of days in the range
    num_days = (chart_end - chart_start).days + 1
    
    monthly_daily_sales = []  # Actual sales for each day
    monthly_daily_forecasts = []  # Forecasted revenue for each day
    monthly_daily_labels = []  # Date labels
    
    # Get actual sales and forecasts for each day in the range
    for day_offset in range(num_days):
        date = chart_start + timedelta(days=day_offset)
        
        # Create label
        monthly_daily_labels.append(date.strftime('%m/%d'))
        
        # Get actual sales revenue (only if date has passed)
        if date.date() <= today.date():
            day_revenue = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
                db.func.date(Sale.sale_date) == date.date()
            ).scalar() or 0
            monthly_daily_sales.append(float(day_revenue))
        else:
            monthly_daily_sales.append(None)  # No actual sales for future days
        
        # Get forecast revenue (for all days that have forecasts)
        # Get average price from recent sales and multiply by forecast quantity
        avg_price_query = db.session.query(
            db.func.avg(Sale.price)
        ).filter(
            Sale.sale_date >= chart_start
        ).scalar() or 10.0  # Default price if no sales data
        
        day_forecast_quantity = db.session.query(
            db.func.sum(Forecast.predicted_quantity)
        ).filter(
            db.func.date(Forecast.forecast_date) == date.date(),
            Forecast.aggregation_level == 'daily'
        ).scalar()
        
        if day_forecast_quantity and day_forecast_quantity > 0:
            day_forecast_revenue = day_forecast_quantity * avg_price_query
            monthly_daily_forecasts.append(float(day_forecast_revenue))
        else:
            monthly_daily_forecasts.append(None)  # No forecast available for this day
    
    # Get last 7 days of sales data for backwards compatibility
    daily_sales = []
    daily_forecasts = []
    chart_labels = []
    
    # Get past 7 days for actual sales
    seven_days_ago = today - timedelta(days=6)
    for i in range(7):
        date = seven_days_ago + timedelta(days=i)
        day_sales = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
            db.func.date(Sale.sale_date) == date.date()
        ).scalar() or 0
        daily_sales.append(float(day_sales))
        chart_labels.append(date.strftime('%m/%d'))
    
    # Get next 7 days for forecasts (future dates)
    today = datetime.now().date()
    for i in range(7):
        future_date = today + timedelta(days=i+1)
        day_forecast = db.session.query(db.func.sum(Forecast.predicted_quantity)).filter(
            db.func.date(Forecast.forecast_date) == future_date
        ).scalar() or 0
        daily_forecasts.append(float(day_forecast))
    
    # Get monthly data - respect date filter if set, otherwise show last 6 months
    monthly_labels = []
    monthly_data = []
    
    if filter_start and filter_end:
        # Group by month within the filtered date range
        from sqlalchemy import extract
        results = db.session.query(
            extract('year', Sale.sale_date).label('year'),
            extract('month', Sale.sale_date).label('month'),
            db.func.sum(Sale.quantity * Sale.price).label('revenue')
        ).filter(
            Sale.sale_date >= filter_start,
            Sale.sale_date < filter_end
        ).group_by('year', 'month').order_by('year', 'month').all()
        
        for year, month, revenue in results:
            month_date = datetime(int(year), int(month), 1)
            monthly_labels.append(month_date.strftime('%b %Y'))
            monthly_data.append(float(revenue or 0))
    else:
        # Default: last 6 months
        for i in range(5, -1, -1):
            month_date = today - timedelta(days=30*i)
            month_sales = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
                db.func.strftime('%Y-%m', Sale.sale_date) == month_date.strftime('%Y-%m')
            ).scalar() or 0
            monthly_labels.append(month_date.strftime('%b'))
            monthly_data.append(float(month_sales))
    
    # Month-over-Month Comparison (DYNAMIC: same day range)
    # Today is Nov 10, so compare Nov 1-10 vs Oct 1-10
    current_month_start = today.replace(day=1)
    current_day_of_month = today.day  # e.g., 10 for Nov 10
    
    # Last month calculation
    if current_month_start.month == 1:
        last_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
    else:
        last_month_start = current_month_start.replace(month=current_month_start.month - 1)
    
    # Calculate the end date for last month comparison (same day of month)
    # If current day doesn't exist in last month (e.g., Jan 31 -> Feb 31), use last day of that month
    try:
        last_month_end = last_month_start.replace(day=current_day_of_month)
    except ValueError:
        # Day doesn't exist in that month, use last day of the month
        if last_month_start.month == 12:
            last_month_end = last_month_start.replace(year=last_month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_month_end = last_month_start.replace(month=last_month_start.month + 1, day=1) - timedelta(days=1)
    
    # Current month revenue (from start of month to today)
    current_month_revenue = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
        Sale.sale_date >= current_month_start,
        Sale.sale_date <= today
    ).scalar() or 0
    
    # Last month revenue (same day range)
    last_month_revenue = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
        Sale.sale_date >= last_month_start,
        Sale.sale_date <= last_month_end
    ).scalar() or 0
    
    # Current month units (from start of month to today)
    current_month_units = db.session.query(db.func.sum(Sale.quantity)).filter(
        Sale.sale_date >= current_month_start,
        Sale.sale_date <= today
    ).scalar() or 0
    
    # Last month units (same day range)
    last_month_units = db.session.query(db.func.sum(Sale.quantity)).filter(
        Sale.sale_date >= last_month_start,
        Sale.sale_date <= last_month_end
    ).scalar() or 0
    
    # Calculate month-over-month percentage changes
    month_revenue_change = None
    if last_month_revenue > 0:
        month_revenue_change = ((current_month_revenue - last_month_revenue) / last_month_revenue) * 100
    
    month_units_change = None
    if last_month_units > 0:
        month_units_change = ((current_month_units - last_month_units) / last_month_units) * 100
    
    # Year-over-Year Comparison (DYNAMIC: same day range last year)
    # Today is Nov 10, 2025, so compare Nov 1-10, 2025 vs Nov 1-10, 2024
    year_ago_month_start = current_month_start.replace(year=current_month_start.year - 1)
    
    # Calculate the end date for last year comparison (same day of current month)
    try:
        year_ago_end = year_ago_month_start.replace(day=current_day_of_month)
    except ValueError:
        # Day doesn't exist in that month (e.g., leap year issue)
        if year_ago_month_start.month == 12:
            year_ago_end = year_ago_month_start.replace(year=year_ago_month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            year_ago_end = year_ago_month_start.replace(month=year_ago_month_start.month + 1, day=1) - timedelta(days=1)
    
    # Same period last year revenue
    year_ago_revenue = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
        Sale.sale_date >= year_ago_month_start,
        Sale.sale_date <= year_ago_end
    ).scalar() or 0
    
    # Same period last year units
    year_ago_units = db.session.query(db.func.sum(Sale.quantity)).filter(
        Sale.sale_date >= year_ago_month_start,
        Sale.sale_date <= year_ago_end
    ).scalar() or 0
    
    # Calculate year-over-year percentage changes
    year_revenue_change = None
    if year_ago_revenue > 0:
        year_revenue_change = ((current_month_revenue - year_ago_revenue) / year_ago_revenue) * 100
    
    year_units_change = None
    if year_ago_units > 0:
        year_units_change = ((current_month_units - year_ago_units) / year_ago_units) * 100
    
    # Inventory turnover (simple: revenue / inventory value) guarded against division by zero
    turnover_rate = 0.0
    if total_inventory_value and total_inventory_value > 0:
        try:
            turnover_rate = float(total_revenue) / float(total_inventory_value)
        except Exception:
            turnover_rate = 0.0

    return jsonify({
        'total_revenue': float(total_revenue),
        'total_units_sold': int(total_units_sold),
        'total_products': total_products,
        'total_inventory': total_inventory,
        'total_inventory_value': float(total_inventory_value),
        'has_fake_data': has_fake_data,
        'fake_sales_count': int(fake_sales_count),
        'accuracy': round(accuracy, 1),  # Return as number, not string with %
        'alerts': alerts,
        'turnover_rate': round(turnover_rate, 2),
        
        # 7-day period comparison (existing)
        'revenue_change': round(revenue_change, 1) if revenue_change is not None else None,
        'units_change': round(units_change, 1) if units_change is not None else None,
        
        # Month-over-Month comparison (NEW)
        'current_month_revenue': float(current_month_revenue),
        'last_month_revenue': float(last_month_revenue),
        'current_month_units': int(current_month_units),
        'last_month_units': int(last_month_units),
        'month_revenue_change': round(month_revenue_change, 1) if month_revenue_change is not None else None,
        'month_units_change': round(month_units_change, 1) if month_units_change is not None else None,
        
        # Year-over-Year comparison (NEW)
        'year_ago_revenue': float(year_ago_revenue),
        'year_ago_units': int(year_ago_units),
        'year_revenue_change': round(year_revenue_change, 1) if year_revenue_change is not None else None,
        'year_units_change': round(year_units_change, 1) if year_units_change is not None else None,
        
        # Chart data (backwards compatibility - last 7 days)
        'daily_sales': daily_sales,
        'daily_forecasts': daily_forecasts,
        'chart_labels': chart_labels,
        
        # Monthly chart data (current month daily breakdown)
        'monthly_daily_sales': monthly_daily_sales,
        'monthly_daily_forecasts': monthly_daily_forecasts,
        'monthly_daily_labels': monthly_daily_labels,
        
        # Monthly aggregated data (last 6 months)
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data
    })


@api_bp.route('/upload-sales', methods=['POST'])
def upload_sales_data():
    """Endpoint for manual CSV upload."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file type. Must be CSV."}), 400
        
    try:
        df = pd.read_csv(file)
        return jsonify({"message": f"Successfully processed and stored {len(df)} sales records."})
    except Exception as e:
        return jsonify({"error": f"Data processing error: {str(e)}"}), 500


@api_bp.route('/forecast/<int:product_id>', methods=['GET'])
@login_required
def get_product_forecast(product_id):
    """Generates and returns the 7-day sales forecast for a product."""
    from flask import current_app
    
    # Check if product exists
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": f"Product {product_id} not found"}), 404
    
    # Check if we have enough historical sales data
    sales_count = Sale.query.filter_by(product_id=product_id).count()
    if sales_count < 2:
        return jsonify({
            "error": f"Insufficient sales data for product {product_id}. Need at least 2 sales records.",
            "product_id": product_id,
            "product_name": product.name,
            "sales_count": sales_count
        }), 400
    
    try:
        # Use linear regression model with actual database connection
        forecast_data = forecast_linear_regression(None, product_id, 
                                                   days_ahead=current_app.config['DEFAULT_FORECAST_DAYS'])
        
        if 'error' in forecast_data:
            return jsonify(forecast_data), 404
            
        return jsonify({
            "product_id": product_id,
            "product_name": product.name,
            "model": "Linear Regression",
            "forecast": forecast_data
        })
    except Exception as e:
        return jsonify({
            "error": f"Error generating forecast: {str(e)}",
            "product_id": product_id
        }), 500


@api_bp.route('/restock-alerts', methods=['GET'])
@login_required
def get_restocking_recommendations():
    """Checks stock vs. forecast and generates proactive alerts based on real product data."""
    alerts = []
    
    # Get all products from database
    products = Product.query.all()
    
    for product in products:
        current_stock = product.current_stock
        
        # Calculate 7-day projected demand from forecasts
        today = datetime.now()
        seven_days_later = today + timedelta(days=7)
        
        # Get forecasts for the next 7 days
        forecasts = Forecast.query.filter(
            Forecast.product_id == product.id,
            Forecast.forecast_date >= today,
            Forecast.forecast_date <= seven_days_later
        ).all()
        
        if not forecasts:
            # If no forecasts exist, check if stock is critically low
            if current_stock < 10:
                alerts.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_stock": current_stock,
                    "demand_7d": 0,
                    "status": "WARNING",
                    "recommendation": f"Low stock detected. No forecast available. Consider restocking.",
                    "forecast": []
                })
            continue
        
        # Sum up projected demand
        projected_demand_7d = sum(f.predicted_quantity for f in forecasts)
        
        # Check against the restock threshold
        if current_stock < projected_demand_7d:
            # Calculate recommended order quantity
            shortage = projected_demand_7d - current_stock
            order_quantity = max(0, int(shortage * 1.2))
            
            status = "CRITICAL" if current_stock < (projected_demand_7d * 0.5) else "WARNING"
            
            alerts.append({
                "product_id": product.id,
                "product_name": product.name,
                "current_stock": current_stock,
                "demand_7d": round(projected_demand_7d, 2),
                "status": status,
                "recommendation": f"Order {order_quantity} units. Stock shortage expected.",
                "forecast": [
                    {
                        "date": f.forecast_date.strftime('%Y-%m-%d'),
                        "prediction": round(f.predicted_quantity, 2)
                    } for f in forecasts
                ]
            })
    
    return jsonify(alerts)


@api_bp.route('/reports/turnover', methods=['GET'])
@login_required
def get_inventory_turnover_report():
    """Generates and returns a report on inventory turnover and forecast accuracy from real data."""
    products = Product.query.all()
    report_data = {
        "report_type": "Inventory & Accuracy",
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "products": []
    }
    
    for product in products:
        # Calculate inventory turnover
        total_sales = db.session.query(db.func.sum(Sale.quantity * Sale.price)).filter(
            Sale.product_id == product.id
        ).scalar() or 0
        
        # Average inventory
        avg_inventory_value = product.current_stock * product.unit_cost if product.unit_cost else 0
        
        turnover = (total_sales / avg_inventory_value) if avg_inventory_value > 0 else 0.0
        
        # Calculate forecast accuracy for this product
        forecasts_with_actuals = db.session.query(Forecast).filter(
            Forecast.product_id == product.id,
            Forecast.forecast_date <= datetime.now()
        ).all()
        
        accuracy = 0.0
        if forecasts_with_actuals:
            total_error = 0
            count = 0
            for forecast in forecasts_with_actuals:
                # Get actual sales for the forecast date
                actual = db.session.query(db.func.sum(Sale.quantity)).filter(
                    Sale.product_id == product.id,
                    db.func.date(Sale.sale_date) == forecast.forecast_date.date()
                ).scalar() or 0
                
                if actual > 0:
                    error = abs(forecast.predicted_quantity - actual) / actual
                    total_error += error
                    count += 1
            
            if count > 0:
                mape = total_error / count
                accuracy = max(0, 1 - mape)
        
        report_data["products"].append({
            "product_id": product.id,
            "product_name": product.name,
            "turnover": round(turnover, 2),
            "accuracy": round(accuracy, 2),
            "current_stock": product.current_stock,
            "total_sales": round(total_sales, 2)
        })
    
    report_data["description"] = f"Report on sales performance, inventory turnover, and forecasting accuracy for {len(products)} products."
    
    return jsonify(report_data)


@api_bp.route('/export-alerts', methods=['GET'])
@login_required
def export_alerts_csv():
    """Admin/Manager only: Export restock alerts as CSV."""
    user_role = getattr(current_user, 'role', 'user')
    if user_role not in ('admin', 'manager'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Fetch alerts data
    alerts_data = get_restocking_recommendations().get_json()
    
    # Convert to CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product ID', 'Current Stock', 'Demand (7d)', 'Status', 'Recommendation'])
    
    for alert in alerts_data:
        writer.writerow([
            alert['product_id'],
            alert['current_stock'],
            alert['demand_7d'],
            alert['status'],
            alert['recommendation']
        ])
    
    output.seek(0)
    mem_file = io.BytesIO(output.getvalue().encode())
    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@api_bp.route('/export-report', methods=['GET'])
@login_required
def export_report():
    """Admin/Manager only: Export inventory turnover report as CSV."""
    user_role = getattr(current_user, 'role', 'user')
    if user_role not in ('admin', 'manager'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Fetch report data
    report_data = get_inventory_turnover_report().get_json()
    
    # Convert to CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product ID', 'Turnover Ratio', 'Forecast Accuracy'])
    
    for product_info in report_data.get('products', []):
        writer.writerow([
            product_info['product_id'],
            product_info['turnover'],
            product_info['accuracy']
        ])
    
    output.seek(0)
    mem_file = io.BytesIO(output.getvalue().encode())
    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@api_bp.route('/download-all-data', methods=['GET'])
@login_required
def download_all_data():
    """Download all dashboard data as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Create CSV with all dashboard data
    writer.writerow(['Dashboard Data Export', '', ''])
    writer.writerow(['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ''])
    writer.writerow([''])
    
    # Add metrics
    writer.writerow(['Metric', 'Value', ''])
    total_sales = db.session.query(db.func.sum(Sale.quantity * Sale.price)).scalar() or 0
    writer.writerow(['Total Sales', f'{total_sales:.2f}', ''])
    
    total_sales_count = db.session.query(db.func.count(Sale.id)).scalar() or 0
    writer.writerow(['Total Orders', total_sales_count, ''])
    
    total_products = db.session.query(db.func.count(Product.id)).scalar() or 0
    writer.writerow(['Total Products', total_products, ''])
    
    total_inventory = db.session.query(db.func.sum(Product.current_stock)).scalar() or 0
    writer.writerow(['Total Inventory', total_inventory, ''])
    writer.writerow([''])
    
    # Add products list
    writer.writerow(['Products', '', ''])
    writer.writerow(['Product ID', 'Name', 'Current Stock', 'Category'])
    products = Product.query.all()
    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.current_stock,
            product.category or 'N/A'
        ])
    writer.writerow([''])
    
    # Add recent sales
    writer.writerow(['Recent Sales', '', ''])
    writer.writerow(['Date', 'Product', 'Quantity', 'Price', 'Total'])
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(50).all()
    for sale in recent_sales:
        product = Product.query.get(sale.product_id)
        writer.writerow([
            sale.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            product.name if product else f'Product {sale.product_id}',
            sale.quantity,
            f'{sale.price:.2f}',
            f'{sale.quantity * sale.price:.2f}'
        ])
    
    output.seek(0)
    mem_file = io.BytesIO(output.getvalue().encode())
    return send_file(
        mem_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'dashboard_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@api_bp.route('/upload-csv', methods=['POST'])
@login_required
def upload_csv_file():
    """Admin/Manager only: Upload and process CSV file (sales, products, or inventory)."""
    user_role = getattr(current_user, 'role', 'user')
    if user_role not in ('admin', 'manager'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    data_type = request.form.get('data_type', 'sales')
    
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
        
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files allowed'}), 400
    
    # Schema definitions for validation
    SCHEMA_DEFINITIONS = {
        'sales': {
            'required': ['product_id', 'quantity', 'price'],
            'optional': ['sale_date'],
            'friendly_names': {
                'product_id': 'Product ID',
                'quantity': 'Quantity',
                'price': 'Price',
                'sale_date': 'Sale Date'
            }
        },
        'products': {
            'required': ['name'],
            'optional': ['category', 'unit_cost', 'current_stock'],
            'friendly_names': {
                'name': 'Product Name',
                'category': 'Category',
                'unit_cost': 'Unit Cost',
                'current_stock': 'Current Stock'
            }
        },
        'inventory': {
            'required': ['product_id', 'quantity'],
            'optional': ['operation', 'date'],
            'friendly_names': {
                'product_id': 'Product ID',
                'quantity': 'Quantity',
                'operation': 'Operation',
                'date': 'Date'
            }
        }
        ,
        # Unified sales CSV: recommended single-file format containing product, sale and optional inventory info
        'unified_sales': {
            'required': ['product_name', 'quantity_sold', 'sale_price'],
            'optional': ['category', 'unit_cost', 'sale_date', 'stock_after_sale'],
            'friendly_names': {
                'product_name': 'Product Name',
                'quantity_sold': 'Quantity Sold',
                'sale_price': 'Sale Price',
                'category': 'Category',
                'unit_cost': 'Unit Cost',
                'sale_date': 'Sale Date',
                'stock_after_sale': 'Stock After Sale'
            }
        }
    }
    
    # Create import log entry
    import_log = ImportLog(
        filename=file.filename,
        user_id=current_user.id,
        data_type=data_type,
        status='processing'
    )
    db.session.add(import_log)
    db.session.commit()
    
    try:
        # Read CSV
        df = pd.read_csv(file)
        
        # Validate schema
        schema = SCHEMA_DEFINITIONS.get(data_type)
        if not schema:
            raise ValueError(f"Unknown data type: {data_type}")
        
        # Check required columns
        missing_cols = [col for col in schema['required'] if col not in df.columns]
        if missing_cols:
            friendly_missing = [schema['friendly_names'].get(col, col) for col in missing_cols]
            error_msg = f"Missing required columns: {', '.join(friendly_missing)}"
            import_log.status = 'failed'
            import_log.validation_errors = error_msg
            db.session.commit()
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Check for unexpected columns (optional - can be relaxed)
        expected_cols = schema['required'] + schema['optional']
        unexpected_cols = [col for col in df.columns if col not in expected_cols]
        if unexpected_cols:
            warning_msg = f"Note: Unexpected columns will be ignored: {', '.join(unexpected_cols)}"
            # We'll still process but log the warning
        
        rows_processed = 0
        rows_failed = 0
        rows_skipped = 0
        errors = []
        
        # Auto-wipe fake data on first real import
        try:
            fake_sales_existing = Sale.query.filter_by(is_fake=True).count()
            fake_products_existing = Product.query.filter_by(is_fake=True).count()
            if fake_sales_existing > 0 or fake_products_existing > 0:
                # Only wipe if the uploaded data is not explicitly flagged as fake (we treat admin uploads as real)
                Sale.query.filter_by(is_fake=True).delete()
                Product.query.filter_by(is_fake=True).delete()
                db.session.commit()
                # Log the wipe
                log_entry = Log(
                    user_id=current_user.id,
                    action=f"Auto-wiped fake data before import: {fake_sales_existing} sales, {fake_products_existing} products"
                )
                db.session.add(log_entry)
                db.session.commit()
        except Exception as _:
            db.session.rollback()
        
        if data_type == 'sales':
            for idx, row in df.iterrows():
                try:
                    product_id = int(row['product_id'])
                    quantity = int(row['quantity'])
                    price = float(row['price'])
                    sale_date = pd.to_datetime(row['sale_date']) if 'sale_date' in row and pd.notna(row['sale_date']) else datetime.now()
                    
                    # Check for duplicate (same product_id + sale_date)
                    existing_sale = Sale.query.filter_by(
                        product_id=product_id,
                        sale_date=sale_date
                    ).first()
                    
                    if existing_sale:
                        rows_skipped += 1
                        continue  # Skip duplicate
                    
                    # Create new sale record
                    sale = Sale(
                        product_id=product_id,
                        quantity=quantity,
                        price=price,
                        sale_date=sale_date,
                        user_id=current_user.id
                    )
                    db.session.add(sale)
                    rows_processed += 1
                    
                except Exception as e:
                    rows_failed += 1
                    errors.append(f"Row {idx + 2}: {str(e)}")
                    
        elif data_type == 'products':
            for idx, row in df.iterrows():
                try:
                    product_name = str(row['name']).strip()
                    
                    # Check for duplicate product name
                    existing_product = Product.query.filter_by(name=product_name).first()
                    
                    if existing_product:
                        rows_skipped += 1
                        continue  # Skip duplicate
                    
                    # Create new product
                    product = Product(
                        name=product_name,
                        category=str(row['category']).strip() if 'category' in row and pd.notna(row['category']) else None,
                        unit_cost=float(row['unit_cost']) if 'unit_cost' in row and pd.notna(row['unit_cost']) else 0.0,
                        current_stock=int(row['current_stock']) if 'current_stock' in row and pd.notna(row['current_stock']) else 0
                    )
                    db.session.add(product)
                    rows_processed += 1
                    
                except Exception as e:
                    rows_failed += 1
                    errors.append(f"Row {idx + 2}: {str(e)}")
                    
        elif data_type == 'inventory':
            for idx, row in df.iterrows():
                try:
                    product_id = int(row['product_id'])
                    quantity = int(row['quantity'])
                    operation = str(row['operation']).lower() if 'operation' in row and pd.notna(row['operation']) else 'add'
                    inv_date = pd.to_datetime(row['date']) if 'date' in row and pd.notna(row['date']) else datetime.now()
                    
                    # Check for duplicate inventory record (same product + date + quantity + operation)
                    existing_inv = Inventory.query.filter_by(
                        product_id=product_id,
                        quantity=quantity,
                        operation=operation,
                        date=inv_date
                    ).first()
                    
                    if existing_inv:
                        rows_skipped += 1
                        continue  # Skip duplicate
                    
                    # Create inventory record
                    inventory = Inventory(
                        product_id=product_id,
                        quantity=quantity,
                        operation=operation,
                        date=inv_date,
                        user_id=current_user.id
                    )
                    db.session.add(inventory)
                    
                    # Update product stock
                    product = Product.query.get(product_id)
                    if product:
                        if operation == 'add':
                            product.current_stock += quantity
                        else:
                            product.current_stock -= quantity
                    
                    rows_processed += 1
                    
                except Exception as e:
                    rows_failed += 1
                    errors.append(f"Row {idx + 2}: {str(e)}")
        
        elif data_type == 'unified_sales':
            for idx, row in df.iterrows():
                try:
                    product_name = str(row['product_name']).strip()

                    # Find or create product by name
                    product = Product.query.filter_by(name=product_name).first()
                    if not product:
                        product = Product(
                            name=product_name,
                            category=str(row['category']).strip() if 'category' in row and pd.notna(row['category']) else None,
                            unit_cost=float(row['unit_cost']) if 'unit_cost' in row and pd.notna(row['unit_cost']) else 0.0,
                            current_stock=int(row['stock_after_sale']) if 'stock_after_sale' in row and pd.notna(row['stock_after_sale']) else 0
                        )
                        db.session.add(product)
                        db.session.flush()  # ensure product.id is available

                    # Parse sale fields
                    quantity = int(row['quantity_sold'])
                    price = float(row['sale_price'])
                    sale_date = pd.to_datetime(row['sale_date']) if 'sale_date' in row and pd.notna(row['sale_date']) else datetime.now()

                    # Check for duplicate sale (same product + sale_date)
                    existing_sale = Sale.query.filter_by(
                        product_id=product.id,
                        sale_date=sale_date
                    ).first()
                    if existing_sale:
                        rows_skipped += 1
                        continue

                    # Create sale record
                    sale = Sale(
                        product_id=product.id,
                        quantity=quantity,
                        price=price,
                        sale_date=sale_date,
                        user_id=current_user.id
                    )
                    db.session.add(sale)

                    # If stock_after_sale provided, set product stock to that value; otherwise, decrement by quantity
                    if 'stock_after_sale' in row and pd.notna(row['stock_after_sale']):
                        try:
                            new_stock = int(row['stock_after_sale'])
                            product.current_stock = new_stock
                        except Exception:
                            # fallback to decrement
                            product.current_stock = max(0, (product.current_stock or 0) - quantity)
                    else:
                        product.current_stock = max(0, (product.current_stock or 0) - quantity)

                    rows_processed += 1
                except Exception as e:
                    rows_failed += 1
                    errors.append(f"Row {idx + 2}: {str(e)}")

        # Commit all changes
        db.session.commit()
        
        # Update import log
        import_log.rows_processed = rows_processed
        import_log.rows_failed = rows_failed
        import_log.rows_skipped = rows_skipped
        import_log.status = 'success' if rows_failed == 0 else ('partial' if rows_processed > 0 else 'failed')
        if errors:
            import_log.error_message = '\n'.join(errors[:10])
        db.session.commit()
        
        # ==================== UPDATE FORECAST SNAPSHOTS WITH ACTUALS ====================
        # Update forecast snapshots with actual sales data when new sales arrive
        if data_type in ('sales', 'unified_sales') and rows_processed > 0:
            try:
                # Get all new sales from this import
                new_sales = Sale.query.filter(
                    Sale.user_id == current_user.id
                ).order_by(Sale.sale_date.desc()).limit(rows_processed).all()
                
                for sale in new_sales:
                    sale_date = sale.sale_date.date() if isinstance(sale.sale_date, datetime) else sale.sale_date
                    ForecastingPipeline.update_snapshot_with_actual(
                        product_id=sale.product_id,
                        sale_date=sale_date,
                        actual_qty=sale.quantity
                    )
            except Exception as e:
                print(f"Warning: Snapshot update failed: {str(e)}")
        
        # ==================== AUTOMATED FORECASTING PIPELINE ====================
        # Auto-regenerate forecasts if sales data was imported
        retraining_stats = {'retrained': 0, 'skipped': 0, 'failed': 0}
        daily_forecast_count = 0
        weekly_forecast_count = 0
        rolling_created = 0
        newly_forecasted_products = []
        
        if data_type in ('sales', 'unified_sales') and rows_processed > 0:
            try:
                # Get ALL products with sales data and check which ones have sufficient data
                products_with_sales = db.session.query(Product).join(
                    Sale, Product.id == Sale.product_id
                ).distinct().all()
                
                print(f"[CSV Upload] Checking {len(products_with_sales)} products for forecast eligibility...")
                
                for product in products_with_sales:
                    # Check if product has enough sales data (minimum 7 days)
                    sales_count = Sale.query.filter_by(product_id=product.id).count()
                    
                    if sales_count < 7:
                        print(f"[CSV Upload] Product {product.id} ({product.name}): {sales_count} sales - SKIPPED (need 7+)")
                        retraining_stats['skipped'] += 1
                        continue
                    
                    # Check if this product already has future forecasts
                    existing_forecasts = Forecast.query.filter(
                        Forecast.product_id == product.id,
                        Forecast.forecast_date > datetime.now()
                    ).count()
                    
                    try:
                        # Generate multi-horizon forecasts for this product
                        success = ForecastingPipeline.generate_multi_horizon_forecasts(
                            product.id,
                            horizons=[1, 7, 30]
                        )
                        
                        if success:
                            retraining_stats['retrained'] += 1
                            if existing_forecasts == 0:
                                # This is a newly forecasted product
                                newly_forecasted_products.append(product.name)
                            print(f"[CSV Upload] Product {product.id} ({product.name}): Forecasts generated ✓")
                        else:
                            retraining_stats['failed'] += 1
                            print(f"[CSV Upload] Product {product.id} ({product.name}): Failed to generate forecasts")
                    except Exception as e:
                        retraining_stats['failed'] += 1
                        print(f"[CSV Upload] Product {product.id} ({product.name}): Error - {str(e)}")
                
                # Count generated forecasts
                from models import Forecast
                today = datetime.now().date()
                daily_forecast_count = Forecast.query.filter(
                    Forecast.aggregation_level == 'daily',
                    Forecast.forecast_date > today
                ).count()
                weekly_forecast_count = Forecast.query.filter(
                    Forecast.aggregation_level == 'weekly',
                    Forecast.forecast_date > today
                ).count()

                # NEW: Foundation-based rolling retrain to backfill historical forecasts and enable accuracy
                print("[CSV Upload] Starting rolling retrain for historical forecasts (this may take several minutes)...")
                try:
                    # Determine up_to from uploaded data if sale_date available
                    new_max_date = None
                    if 'sale_date' in df.columns and pd.notna(df['sale_date']).any():
                        try:
                            new_max_date = pd.to_datetime(df['sale_date']).max()
                        except Exception:
                            new_max_date = None
                    if new_max_date is None:
                        new_max_date = datetime.now()

                    rolling_created = ForecastingPipeline.rolling_retrain_all_products(
                        foundation_days_large=365,
                        foundation_days_small=90,
                        horizon_days=30,
                        step_days=1,
                        up_to=new_max_date,
                    )
                    print(f"[CSV Upload] Rolling retrain completed: {rolling_created} historical forecasts created")
                except Exception as e:
                    print(f"[CSV Upload] Rolling retrain failed: {str(e)}")
                    # non-critical
                    pass
                
            except Exception as e:
                import traceback
                print(f"Warning: Forecast generation failed: {str(e)}")
                print(traceback.format_exc())
        
        # Trigger metrics update
        trigger_metrics_broadcast()
        
        # Log CSV upload activity using centralized logger
        ActivityLogger.log_csv_upload(
            data_type,
            file.filename,
            rows_processed,
            rows_skipped,
            rows_failed
        )
        
        # Build success message
        message = f'Import completed: {rows_processed} rows added'
        if retraining_stats['retrained'] > 0:
            message += f", {retraining_stats['retrained']} products forecasted"
        if retraining_stats['skipped'] > 0:
            message += f" ({retraining_stats['skipped']} skipped - need more data)"
        if daily_forecast_count > 0:
            message += f", {daily_forecast_count} total daily forecasts"
        if weekly_forecast_count > 0:
            message += f", {weekly_forecast_count} total weekly forecasts"
        if rolling_created > 0:
            message += f", {rolling_created} rolling forecasts backfilled"
        if newly_forecasted_products:
            message += f"\n✨ NEW products now being forecasted: {', '.join(newly_forecasted_products)}"
        
        return jsonify({
            'success': True,
            'message': message,
            'summary': {
                'total_rows': len(df),
                'processed': rows_processed,
                'failed': rows_failed,
                'skipped': rows_skipped,
                'duplicates_found': rows_skipped,
                'new_records': rows_processed,
                'forecasts_regenerated': retraining_stats['retrained'],
                'forecasts_skipped': retraining_stats['skipped'],
                'forecasts_failed': retraining_stats['failed']
            },
            'import_id': import_log.id,
            'status': import_log.status,
            'errors': errors[:5] if errors else None
        })
        
    except Exception as e:
        db.session.rollback()
        import_log.status = 'failed'
        import_log.error_message = str(e)
        import_log.rows_failed = len(df) if 'df' in locals() else 0
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': f'Error processing CSV: {str(e)}'
        }), 400


@api_bp.route('/list-imports', methods=['GET'])
@login_required
def list_imports():
    """Get list of previously imported CSV files."""
    # Get limit parameter from query string
    limit_param = request.args.get('limit', '50')
    
    # Build query
    query = ImportLog.query.order_by(ImportLog.upload_date.desc())
    
    # Apply limit if not 'all'
    if limit_param != 'all':
        try:
            limit = int(limit_param)
            query = query.limit(limit)
        except ValueError:
            # Default to 50 if invalid
            query = query.limit(50)
    
    imports = query.all()
    
    import_list = []
    for imp in imports:
        user = User.query.get(imp.user_id) if imp.user_id else None
        import_list.append({
            'id': imp.id,
            'filename': imp.filename,
            'upload_date': imp.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
            'rows_processed': imp.rows_processed,
            'rows_failed': imp.rows_failed,
            'rows_skipped': imp.rows_skipped or 0,  # NEW: Include skipped count
            'status': imp.status,
            'data_type': imp.data_type,
            'username': user.username if user else 'Unknown',
            'error_message': imp.error_message,
            'validation_errors': imp.validation_errors  # NEW: Include validation errors
        })
    
    return jsonify({
        'success': True,
        'imports': import_list,
        'total': len(import_list)
    })


@api_bp.route('/products', methods=['GET'])
@login_required
def get_products():
    """Get all products with optional filtering."""
    category = request.args.get('category')
    search = request.args.get('search')
    with_forecasts = request.args.get('with_forecasts', 'false').lower() == 'true'
    
    query = Product.query
    
    if category:
        query = query.filter(Product.category == category)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    # If with_forecasts is true, only return products that have forecasts
    if with_forecasts:
        # Get product IDs that have forecasts
        today = datetime.now().date()
        product_ids_with_forecasts = db.session.query(Forecast.product_id).filter(
            Forecast.forecast_date > today
        ).distinct().all()
        
        product_ids = [pid[0] for pid in product_ids_with_forecasts]
        
        if product_ids:
            query = query.filter(Product.id.in_(product_ids))
        else:
            # No products with forecasts
            return jsonify({
                'success': True,
                'products': [],
                'total': 0,
                'message': 'No products with forecast data'
            })
    
    products = query.all()
    
    product_list = []
    for product in products:
        product_list.append({
            'id': product.id,
            'name': product.name,
            'category': product.category,
            'unit_cost': product.unit_cost,
            'current_stock': product.current_stock,
            'created_at': product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else None
        })
    
    return jsonify({
        'success': True,
        'products': product_list,
        'total': len(product_list)
    })


@api_bp.route('/products', methods=['POST'])
@login_required
def create_product():
    """Admin/Manager only: Create a new product."""
    user_role = getattr(current_user, 'role', 'user')
    if user_role not in ('admin', 'manager'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Product name is required'}), 400
    
    try:
        product = Product(
            name=data['name'],
            category=data.get('category'),
            unit_cost=float(data.get('unit_cost', 0)),
            current_stock=int(data.get('current_stock', 0))
        )
        db.session.add(product)
        db.session.commit()
        
        # Log activity using centralized logger
        ActivityLogger.log_product_action(
            ActivityLogger.PRODUCT_CREATE, 
            product.name, 
            f"ID: {product.id}, Category: {product.category or 'N/A'}, Stock: {product.current_stock}"
        )

        # WebSocket: metrics update
        trigger_metrics_broadcast()
        
        return jsonify({
            'success': True,
            'message': 'Product created successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'unit_cost': product.unit_cost,
                'current_stock': product.current_stock
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating product: {str(e)}'}), 400


@api_bp.route('/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    """Admin/Manager only: Update a product."""
    user_role = getattr(current_user, 'role', 'user')
    if user_role not in ('admin', 'manager'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    data = request.get_json()
    
    try:
        # Track changes for logging
        changes = []
        if 'name' in data and data['name'] != product.name:
            changes.append(f"name: {product.name} → {data['name']}")
            product.name = data['name']
        if 'category' in data and data['category'] != product.category:
            changes.append(f"category: {product.category} → {data['category']}")
            product.category = data['category']
        if 'unit_cost' in data:
            new_cost = float(data['unit_cost'])
            if new_cost != product.unit_cost:
                changes.append(f"unit_cost: ₱{product.unit_cost} → ₱{new_cost}")
                product.unit_cost = new_cost
        if 'current_stock' in data:
            new_stock = int(data['current_stock'])
            if new_stock != product.current_stock:
                changes.append(f"stock: {product.current_stock} → {new_stock}")
                product.current_stock = new_stock
        
        db.session.commit()
        
        # Log activity with detailed changes
        if changes:
            ActivityLogger.log_product_action(
                ActivityLogger.PRODUCT_UPDATE,
                product.name,
                ", ".join(changes)
            )

        # Alerts + WebSocket
        if 'current_stock' in data:
            check_low_stock_and_alert(product)
        trigger_metrics_broadcast()
        
        return jsonify({
            'success': True,
            'message': 'Product updated successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'unit_cost': product.unit_cost,
                'current_stock': product.current_stock
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error updating product: {str(e)}'}), 400


@api_bp.route('/products/<int:product_id>/sales-count', methods=['GET'])
@login_required
def get_product_sales_count(product_id):
    """Get the count of sales records for a product."""
    try:
        count = Sale.query.filter_by(product_id=product_id).count()
        return jsonify({
            'success': True,
            'count': count
        })
    except Exception as e:
        return jsonify({'error': f'Error getting sales count: {str(e)}'}), 400


@api_bp.route('/products/<int:product_id>', methods=['GET'])
@login_required
def get_product_by_id(product_id):
    """Get a single product by ID."""
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify({
        'success': True,
        'product': {
            'id': product.id,
            'name': product.name,
            'category': product.category,
            'unit_cost': float(product.unit_cost) if product.unit_cost else 0,
            'current_stock': product.current_stock
        }
    })


@api_bp.route('/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    """Admin/Manager only: Delete a product."""
    user_role = getattr(current_user, 'role', 'user')
    if user_role not in ('admin', 'manager'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    try:
        product_name = product.name
        product_category = product.category
        
        # Delete related records first to avoid foreign key constraint errors
        # Delete alerts related to this product
        Alert.query.filter_by(product_id=product_id).delete()
        
        # Delete forecasts related to this product
        Forecast.query.filter_by(product_id=product_id).delete()
        
        # Delete forecast snapshots related to this product
        ForecastSnapshot.query.filter_by(product_id=product_id).delete()
        
        # Delete inventory records related to this product
        Inventory.query.filter_by(product_id=product_id).delete()
        
        # Delete sales records related to this product
        Sale.query.filter_by(product_id=product_id).delete()
        
        # Now delete the product itself
        db.session.delete(product)
        db.session.commit()
        
        # Log activity with product details
        ActivityLogger.log_product_action(
            ActivityLogger.PRODUCT_DELETE,
            product_name,
            f"ID: {product_id}, Category: {product_category or 'N/A'}"
        )

        # WebSocket: metrics update
        trigger_metrics_broadcast()
        
        return jsonify({
            'success': True,
            'message': f'Product {product_name} deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error deleting product: {str(e)}'}), 400


@api_bp.route('/inventory/adjust', methods=['POST'])
@login_required
def adjust_inventory():
    """Admin/Manager only: Adjust inventory (add or remove stock)."""
    user_role = getattr(current_user, 'role', 'user')
    if user_role not in ('admin', 'manager'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data.get('product_id') or not data.get('quantity'):
        return jsonify({'error': 'product_id and quantity are required'}), 400
    
    product_id = int(data['product_id'])
    quantity = int(data['quantity'])
    operation = data.get('operation', 'add')
    reason = data.get('reason', '')  # Optional reason for the adjustment
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    try:
        # Create inventory record
        inventory = Inventory(
            product_id=product_id,
            quantity=abs(quantity),
            operation=operation,
            user_id=current_user.id
        )
        db.session.add(inventory)
        
        # Update product stock
        if operation == 'add':
            product.current_stock += abs(quantity)
        else:
            product.current_stock -= abs(quantity)
            if product.current_stock < 0:
                product.current_stock = 0
        
        db.session.commit()
        
        # Log activity using centralized logger
        ActivityLogger.log_inventory_adjustment(
            product.name,
            operation,
            abs(quantity),
            reason
        )
        
        # Alerts + WebSocket
        if operation == 'remove':
            check_low_stock_and_alert(product)
        trigger_metrics_broadcast()

        return jsonify({
            'success': True,
            'message': f'Inventory adjusted successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'current_stock': product.current_stock
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error adjusting inventory: {str(e)}'}), 400


@api_bp.route('/inventory/history', methods=['GET'])
@login_required
def get_inventory_history():
    """Get inventory adjustment history."""
    product_id = request.args.get('product_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    
    query = Inventory.query
    
    if product_id:
        query = query.filter(Inventory.product_id == product_id)
    
    history = query.order_by(Inventory.date.desc()).limit(limit).all()
    
    history_list = []
    for item in history:
        product = Product.query.get(item.product_id)
        user = User.query.get(item.user_id) if item.user_id else None
        
        history_list.append({
            'id': item.id,
            'product_id': item.product_id,
            'product_name': product.name if product else 'Unknown',
            'quantity': item.quantity,
            'operation': item.operation,
            'date': item.date.strftime('%Y-%m-%d %H:%M:%S'),
            'username': user.username if user else 'System'
        })
    
    return jsonify({
        'success': True,
        'history': history_list,
        'total': len(history_list)
    })


@api_bp.route('/top-products', methods=['GET'])
@login_required
def get_top_products():
    """Get top-selling products by revenue or quantity.

    Query params:
      - limit: number of products to return (default 10)
      - metric: 'revenue' or 'quantity'
      - period: preset window: 7d, 30d, 90d, 1y, all
      - year, month, week: optional calendar filters; if provided, these override 'period'
        week is week number within month (1-5) using 7-day buckets starting on the 1st.
    """
    limit = request.args.get('limit', 10, type=int)
    period = request.args.get('period', '7d')
    metric = request.args.get('metric', 'revenue')
    # Calendar filters (override period if provided)
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    week = request.args.get('week', type=int)

    # Calculate date filter window
    start_date = None
    end_date = None

    if year:
        # If year is provided, restrict to that year
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)
        if month and 1 <= month <= 12:
            # Narrow to month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
            if week and 1 <= week <= 5:
                # 7-day buckets within month, Week 1 starts on day 1
                week_start_day = (week - 1) * 7 + 1
                # Guard against overflow
                try:
                    start_date = datetime(year, month, week_start_day)
                except ValueError:
                    # Invalid week start -> clamp to end of month
                    from calendar import monthrange
                    start_date = datetime(year, month, monthrange(year, month)[1])
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                week_end_day = min(week * 7, last_day)
                end_date = datetime(year, month, week_end_day) + timedelta(days=1)
    else:
        # Preset period relative to now
        if period == '7d':
            start_date = datetime.now() - timedelta(days=7)
        elif period == '30d':
            start_date = datetime.now() - timedelta(days=30)
        elif period == '90d':
            start_date = datetime.now() - timedelta(days=90)
        elif period == '1y':
            start_date = datetime.now() - timedelta(days=365)
        else:
            start_date = None
            end_date = None

    # Build query
    if metric == 'revenue':
        query = db.session.query(
            Product.id,
            Product.name,
            Product.category,
            db.func.sum(Sale.quantity * Sale.price).label('total_revenue'),
            db.func.sum(Sale.quantity).label('total_quantity'),
            db.func.count(Sale.id).label('sales_count')
        )
    else:
        query = db.session.query(
            Product.id,
            Product.name,
            Product.category,
            db.func.sum(Sale.quantity).label('total_quantity'),
            db.func.sum(Sale.quantity * Sale.price).label('total_revenue'),
            db.func.count(Sale.id).label('sales_count')
        )
    
    query = query.join(Sale, Product.id == Sale.product_id)

    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        query = query.filter(Sale.sale_date < end_date)
    
    query = query.group_by(Product.id, Product.name, Product.category)
    
    if metric == 'revenue':
        query = query.order_by(db.desc('total_revenue'))
    else:
        query = query.order_by(db.desc('total_quantity'))
    
    results = query.limit(limit).all()
    
    top_products = []
    for result in results:
        top_products.append({
            'product_id': result.id,
            'product_name': result.name,
            'category': result.category,
            'total_revenue': float(result.total_revenue) if result.total_revenue else 0,
            'total_quantity': int(result.total_quantity) if result.total_quantity else 0,
            'sales_count': int(result.sales_count) if hasattr(result, 'sales_count') else 0
        })
    
    return jsonify({
        'success': True,
        'products': top_products,
        'period': period,
        'metric': metric,
        'total': len(top_products)
    })


@api_bp.route('/available-periods', methods=['GET'])
@login_required
def get_available_periods():
    """Return available years, months, and weeks that have either actual sales or forecast data.

    Response structure:
      {
        "years": [2022, 2023, ...],
        "monthsByYear": {"2022": [1,2,...]},
        "weeksByYearMonth": {"2022-01": [1,2,3,4]},
      }
    """
    try:
        from sqlalchemy import extract

        years = set()
        months_by_year = {}
        weeks_by_year_month = {}

        # Collect from sales
        sales_results = db.session.query(
            extract('year', Sale.sale_date).label('y'),
            extract('month', Sale.sale_date).label('m'),
            func.count(Sale.id)
        ).group_by('y', 'm').all()

        for y, m, _ in sales_results:
            yi = int(y)
            mi = int(m)
            years.add(yi)
            months_by_year.setdefault(str(yi), set()).add(mi)

        # Collect from forecasts (use forecast_date)
        forecast_results = db.session.query(
            extract('year', Forecast.forecast_date).label('y'),
            extract('month', Forecast.forecast_date).label('m'),
            func.count(Forecast.id)
        ).group_by('y', 'm').all()

        for y, m, _ in forecast_results:
            yi = int(y)
            mi = int(m)
            years.add(yi)
            months_by_year.setdefault(str(yi), set()).add(mi)

        # Build weeks per (year, month) where there is data
        from calendar import monthrange
        for y_str, months in months_by_year.items():
            yi = int(y_str)
            for mi in sorted(months):
                last_day = monthrange(yi, mi)[1]
                num_weeks = (last_day + 6) // 7  # ceil(last_day/7)
                key = f"{yi}-{mi:02d}"
                weeks_by_year_month[key] = list(range(1, max(1, min(5, num_weeks)) + 1))

        return jsonify({
            'success': True,
            'years': sorted(list(years)),
            'monthsByYear': {k: sorted(list(v)) for k, v in months_by_year.items()},
            'weeksByYearMonth': weeks_by_year_month
        })
    except Exception as e:
        import traceback
        print(f"Error in /available-periods: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/recent-activity', methods=['GET'])
@login_required
def get_recent_activity():
    """Get recent activity logs from the system."""
    limit = request.args.get('limit', 10, type=int)
    
    logs = Log.query.order_by(Log.timestamp.desc()).limit(limit).all()
    
    activity_list = []
    for log in logs:
        user = User.query.get(log.user_id) if log.user_id else None
        activity_list.append({
            'id': log.id,
            'action': log.action,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'username': user.username if user else 'System'
        })
    
    return jsonify({
        'success': True,
        'activities': activity_list,
        'total': len(activity_list)
    })


@api_bp.route('/forecast-accuracy', methods=['GET'])
@login_required
def get_forecast_accuracy():
    """
    Get forecast accuracy metrics for different time horizons.
    Used for model performance tracking dashboard.
    """
    from utils.forecast_evaluator import ForecastEvaluator
    
    try:
        days_back = request.args.get('days_back', 7, type=int)
        
        # Get multi-horizon accuracy
        accuracy_stats = ForecastEvaluator.get_multi_horizon_accuracy(days_back=days_back)
        
        return jsonify({
            'success': True,
            'accuracy': {
                '1_day': accuracy_stats['1_day'],
                '7_day': accuracy_stats['7_day'],
                '30_day': accuracy_stats['30_day']
            },
            'days_evaluated': days_back,
            'note': 'Accuracy is calculated as 100% - MAPE (Mean Absolute Percentage Error)'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/forecast-vs-actual/<int:product_id>', methods=['GET'])
@login_required
def get_forecast_vs_actual(product_id):
    """
    Get forecast vs actual sales comparison for a specific product.
    Used for charting model performance.
    """
    from utils.forecast_evaluator import ForecastEvaluator
    
    try:
        days = request.args.get('days', 7, type=int)
        
        # Get comparison data
        comparison = ForecastEvaluator.get_forecast_vs_actual(product_id, days=days)
        
        # Get product accuracy
        accuracy = ForecastEvaluator.get_product_accuracy(product_id, days_back=days)
        
        # Get product info
        product = Product.query.get(product_id)
        
        return jsonify({
            'success': True,
            'product_name': product.name if product else 'Unknown',
            'dates': comparison['dates'],
            'actual': comparison['actual'],
            'forecast': comparison['forecast'],
            'accuracy': accuracy
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/weekly-forecast', methods=['GET'])
@login_required
def get_weekly_forecast():
    """
    Get next 7 days forecast for all products.
    Used for weekly planning and restock decision making.
    """
    from utils.model_trainer import ForecastingPipeline
    
    try:
        today = datetime.now().date()
        forecast_data = []
        
        # Get all products
        products = Product.query.all()
        
        for product in products:
            # Get multi-horizon forecasts (1-day, 7-day, 30-day)
            forecast_1d = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=1)
            forecast_7d = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=7)
            forecast_30d = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=30)
            
            if forecast_7d is not None:
                # Calculate restock status using SAME LOGIC as dashboard alerts
                current_stock = product.current_stock or 0
                predicted_demand_7d = forecast_7d.predicted_quantity
                
                # Multi-horizon urgency calculation (matches dashboard)
                if forecast_1d and current_stock < forecast_1d.predicted_quantity:
                    status = 'CRITICAL'
                    status_color = '#ef4444'  # Red - stock won't last 1 day
                elif current_stock < predicted_demand_7d:
                    status = 'HIGH'
                    status_color = '#f59e0b'  # Orange - stock won't last 7 days
                elif forecast_30d and current_stock < forecast_30d.predicted_quantity:
                    status = 'MEDIUM'
                    status_color = '#eab308'  # Yellow - stock won't last 30 days
                else:
                    status = 'OK'
                    status_color = '#10b981'  # Green - sufficient stock
                
                forecast_data.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'current_stock': current_stock,
                    'predicted_7d': round(predicted_demand_7d, 1),
                    'status': status,
                    'status_color': status_color,
                    'reorder_recommended': current_stock < predicted_demand_7d
                })
        
        # Sort by urgency (CRITICAL first, then HIGH, then MEDIUM, then OK)
        status_priority = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'OK': 3}
        forecast_data.sort(key=lambda x: status_priority.get(x['status'], 4))
        
        return jsonify({
            'success': True,
            'forecasts': forecast_data,
            'total_products': len(forecast_data),
            'critical_count': sum(1 for f in forecast_data if f['status'] == 'CRITICAL'),
            'high_count': sum(1 for f in forecast_data if f['status'] == 'HIGH'),
            'medium_count': sum(1 for f in forecast_data if f['status'] == 'MEDIUM'),
            'low_count': sum(1 for f in forecast_data if f['status'] in ['CRITICAL', 'HIGH']),  # Legacy: sum of CRITICAL + HIGH
            'forecast_date': today.isoformat()
        })
    except Exception as e:
        import traceback
        print(f"Error in weekly-forecast endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/forecast-visualization', methods=['GET'])
@login_required
def get_forecast_visualization():
    """
    Get comprehensive forecast visualization data for a product.
    Includes:
    - Historical sales data (last 30 days)
    - Multi-horizon forecasts (1, 7, 30 days)
    - Confidence intervals
    - Model performance metrics
    - Actual vs Predicted comparison
    
    Query params:
        product_id: Product ID to visualize
        days_back: Historical days to show (default: 30)
    """
    from utils.model_trainer import ForecastingPipeline
    import pandas as pd
    
    try:
        product_id = request.args.get('product_id', type=int)
        days_back = request.args.get('days_back', default=30, type=int)
        
        if not product_id:
            return jsonify({'success': False, 'error': 'product_id is required'}), 400
        
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
        # Get historical sales data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        sales_query = db.session.query(
            db.func.date(Sale.sale_date).label('date'),
            db.func.sum(Sale.quantity).label('quantity')
        ).filter(
            Sale.product_id == product_id,
            Sale.sale_date >= start_date
        ).group_by(db.func.date(Sale.sale_date)).all()
        
        # Format historical data
        historical_dates = []
        historical_values = []
        for sale in sales_query:
            historical_dates.append(sale.date.isoformat())
            historical_values.append(float(sale.quantity))
        
        # Get forecast data with confidence intervals
        forecast_dates = []
        forecast_values = []
        forecast_lower = []
        forecast_upper = []
        model_types = []
        
        # Query forecasts for next 30 days
        today = datetime.now().date()
        forecasts = Forecast.query.filter(
            Forecast.product_id == product_id,
            Forecast.forecast_date >= today
        ).order_by(Forecast.forecast_date).limit(30).all()
        
        for fc in forecasts:
            forecast_dates.append(fc.forecast_date.strftime('%Y-%m-%d'))
            forecast_values.append(float(fc.predicted_quantity or 0))
            forecast_lower.append(float(fc.confidence_lower or fc.predicted_quantity or 0))
            forecast_upper.append(float(fc.confidence_upper or fc.predicted_quantity or 0))
            model_types.append(fc.model_used or 'UNKNOWN')
        
        # Calculate model performance metrics
        metrics = {}
        if forecasts:
            # Get average MAE and RMSE from recent forecasts
            recent_forecasts = Forecast.query.filter(
                Forecast.product_id == product_id,
                Forecast.mae.isnot(None)
            ).order_by(Forecast.created_at.desc()).limit(10).all()
            
            if recent_forecasts:
                avg_mae = sum(f.mae for f in recent_forecasts if f.mae) / len([f for f in recent_forecasts if f.mae])
                avg_rmse = sum(f.rmse for f in recent_forecasts if f.rmse) / len([f for f in recent_forecasts if f.rmse])
                
                metrics = {
                    'mae': round(avg_mae, 2),
                    'rmse': round(avg_rmse, 2),
                    'model_used': forecasts[0].model_used or 'UNKNOWN',
                    'total_forecasts': len(forecasts)
                }
        
        # Model comparison (count by model type)
        model_comparison = {}
        for model in model_types:
            model_comparison[model] = model_comparison.get(model, 0) + 1
        
        return jsonify({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'current_stock': product.current_stock
            },
            'historical': {
                'dates': historical_dates,
                'values': historical_values
            },
            'forecast': {
                'dates': forecast_dates,
                'values': forecast_values,
                'confidence_lower': forecast_lower,
                'confidence_upper': forecast_upper,
                'models': model_types
            },
            'metrics': metrics,
            'model_comparison': model_comparison
        })
        
    except Exception as e:
        import traceback
        print(f"Error in forecast-visualization endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/model-comparison', methods=['GET'])
@login_required
def get_model_comparison():
    """
    Compare performance of different forecasting models (ARIMA vs Linear Regression).
    
    Returns:
    - Model accuracy comparison
    - MAE and RMSE comparison
    - Model usage statistics
    """
    try:
        # Get all forecasts with performance metrics
        forecasts_with_metrics = Forecast.query.filter(
            Forecast.mae.isnot(None),
            Forecast.model_used.isnot(None)
        ).all()
        
        if not forecasts_with_metrics:
            return jsonify({
                'success': True,
                'models': [],
                'message': 'No model performance data available yet'
            })
        
        # Group by model type
        model_stats = {}
        for fc in forecasts_with_metrics:
            model = fc.model_used or 'UNKNOWN'
            if model not in model_stats:
                model_stats[model] = {
                    'mae_values': [],
                    'rmse_values': [],
                    'accuracy_values': [],
                    'count': 0
                }
            
            if fc.mae:
                model_stats[model]['mae_values'].append(fc.mae)
            if fc.rmse:
                model_stats[model]['rmse_values'].append(fc.rmse)
            if fc.accuracy:
                model_stats[model]['accuracy_values'].append(fc.accuracy)
            model_stats[model]['count'] += 1
        
        # Calculate averages
        comparison_data = []
        for model, stats in model_stats.items():
            avg_mae = sum(stats['mae_values']) / len(stats['mae_values']) if stats['mae_values'] else 0
            avg_rmse = sum(stats['rmse_values']) / len(stats['rmse_values']) if stats['rmse_values'] else 0
            avg_accuracy = sum(stats['accuracy_values']) / len(stats['accuracy_values']) if stats['accuracy_values'] else 0
            
            comparison_data.append({
                'model': model,
                'avg_mae': round(avg_mae, 2),
                'avg_rmse': round(avg_rmse, 2),
                'avg_accuracy': round(avg_accuracy, 2),
                'total_forecasts': stats['count']
            })
        
        # Sort by accuracy (descending)
        comparison_data.sort(key=lambda x: x['avg_accuracy'], reverse=True)
        
        return jsonify({
            'success': True,
            'models': comparison_data,
            'total_models': len(comparison_data)
        })
        
    except Exception as e:
        import traceback
        print(f"Error in model-comparison endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/enhanced-restock-alerts', methods=['GET'])
@login_required
def get_enhanced_restock_alerts():
    """
    Get intelligent restock alerts using multi-horizon forecasts (1-day, 7-day, 30-day).
    
    Returns alerts with:
    - Urgency level (CRITICAL/HIGH/MEDIUM)
    - Recommended order quantity
    - Forecast-based analysis
    - Time horizons affected
    """
    from utils.model_trainer import ForecastingPipeline
    
    try:
        alerts_data = []
        products = Product.query.all()
        
        for product in products:
            current_stock = product.current_stock or 0
            
            # Get multi-horizon forecasts
            forecast_1d = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=1)
            forecast_7d = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=7)
            forecast_30d = ForecastingPipeline.get_latest_forecast(product.id, days_ahead=30)
            
            # Fallback: If no forecasts available, use stock-based alerts
            if forecast_1d is None and forecast_7d is None and forecast_30d is None:
                # Check if stock is below reorder point (simple threshold-based alert)
                reorder_point = product.reorder_point if hasattr(product, 'reorder_point') and product.reorder_point else 20
                
                if current_stock <= reorder_point:
                    urgency = 'HIGH' if current_stock <= reorder_point * 0.5 else 'MEDIUM'
                    severity = 2 if urgency == 'HIGH' else 1
                    recommended_qty = int(reorder_point * 2)
                    
                    alerts_data.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'category': product.category or 'N/A',
                        'current_stock': current_stock,
                        'urgency': urgency,
                        'severity': severity,
                        'shortage': reorder_point - current_stock,
                        'recommended_order_qty': recommended_qty,
                        'horizons_affected': ['No forecast data available'],
                        'forecasts': {
                            '1_day': None,
                            '7_day': None,
                            '30_day': None
                        },
                        'urgency_color': {
                            'HIGH': '#f59e0b',
                            'MEDIUM': '#10b981'
                        }.get(urgency, '#6b7280'),
                        'note': 'Based on reorder point (no forecast data yet)'
                    })
                continue
            
            # Determine urgency level
            urgency = None
            severity = None
            recommended_qty = None
            horizons_affected = []
            shortage = 0
            
            # Extract forecast quantities from Forecast objects
            forecast_1d_qty = forecast_1d.predicted_quantity if forecast_1d else None
            forecast_7d_qty = forecast_7d.predicted_quantity if forecast_7d else None
            forecast_30d_qty = forecast_30d.predicted_quantity if forecast_30d else None
            
            # CRITICAL: Insufficient for 1-day demand
            if forecast_1d_qty and current_stock < forecast_1d_qty:
                urgency = 'CRITICAL'
                severity = 3
                shortage = forecast_1d_qty - current_stock
                recommended_qty = int(forecast_7d_qty * 1.2) if forecast_7d_qty else int(shortage * 2)
                horizons_affected = ['1-day', '7-day', '30-day']
                
            # HIGH: Insufficient for 7-day demand
            elif forecast_7d_qty and current_stock < forecast_7d_qty:
                urgency = 'HIGH'
                severity = 2
                shortage = forecast_7d_qty - current_stock
                recommended_qty = int(forecast_7d_qty * 1.2)
                horizons_affected = ['7-day', '30-day']
                
            # MEDIUM: Insufficient for 30-day demand
            elif forecast_30d_qty and current_stock < forecast_30d_qty:
                urgency = 'MEDIUM'
                severity = 1
                shortage = forecast_30d_qty - current_stock
                recommended_qty = int(forecast_30d_qty * 1.2)
                horizons_affected = ['30-day']
            
            # Only add if there's an alert
            if urgency:
                alerts_data.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'category': product.category or 'N/A',
                    'current_stock': current_stock,
                    'urgency': urgency,
                    'severity': severity,
                    'shortage': round(shortage, 1),
                    'recommended_order_qty': recommended_qty,
                    'horizons_affected': horizons_affected,
                    'forecasts': {
                        '1_day': round(forecast_1d_qty, 1) if forecast_1d_qty else None,
                        '7_day': round(forecast_7d_qty, 1) if forecast_7d_qty else None,
                        '30_day': round(forecast_30d_qty, 1) if forecast_30d_qty else None
                    },
                    'urgency_color': {
                        'CRITICAL': '#ef4444',
                        'HIGH': '#f59e0b', 
                        'MEDIUM': '#10b981'
                    }.get(urgency, '#6b7280')
                })
        
        # Sort by severity (CRITICAL first)
        alerts_data.sort(key=lambda x: x['severity'], reverse=True)
        
        # Filter to show only CRITICAL and HIGH alerts (to avoid overcrowding dashboard)
        critical_high_alerts = [a for a in alerts_data if a['urgency'] in ['CRITICAL', 'HIGH']]
        
        return jsonify({
            'success': True,
            'alerts': critical_high_alerts,  # Only CRITICAL + HIGH
            'total_alerts': len(critical_high_alerts),
            'critical_count': sum(1 for a in alerts_data if a['urgency'] == 'CRITICAL'),
            'high_count': sum(1 for a in alerts_data if a['urgency'] == 'HIGH'),
            'medium_count': sum(1 for a in alerts_data if a['urgency'] == 'MEDIUM')
        })
        
    except Exception as e:
        import traceback
        print(f"Error in enhanced-restock-alerts endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== SYNCHRONIZED DAILY & WEEKLY FORECAST ENDPOINTS ====================

@api_bp.route('/forecast/daily', methods=['GET'])
@login_required
def get_synchronized_daily_forecast():
    """
    Get daily forecast for a specific week (Monday-Sunday).
    
    Query Parameters:
        product_id (int, optional): Product ID to forecast. If not provided or empty, aggregates all products.
        year (int, optional): Year for the target week. Defaults to current year.
        month (int, optional): Month (1-12) for the target week. Defaults to current month.
        week (int, optional): Week number within the month (1-5). Defaults to current week.
    
    Returns:
        JSON response with:
        - week_start: Start date of selected week (Monday)
        - week_end: End date of selected week (Sunday)
        - week_number: Week number within the month
        - actual: List of {date, sales, day_name} for past days
        - forecast: List of {date, sales, confidence_lower, confidence_upper, day_name} for future days
        - accuracy: Yesterday's forecast accuracy percentage (if available)
    """
    try:
        product_id = request.args.get('product_id', type=int)
        # Optional date components
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        week_num = request.args.get('week', type=int)

        # If no product_id, aggregate all products (don't default to first product)
        aggregate_all = not product_id
        
        # Determine basis date
        today = datetime.now().date()
        basis_year = year if year else today.year
        basis_month = month if month else today.month
        
        # Calculate the first day of the month
        month_start = datetime(basis_year, basis_month, 1).date()
        
        # Calculate week boundaries
        if not week_num:
            # No week specified - use the actual current week for current month
            if basis_year == today.year and basis_month == today.month:
                week_start = today - timedelta(days=today.weekday())
                week_end = week_start + timedelta(days=6)
                # Calculate which week number this is within the month
                days_into_month = (week_start - month_start).days
                week_num = max(1, (days_into_month // 7) + 1)
            else:
                # For other months, default to week 1
                week_num = 1
        
        # Week number is provided OR was calculated above
        # For current month, check if the provided week number matches the current week
        if basis_year == today.year and basis_month == today.month:
            # Calculate what the current week number should be
            current_week_start = today - timedelta(days=today.weekday())
            days_into_month_current = (current_week_start - month_start).days
            current_week_num = max(1, (days_into_month_current // 7) + 1)
            
            # If requested week matches current week, use today's actual week
            if week_num == current_week_num:
                week_start = current_week_start
                week_end = week_start + timedelta(days=6)
            else:
                # Different week requested - calculate it normally
                week_start = month_start + timedelta(days=(week_num - 1) * 7)
                days_to_monday = week_start.weekday()
                week_start = week_start - timedelta(days=days_to_monday)
                week_end = week_start + timedelta(days=6)
        else:
            # Not current month - calculate week normally
            week_start = month_start + timedelta(days=(week_num - 1) * 7)
            days_to_monday = week_start.weekday()
            week_start = week_start - timedelta(days=days_to_monday)
            week_end = week_start + timedelta(days=6)
        
        # IMPORTANT: Determine if we're viewing historical data or future data
        # If the selected week is in the past, show all data for that week
        # If the selected week includes today or is future, use today as basis
        if week_end < today:
            # Viewing historical week - for BACKTESTING
            # Show forecasts that would have been made BEFORE this week
            # and predict dates WITHIN this week
            basis_date = week_start - timedelta(days=1)  # Day before week starts
            forecast_start = week_start  # Start of the week
            forecast_end = week_end  # End of the week
            is_historical_view = True
        else:
            # Current or future week - use today as basis
            basis_date = today
            forecast_start = today  # Include today in forecast
            forecast_end = week_end  # Show forecasts up to and including the last day of week
            is_historical_view = False
        
        # Show ONLY the selected week (7 days), not historical context
        history_start = week_start  # START OF SELECTED WEEK, not 4 weeks back
        
        # Get actual sales from the selected week only
        actual_sales_query = db.session.query(
            func.date(Sale.sale_date).label('date'),
            func.sum(Sale.quantity).label('quantity')
        ).filter(
            func.date(Sale.sale_date) >= week_start,  # Only from week start
            func.date(Sale.sale_date) <= (week_end if is_historical_view else basis_date)  # Up to week end (historical) or today (current)
        )
        
        # Filter by product if specific product selected
        if not aggregate_all:
            actual_sales_query = actual_sales_query.filter(Sale.product_id == product_id)
        
        actual_sales = actual_sales_query.group_by(func.date(Sale.sale_date)).all()
        
        print(f"[DEBUG /forecast/daily] Actual sales query returned {len(actual_sales)} rows")
        if len(actual_sales) > 0:
            print(f"[DEBUG /forecast/daily] First actual sale: date={actual_sales[0].date}, qty={actual_sales[0].quantity}")
        
        # Get year-over-year data (same period last year)
        last_year_start = history_start.replace(year=history_start.year - 1)
        last_year_end = basis_date.replace(year=basis_date.year - 1)
        
        yoy_sales_query = db.session.query(
            func.date(Sale.sale_date).label('date'),
            func.sum(Sale.quantity).label('quantity')
        ).filter(
            Sale.sale_date >= last_year_start,
            Sale.sale_date <= last_year_end
        )
        
        # Filter by product if specific product selected
        if not aggregate_all:
            yoy_sales_query = yoy_sales_query.filter(Sale.product_id == product_id)
        
        yoy_sales = yoy_sales_query.group_by(func.date(Sale.sale_date)).all()
        
        # Format actual data - ENSURE CONTINUOUS DATES (fill gaps with 0)
        actual_data = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Create a dictionary of sales by date for quick lookup
        sales_by_date = {}
        for sale in actual_sales:
            sale_date = sale.date if isinstance(sale.date, datetime) else datetime.strptime(str(sale.date), '%Y-%m-%d').date()
            if isinstance(sale_date, datetime):
                sale_date = sale_date.date()
            sales_by_date[sale_date] = float(sale.quantity)
        
        print(f"[DEBUG /forecast/daily] sales_by_date has {len(sales_by_date)} entries")
        print(f"[DEBUG /forecast/daily] sales_by_date keys: {list(sales_by_date.keys())[:5]}")
        
        # Fill in all dates from week_start to basis_date (or week_end if historical)
        end_date_for_actual = week_end if is_historical_view else min(basis_date, week_end)
        current_date = week_start
        while current_date <= end_date_for_actual:
            sales_value = sales_by_date.get(current_date, 0.0)  # Default to 0 if no sales
            actual_data.append({
                'date': current_date.isoformat(),
                'sales': sales_value,
                'day_name': day_names[current_date.weekday()],
                'week_label': 'Current Week' if current_date >= week_start else f'-{((week_start - current_date).days // 7)} weeks'
            })
            current_date += timedelta(days=1)
        
        # Format year-over-year data
        yoy_data = []
        for sale in yoy_sales:
            sale_date = sale.date if isinstance(sale.date, datetime) else datetime.strptime(str(sale.date), '%Y-%m-%d').date()
            # Map to current year date for comparison
            current_year_date = sale_date.replace(year=basis_date.year)
            yoy_data.append({
                'date': current_year_date.isoformat(),
                'original_date': sale_date.isoformat(),
                'sales': float(sale.quantity),
                'day_name': day_names[sale_date.weekday()]
            })
        
        # Get forecast for remaining days
        forecast_data = []
        
        # DEBUG: Log query parameters
        print(f"[DEBUG /forecast/daily] product_id={product_id}, aggregate_all={aggregate_all}")
        print(f"[DEBUG /forecast/daily] week_start={week_start}, week_end={week_end}")
        print(f"[DEBUG /forecast/daily] basis_date={basis_date}, forecast_start={forecast_start}, forecast_end={forecast_end}")
        print(f"[DEBUG /forecast/daily] is_historical_view={is_historical_view}")
        
        if aggregate_all:
            # Aggregate forecasts across all products
            if is_historical_view:
                # Historical: Show forecasts FOR the week (forecast_date within week)
                # that were generated BEFORE the week (generated_at < week_start)
                forecast_agg = db.session.query(
                    func.date(Forecast.forecast_date).label('date'),
                    func.sum(Forecast.predicted_quantity).label('quantity'),
                    func.sum(Forecast.confidence_lower).label('conf_lower'),
                    func.sum(Forecast.confidence_upper).label('conf_upper')
                ).filter(
                    Forecast.aggregation_level == 'daily',
                    func.date(Forecast.forecast_date) >= forecast_start,
                    func.date(Forecast.forecast_date) <= forecast_end,
                    Forecast.generated_at < week_start  # Only forecasts generated before this week
                ).group_by(func.date(Forecast.forecast_date)).order_by(func.date(Forecast.forecast_date)).all()
            else:
                # Current/Future: Show forecasts from forecast_start through the end of the selected week
                forecast_agg = db.session.query(
                    func.date(Forecast.forecast_date).label('date'),
                    func.sum(Forecast.predicted_quantity).label('quantity'),
                    func.sum(Forecast.confidence_lower).label('conf_lower'),
                    func.sum(Forecast.confidence_upper).label('conf_upper')
                ).filter(
                    Forecast.aggregation_level == 'daily',
                    func.date(Forecast.forecast_date) >= forecast_start,
                    func.date(Forecast.forecast_date) <= week_end  # Include all days through Sunday
                ).group_by(func.date(Forecast.forecast_date)).order_by(func.date(Forecast.forecast_date)).all()
            
            print(f"[DEBUG /forecast/daily] Aggregate query returned {len(forecast_agg)} results")
            
            # Create a dictionary of forecasts by date for continuous filling
            forecasts_by_date = {}
            for fc in forecast_agg:
                fc_date = fc.date if isinstance(fc.date, datetime) else datetime.strptime(str(fc.date), '%Y-%m-%d').date()
                if isinstance(fc_date, datetime):
                    fc_date = fc_date.date()
                forecasts_by_date[fc_date] = {
                    'quantity': float(fc.quantity or 0),
                    'conf_lower': float(fc.conf_lower or fc.quantity or 0),
                    'conf_upper': float(fc.conf_upper or fc.quantity or 0)
                }
            
            # Fill in all forecast dates from forecast_start to week_end
            current_date = forecast_start
            while current_date <= week_end:
                fc_data = forecasts_by_date.get(current_date, {'quantity': 0, 'conf_lower': 0, 'conf_upper': 0})
                forecast_data.append({
                    'date': current_date.isoformat(),
                    'sales': fc_data['quantity'],
                    'confidence_lower': fc_data['conf_lower'],
                    'confidence_upper': fc_data['conf_upper'],
                    'day_name': day_names[current_date.weekday()]
                })
                current_date += timedelta(days=1)
        else:
            # Single product forecasts
            if is_historical_view:
                # Historical: Show forecasts FOR the week that were generated BEFORE the week
                forecasts = Forecast.query.filter(
                    Forecast.product_id == product_id,
                    Forecast.aggregation_level == 'daily',
                    func.date(Forecast.forecast_date) >= forecast_start,
                    func.date(Forecast.forecast_date) <= forecast_end,
                    Forecast.generated_at < week_start  # Only forecasts generated before this week
                ).order_by(Forecast.forecast_date).all()
            else:
                # Current/Future: Show forecasts from forecast_start through the end of the selected week
                forecasts = Forecast.query.filter(
                    Forecast.product_id == product_id,
                    Forecast.aggregation_level == 'daily',
                    func.date(Forecast.forecast_date) >= forecast_start,
                    func.date(Forecast.forecast_date) <= week_end  # Include all days through Sunday
                ).order_by(Forecast.forecast_date).all()
            
            print(f"[DEBUG /forecast/daily] Single product query returned {len(forecasts)} results")
            if len(forecasts) > 0:
                print(f"[DEBUG /forecast/daily] First forecast: date={forecasts[0].forecast_date}, qty={forecasts[0].predicted_quantity}")
            else:
                # Check if any forecasts exist for this product at all
                total_forecasts = Forecast.query.filter(Forecast.product_id == product_id).count()
                future_forecasts = Forecast.query.filter(
                    Forecast.product_id == product_id,
                    Forecast.forecast_date > basis_date
                ).count()
                print(f"[DEBUG /forecast/daily] Total forecasts for product {product_id}: {total_forecasts}")
                print(f"[DEBUG /forecast/daily] Future forecasts for product {product_id}: {future_forecasts}")
            
            # Create a dictionary of forecasts by date for continuous filling
            forecasts_by_date = {}
            for fc in forecasts:
                fc_date = fc.forecast_date.date() if isinstance(fc.forecast_date, datetime) else fc.forecast_date
                forecasts_by_date[fc_date] = {
                    'quantity': float(fc.predicted_quantity or 0),
                    'conf_lower': float(fc.confidence_lower or fc.predicted_quantity or 0),
                    'conf_upper': float(fc.confidence_upper or fc.predicted_quantity or 0)
                }
            
            # Fill in all forecast dates from forecast_start to week_end
            current_date = forecast_start
            while current_date <= week_end:
                fc_data = forecasts_by_date.get(current_date, {'quantity': 0, 'conf_lower': 0, 'conf_upper': 0})
                forecast_data.append({
                    'date': current_date.isoformat(),
                    'sales': fc_data['quantity'],
                    'confidence_lower': fc_data['conf_lower'],
                    'confidence_upper': fc_data['conf_upper'],
                    'day_name': day_names[current_date.weekday()]
                })
                current_date += timedelta(days=1)
        
        # Calculate accuracy (compare yesterday's forecast vs actual)
        accuracy = None
        if len(actual_sales) > 0 and not aggregate_all:
            yesterday = basis_date - timedelta(days=1)
            yesterday_forecast = Forecast.query.filter(
                Forecast.product_id == product_id,
                Forecast.aggregation_level == 'daily',
                func.date(Forecast.forecast_date) == yesterday
            ).first()
            
            if yesterday_forecast:
                yesterday_actual = db.session.query(
                    func.sum(Sale.quantity)
                ).filter(
                    Sale.product_id == product_id,
                    func.date(Sale.sale_date) == yesterday
                ).scalar() or 0
                
                if yesterday_actual > 0:
                    error = abs(yesterday_forecast.predicted_quantity - yesterday_actual) / yesterday_actual
                    accuracy = round((1 - error) * 100, 2)
        
        return jsonify({
            'success': True,
            'product_id': product_id if not aggregate_all else 'all',
            'aggregate_all': aggregate_all,
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'week_number': week_num,
            'history_start': history_start.isoformat(),
            'current_day': basis_date.isoformat(),
            'actual': actual_data,
            'forecast': forecast_data,
            'yoy_data': yoy_data,  # Year-over-year comparison
            'accuracy': accuracy
        })
        
    except Exception as e:
        import traceback
        print(f"Error in /forecast/daily: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/forecast/weekly', methods=['GET'])
@login_required
def get_synchronized_weekly_forecast():
    """
    Get weekly forecast for a specific month (Week 1-4/5).
    
    Query Parameters:
        product_id (int, optional): Product ID to forecast. If not provided or empty, aggregates all products.
        year (int, optional): Year of target month. Defaults to current year.
        month (int, optional): Month (1-12) of target month. Defaults to current month.
    
    Returns:
        JSON response with:
        - month: Selected month (YYYY-MM)
        - month_name: Month name (e.g., "November 2025")
        - current_week: Current week number within the month
        - actual: List of {week, start, end, sales} for completed weeks
        - forecast: List of {week, start, end, sales, confidence_lower, confidence_upper} for future weeks
        - accuracy: Last week's forecast accuracy percentage (if available)
    """
    try:
        product_id = request.args.get('product_id', type=int)
        # Optional date components
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        # If no product_id, aggregate all products
        aggregate_all = not product_id
        
        today = datetime.now().date()
        # Determine basis date for month
        basis_year = year if year else today.year
        basis_month = month if month else today.month
        
        # Calculate month boundaries
        month_start = datetime(basis_year, basis_month, 1).date()
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
        
        # Determine if viewing historical month
        is_historical_month = month_end < today
        
        # Calculate weeks in month (7-day chunks)
        weeks = []
        current_week_start = month_start
        week_num = 1
        current_week_num = None
        
        while current_week_start <= month_end:
            current_week_end = min(current_week_start + timedelta(days=6), month_end)
            
            # Check if selected basis date (today) is in this week
            if current_week_start <= today <= current_week_end:
                current_week_num = week_num
            
            weeks.append({
                'week': week_num,
                'start': current_week_start,
                'end': current_week_end
            })
            current_week_start = current_week_end + timedelta(days=1)
            week_num += 1
        
        # Get actual sales for completed weeks and forecasts for future weeks
        actual_data = []
        forecast_data = []
        
        for week in weeks:
            # Determine if this week should show actual sales or forecasts
            # For historical months: Show BOTH actual sales AND historical forecasts (backtesting)
            # For current/future months: Show actuals for completed weeks, forecasts for future weeks
            is_completed_week = week['end'] < today
            
            # Get actual sales for weeks that have STARTED (even if not fully completed)
            # This includes: completed weeks, current week, and all weeks in historical months
            week_has_started = week['start'] <= today
            
            # ALWAYS add actual_data entry for EVERY week (continuous bars)
            # This prevents gaps in the bar chart visualization
            if week_has_started:
                # Get actual sales for any week that has started
                if aggregate_all:
                    total_sales = db.session.query(
                        func.sum(Sale.quantity)
                    ).filter(
                        func.date(Sale.sale_date) >= week['start'],
                        func.date(Sale.sale_date) <= week['end']
                    ).scalar() or 0
                else:
                    total_sales = db.session.query(
                        func.sum(Sale.quantity)
                    ).filter(
                        Sale.product_id == product_id,
                        func.date(Sale.sale_date) >= week['start'],
                        func.date(Sale.sale_date) <= week['end']
                    ).scalar() or 0
                
                actual_data.append({
                    'week': week['week'],
                    'start': week['start'].isoformat(),
                    'end': week['end'].isoformat(),
                    'sales': float(total_sales)
                })
            else:
                # Future week - add 0 to maintain continuous data structure
                actual_data.append({
                    'week': week['week'],
                    'start': week['start'].isoformat(),
                    'end': week['end'].isoformat(),
                    'sales': 0
                })
            
            # Get forecasts for comparison/planning:
            # - Historical months: Show historical forecasts (made before the week) for backtesting
            # - Current month: Show all forecasts (both for completed weeks comparison and future planning)
            # This allows users to compare actual vs predicted for completed weeks
            
            # Always get forecasts for all weeks
            if is_historical_month:
                # Historical: Only use forecasts generated BEFORE the week started (backtesting)
                generated_before = week['start']
            else:
                # Current/Future month: Use latest forecasts (no time filter)
                generated_before = None
            
            # Get forecast by aggregating DAILY forecasts
            if aggregate_all:
                # Sum DAILY forecasts across all products for this week
                total_forecast_query = db.session.query(
                    func.sum(Forecast.predicted_quantity).label('total'),
                    func.sum(Forecast.confidence_lower).label('lower'),
                    func.sum(Forecast.confidence_upper).label('upper')
                ).filter(
                    Forecast.aggregation_level == 'daily',
                    func.date(Forecast.forecast_date) >= week['start'],
                    func.date(Forecast.forecast_date) <= week['end']
                )
                
                # Add generated_at filter for historical backtesting
                if generated_before:
                    total_forecast_query = total_forecast_query.filter(
                        Forecast.generated_at < generated_before
                    )
                
                result = total_forecast_query.first()
                total_forecast = result.total or 0
                total_lower = result.lower or 0
                total_upper = result.upper or 0
                
                forecast_data.append({
                    'week': week['week'],
                    'start': week['start'].isoformat(),
                    'end': week['end'].isoformat(),
                    'sales': float(total_forecast),
                    'confidence_lower': float(total_lower),
                    'confidence_upper': float(total_upper)
                })
            else:
                # Single product forecast - aggregate daily forecasts
                forecast_query = db.session.query(
                    func.sum(Forecast.predicted_quantity).label('total'),
                    func.sum(Forecast.confidence_lower).label('lower'),
                    func.sum(Forecast.confidence_upper).label('upper')
                ).filter(
                    Forecast.product_id == product_id,
                    Forecast.aggregation_level == 'daily',
                    func.date(Forecast.forecast_date) >= week['start'],
                    func.date(Forecast.forecast_date) <= week['end']
                )
                
                # Add generated_at filter for historical backtesting
                if generated_before:
                    forecast_query = forecast_query.filter(
                        Forecast.generated_at < generated_before
                    )
                
                result = forecast_query.first()
                
                if result and result.total:
                    forecast_data.append({
                        'week': week['week'],
                        'start': week['start'].isoformat(),
                        'end': week['end'].isoformat(),
                        'sales': float(result.total or 0),
                        'confidence_lower': float(result.lower or 0),
                        'confidence_upper': float(result.upper or 0)
                    })
                else:
                    # No forecast available, add 0
                    forecast_data.append({
                        'week': week['week'],
                            'start': week['start'].isoformat(),
                            'end': week['end'].isoformat(),
                            'sales': 0,
                            'confidence_lower': 0,
                            'confidence_upper': 0
                        })
        
        # Calculate accuracy (last week's forecast vs actual if available)
        accuracy = None
        if len(actual_data) > 0 and len(actual_data) >= 2:
            last_week = actual_data[-1]
            # Find forecast for that week (created before it happened)
            past_forecast = Forecast.query.filter(
                Forecast.product_id == product_id,
                Forecast.aggregation_level == 'weekly',
                func.date(Forecast.forecast_date) == datetime.strptime(last_week['start'], '%Y-%m-%d').date()
            ).first()
            
            if past_forecast and last_week['sales'] > 0:
                error = abs(past_forecast.predicted_quantity - last_week['sales']) / last_week['sales']
                accuracy = round((1 - error) * 100, 2)
        
        return jsonify({
            'success': True,
            'product_id': product_id,
            'month': month_start.strftime('%Y-%m'),
            'month_name': month_start.strftime('%B %Y'),
            'current_week': current_week_num,
            'actual': actual_data,
            'forecast': forecast_data,
            'accuracy': accuracy
        })
        
    except Exception as e:
        import traceback
        print(f"Error in /forecast/weekly: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# Removed deprecated /forecast-history endpoint; functionality consolidated into synchronized views


@api_bp.route('/wipe-fake-data', methods=['POST'])
@login_required
def wipe_fake_data():
    """
    Delete all fake data (products and sales) created by the fake data generator.
    Admin only endpoint.
    """
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({
                'success': False,
                'error': 'Unauthorized. Admin access required.'
            }), 403
        
        # Count fake records before deletion
        fake_sales_count = Sale.query.filter_by(is_fake=True).count()
        fake_products_count = Product.query.filter_by(is_fake=True).count()
        
        if fake_sales_count == 0 and fake_products_count == 0:
            return jsonify({
                'success': True,
                'message': 'No fake data found to delete.',
                'deleted_sales': 0,
                'deleted_products': 0
            })
        
        # Delete fake sales first (due to foreign key constraints)
        Sale.query.filter_by(is_fake=True).delete()
        
        # Delete fake products
        Product.query.filter_by(is_fake=True).delete()
        
        # Commit transaction
        db.session.commit()
        
        # Log the action
        log_entry = Log(
            user_id=current_user.id,
            action=f"Wiped fake data: {fake_sales_count} sales, {fake_products_count} products"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {fake_sales_count:,} fake sales and {fake_products_count} fake products.',
            'deleted_sales': fake_sales_count,
            'deleted_products': fake_products_count
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error wiping fake data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Failed to wipe fake data: {str(e)}'
        }), 500


@api_bp.route('/generate-fake-data', methods=['POST'])
@login_required
def generate_fake_data_endpoint():
    """
    Trigger the fake data generation script.
    Admin only endpoint.
    """
    try:
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({
                'success': False,
                'error': 'Unauthorized. Admin access required.'
            }), 403
        
        # Import and run the generation function
        import sys
        import os
        
        # Load generator module dynamically
        scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts')
        import importlib.util
        gen_path = os.path.join(scripts_path, 'generate_fake_data.py')
        spec = importlib.util.spec_from_file_location('scripts.generate_fake_data', gen_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader, 'Failed to load generate_fake_data module spec'
        spec.loader.exec_module(module)  # type: ignore
        seed_fake_data = getattr(module, 'seed_fake_data')
        
        # Count before
        products_before = Product.query.count()
        sales_before = Sale.query.count()
        
        # Generate data
        seed_fake_data()
        
        # Count after
        products_after = Product.query.count()
        sales_after = Sale.query.count()
        
        products_created = products_after - products_before
        sales_created = sales_after - sales_before
        
        # Log the action
        log_entry = Log(
            user_id=current_user.id,
            action=f"Generated fake data: {products_created} products, {sales_created} sales"
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully generated fake data!',
            'products_created': products_created,
            'sales_created': sales_created
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error generating fake data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Failed to generate fake data: {str(e)}'
        }), 500


@api_bp.route('/sales-report', methods=['GET'])
@login_required
def sales_report():
    """Get sales report data for the specified period."""
    try:
        period = request.args.get('period', '30d')
        
        # Calculate date range
        end_date = datetime.now()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
            period_label = 'Last 7 Days'
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
            period_label = 'Last 30 Days'
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
            period_label = 'Last 90 Days'
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
            period_label = 'Last Year'
        elif period == 'all':
            start_date = datetime(2000, 1, 1)
            period_label = 'All Time'
        else:
            start_date = end_date - timedelta(days=30)
            period_label = 'Last 30 Days'
        
        # Query sales with product information
        sales_query = db.session.query(
            Sale.sale_date,
            Product.name.label('product_name'),
            Sale.quantity,
            Sale.price,
            (Sale.quantity * Sale.price).label('revenue')
        ).join(Product, Sale.product_id == Product.id).filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).order_by(Sale.sale_date.desc())
        
        sales_data = []
        total_revenue = 0
        
        for sale in sales_query.all():
            revenue = float(sale.quantity * sale.price)
            sales_data.append({
                'date': sale.sale_date.strftime('%Y-%m-%d'),
                'product_name': sale.product_name,
                'quantity': sale.quantity,
                'price': float(sale.price),
                'revenue': revenue
            })
            total_revenue += revenue
        
        return jsonify({
            'success': True,
            'period': period,
            'period_label': period_label,
            'sales': sales_data,
            'total_sales': len(sales_data),
            'total_revenue': total_revenue
        })
        
    except Exception as e:
        import traceback
        print(f"Error generating sales report: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Failed to generate sales report: {str(e)}'
        }), 500


@api_bp.route('/sales-report/download', methods=['GET'])
@login_required
def download_sales_report():
    """Download sales report as CSV."""
    try:
        period = request.args.get('period', '30d')
        
        # Calculate date range
        end_date = datetime.now()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == 'all':
            start_date = datetime(2000, 1, 1)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Query sales
        sales_query = db.session.query(
            Sale.sale_date,
            Product.name.label('product_name'),
            Product.category,
            Sale.quantity,
            Sale.price,
            (Sale.quantity * Sale.price).label('revenue')
        ).join(Product, Sale.product_id == Product.id).filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date
        ).order_by(Sale.sale_date.desc())
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Product', 'Category', 'Quantity', 'Price', 'Revenue'])
        
        for sale in sales_query.all():
            writer.writerow([
                sale.sale_date.strftime('%Y-%m-%d'),
                sale.product_name,
                sale.category or 'N/A',
                sale.quantity,
                f'{sale.price:.2f}',
                f'{sale.quantity * sale.price:.2f}'
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'sales_report_{period}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        import traceback
        print(f"Error downloading sales report: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@api_bp.route('/inventory-report', methods=['GET'])
@login_required
def inventory_report():
    """Get inventory report data."""
    try:
        report_type = request.args.get('type', 'current')
        
        # Base query
        query = db.session.query(
            Product.name.label('product_name'),
            Product.category,
            Product.current_stock,
            Product.unit_cost
        )
        
        # Apply filters based on report type
        if report_type == 'low':
            query = query.filter(Product.current_stock <= 50)
            report_label = 'Low Stock Items'
        elif report_type == 'current':
            query = query.filter(Product.current_stock > 0)
            report_label = 'Current Stock Levels'
        else:  # all
            report_label = 'All Inventory'
        
        query = query.order_by(Product.current_stock.asc())
        
        inventory_data = []
        total_value = 0
        
        for item in query.all():
            unit_cost = float(item.unit_cost) if item.unit_cost else 0
            item_value = item.current_stock * unit_cost
            
            inventory_data.append({
                'product_name': item.product_name,
                'category': item.category,
                'current_stock': item.current_stock,
                'unit_cost': unit_cost,
                'total_value': item_value
            })
            total_value += item_value
        
        return jsonify({
            'success': True,
            'report_type': report_type,
            'report_label': report_label,
            'inventory': inventory_data,
            'total_value': total_value
        })
        
    except Exception as e:
        import traceback
        print(f"Error generating inventory report: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Failed to generate inventory report: {str(e)}'
        }), 500


@api_bp.route('/inventory-report/download', methods=['GET'])
@login_required
def download_inventory_report():
    """Download inventory report as CSV."""
    try:
        report_type = request.args.get('type', 'current')
        
        # Base query
        query = db.session.query(
            Product.name.label('product_name'),
            Product.category,
            Product.current_stock,
            Product.unit_cost
        )
        
        # Apply filters
        if report_type == 'low':
            query = query.filter(Product.current_stock <= 50)
        elif report_type == 'current':
            query = query.filter(Product.current_stock > 0)
        
        query = query.order_by(Product.current_stock.asc())
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'Category', 'Current Stock', 'Unit Cost', 'Total Value', 'Status'])
        
        for item in query.all():
            unit_cost = float(item.unit_cost) if item.unit_cost else 0
            total_value = item.current_stock * unit_cost
            
            if item.current_stock <= 10:
                status = 'Low Stock'
            elif item.current_stock <= 50:
                status = 'Medium'
            else:
                status = 'Good'
            
            writer.writerow([
                item.product_name,
                item.category or 'N/A',
                item.current_stock,
                f'{unit_cost:.2f}',
                f'{total_value:.2f}',
                status
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'inventory_report_{report_type}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        import traceback
        print(f"Error downloading inventory report: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500







