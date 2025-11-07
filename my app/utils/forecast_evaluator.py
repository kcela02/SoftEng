"""
Forecast accuracy evaluation utilities.
Calculates MAPE (Mean Absolute Percentage Error) and other accuracy metrics.
"""
from models import db, Sale, Forecast
from datetime import datetime, timedelta
from sqlalchemy import func


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
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            # Get all forecasts in the evaluation period
            forecasts = Forecast.query.filter(
                func.date(Forecast.forecast_date) >= start_date,
                func.date(Forecast.forecast_date) <= end_date
            ).all()
            
            if not forecasts:
                return 0.0
            
            total_percentage_error = 0.0
            valid_count = 0
            
            for forecast in forecasts:
                # Get actual sales for that date and product
                actual_sales = db.session.query(
                    func.sum(Sale.quantity)
                ).filter(
                    Sale.product_id == forecast.product_id,
                    func.date(Sale.sale_date) == func.date(forecast.forecast_date)
                ).scalar()
                
                actual = float(actual_sales) if actual_sales else 0.0
                predicted = float(forecast.predicted_quantity) if forecast.predicted_quantity else 0.0
                
                # Skip if no actual sales (can't calculate error)
                if actual == 0:
                    continue
                
                # Calculate absolute percentage error
                percentage_error = abs(predicted - actual) / actual
                total_percentage_error += percentage_error
                valid_count += 1
            
            if valid_count == 0:
                return 0.0
            
            # Calculate MAPE
            mape = (total_percentage_error / valid_count) * 100
            
            # Convert to accuracy percentage (100% - MAPE)
            accuracy = max(0.0, 100.0 - mape)
            
            return round(accuracy, 2)
            
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
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            # Get forecasts for this product
            forecasts = Forecast.query.filter(
                Forecast.product_id == product_id,
                func.date(Forecast.forecast_date) >= start_date,
                func.date(Forecast.forecast_date) <= end_date
            ).all()
            
            if not forecasts:
                return 0.0
            
            total_percentage_error = 0.0
            valid_count = 0
            
            for forecast in forecasts:
                # Get actual sales
                actual_sales = db.session.query(
                    func.sum(Sale.quantity)
                ).filter(
                    Sale.product_id == product_id,
                    func.date(Sale.sale_date) == func.date(forecast.forecast_date)
                ).scalar()
                
                actual = float(actual_sales) if actual_sales else 0.0
                predicted = float(forecast.forecast_value) if forecast.forecast_value else 0.0
                
                if actual == 0:
                    continue
                
                percentage_error = abs(predicted - actual) / actual
                total_percentage_error += percentage_error
                valid_count += 1
            
            if valid_count == 0:
                return 0.0
            
            mape = (total_percentage_error / valid_count) * 100
            accuracy = max(0.0, 100.0 - mape)
            
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
