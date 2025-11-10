"""
Generate a large historical sales CSV with at least 40 products
Date range: Jan 1, 2022 to Nov 10, 2025
Format: unified_sales CSV compatible with upload (product_name, quantity_sold, sale_price, category, unit_cost, sale_date, stock_after_sale)
"""
import csv
from datetime import datetime, timedelta
import random

# Build 40+ products across several categories
CATEGORIES = [
    ("Electronics", [
        ("Laptop", 28000, 2, 34999.00),
        ("Mouse", 180, 6, 299.00),
        ("Keyboard", 900, 4, 1299.00),
        ("Monitor", 9000, 2, 14999.00),
        ("Webcam", 1600, 2, 2499.00),
        ("Headphones", 1400, 3, 2199.00),
        ("Power Bank", 700, 3, 1599.00),
        ("Bluetooth Speaker", 1100, 2, 1999.00),
    ]),
    ("Accessories", [
        ("USB Cable", 60, 12, 120.00),
        ("HDMI Cable", 120, 7, 350.00),
        ("Phone Case", 90, 8, 299.00),
        ("Screen Protector", 30, 10, 199.00),
        ("Charger", 250, 6, 799.00),
        ("Earbuds", 500, 5, 899.00),
        ("Memory Card 64GB", 400, 4, 699.00),
        ("OTG Adapter", 40, 10, 149.00),
    ]),
    ("Home & Living", [
        ("Desk Lamp", 450, 3, 799.00),
        ("LED Strip", 200, 3, 499.00),
        ("Extension Cord", 300, 4, 399.00),
        ("Electric Kettle", 700, 2, 1499.00),
        ("Rice Cooker", 1200, 2, 1899.00),
        ("Stand Fan", 1500, 2, 1699.00),
        ("Air Purifier Filter", 800, 2, 1299.00),
        ("Water Bottle", 120, 5, 399.00),
    ]),
    ("Office", [
        ("Printer Paper (Ream)", 160, 5, 320.00),
        ("Ink Cartridge", 500, 3, 1099.00),
        ("Stapler", 200, 3, 299.00),
        ("Notebook", 45, 8, 99.00),
        ("Pen Set", 25, 9, 149.00),
        ("Office Chair", 3500, 1, 4999.00),
        ("Desk Organizer", 180, 3, 399.00),
        ("Whiteboard Marker", 30, 7, 79.00),
    ]),
    ("Gadgets", [
        ("Smartwatch", 2500, 2, 4999.00),
        ("Fitness Band", 1200, 3, 1999.00),
        ("Tablet", 9000, 1, 12999.00),
        ("E-Reader", 4500, 1, 6999.00),
        ("Drone", 15000, 1, 19999.00),
        ("Action Camera", 4500, 1, 9999.00),
        ("Gaming Mouse", 600, 3, 1799.00),
        ("Mechanical Keyboard", 1500, 2, 3599.00),
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
    # A few overrides by keyword
    if "Laptop" in name or "Tablet" in name:
        base = 1.0 + 0.015 * months_elapsed
    if "Monitor" in name or "Printer" in name:
        base = 1.0 - 0.003 * months_elapsed
    if "USB" in name or "Cable" in name or "Memory Card" in name:
        base = 1.0 + 0.02 * months_elapsed
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
    save_csv(rows, 'data/historical_sales_2022_2025_large.csv')
