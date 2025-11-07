"""
Automated forecasting model training pipeline.
Triggered by CSV upload to retrain models and generate multi-horizon forecasts.
"""
from models import db, Sale, Product, Forecast, ForecastSnapshot
from models.regression import forecast_linear_regression
from datetime import datetime, timedelta
from utils.activity_logger import ActivityLogger


class ForecastingPipeline:
    """Centralized forecasting model training and prediction pipeline."""
    
    @staticmethod
    def retrain_on_csv_upload(user_id=None):
        """
        Main retraining pipeline triggered after CSV upload.
        
        Args:
            user_id: User ID for activity logging
        
        Returns:
            Dictionary with retraining statistics
        """
        try:
            # Get all products that have sales data
            products_with_sales = db.session.query(Product).join(
                Sale, Product.id == Sale.product_id
            ).distinct().all()
            
            retrained_count = 0
            skipped_count = 0
            failed_count = 0
            
            for product in products_with_sales:
                try:
                    # Check if enough historical data exists (minimum 2 years = 730 days)
                    # Get date range of sales
                    first_sale = db.session.query(db.func.min(Sale.sale_date)).filter(
                        Sale.product_id == product.id
                    ).scalar()
                    last_sale = db.session.query(db.func.max(Sale.sale_date)).filter(
                        Sale.product_id == product.id
                    ).scalar()
                    
                    if not first_sale or not last_sale:
                        skipped_count += 1
                        continue
                    
                    days_of_data = (last_sale - first_sale).days
                    if days_of_data < 730:  # Less than 2 years
                        print(f"Product {product.id} ({product.name}): Only {days_of_data} days of data (need 730). Skipping.")
                        skipped_count += 1
                        continue  # Skip - insufficient data
                    
                    # Retrain and generate forecasts
                    success = ForecastingPipeline.generate_multi_horizon_forecasts(
                        product.id,
                        horizons=[1, 7, 30]
                    )
                    
                    if success:
                        retrained_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    print(f"Error retraining product {product.id}: {str(e)}")
                    failed_count += 1
                    continue
            
            # Log the retraining activity
            if user_id and retrained_count > 0:
                ActivityLogger.log(
                    action_type=ActivityLogger.FORECAST,
                    user_id=user_id,
                    action='Auto-generated forecasts after CSV import',
                    details=f'Retrained {retrained_count} products, Skipped {skipped_count} (insufficient data), Failed {failed_count}'
                )
            
            return {
                'retrained': retrained_count,
                'skipped': skipped_count,
                'failed': failed_count,
                'total_products': len(products_with_sales)
            }
            
        except Exception as e:
            print(f"Retraining pipeline error: {str(e)}")
            return {
                'retrained': 0,
                'skipped': 0,
                'failed': 0,
                'error': str(e)
            }

    @staticmethod
    def rolling_retrain_all_products(
        foundation_days_large: int = 365,
        foundation_days_small: int = 90,
        horizon_days: int = 30,
        step_days: int = 1,
        up_to: datetime | None = None,
    ) -> int:
        """
        Run foundation-based rolling retraining for all products.

        - Uses first 365 days as foundation when sufficient history exists, else 90 days
        - For each subsequent day, trains on data up to that day and generates horizon forecasts
        - Saves forecasts with generated_at to enable accuracy comparisons later
        """
        try:
            from utils.rolling_retrain import rolling_retrain_all
            up_to_date = up_to.date() if isinstance(up_to, datetime) else up_to
            created = rolling_retrain_all(
                foundation_days_large=foundation_days_large,
                foundation_days_small=foundation_days_small,
                horizon_days=horizon_days,
                step_days=step_days,
                up_to=up_to_date,
            )
            return created
        except Exception as e:
            print(f"Rolling retrain failed: {e}")
            return 0
    
    @staticmethod
    def generate_multi_horizon_forecasts(product_id, horizons=[1, 7, 30]):
        """
        Generate forecasts for multiple time horizons and aggregation levels.
        Creates daily forecasts starting from Monday of current week through next 30 days.
        Creates weekly forecasts for next 8 weeks.
        
        Args:
            product_id: Product ID to forecast
            horizons: List of forecast horizons in days [1, 7, 30] (kept for compatibility but not used)
        
        Returns:
            Boolean indicating success
        """
        try:
            # Calculate start date: Monday of the current week
            today = datetime.now().date()
            days_to_monday = today.weekday()  # 0=Monday, 6=Sunday
            week_start = today - timedelta(days=days_to_monday)
            
            # Clear old forecasts for this product starting from week_start
            Forecast.query.filter(
                Forecast.product_id == product_id,
                Forecast.forecast_date >= week_start
            ).delete()
            
            # Generate DAILY forecasts for next 30 days starting from Monday of current week
            try:
                forecast_results = forecast_linear_regression(
                    db_conn=None,
                    product_id=product_id,
                    days_ahead=30,  # Generate 30 daily forecasts
                    start_date=week_start  # Start from Monday of current week
                )
                
                if forecast_results and not (isinstance(forecast_results, dict) and 'error' in forecast_results):
                    # Store daily forecasts
                    for forecast_item in forecast_results:
                        try:
                            forecast_date_obj = forecast_item['date']
                            if isinstance(forecast_date_obj, str):
                                forecast_date_obj = datetime.strptime(forecast_date_obj, '%Y-%m-%d')
                            elif isinstance(forecast_date_obj, (datetime, type(None).__class__)):
                                if not isinstance(forecast_date_obj, datetime):
                                    # It's a date object, convert to datetime
                                    forecast_date_obj = datetime.combine(forecast_date_obj, datetime.min.time())
                            
                            # Extract date for period_key calculations
                            if isinstance(forecast_date_obj, datetime):
                                forecast_date_for_key = forecast_date_obj.date()
                            else:
                                forecast_date_for_key = forecast_date_obj
                            
                            predicted_qty = forecast_item['prediction']
                            confidence_lower = forecast_item.get('confidence_lower')
                            confidence_upper = forecast_item.get('confidence_upper')
                            mae = forecast_item.get('mae')
                            rmse = forecast_item.get('rmse')
                            model_used = forecast_item.get('model', 'LINEAR_REGRESSION')
                            
                            # Store as DAILY forecast
                            aggregation_level = 'daily'
                            period_key = forecast_date_for_key.strftime('%Y-%m-%d')
                            
                            # Save to Forecast table (for current predictions)
                            new_forecast = Forecast(
                                product_id=product_id,
                                forecast_date=forecast_date_obj,
                                predicted_quantity=predicted_qty,
                                model_used=model_used,
                                confidence_lower=confidence_lower,
                                confidence_upper=confidence_upper,
                                mae=mae,
                                rmse=rmse,
                                aggregation_level=aggregation_level,
                                period_key=period_key,
                                created_at=datetime.utcnow()
                            )
                            db.session.add(new_forecast)
                            
                            # Save snapshot for historical tracking
                            ForecastingPipeline.save_forecast_snapshot(
                                product_id=product_id,
                                forecast_date=forecast_date_obj,
                                predicted_qty=predicted_qty,
                                model_used=model_used,
                                horizon='1-day',
                                confidence_lower=confidence_lower,
                                confidence_upper=confidence_upper,
                                mae=mae,
                                rmse=rmse
                            )
                            
                        except Exception as e:
                            print(f"Error storing daily forecast for {forecast_item.get('date')}: {str(e)}")
                            continue
                            
            except Exception as e:
                print(f"Error generating daily forecasts for product {product_id}: {str(e)}")
            
            # Generate WEEKLY forecasts by aggregating daily forecasts into weeks
            try:
                # Get all daily forecasts we just created (starting from week_start)
                daily_forecasts = Forecast.query.filter(
                    Forecast.product_id == product_id,
                    Forecast.aggregation_level == 'daily',
                    Forecast.forecast_date >= week_start
                ).order_by(Forecast.forecast_date).all()
                
                if daily_forecasts:
                    # Group by week and create weekly aggregates
                    from collections import defaultdict
                    weekly_data = defaultdict(lambda: {'qty': 0, 'count': 0, 'dates': []})
                    
                    for daily_fc in daily_forecasts:
                        fc_date = daily_fc.forecast_date.date() if isinstance(daily_fc.forecast_date, datetime) else daily_fc.forecast_date
                        # Find Monday of this week
                        days_to_monday = fc_date.weekday()
                        week_start = fc_date - timedelta(days=days_to_monday)
                        
                        weekly_data[week_start]['qty'] += daily_fc.predicted_quantity
                        weekly_data[week_start]['count'] += 1
                        weekly_data[week_start]['dates'].append(fc_date)
                    
                    # Create weekly forecast records
                    for week_start, data in weekly_data.items():
                        if data['count'] > 0:
                            week_forecast = Forecast(
                                product_id=product_id,
                                forecast_date=datetime.combine(week_start, datetime.min.time()),
                                predicted_quantity=int(data['qty']),
                                model_used='AGGREGATED_DAILY',
                                aggregation_level='weekly',
                                period_key=week_start.strftime('%Y-W%W'),
                                created_at=datetime.utcnow()
                            )
                            db.session.add(week_forecast)
                            
                            # Save snapshot
                            ForecastingPipeline.save_forecast_snapshot(
                                product_id=product_id,
                                forecast_date=week_start,
                                predicted_qty=int(data['qty']),
                                model_used='AGGREGATED_DAILY',
                                horizon='7-day'
                            )
                            
            except Exception as e:
                print(f"Error generating weekly forecasts for product {product_id}: {str(e)}")
            
            # Commit all forecasts for this product
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error in multi-horizon forecast generation: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_latest_forecast(product_id, days_ahead=1):
        """
        Get the most recent forecast for a product.
        
        Args:
            product_id: Product ID
            days_ahead: Number of days ahead (1, 7, or 30)
        
        Returns:
            Forecast object or None
        """
        try:
            target_date = datetime.now().date() + timedelta(days=days_ahead)
            
            forecast = Forecast.query.filter(
                Forecast.product_id == product_id,
                db.func.date(Forecast.forecast_date) == target_date
            ).order_by(Forecast.created_at.desc()).first()
            
            return forecast
            
        except Exception as e:
            print(f"Error retrieving forecast: {str(e)}")
            return None
    
    @staticmethod
    def save_forecast_snapshot(product_id, forecast_date, predicted_qty, model_used='LINEAR_REGRESSION', 
                               horizon='1-day', confidence_lower=None, confidence_upper=None, mae=None, rmse=None):
        """
        Save a forecast snapshot for future comparison with actual results.
        
        Args:
            product_id: Product ID
            forecast_date: Date being forecasted (as date object)
            predicted_qty: Predicted quantity
            model_used: Model name
            horizon: Forecast horizon ('1-day', '7-day', '30-day')
            confidence_lower: Lower confidence bound
            confidence_upper: Upper confidence bound
            mae: Mean Absolute Error
            rmse: Root Mean Squared Error
        """
        try:
            # Check if snapshot already exists for this product/date/horizon
            existing = ForecastSnapshot.query.filter_by(
                product_id=product_id,
                forecast_date=forecast_date,
                forecast_horizon=horizon
            ).first()
            
            if existing:
                # Update existing snapshot with newer prediction
                existing.predicted_quantity = predicted_qty
                existing.model_used = model_used
                existing.snapshot_created_at = datetime.utcnow()
                existing.confidence_lower = confidence_lower
                existing.confidence_upper = confidence_upper
                existing.mae = mae
                existing.rmse = rmse
            else:
                # Create new snapshot
                snapshot = ForecastSnapshot(
                    product_id=product_id,
                    forecast_date=forecast_date,
                    predicted_quantity=predicted_qty,
                    model_used=model_used,
                    forecast_horizon=horizon,
                    confidence_lower=confidence_lower,
                    confidence_upper=confidence_upper,
                    mae=mae,
                    rmse=rmse
                )
                db.session.add(snapshot)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving forecast snapshot: {str(e)}")
            return False
    
    @staticmethod
    def update_snapshot_with_actual(product_id, sale_date, actual_qty):
        """
        Update forecast snapshots with actual sales data when it arrives.
        Calculate accuracy and error metrics.
        
        Args:
            product_id: Product ID
            sale_date: Date of actual sale (as date object)
            actual_qty: Actual quantity sold
        """
        try:
            # Find all snapshots for this product/date (different horizons)
            snapshots = ForecastSnapshot.query.filter_by(
                product_id=product_id,
                forecast_date=sale_date
            ).all()
            
            for snapshot in snapshots:
                if snapshot.actual_quantity is None:  # Only update if not already filled
                    snapshot.actual_quantity = actual_qty
                    
                    # Calculate accuracy
                    if actual_qty > 0:
                        error = abs(snapshot.predicted_quantity - actual_qty) / actual_qty
                        snapshot.accuracy = round((1 - error) * 100, 2)
                        snapshot.error_percentage = round(error * 100, 2)
                    else:
                        # If actual is 0 but predicted > 0, it's 0% accuracy
                        if snapshot.predicted_quantity > 0:
                            snapshot.accuracy = 0.0
                            snapshot.error_percentage = 100.0
                        else:
                            snapshot.accuracy = 100.0
                            snapshot.error_percentage = 0.0
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating snapshot with actual: {str(e)}")
            return False

