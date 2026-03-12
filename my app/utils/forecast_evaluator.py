"""
Forecast accuracy evaluation utilities.
Calculates MAPE (Mean Absolute Percentage Error) and other accuracy metrics.
"""
from models import db, Sale, Forecast
from datetime import datetime, timedelta, date as date_type
from sqlalchemy import func
import time as _time

# Simple in-process TTL cache: {days_back: (accuracy, timestamp)}
_mape_cache: dict = {}
_MAPE_CACHE_TTL = 120  # seconds — recompute at most every 2 minutes


class ForecastEvaluator:
    """Evaluate forecasting model accuracy."""
    
    @staticmethod
    def calculate_mape(horizon_days=7, days_back=7):
        """
        Calculate Mean Absolute Percentage Error for forecasts.
        
        Args:
            horizon_days: Forecast horizon (1, 7, or 30 days)
            days_back: How many days to evaluate
        
        Returns:
            Accuracy percentage (0-100), where 100% is perfect
        """
        try:
            # Use the last date with actual sales data instead of today
            last_sale_date = db.session.query(func.max(Sale.sale_date)).scalar()
            if not last_sale_date:
                return 0.0

            # Check TTL cache first (accuracy changes rarely)
            cache_key = days_back
            cached = _mape_cache.get(cache_key)
            if cached and (_time.time() - cached[1]) < _MAPE_CACHE_TTL:
                return cached[0]

            # Convert to date if datetime
            end_date = last_sale_date.date() if hasattr(last_sale_date, 'date') else last_sale_date
            start_date = end_date - timedelta(days=days_back)

            # Use datetime bounds so index on sale_date / forecast_date is usable
            start_dt = datetime(start_date.year, start_date.month, start_date.day)
            end_dt   = datetime(end_date.year,   end_date.month,   end_date.day, 23, 59, 59)

            # Query 1: aggregate actual sales by product + day (uses sale_date index)
            sales_rows = db.session.query(
                Sale.product_id,
                func.date(Sale.sale_date).label('sale_day'),
                func.sum(Sale.quantity).label('actual_qty')
            ).filter(
                Sale.sale_date >= start_dt,
                Sale.sale_date <= end_dt,
                Sale.is_fake == False
            ).group_by(Sale.product_id, func.date(Sale.sale_date)).all()

            actual_map = {(r.product_id, str(r.sale_day)): float(r.actual_qty) for r in sales_rows}

            # Query 2: aggregate forecasts by product + day
            # Only use daily-level forecasts to avoid double-counting with weekly aggregates
            fc_rows = db.session.query(
                Forecast.product_id,
                func.date(Forecast.forecast_date).label('fc_day'),
                func.sum(Forecast.predicted_quantity).label('predicted_qty')
            ).filter(
                Forecast.forecast_date >= start_dt,
                Forecast.forecast_date <= end_dt,
                Forecast.aggregation_level == 'daily'
            ).group_by(Forecast.product_id, func.date(Forecast.forecast_date)).all()

            if not fc_rows:
                return 0.0

            total_abs_error = 0.0
            total_actual = 0.0

            for product_id, fc_day, predicted_qty in fc_rows:
                actual    = actual_map.get((product_id, str(fc_day)), 0.0)
                predicted = float(predicted_qty) if predicted_qty else 0.0

                if actual == 0:
                    continue

                total_abs_error += abs(predicted - actual)
                total_actual += actual

            if total_actual == 0:
                return 0.0

            # Use WMAPE (Weighted MAPE) — more robust against outliers
            # than plain MAPE which can exceed 100% from a few bad points
            wmape    = (total_abs_error / total_actual) * 100
            accuracy = max(0.0, 100.0 - wmape)
            result   = round(accuracy, 2)

            # Store in cache
            _mape_cache[cache_key] = (result, _time.time())
            return result

        except Exception as e:
            print(f"Error calculating MAPE: {str(e)}")
            return 0.0
    
    @staticmethod
    def get_multi_horizon_accuracy(days_back=7):
        """
        Get accuracy for all forecast horizons (1-day, 7-day, 30-day).
        
        Args:
            days_back: How many days to evaluate
        
        Returns:
            Dictionary with accuracy for each horizon
        """
        try:
            return {
                '1_day': ForecastEvaluator.calculate_mape(horizon_days=1, days_back=days_back),
                '7_day': ForecastEvaluator.calculate_mape(horizon_days=7, days_back=days_back),
                '30_day': ForecastEvaluator.calculate_mape(horizon_days=30, days_back=min(days_back, 30))
            }
        except Exception as e:
            print(f"Error getting multi-horizon accuracy: {str(e)}")
            return {
                '1_day': 0.0,
                '7_day': 0.0,
                '30_day': 0.0
            }
    
    @staticmethod
    def get_product_accuracy(product_id, days_back=7):
        """
        Calculate forecast accuracy for a specific product.
        
        Args:
            product_id: Product ID
            days_back: How many days to evaluate
        
        Returns:
            Accuracy percentage (0-100)
        """
        try:
            # Use the last date with actual sales data
            last_sale_date = db.session.query(func.max(Sale.sale_date)).scalar()
            if not last_sale_date:
                return 0.0
            
            end_date = last_sale_date.date() if hasattr(last_sale_date, 'date') else last_sale_date
            start_date = end_date - timedelta(days=days_back)
            
            # Get forecasts for this product
            forecasts = Forecast.query.filter(
                Forecast.product_id == product_id,
                Forecast.aggregation_level == 'daily',
                func.date(Forecast.forecast_date) >= start_date,
                func.date(Forecast.forecast_date) <= end_date
            ).all()
            
            if not forecasts:
                return 0.0
            
            total_abs_error = 0.0
            total_actual = 0.0
            
            for forecast in forecasts:
                # Get actual sales
                actual_sales = db.session.query(
                    func.sum(Sale.quantity)
                ).filter(
                    Sale.product_id == product_id,
                    Sale.is_fake == False,
                    func.date(Sale.sale_date) == func.date(forecast.forecast_date)
                ).scalar()
                
                actual = float(actual_sales) if actual_sales else 0.0
                predicted = float(forecast.predicted_quantity) if forecast.predicted_quantity else 0.0
                
                if actual == 0:
                    continue
                
                total_abs_error += abs(predicted - actual)
                total_actual += actual
            
            if total_actual == 0:
                return 0.0
            
            wmape = (total_abs_error / total_actual) * 100
            accuracy = max(0.0, 100.0 - wmape)
            
            return round(accuracy, 2)
            
        except Exception as e:
            print(f"Error calculating product accuracy: {str(e)}")
            return 0.0
    
    @staticmethod
    def get_forecast_vs_actual(product_id, days=7):
        """
        Get forecast vs actual sales comparison for charting.
        
        Args:
            product_id: Product ID
            days: Number of days to compare
        
        Returns:
            Dictionary with dates, actual, and forecast arrays
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            dates = []
            actuals = []
            forecasts = []
            
            current_date = start_date
            while current_date <= end_date:
                dates.append(current_date.strftime('%Y-%m-%d'))
                
                # Get actual sales
                actual_sales = db.session.query(
                    func.sum(Sale.quantity)
                ).filter(
                    Sale.product_id == product_id,
                    func.date(Sale.sale_date) == current_date
                ).scalar()
                
                actuals.append(float(actual_sales) if actual_sales else 0.0)
                
                # Get forecast
                forecast = Forecast.query.filter(
                    Forecast.product_id == product_id,
                    func.date(Forecast.forecast_date) == current_date
                ).order_by(Forecast.created_at.desc()).first()
                
                forecasts.append(float(forecast.forecast_value) if forecast else 0.0)
                
                current_date += timedelta(days=1)
            
            return {
                'dates': dates,
                'actual': actuals,
                'forecast': forecasts
            }
            
        except Exception as e:
            print(f"Error getting forecast vs actual: {str(e)}")
            return {
                'dates': [],
                'actual': [],
                'forecast': []
            }
