# models/utils.py
import pandas as pd
from models import Sale
from app import db

def load_sales_data(db_conn, product_id=None, end_date=None):
    """
    Fetches historical sales data from the database using SQLAlchemy.
    
    Args:
        db_conn: Database connection object
        product_id: Optional product ID to filter by
        end_date: Optional cutoff date - only load sales up to this date (for backtesting)
    """
    try:
        print(f"DEBUG: Fetching data for product_id: {product_id}, end_date: {end_date}")
        
        # Query sales data using SQLAlchemy
        query = db.session.query(
            Sale.sale_date,
            db.func.sum(Sale.quantity).label('sales_quantity')
        )
        
        if product_id:
            query = query.filter(Sale.product_id == product_id)
        
        if end_date:
            query = query.filter(db.func.date(Sale.sale_date) <= end_date)
        
        query = query.group_by(Sale.sale_date).order_by(Sale.sale_date)
        
        # Execute query and convert to DataFrame
        results = query.all()
        
        if not results:
            print(f"No sales data found for product_id: {product_id}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=['sale_date', 'sales_quantity'])
        
        # Ensure sale_date is datetime
        df['sale_date'] = pd.to_datetime(df['sale_date'])
        
        # Set index and rename columns
        df = df.set_index('sale_date')
        df = df.rename(columns={'sales_quantity': 'y'})
        
        # Reset index to make 'sale_date' a column named 'ds' (required by forecasting models)
        df = df.reset_index()
        df = df.rename(columns={'sale_date': 'ds'})
        
        return df
        
    except Exception as e:
        print(f"Error loading sales data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def create_future_dates(df, days_ahead=7, start_date=None):
    """
    Creates a list of future dates for prediction.
    
    Args:
        df: DataFrame with 'ds' column containing dates
        days_ahead: Number of days to forecast
        start_date: Optional start date (datetime/date object). If None, starts from last date in df + 1 day
    
    Returns:
        List of date strings in 'YYYY-MM-DD' format
    """
    if start_date is None:
        # Get the last date from the 'ds' column (not the index)
        last_date = df['ds'].iloc[-1]
        future_dates = pd.date_range(start=last_date, periods=days_ahead + 1, inclusive='right')
    else:
        # Start from specified date
        if not isinstance(start_date, pd.Timestamp):
            start_date = pd.Timestamp(start_date)
        future_dates = pd.date_range(start=start_date, periods=days_ahead)
    
    return future_dates.to_series().dt.strftime('%Y-%m-%d').tolist()