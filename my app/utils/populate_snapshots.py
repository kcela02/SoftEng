"""
Populate ForecastSnapshot table from Forecast table with generated_at dates
"""
from datetime import datetime, timedelta
from models import db, Forecast, ForecastSnapshot, Sale
from sqlalchemy import func


def populate_snapshots_from_rolling_forecasts():
    """
    Create ForecastSnapshot records from Forecast records that have generated_at set.
    Match with actual sales data to enable accuracy calculations.
    
    Returns:
        Tuple of (snapshots_created, snapshots_with_actuals)
    """
    snapshots_created = 0
    snapshots_with_actuals = 0
    
    # Get all forecasts with generated_at (from rolling retrain)
    forecasts = Forecast.query.filter(
        Forecast.generated_at.isnot(None)
    ).all()
    
    print(f"Found {len(forecasts)} forecasts with generated_at dates")
    
    for forecast in forecasts:
        # Check if snapshot already exists
        existing = ForecastSnapshot.query.filter_by(
            product_id=forecast.product_id,
            forecast_date=forecast.forecast_date.date() if isinstance(forecast.forecast_date, datetime) else forecast.forecast_date,
            snapshot_created_at=forecast.generated_at
        ).first()
        
        if existing:
            continue
        
        # Convert forecast_date to date object
        forecast_date = forecast.forecast_date.date() if isinstance(forecast.forecast_date, datetime) else forecast.forecast_date
        
        # Calculate forecast horizon
        if forecast.generated_at:
            horizon_days = (forecast_date - forecast.generated_at).days
            if horizon_days == 1:
                horizon = '1-day'
            elif horizon_days <= 7:
                horizon = '7-day'
            elif horizon_days <= 30:
                horizon = '30-day'
            else:
                horizon = f'{horizon_days}-day'
        else:
            horizon = 'unknown'
        
        # Try to find actual sales for this date
        actual_sale = db.session.query(
            func.sum(Sale.quantity)
        ).filter(
            Sale.product_id == forecast.product_id,
            func.date(Sale.sale_date) == forecast_date
        ).scalar()
        
        # Create snapshot
        snapshot = ForecastSnapshot(
            product_id=forecast.product_id,
            forecast_date=forecast_date,
            predicted_quantity=forecast.predicted_quantity,
            actual_quantity=float(actual_sale) if actual_sale else None,
            snapshot_created_at=forecast.generated_at,
            model_used=forecast.model_used or 'LINEAR_REGRESSION',
            forecast_horizon=horizon,
            confidence_lower=forecast.confidence_lower,
            confidence_upper=forecast.confidence_upper,
            mae=forecast.mae,
            rmse=forecast.rmse
        )
        
        # Calculate accuracy if actual exists
        if actual_sale and actual_sale > 0:
            error_pct = abs(forecast.predicted_quantity - actual_sale) / actual_sale * 100
            accuracy_pct = max(0, 100 - error_pct)
            snapshot.error_percentage = error_pct
            snapshot.accuracy = accuracy_pct
            snapshots_with_actuals += 1
        
        db.session.add(snapshot)
        snapshots_created += 1
        
        # Commit in batches to avoid memory issues
        if snapshots_created % 100 == 0:
            db.session.commit()
            print(f"Created {snapshots_created} snapshots...")
    
    # Final commit
    db.session.commit()
    
    print(f"✓ Created {snapshots_created} snapshots")
    print(f"✓ {snapshots_with_actuals} snapshots have actual sales data")
    
    return snapshots_created, snapshots_with_actuals


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        populate_snapshots_from_rolling_forecasts()
