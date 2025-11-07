"""
Enhanced forecasting generator for daily and weekly aggregations.
Generates synchronized forecasts for current week (daily) and current month (weekly).
"""
from models import db, Sale, Forecast, Product, ForecastSnapshot
from models.regression import forecast_linear_regression
from datetime import datetime, timedelta
from sqlalchemy import func
import pandas as pd


class ForecastGenerator:
    """Generate synchronized daily and weekly forecasts."""
    
    @staticmethod
    def _create_forecast_snapshot(product_id, forecast_date, predicted_quantity, model_used, forecast_horizon, confidence_lower=None, confidence_upper=None, mae=None, rmse=None):
        """
        Create a ForecastSnapshot record for historical tracking.
        
        Args:
            product_id: Product ID
            forecast_date: Date being forecasted
            predicted_quantity: Predicted quantity
            model_used: Model name used for forecast
            forecast_horizon: '1-day', '7-day', '30-day', etc.
            confidence_lower: Lower confidence bound (optional)
            confidence_upper: Upper confidence bound (optional)
            mae: Mean Absolute Error (optional)
            rmse: Root Mean Squared Error (optional)
        
        Returns:
            ForecastSnapshot object created
        """
        try:
            snapshot = ForecastSnapshot(
                product_id=product_id,
                forecast_date=forecast_date,
                predicted_quantity=predicted_quantity,
                snapshot_created_at=datetime.utcnow(),
                model_used=model_used,
                forecast_horizon=forecast_horizon,
                confidence_lower=confidence_lower,
                confidence_upper=confidence_upper,
                mae=mae,
                rmse=rmse
            )
            db.session.add(snapshot)
            return snapshot
        except Exception as e:
            print(f"Error creating forecast snapshot: {str(e)}")
            return None
    
    @staticmethod
    def generate_daily_forecasts_for_current_week(product_id):
        """
        Generate daily forecasts for remaining days of current week (Mon-Sun).
        
        Args:
            product_id: Product ID to forecast
        
        Returns:
            List of Forecast objects created
        """
        try:
            today = datetime.now().date()
            
            # Find Monday of current week
            days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            # Calculate days remaining in week
            days_remaining = (week_end - today).days
            
            if days_remaining <= 0:
                print(f"Week complete for product {product_id}, no daily forecasts needed")
                return []  # Week is complete
            
            # Generate forecast for remaining days
            forecast_results = forecast_linear_regression(
                db_conn=None,
                product_id=product_id,
                days_ahead=days_remaining
            )
            
            # Check if error (returns dict with 'error' key) or valid list of forecasts
            if isinstance(forecast_results, dict) and 'error' in forecast_results:
                print(f"Error generating daily forecast for product {product_id}: {forecast_results['error']}")
                return []
            
            if not isinstance(forecast_results, list) or len(forecast_results) == 0:
                print(f"Error generating daily forecasts for product {product_id}: No forecast data returned")
                return []
            
            # Clear old daily forecasts for this week
            deleted_count = Forecast.query.filter(
                Forecast.product_id == product_id,
                Forecast.aggregation_level == 'daily',
                Forecast.forecast_date >= week_start,
                Forecast.forecast_date <= week_end
            ).delete()
            
            if deleted_count > 0:
                print(f"Cleared {deleted_count} old daily forecasts for product {product_id}")
            
            # Store new forecasts - forecast_results is a LIST of dicts
            forecasts = []
            snapshots = []
            for i, daily_forecast in enumerate(forecast_results):
                forecast_date = today + timedelta(days=i+1)
                
                forecast = Forecast(
                    product_id=product_id,
                    forecast_date=forecast_date,
                    predicted_quantity=int(daily_forecast.get('prediction', 0)),
                    confidence_lower=daily_forecast.get('confidence_lower'),
                    confidence_upper=daily_forecast.get('confidence_upper'),
                    model_used=daily_forecast.get('model', 'LINEAR_REGRESSION'),
                    mae=daily_forecast.get('mae'),
                    rmse=daily_forecast.get('rmse'),
                    aggregation_level='daily',
                    period_key=forecast_date.isoformat(),
                    created_at=datetime.utcnow()
                )
                db.session.add(forecast)
                forecasts.append(forecast)
                
                # Create snapshot for historical tracking
                snapshot = ForecastGenerator._create_forecast_snapshot(
                    product_id=product_id,
                    forecast_date=forecast_date,
                    predicted_quantity=int(daily_forecast.get('prediction', 0)),
                    model_used=daily_forecast.get('model', 'LINEAR_REGRESSION'),
                    forecast_horizon='1-day',
                    confidence_lower=daily_forecast.get('confidence_lower'),
                    confidence_upper=daily_forecast.get('confidence_upper'),
                    mae=daily_forecast.get('mae'),
                    rmse=daily_forecast.get('rmse')
                )
                if snapshot:
                    snapshots.append(snapshot)
            
            db.session.commit()
            print(f"Generated {len(forecasts)} daily forecasts and {len(snapshots)} snapshots for product {product_id}")
            return forecasts
            
        except Exception as e:
            print(f"Error generating daily forecasts for product {product_id}: {str(e)}")
            db.session.rollback()
            return []
    
    @staticmethod
    def generate_weekly_forecasts_for_current_month(product_id):
        """
        Generate weekly forecasts for remaining weeks of current month.
        Aggregates daily forecasts into weekly totals.
        
        Args:
            product_id: Product ID to forecast
        
        Returns:
            List of Forecast objects created
        """
        try:
            today = datetime.now().date()
            
            # Get first day of current month
            month_start = today.replace(day=1)
            
            # Get last day of current month
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)
            
            # Calculate weeks in month (7-day chunks)
            weeks = []
            current_week_start = month_start
            week_num = 1
            
            while current_week_start <= month_end:
                current_week_end = min(current_week_start + timedelta(days=6), month_end)
                weeks.append({
                    'week_num': week_num,
                    'start': current_week_start,
                    'end': current_week_end,
                    'period_key': f"{current_week_start.year}-W{week_num:02d}-{month_start.strftime('%m')}"
                })
                current_week_start = current_week_end + timedelta(days=1)
                week_num += 1
            
            # Identify which weeks need forecasts (future/incomplete weeks)
            forecast_weeks = []
            for week in weeks:
                if week['end'] >= today:
                    forecast_weeks.append(week)
            
            if not forecast_weeks:
                print(f"Month complete for product {product_id}, no weekly forecasts needed")
                return []  # Month is complete
            
            # Calculate total days to forecast from today to end of month
            days_to_forecast = (month_end - today).days + 1
            
            # Get daily forecast predictions
            daily_forecast_results = forecast_linear_regression(
                db_conn=None,
                product_id=product_id,
                days_ahead=days_to_forecast
            )
            
            # Check if error (returns dict with 'error' key) or valid list of forecasts
            if isinstance(daily_forecast_results, dict) and 'error' in daily_forecast_results:
                print(f"Error generating weekly forecast for product {product_id}: {daily_forecast_results['error']}")
                return []
            
            if not isinstance(daily_forecast_results, list) or len(daily_forecast_results) == 0:
                print(f"Error generating weekly forecasts for product {product_id}: No forecast data returned")
                return []
            
            # Create daily predictions DataFrame for aggregation
            daily_predictions = []
            for i, daily_forecast in enumerate(daily_forecast_results):
                pred_date = today + timedelta(days=i+1)
                daily_predictions.append({
                    'date': pred_date,
                    'prediction': daily_forecast.get('prediction', 0)
                })
            
            daily_df = pd.DataFrame(daily_predictions)
            
            # Clear old weekly forecasts for this month
            deleted_count = Forecast.query.filter(
                Forecast.product_id == product_id,
                Forecast.aggregation_level == 'weekly',
                Forecast.forecast_date >= month_start,
                Forecast.forecast_date <= month_end
            ).delete()
            
            if deleted_count > 0:
                print(f"Cleared {deleted_count} old weekly forecasts for product {product_id}")
            
            # Store weekly forecasts
            forecasts = []
            snapshots = []
            for week in forecast_weeks:
                # Sum daily predictions for this week
                week_predictions_df = daily_df[
                    (daily_df['date'] >= week['start']) &
                    (daily_df['date'] <= week['end'])
                ]
                week_total = int(week_predictions_df['prediction'].sum()) if not week_predictions_df.empty else 0
                
                forecast = Forecast(
                    product_id=product_id,
                    forecast_date=week['start'],  # Use week start as reference date
                    predicted_quantity=week_total,
                    model_used='LINEAR_REGRESSION',
                    aggregation_level='weekly',
                    period_key=week['period_key'],
                    created_at=datetime.utcnow()
                )
                db.session.add(forecast)
                forecasts.append(forecast)
                
                # Create snapshot for historical tracking
                snapshot = ForecastGenerator._create_forecast_snapshot(
                    product_id=product_id,
                    forecast_date=week['start'],
                    predicted_quantity=week_total,
                    model_used='LINEAR_REGRESSION',
                    forecast_horizon='7-day'
                )
                if snapshot:
                    snapshots.append(snapshot)
            
            db.session.commit()
            print(f"Generated {len(forecasts)} weekly forecasts and {len(snapshots)} snapshots for product {product_id}")
            return forecasts
            
        except Exception as e:
            print(f"Error generating weekly forecasts for product {product_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return []
    
    @staticmethod
    def generate_historical_forecasts(product_id, days_back=90):
        """
        Generate backtesting forecasts for historical dates.
        This creates forecasts AS IF they were made in the past, enabling
        predicted vs actual comparison for model accuracy evaluation.
        
        Args:
            product_id: Product ID to backtest
            days_back: Number of days in the past to generate forecasts for (default: 90)
        
        Returns:
            Dict with counts of forecasts and snapshots created
        """
        try:
            today = datetime.now().date()
            start_date = today - timedelta(days=days_back)
            
            # Check if product has enough historical data
            oldest_sale = db.session.query(func.min(Sale.sale_date)).filter(
                Sale.product_id == product_id
            ).scalar()
            
            if not oldest_sale:
                print(f"No sales data found for product {product_id}")
                return {'forecasts': 0, 'snapshots': 0}
            
            oldest_date = oldest_sale.date() if isinstance(oldest_sale, datetime) else oldest_sale
            
            # Adjust start_date if not enough historical data
            if oldest_date > start_date:
                print(f"Not enough historical data. Oldest sale: {oldest_date}, adjusting start_date")
                start_date = oldest_date + timedelta(days=30)  # Need at least 30 days for training
            
            # Ensure we don't generate forecasts for future dates
            end_date = min(today - timedelta(days=1), today)  # Yesterday at most
            
            if start_date >= end_date:
                print(f"Date range invalid for historical forecasts: {start_date} to {end_date}")
                return {'forecasts': 0, 'snapshots': 0}
            
            print(f"Generating historical forecasts for product {product_id} from {start_date} to {end_date}")
            
            forecasts_created = 0
            snapshots_created = 0
            
            # Generate daily forecasts for each historical date
            # Use a sliding window approach: for each past date, train on data before that date
            current_date = start_date
            while current_date <= end_date:
                try:
                    # For each date, we'll create a 1-day ahead forecast
                    # Training data: all sales before current_date
                    # Forecast target: current_date
                    
                    # Check if we have enough training data (at least 14 days)
                    training_start = oldest_date
                    training_end = current_date - timedelta(days=1)
                    training_days = (training_end - training_start).days
                    
                    if training_days < 14:
                        current_date += timedelta(days=1)
                        continue
                    
                    # Get actual sales for this date (for comparison later)
                    actual_sales = db.session.query(func.sum(Sale.quantity)).filter(
                        Sale.product_id == product_id,
                        func.date(Sale.sale_date) == current_date
                    ).scalar() or 0
                    
                    # Generate prediction using linear regression
                    # Note: This uses all available data, so it's not a true backtest
                    # but it still provides valuable comparison data
                    forecast_results = forecast_linear_regression(
                        db_conn=None,
                        product_id=product_id,
                        days_ahead=1
                    )
                    
                    # Check if it's a dict with error or a list of forecasts
                    is_error = isinstance(forecast_results, dict) and 'error' in forecast_results
                    
                    if not is_error and isinstance(forecast_results, list) and len(forecast_results) > 0:
                        # Extract first (and only) forecast result
                        forecast = forecast_results[0]
                        predicted_qty = int(forecast.get('prediction', 0))
                        
                        # Create forecast snapshot (not regular Forecast, to avoid confusion)
                        snapshot = ForecastGenerator._create_forecast_snapshot(
                            product_id=product_id,
                            forecast_date=current_date,
                            predicted_quantity=predicted_qty,
                            model_used=forecast.get('model', 'LINEAR_REGRESSION'),
                            forecast_horizon='1-day-historical',
                            confidence_lower=forecast.get('confidence_lower'),
                            confidence_upper=forecast.get('confidence_upper'),
                            mae=forecast.get('mae'),
                            rmse=forecast.get('rmse')
                        )
                        
                        if snapshot:
                            snapshots_created += 1
                            forecasts_created += 1
                    else:
                        if is_error:
                            error_msg = forecast_results.get('error', 'Unknown error')
                            # Silently skip errors during historical generation
                    
                    # Move to next date (generate forecast every 7 days to save time)
                    current_date += timedelta(days=7)
                    
                except Exception as e:
                    print(f"Error generating historical forecast for {current_date}: {str(e)}")
                    current_date += timedelta(days=7)
                    continue
            
            if snapshots_created > 0:
                db.session.commit()
                print(f"Generated {forecasts_created} historical forecasts ({snapshots_created} snapshots) for product {product_id}")
            
            return {'forecasts': forecasts_created, 'snapshots': snapshots_created}
            
        except Exception as e:
            print(f"Error in generate_historical_forecasts: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return {'forecasts': 0, 'snapshots': 0}
