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

    # --- ARIMA Parameter Tuning: Try multiple orders and pick best by AIC ---
    best_aic = float('inf')
    best_order = order
    best_model_fit = None
    for candidate_order in [(1,1,1), (2,1,2), (5,1,0), (2,0,2)]:
        try:
            model = ARIMA(ts['y'], order=candidate_order)
            model_fit = model.fit()
            if model_fit.aic < best_aic:
                best_aic = model_fit.aic
                best_order = candidate_order
                best_model_fit = model_fit
        except Exception:
            continue
    if best_model_fit is None:
        return {"error": "ARIMA model failed for all candidate orders."}

    try:
        # 1. Train Model with best order
        model_fit = best_model_fit

        # 2. Predict with confidence intervals
        forecast_result = model_fit.get_forecast(steps=days_ahead, alpha=0.2)
        predictions = forecast_result.predicted_mean
        conf_int = forecast_result.conf_int()

        # 3. Calculate model performance metrics (on training data)
        fitted_values = model_fit.fittedvalues
        residuals = ts['y'] - fitted_values
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
                'model': f'ARIMA{best_order}',
                'mae': round(mae, 2),
                'rmse': round(rmse, 2)
            })

        # --- Visualization: Plot historical and forecasted sales ---
        try:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(10,5))
            plt.plot(ts['ds'], ts['y'], label='Historical Sales')
            forecast_dates = [f['date'] for f in forecast_results]
            forecast_values = [f['prediction'] for f in forecast_results]
            plt.plot(forecast_dates, forecast_values, label='Forecast', marker='o')
            plt.fill_between(forecast_dates,
                             [f['confidence_lower'] for f in forecast_results],
                             [f['confidence_upper'] for f in forecast_results],
                             color='gray', alpha=0.2, label='Confidence Interval')
            plt.legend()
            plt.title(f'ARIMA Forecast (order={best_order})')
            plt.show()
        except Exception as plot_exc:
            print(f"Plotting failed: {plot_exc}")

        return forecast_results
    except Exception as e:
        return {"error": f"ARIMA model failed: {e}"}