"""Reset database - clear all data while keeping schema intact"""
from app import create_app
from models import db, Product, Sale, Forecast, Inventory, Alert, ImportLog, ForecastSnapshot, InventoryBatch, BatchTransaction

app = create_app()

with app.app_context():
    print("Resetting database...")
    
    # Delete all data in order (respecting foreign key constraints)
    print("Deleting batch transactions...")
    BatchTransaction.query.delete()
    
    print("Deleting inventory batches...")
    InventoryBatch.query.delete()
    
    print("Deleting forecast snapshots...")
    ForecastSnapshot.query.delete()
    
    print("Deleting alerts...")
    Alert.query.delete()
    
    print("Deleting import logs...")
    ImportLog.query.delete()
    
    print("Deleting forecasts...")
    Forecast.query.delete()
    
    print("Deleting sales...")
    Sale.query.delete()
    
    print("Deleting inventory...")
    Inventory.query.delete()
    
    print("Deleting products...")
    Product.query.delete()
    
    # Commit the changes
    db.session.commit()
    
    print("\n✅ Database reset complete!")
    print("All products, sales, forecasts, and related data have been cleared.")
    print("You can now upload your CSV file again.")
