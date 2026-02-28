"""
Upload CSV sales data to database with progress tracking
"""
from app import create_app
from models import db, Product, Sale
from utils.model_trainer import ForecastingPipeline
from datetime import datetime
import pandas as pd

def upload_sales_csv(csv_file='sample_sales_3years.csv'):
    """Upload sales data from CSV with realistic stock management"""
    app = create_app('development')
    
    with app.app_context():
        print("\n" + "="*60)
        print("UPLOADING SALES DATA TO DATABASE")
        print("="*60)
        
        # Read CSV
        print(f"\n📂 Reading {csv_file}...")
        df = pd.read_csv(csv_file)
        print(f"✓ Loaded {len(df):,} records")
        
        # Get unique products
        unique_products = df['product_name'].unique()
        print(f"✓ Found {len(unique_products)} unique products")
        
        # Product categories (for better organization)
        product_categories = {
            'Pod Kit': 'Devices',
            'Vape Mod XL': 'Devices',
            'Starter Kit': 'Devices',
            'Tanks': 'Accessories',
            'Atomizers': 'Accessories',
            'Vape Juice 30ml': 'E-Liquids',
            'Vape Juice 60ml': 'E-Liquids',
            'E-Liquid Premium': 'E-Liquids',
            'Zero Nicotine 30ml': 'E-Liquids',
            'Nicotine Pods': 'Consumables',
            'Replacement Coils': 'Consumables',
            'Cotton Wicking': 'Consumables',
            'Batteries': 'Accessories',
            'Battery 18650': 'Accessories',
            'Chargers': 'Accessories',
            'Charger': 'Accessories',
            'Tank Glass': 'Parts',
            'Drip Tips': 'Parts',
        }
        
        # Average unit costs (wholesale prices for inventory valuation)
        product_unit_costs = {
            'Pod Kit': 28.0,
            'Vape Mod XL': 25.0,
            'Starter Kit': 18.0,
            'Tanks': 30.0,
            'Atomizers': 28.0,
            'Vape Juice 30ml': 22.0,
            'Vape Juice 60ml': 18.0,
            'E-Liquid Premium': 25.0,
            'Zero Nicotine 30ml': 15.0,
            'Nicotine Pods': 22.0,
            'Replacement Coils': 10.0,
            'Cotton Wicking': 18.0,
            'Batteries': 18.0,
            'Battery 18650': 10.0,
            'Chargers': 20.0,
            'Charger': 10.0,
            'Tank Glass': 8.0,
            'Drip Tips': 15.0,
        }
        
        # Step 1: Create products
        print("\n📦 Creating products...")
        product_map = {}
        
        for idx, product_name in enumerate(unique_products, 1):
            print(f"  Creating product {idx}/{len(unique_products)}: {product_name}")
            # Calculate average price and total quantity from CSV
            product_df = df[df['product_name'] == product_name]
            total_qty = product_df['quantity_sold'].sum()
            
            # Set initial stock to cover next 30 days of average demand
            avg_daily_sales = total_qty / len(df['sale_date'].unique())
            initial_stock = int(avg_daily_sales * 30)
            
            product = Product(
                name=product_name,
                category=product_categories.get(product_name, 'Other'),
                unit_cost=product_unit_costs.get(product_name, 20.0),
                current_stock=initial_stock
            )
            db.session.add(product)
            db.session.flush()
            product_map[product_name] = product.id
        
        db.session.commit()
        print(f"✓ Created {len(product_map)} products")
        
        # Step 2: Upload sales with progress bar
        print(f"\n💰 Uploading {len(df):,} sales records...")
        
        # Group by date for better performance
        sales_by_date = df.groupby('sale_date')
        dates = sorted(df['sale_date'].unique())
        
        batch_size = 1000
        sales_batch = []
        total_processed = 0
        progress_interval = len(df) // 20  # Show 20 progress updates
        
        for date in dates:
            date_df = sales_by_date.get_group(date)
            
            for _, row in date_df.iterrows():
                product_id = product_map[row['product_name']]
                sale_date = pd.to_datetime(row['sale_date'])
                
                sale = Sale(
                    product_id=product_id,
                    quantity=int(row['quantity_sold']),
                    price=float(row['sale_price']),
                    sale_date=sale_date,
                    user_id=1  # Admin user
                )
                sales_batch.append(sale)
                total_processed += 1
                
                # Show progress
                if total_processed % progress_interval == 0:
                    progress = (total_processed / len(df)) * 100
                    print(f"  Progress: {progress:.0f}% ({total_processed:,}/{len(df):,} records)")
                
                # Commit in batches for performance
                if len(sales_batch) >= batch_size:
                    db.session.bulk_save_objects(sales_batch)
                    db.session.commit()
                    sales_batch = []
        
        # Commit remaining
        if sales_batch:
            db.session.bulk_save_objects(sales_batch)
            db.session.commit()
        
        print(f"✓ Uploaded {total_processed:,} sales records")
        
        # Step 3: Generate forecasts
        print("\n📈 Generating forecasts...")
        products = Product.query.all()
        forecast_count = 0
        
        for idx, product in enumerate(products, 1):
            try:
                print(f"  Forecasting {idx}/{len(products)}: {product.name}")
                # Generate multi-horizon forecasts (1, 7, 30 days)
                success = ForecastingPipeline.generate_multi_horizon_forecasts(
                    product.id,
                    horizons=[1, 7, 30]
                )
                if success:
                    forecast_count += 1
            except Exception as e:
                print(f"  ⚠️ Warning: Could not generate forecast for {product.name}: {str(e)}")
        
        print(f"✓ Generated forecasts for {forecast_count} products")
        
        # Display summary
        total_revenue = db.session.query(db.func.sum(Sale.quantity * Sale.price)).scalar() or 0
        total_units = db.session.query(db.func.sum(Sale.quantity)).scalar() or 0
        total_inventory_value = db.session.query(
            db.func.sum(Product.current_stock * Product.unit_cost)
        ).scalar() or 0
        
        print("\n" + "="*60)
        print("UPLOAD SUMMARY")
        print("="*60)
        print(f"Products Created:    {len(products):>10,}")
        print(f"Sales Records:       {total_processed:>10,}")
        print(f"Total Revenue:       ${total_revenue:>10,.2f}")
        print(f"Total Units Sold:    {total_units:>10,}")
        print(f"Inventory Value:     ${total_inventory_value:>10,.2f}")
        print(f"Forecasts Generated: {forecast_count:>10}")
        print("="*60)
        print("✅ Upload complete!")

if __name__ == '__main__':
    upload_sales_csv()
