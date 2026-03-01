#!/usr/bin/env python3
"""
One-shot script: loads data/historical_sales_vape.csv into the database.
Run once when starting fresh: python load_data.py
"""
import sys
import os
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from models import db, Product, Sale

CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'historical_sales_vape.csv')

def load():
    app = create_app()
    with app.app_context():
        df = pd.read_csv(CSV_PATH)
        print(f"Read {len(df)} rows from {CSV_PATH}")

        product_map = {}  # name -> Product

        # Pre-load existing products
        for p in Product.query.all():
            product_map[p.name] = p

        added_products = 0
        added_sales = 0
        skipped = 0

        for idx, row in df.iterrows():
            try:
                product_name = str(row['product_name']).strip()
                quantity = int(row['quantity_sold'])
                price = float(row['sale_price'])
                sale_date = pd.to_datetime(row['sale_date']) if pd.notna(row.get('sale_date')) else datetime.now()
                category = str(row.get('category', '')).strip() or 'General'
                unit_cost = float(row['unit_cost']) if pd.notna(row.get('unit_cost')) else price * 0.6
                stock_after = int(row['stock_after_sale']) if pd.notna(row.get('stock_after_sale')) else 0

                # Get or create product
                if product_name not in product_map:
                    product = Product(
                        name=product_name,
                        category=category,
                        unit_cost=unit_cost,
                        current_stock=stock_after,
                    )
                    db.session.add(product)
                    db.session.flush()  # get the ID
                    product_map[product_name] = product
                    added_products += 1
                else:
                    product = product_map[product_name]

                # Skip duplicate same product+date
                sale_date_norm = sale_date if isinstance(sale_date, datetime) else datetime.combine(sale_date, datetime.min.time())
                existing = Sale.query.filter_by(
                    product_id=product.id,
                    sale_date=sale_date_norm
                ).first()
                if existing:
                    skipped += 1
                    continue

                sale = Sale(
                    product_id=product.id,
                    quantity=quantity,
                    price=price,
                    sale_date=sale_date_norm,
                    is_trained=True,  # historical data — mark as already trained baseline
                )
                db.session.add(sale)
                added_sales += 1

                if added_sales % 500 == 0:
                    db.session.commit()
                    print(f"  ... {added_sales} sales committed so far")

            except Exception as e:
                print(f"Row {idx}: ERROR - {e}")
                db.session.rollback()
                continue

        db.session.commit()
        print(f"\nDone!")
        print(f"  Products added : {added_products}")
        print(f"  Sales added    : {added_sales}")
        print(f"  Skipped dupes  : {skipped}")
        print(f"  Total products : {Product.query.count()}")
        print(f"  Total sales    : {Sale.query.count()}")

if __name__ == '__main__':
    load()
