# models/regression.py
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from models.utils import load_sales_data, create_future_dates

def forecast_linear_regression(db_conn, product_id, days_ahead=7, start_date=None, training_end_date=None):
    """
    Performs Enhanced Linear Regression forecasting with:
    - Extended historical context (uses all available data)
    - Year-over-year seasonal patterns
    - Day-of-week features
    - Recent trend weighting
    
    Args:
        db_conn: Database connection object
        product_id (int): The product to forecast
        days_ahead (int): Number of days to predict into the future
        start_date: Optional start date for forecasts (datetime/date). If None, starts from tomorrow.
        training_end_date: Optional cutoff date for training data (for backtesting). If None, uses all data.
        
    Returns:
        dict: Forecast results with predictions and confidence intervals
    """
    ts = load_sales_data(db_conn, product_id, end_date=training_end_date)
    if ts.empty or len(ts) < 5:
        return {"error": "Insufficient data to run Linear Regression model (minimum 5 days required)."}

    try:
        # 1. Enhanced Feature Engineering
        ts['day_num'] = np.arange(len(ts))
        ts['day_of_week'] = ts['ds'].dt.dayofweek  # 0=Monday, 6=Sunday
        ts['month'] = ts['ds'].dt.month
        ts['day_of_month'] = ts['ds'].dt.day
        
        # Create day-of-week dummy variables for seasonality
        ts = pd.get_dummies(ts, columns=['day_of_week'], prefix='dow', drop_first=False)
        
        # Add year-over-year seasonal factor if we have enough history
        if len(ts) > 365:
            # Calculate average sales for each day-of-year from last year
            ts['day_of_year'] = ts['ds'].dt.dayofyear
            last_year_avg = ts[ts['ds'] < (ts['ds'].max() - timedelta(days=365))].groupby('day_of_year')['y'].mean()
            ts['yoy_seasonal_factor'] = ts['day_of_year'].map(last_year_avg).fillna(ts['y'].mean())
        else:
            ts['yoy_seasonal_factor'] = ts['y'].mean()
        
        # Add recent trend (weighted moving average of last 7 days)
        ts['recent_trend'] = ts['y'].rolling(window=min(7, len(ts)), min_periods=1).mean()
        
        # 2. Prepare feature matrix with enhanced features
        feature_cols = ['day_num', 'month', 'day_of_month', 'yoy_seasonal_factor', 'recent_trend']
        dow_cols = [col for col in ts.columns if col.startswith('dow_')]
        feature_cols.extend(dow_cols)
        
        X = ts[feature_cols]
        y = ts['y']
        
        # Weight recent data more heavily (exponential decay)
        sample_weights = np.exp(0.01 * ts['day_num'])  # Recent data gets higher weight
        
        # 3. Train Enhanced Model with sample weights
        model = LinearRegression()
        model.fit(X, y, sample_weight=sample_weights)
        
        # 4. Calculate model performance on training data
        y_pred_train = model.predict(X)
        mae = mean_absolute_error(y, y_pred_train)
        rmse = np.sqrt(mean_squared_error(y, y_pred_train))
        
        # Calculate residual standard deviation for confidence intervals
        residuals = y - y_pred_train
        residual_std = np.std(residuals)

        # 5. Create future feature matrix for predictions
        last_date = ts['ds'].iloc[-1]
        last_day_num = ts['day_num'].iloc[-1]
        
        # Use start_date if provided, otherwise use tomorrow
        future_dates = create_future_dates(ts, days_ahead, start_date=start_date)
        
        # Calculate day_num offset based on start_date
        if start_date:
            if not isinstance(start_date, datetime):
                from datetime import datetime as dt_class
                start_date = pd.Timestamp(start_date)
            days_from_last = (start_date - last_date).days
        else:
            days_from_last = 1  # Tomorrow
        
        future_data = []
        for i, future_date in enumerate(future_dates):
            dt = datetime.strptime(str(future_date), '%Y-%m-%d') if isinstance(future_date, str) else future_date
            
            # Base features
            features = {
                'day_num': last_day_num + days_from_last + i,
                'month': dt.month,
                'day_of_month': dt.day,
            }
            
            # Day of week dummies
            dow = dt.weekday()
            for j in range(7):
                features[f'dow_{j}'] = 1 if dow == j else 0
            
            # YoY seasonal factor: use historical average for this day-of-year
            if len(ts) > 365:
                day_of_year = dt.timetuple().tm_yday
                features['yoy_seasonal_factor'] = last_year_avg.get(day_of_year, ts['y'].mean())
            else:
                features['yoy_seasonal_factor'] = ts['y'].mean()
            
            # Recent trend: use last known trend value
            features['recent_trend'] = ts['recent_trend'].iloc[-1]
            
            future_data.append(features)
        
        future_df = pd.DataFrame(future_data)
        
        # Ensure columns match training data
        for col in feature_cols:
            if col not in future_df.columns:
                future_df[col] = 0
        
        X_future = future_df[feature_cols]
        predictions = model.predict(X_future)
        
        # 6. Calculate adaptive confidence intervals
        # Confidence widens with forecast horizon and recent volatility
        recent_volatility = ts['y'].tail(7).std() if len(ts) > 7 else residual_std
        confidence_margin = 1.28 * residual_std * (1 + 0.15 * np.arange(days_ahead))
        
        # Adjust for recent volatility
        volatility_factor = min(recent_volatility / (residual_std + 1e-6), 2.0)
        confidence_margin *= volatility_factor
        
        # 7. Format results
        forecast_results = []
        for i, (date, pred) in enumerate(zip(future_dates, predictions)):
            forecast_results.append({
                'date': date,
                'prediction': max(0, round(pred)),
                'confidence_lower': max(0, round(pred - confidence_margin[i])),
                'confidence_upper': max(0, round(pred + confidence_margin[i])),
                'model': 'ENHANCED_LINEAR_REGRESSION',
                'mae': round(mae, 2),
                'rmse': round(rmse, 2)
            })
        
        return forecast_results
        
    except Exception as e:
        return {"error": f"Enhanced Linear Regression model failed: {str(e)}"}