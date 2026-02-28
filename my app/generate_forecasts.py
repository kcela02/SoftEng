"""
Manual Forecast Generation Script
Generates forecasts for all products with sufficient sales history.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Product, Sale
from utils.model_trainer import ForecastingPipeline
from datetime import datetime, timedelta

def generate_all_forecasts():
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("  MANUAL FORECAST GENERATION")
        print("=" * 70)
        print()
        
        # Get all products with sales
        products_with_sales = db.session.query(Product).join(
            Sale, Product.id == Sale.product_id
        ).distinct().all()
        
        print(f"Found {len(products_with_sales)} products with sales data")
        print()
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for product in products_with_sales:
            # Check sales count
            sales_count = Sale.query.filter_by(product_id=product.id).count()
            
            print(f"Processing: {product.name} (ID: {product.id})")
            print(f"  Sales records: {sales_count}")
            
            if sales_count < 7:
                print(f"  ⚠️  SKIPPED - Need at least 7 sales (has {sales_count})")
                skip_count += 1
                continue
            
            try:
                # Generate forecasts
                print(f"  🔄 Generating forecasts...")
                success = ForecastingPipeline.generate_multi_horizon_forecasts(
                    product.id,
                    horizons=[1, 7, 30]
                )
                
                if success:
                    print(f"  ✅ SUCCESS")
                    success_count += 1
                else:
                    print(f"  ❌ FAILED")
                    fail_count += 1
            except Exception as e:
                print(f"  ❌ ERROR: {str(e)}")
                fail_count += 1
                import traceback
                traceback.print_exc()
            
            print()
        
        print("=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        print(f"✅ Successfully generated forecasts: {success_count} products")
        print(f"⚠️  Skipped (insufficient data): {skip_count} products")
        print(f"❌ Failed: {fail_count} products")
        print()
        
        # Verify forecasts were created
        from models import Forecast
        total_forecasts = Forecast.query.count()
        print(f"📈 Total forecasts in database: {total_forecasts}")
        
        if total_forecasts > 0:
            today = datetime.now().date()
            future_forecasts = Forecast.query.filter(Forecast.forecast_date > today).count()
            print(f"   Future forecasts: {future_forecasts}")
            
            daily_forecasts = Forecast.query.filter_by(aggregation_level='daily').count()
            weekly_forecasts = Forecast.query.filter_by(aggregation_level='weekly').count()
            print(f"   Daily: {daily_forecasts}, Weekly: {weekly_forecasts}")
        
        print()
        print("✨ Forecast generation complete!")
        print()

if __name__ == '__main__':
    generate_all_forecasts()
