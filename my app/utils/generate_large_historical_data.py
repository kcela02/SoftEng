"""
Generate a large historical sales CSV with at least 40 products
Date range: Jan 1, 2022 to Nov 10, 2025
Format: unified_sales CSV compatible with upload (product_name, quantity_sold, sale_price, category, unit_cost, sale_date, stock_after_sale)
"""
import csv
from datetime import datetime, timedelta
import random

# Vape Products - 40+ products across vape-related categories
CATEGORIES = [
    ("Disposable Vapes", [
        ("Classic 500 Puff", 150, 8, 399.00),
        ("Premium 2000 Puff", 280, 5, 799.00),
        ("Max 3000 Puff", 350, 4, 999.00),
        ("Lite 200 Puff", 100, 12, 249.00),
        ("Tropical Mix 500 Puff", 150, 8, 399.00),
        ("Berry Blast 1000 Puff", 200, 7, 549.00),
        ("Mint Fresh 500 Puff", 150, 8, 399.00),
        ("Ice Cool 2000 Puff", 280, 5, 799.00),
        ("Fruity Fusion 1500 Puff", 250, 6, 699.00),
        ("Grape 500 Puff", 150, 8, 399.00),
    ]),
    ("Pod Systems", [
        ("Pod System Kit", 800, 3, 1499.00),
        ("Replacement Pods (4-Pack)", 200, 6, 599.00),
        ("Compact Pod Kit", 600, 4, 1199.00),
        ("Advanced Pod Kit", 1200, 2, 1999.00),
        ("Starter Pod System", 500, 5, 999.00),
        ("Pod Mesh Coil (5-Pack)", 250, 5, 699.00),
        ("Refillable Pod Kit", 700, 4, 1299.00),
        ("Premium Pod Device", 1000, 3, 1799.00),
    ]),
    ("E-Liquids", [
        ("E-Liquid 30ml", 120, 10, 299.00),
        ("E-Liquid 60ml Premium", 200, 6, 499.00),
        ("E-Liquid 100ml Bulk", 300, 4, 699.00),
        ("Zero Nicotine 30ml", 100, 8, 249.00),
        ("High Strength 50mg 30ml", 150, 5, 399.00),
        ("Menthol 30ml", 120, 10, 299.00),
        ("Tobacco Blend 30ml", 120, 8, 299.00),
        ("Dessert Flavor 30ml", 130, 7, 349.00),
        ("Fruit Mix 60ml", 200, 6, 499.00),
        ("Strawberry 30ml", 120, 9, 299.00),
    ]),
    ("Accessories", [
        ("Coil Pack (10 pcs)", 200, 6, 499.00),
        ("Battery 18650", 80, 12, 249.00),
        ("Battery Charger", 250, 4, 599.00),
        ("Tank Glass Replacement", 150, 8, 399.00),
        ("Drip Tips (5-Pack)", 100, 7, 249.00),
        ("Vape Carrying Case", 200, 5, 499.00),
        ("Cotton Wicks", 50, 10, 149.00),
        ("USB-C Cable for Vape", 60, 8, 199.00),
    ]),
    ("Premium Devices", [
        ("Advanced Mod", 1800, 3, 2999.00),
        ("Professional Starter Kit", 1500, 2, 2499.00),
        ("Temperature Control Device", 3000, 1, 4999.00),
        ("Dual Battery Mod", 2000, 2, 3499.00),
        ("Smart Display Mod", 2500, 2, 3999.00),
        ("Sub-Ohm Tank System", 1200, 3, 1999.00),
    ]),
]

PRODUCTS = []
for cat, items in CATEGORIES:
    for name, unit_cost, base_qty, price in items:
        PRODUCTS.append({
            "name": name,
            "category": cat,
            "unit_cost": float(unit_cost),
            "base_qty": int(base_qty),
            "price": float(price),
        })

# Ensure >= 40
assert len(PRODUCTS) >= 40, f"Only {len(PRODUCTS)} products prepared"


def seasonal_factor(month):
    return {
        1: 0.85, 2: 0.75, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.10,
        7: 1.05, 8: 0.90, 9: 1.15, 10: 1.10, 11: 1.25, 12: 1.35
    }.get(month, 1.0)


def weekday_factor(dow):
    return {0:1.15,1:1.20,2:1.25,3:1.20,4:1.10,5:0.70,6:0.60}.get(dow, 1.0)


def product_trend(name, year, month):
    months_elapsed = (year - 2022) * 12 + (month - 1)
    # Generic mild growth by default
    base = 1.0 + 0.01 * months_elapsed
    # Vape product trends
    if "Disposable" in name or "Puff" in name:
        base = 1.0 + 0.015 * months_elapsed  # Disposable vapes growing
    if "Pod" in name:
        base = 1.0 + 0.012 * months_elapsed  # Pod systems steady growth
    if "E-Liquid" in name or "Liquid" in name:
        base = 1.0 + 0.01 * months_elapsed  # E-liquids consistent
    if "Coil" in name or "Battery" in name or "Tank" in name:
        base = 1.0 - 0.002 * months_elapsed  # Accessories saturation
    if "Premium" in name or "Advanced" in name or "Temperature Control" in name or "Mod" in name:
        base = 1.0 + 0.02 * months_elapsed  # Premium devices growing
    return max(0.1, base)


def generate_rows():
    start = datetime(2022, 1, 1)
    end = datetime(2025, 11, 10)
    date = start

    # Initial stocks
    stock = {p["name"]: random.randint(50, 500) for p in PRODUCTS}

    rows = []
    print(f"Generating data {start.date()} .. {end.date()} for {len(PRODUCTS)} products")
    while date <= end:
        s = seasonal_factor(date.month)
        w = weekday_factor(date.weekday())
        for p in PRODUCTS:
            trend = product_trend(p["name"], date.year, date.month)
            expected = p["base_qty"] * s * w * trend
            qty = int(expected * random.uniform(0.6, 1.4))
            # 25% chance of no sale that day for a product
            if random.random() < 0.25:
                qty = 0
            if qty <= 0:
                continue
            if stock[p["name"]] < qty:
                stock[p["name"]] += qty * 30  # restock generously
            price = round(p["price"] * random.uniform(0.95, 1.06), 2)
            stock[p["name"]] -= qty
            rows.append({
                "product_name": p["name"],
                "category": p["category"],
                "unit_cost": p["unit_cost"],
                "quantity_sold": qty,
                "sale_price": price,
                "sale_date": date.strftime('%Y-%m-%d'),
                "stock_after_sale": stock[p["name"]]
            })
        # progress each month boundary
        if date.day == 1:
            print(f"  {date.strftime('%b %Y')}")
        date += timedelta(days=1)
    return rows


def save_csv(rows, filename):
    fields = ["product_name","category","unit_cost","quantity_sold","sale_price","sale_date","stock_after_sale"]
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Saved {len(rows):,} rows to {filename}")


if __name__ == '__main__':
    rows = generate_rows()
    # Use parent directory path
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    data_path = os.path.join(parent_dir, 'data', 'historical_sales_2022_2025_large.csv')
    save_csv(rows, data_path)
