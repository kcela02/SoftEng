# models/arima.py
# ARIMA forecasting with confidence intervals
from statsmodels.tsa.arima.model import ARIMA
from models.utils import load_sales_data, create_future_dates
import numpy as np

def forecast_arima(db_conn, product_id, days_ahead=7, order=(5,1,0)):
    """
    Performs ARIMA forecasting with confidence intervals.
    
    Args:
        db_conn: Database connection
        product_id: Product ID to forecast
        days_ahead: Number of days to forecast
        order: ARIMA (p,d,q) parameters
    
    Returns:
        Dictionary with forecast results including confidence intervals
    """
    ts = load_sales_data(db_conn, product_id)
    if ts.empty or len(ts) < 30:  # ARIMA needs sufficient data points
        return {"error": "Insufficient data to run ARIMA model (minimum 30 days required)."}

    try:
        # 1. Train Model
        model = ARIMA(ts, order=order)
        model_fit = model.fit()

        # 2. Predict with confidence intervals
        forecast_index = len(ts)
        forecast_end = forecast_index + days_ahead - 1
        
        # Get predictions with confidence intervals (80% interval = alpha 0.2)
        forecast_result = model_fit.get_forecast(steps=days_ahead, alpha=0.2)
        predictions = forecast_result.predicted_mean
        conf_int = forecast_result.conf_int()
        # 3. Calculate model performance metrics (on training data)
        fitted_values = model_fit.fittedvalues
        residuals = ts - fitted_values
        mae = np.mean(np.abs(residuals))
        rmse = np.sqrt(np.mean(residuals**2))

        # 4. Format results
        future_dates = create_future_dates(ts, days_ahead)
        forecast_results = []
        
        for i, date in enumerate(future_dates):
            forecast_results.append({
                'date': date,
                'prediction': max(0, round(predictions.iloc[i])),
                'confidence_lower': max(0, round(conf_int.iloc[i, 0])),
                'confidence_upper': max(0, round(conf_int.iloc[i, 1])),
                'model': 'ARIMA',
                'mae': round(mae, 2),
                'rmse': round(rmse, 2)
            })
        
        return forecast_results
        
    except Exception as e:
        return {"error": f"ARIMA model failed: {e}"}