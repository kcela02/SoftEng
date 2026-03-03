"""
Regenerate forecasts and fix incomplete week data
"""
from app import create_app
from models import db, Forecast, Product
from utils.model_trainer import ForecastingPipeline
from datetime import datetime, timedelta

app = create_app('development')
with app.app_context():
    print('=== Forecast Regeneration Script ===\n')
    
    print('Step 1: Clearing old forecasts...')
    deleted = Forecast.query.delete()
    db.session.commit()
    print(f'  Deleted {deleted} forecasts\n')
    
    print('Step 2: Regenerating forecasts for valid products...')
    products = Product.query.all()
    print(f'  Found {len(products)} products\n')
    
    success_count = 0
    for i, product in enumerate(products, 1):
        try:
            print(f'  [{i}/{len(products)}] Generating for product {product.id}: {product.name[:40]}...', end='', flush=True)
            ForecastingPipeline.generate_multi_horizon_forecasts(product_id=product.id)
            success_count += 1
            print(' OK')
        except Exception as e:
            print(f' FAILED: {str(e)[:60]}')
    
    db.session.commit()
    
    print(f'\n[OK] Generated forecasts for {success_count}/{len(products)} products\n')
    
    # Verification
    print('Step 3: Verifying coverage...')
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    # Check full 30 days
    all_dates = set()
    all_fc = Forecast.query.filter_by(aggregation_level='daily').all()
    for fc in all_fc:
        d = fc.forecast_date if isinstance(fc.forecast_date, datetime) else fc.forecast_date
        if isinstance(d, datetime):
            d = d.date()
        all_dates.add(d)
    
    print(f'  Total unique forecast dates: {len(all_dates)}')
    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
        print(f'  Range: {min_date} to {max_date}')
        
        # Check week specifically
        print(f'\n  Weekly coverage ({week_start} to {week_start + timedelta(days=6)}):')
        week_dates = set()
        for fc in Forecast.query.filter(
            Forecast.aggregation_level == 'daily',
            Forecast.forecast_date >= week_start
        ).all():
            d = fc.forecast_date.date() if isinstance(fc.forecast_date, datetime) else fc.forecast_date
            week_dates.add(d)
        
        for i in range(7):
            d = week_start + timedelta(days=i)
            day_name = d.strftime('%A')
            status = '[OK]' if d in week_dates else '[MISS]'
            print(f'    {status} {day_name}: {d}')
    
    print('\n=== Regeneration Complete ===')
