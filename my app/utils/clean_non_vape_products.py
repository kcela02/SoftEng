"""
Utility script to remove non-vape products from the database.
Only keeps products related to vaping.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Product, Sale, Inventory, Forecast, ForecastSnapshot, Alert, InventoryBatch, BatchTransaction

# List of non-vape product keywords to identify and remove
NON_VAPE_KEYWORDS = [
    'laptop', 'mouse', 'keyboard', 'monitor', 'webcam', 'headphone',
    'power bank', 'bluetooth speaker', 'usb cable', 'hdmi cable',
    'phone case', 'screen protector', 'charger', 'earbud', 'memory card',
    'otg adapter', 'desk lamp', 'led strip', 'extension cord', 'kettle',
    'rice cooker', 'fan', 'air purifier', 'water bottle', 'printer',
    'ink cartridge', 'stapler', 'notebook', 'pen set', 'office chair',
    'desk organizer', 'whiteboard marker', 'smartwatch', 'fitness band',
    'tablet', 'e-reader', 'drone', 'camera', 'gaming'
]


def is_non_vape_product(product_name, category):
    """Check if a product is non-vape related."""
    name_lower = product_name.lower()
    category_lower = (category or '').lower()
    
    # Check if any non-vape keyword is in the name
    for keyword in NON_VAPE_KEYWORDS:
        if keyword in name_lower or keyword in category_lower:
            return True
    
    # Check if category suggests non-vape
    non_vape_categories = ['electronics', 'office', 'home', 'gadgets', 'accessories']
    if any(cat in category_lower for cat in non_vape_categories):
        # But exclude if it has vape keywords
        vape_keywords = ['vape', 'pod', 'liquid', 'coil', 'battery', 'mod', 'puff', 'disposable']
        if not any(vk in name_lower for vk in vape_keywords):
            return True
    
    return False


def clean_non_vape_products():
    """Remove all non-vape products and their related data."""
    app = create_app()
    
    with app.app_context():
        try:
            products = Product.query.all()
            removed_count = 0
            kept_count = 0
            
            print("\n🔍 Scanning products...")
            print("-" * 60)
            
            for product in products:
                if is_non_vape_product(product.name, product.category):
                    print(f"[DELETE] Removing: {product.name} (Category: {product.category or 'N/A'})")
                    
                    # Delete related records
                    # Get batch IDs first
                    batch_ids = [batch.id for batch in InventoryBatch.query.filter_by(product_id=product.id).all()]
                    if batch_ids:
                        BatchTransaction.query.filter(BatchTransaction.batch_id.in_(batch_ids)).delete(synchronize_session=False)
                    
                    # Delete other related records
                    InventoryBatch.query.filter_by(product_id=product.id).delete()
                    Alert.query.filter_by(product_id=product.id).delete()
                    Forecast.query.filter_by(product_id=product.id).delete()
                    ForecastSnapshot.query.filter_by(product_id=product.id).delete()
                    Inventory.query.filter_by(product_id=product.id).delete()
                    Sale.query.filter_by(product_id=product.id).delete()
                    
                    # Delete product
                    db.session.delete(product)
                    removed_count += 1
                else:
                    print(f"[KEEP] Keeping: {product.name} (Category: {product.category or 'N/A'})")
                    kept_count += 1
            
            db.session.commit()
            
            print("-" * 60)
            print(f"\n[OK] Cleanup complete!")
            print(f"   Removed: {removed_count} non-vape products")
            print(f"   Kept: {kept_count} vape-related products")
            print(f"\n[TIP] You can now import the clean vape CSV files to populate with vape products only.")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Error during cleanup: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    print("=" * 60)
    print("  Non-Vape Product Cleanup Utility")
    print("=" * 60)
    print("\nThis will remove all non-vape products from the database.")
    print("This includes products like laptops, keyboards, office supplies, etc.")
    print("\nVape-related products (pods, e-liquids, coils, mods, etc.) will be kept.")
    
    response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        clean_non_vape_products()
    else:
        print("\n[INFO] Cleanup cancelled.")
