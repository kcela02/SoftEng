#!/usr/bin/env python3
"""
Generate historical sales CSV with VAPE CRIB products
Date range: Jan 1, 2022 to Feb 10, 2026
"""
import csv
from datetime import datetime, timedelta
import random

# 15+ Vape Products across categories
VAPE_PRODUCTS = [
    # Disposable Vapes (5 products)
    {"name": "Classic 500 Puff", "category": "Disposable Vapes", "unit_cost": 150, "base_qty": 8, "price": 399.00},
    {"name": "Premium 2000 Puff", "category": "Disposable Vapes", "unit_cost": 280, "base_qty": 5, "price": 799.00},
    {"name": "Max 3000 Puff", "category": "Disposable Vapes", "unit_cost": 350, "base_qty": 4, "price": 999.00},
    {"name": "Lite 200 Puff", "category": "Disposable Vapes", "unit_cost": 100, "base_qty": 12, "price": 249.00},
    {"name": "Tropical Mix 500 Puff", "category": "Disposable Vapes", "unit_cost": 150, "base_qty": 8, "price": 399.00},
    
    # Pod Systems (4 products)
    {"name": "Pod System Kit", "category": "Pod Systems", "unit_cost": 800, "base_qty": 3, "price": 1499.00},
    {"name": "Replacement Pods (4-Pack)", "category": "Pod Systems", "unit_cost": 200, "base_qty": 6, "price": 599.00},
    {"name": "Compact Pod Kit", "category": "Pod Systems", "unit_cost": 600, "base_qty": 4, "price": 1199.00},
    {"name": "Advanced Pod Kit", "category": "Pod Systems", "unit_cost": 1200, "base_qty": 2, "price": 1999.00},
    
    # E-Liquids (5 products)
    {"name": "E-Liquid 30ml", "category": "E-Liquids", "unit_cost": 120, "base_qty": 10, "price": 299.00},
    {"name": "E-Liquid 60ml Premium", "category": "E-Liquids", "unit_cost": 200, "base_qty": 6, "price": 499.00},
    {"name": "E-Liquid 100ml Bulk", "category": "E-Liquids", "unit_cost": 300, "base_qty": 4, "price": 699.00},
    {"name": "Zero Nicotine 30ml", "category": "E-Liquids", "unit_cost": 100, "base_qty": 8, "price": 249.00},
    {"name": "High Strength 50mg 30ml", "category": "E-Liquids", "unit_cost": 150, "base_qty": 5, "price": 399.00},
    
    # Accessories (4 products)
    {"name": "Coil Pack (10 pcs)", "category": "Accessories", "unit_cost": 200, "base_qty": 6, "price": 499.00},
    {"name": "Battery 18650", "category": "Accessories", "unit_cost": 80, "base_qty": 12, "price": 249.00},
    {"name": "Battery Charger", "category": "Accessories", "unit_cost": 250, "base_qty": 4, "price": 599.00},
    {"name": "Tank Glass Replacement", "category": "Accessories", "unit_cost": 150, "base_qty": 8, "price": 399.00},
    
    # Premium Devices (3 products)
    {"name": "Advanced Mod", "category": "Premium Devices", "unit_cost": 1800, "base_qty": 3, "price": 2999.00},
    {"name": "Professional Starter Kit", "category": "Premium Devices", "unit_cost": 1500, "base_qty": 2, "price": 2499.00},
    {"name": "Temperature Control Device", "category": "Premium Devices", "unit_cost": 3000, "base_qty": 1, "price": 4999.00},
]


def seasonal_factor(month):
    return {
        1: 0.85, 2: 0.75, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.10,
        7: 1.05, 8: 0.90, 9: 1.15, 10: 1.10, 11: 1.25, 12: 1.35
    }.get(month, 1.0)


def weekday_factor(dow):
    return {0: 1.15, 1: 1.20, 2: 1.25, 3: 1.20, 4: 1.10, 5: 0.70, 6: 0.60}.get(dow, 1.0)


def product_trend(name, year, month):
    months_elapsed = (year - 2022) * 12 + (month - 1)
    # Disposable vapes steady growth
    if "Disposable" in name or "Puff" in name:
        return 1.0 + 0.015 * months_elapsed
    # Pod systems gradual growth
    if "Pod" in name:
        return 1.0 + 0.012 * months_elapsed
    # E-liquids consistent
    if "E-Liquid" in name:
        return 1.0 + 0.01 * months_elapsed
    # Accessories slight decline (saturated market)
    if "Accessories" in name or "Coil" in name or "Battery" in name:
        return 1.0 - 0.002 * months_elapsed
    # Premium devices growth
    if "Premium" in name or "Advanced" in name or "Control" in name:
        return 1.0 + 0.02 * months_elapsed
    return 1.0


def generate_sales_csv(output_file):
    rows = []
    rows.append(["product_name", "category", "unit_cost", "quantity_sold", "sale_price", "sale_date", "stock_after_sale"])
    
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2026, 2, 10)
    
    current_date = start_date
    stock = {p["name"]: random.randint(200, 500) for p in VAPE_PRODUCTS}
    
    while current_date <= end_date:
        month = current_date.month
        year = current_date.year
        dow = current_date.weekday()
        
        # 60% chance of sales activity on any given day
        if random.random() < 0.6:
            # Pick 2-5 random products to sell on this day
            products_to_sell = random.sample(VAPE_PRODUCTS, random.randint(2, min(5, len(VAPE_PRODUCTS))))
            
            for product in products_to_sell:
                base_qty = product["base_qty"]
                seasonal = seasonal_factor(month)
                weekday = weekday_factor(dow)
                trend = product_trend(product["name"], year, month)
                
                # Calculate quantity with some randomness
                qty = max(1, int(base_qty * seasonal * weekday * trend * random.uniform(0.7, 1.3)))
                
                stock[product["name"]] = max(1, stock[product["name"]] - qty)
                
                rows.append([
                    product["name"],
                    product["category"],
                    product["unit_cost"],
                    qty,
                    product["price"],
                    current_date.strftime("%Y-%m-%d"),
                    stock[product["name"]]
                ])
        
        current_date += timedelta(days=1)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"✅ Generated {len(rows) - 1} sales records for {len(VAPE_PRODUCTS)} vape products")
    print(f"📁 Saved to: {output_file}")


if __name__ == "__main__":
    generate_sales_csv("data/historical_sales_vape.csv")
    print("\n📊 Vape product data generated successfully!")
    print(f"📦 Total products: {len(VAPE_PRODUCTS)}")
    print("\nProducts included:")
    for p in VAPE_PRODUCTS:
        print(f"  • {p['name']} ({p['category']}) - ₱{p['price']:.2f}")
