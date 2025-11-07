"""
Comprehensive system sweep: verify main pages and API endpoints are reachable and consistent.
- Logs in as admin
- GET checks for all known API endpoints
- CRUD cycle on products (create/update/get/delete) using a test product
- Reversible inventory adjust (+1 then -1) on an existing product
- Prints PASS/FAIL per check
"""
import requests
import os
import time
from datetime import datetime

BASE_URL = os.getenv("SWEEP_BASE_URL", "http://127.0.0.1:5000")
s = requests.Session()

results = []

def check(name, func):
    try:
        ok, info = func()
        results.append((name, ok, info))
    except Exception as e:
        results.append((name, False, f"EXCEPTION: {e}"))

# 1) Login
def do_login():
    r = s.post(f"{BASE_URL}/login", data={"username": "admin", "password": "admin123"}, allow_redirects=True)
    return (r.status_code == 200, f"status={r.status_code}")

# 2) Pages
PAGES = ["/", "/dashboard", "/products", "/forecasting", "/reports", "/settings"]

def check_pages():
    for path in PAGES:
        r = s.get(f"{BASE_URL}{path}")
        if r.status_code != 200:
            return False, f"{path} => {r.status_code}"
    return True, f"{len(PAGES)} pages OK"

# 3) API GET endpoints
GET_ENDPOINTS = [
    "/api/metrics",
    "/api/restock-alerts",
    "/api/reports/turnover",
    "/api/export-alerts",
    "/api/export-report",
    "/api/download-all-data",
    "/api/list-imports",
    "/api/products",
    "/api/top-products",
    "/api/recent-activity",
    "/api/forecast-accuracy",
    "/api/weekly-forecast",
    "/api/model-comparison",
    "/api/enhanced-restock-alerts",
]

def _get_any_product_id():
    r = s.get(f"{BASE_URL}/api/products")
    if r.status_code == 200:
        try:
            data = r.json()
            products = data.get("products") or data
            if isinstance(products, list) and products:
                return products[0].get("id") or products[0].get("product_id")
        except Exception:
            pass
    return None

def check_get_endpoints():
    # First check generic endpoints
    for ep in GET_ENDPOINTS:
        r = s.get(f"{BASE_URL}{ep}")
        if r.status_code != 200:
            return False, f"{ep} => {r.status_code}"
    # Endpoints requiring params: supply a valid product_id if available
    pid = _get_any_product_id()
    if pid:
        # forecast visualization
        r = s.get(f"{BASE_URL}/api/forecast-visualization", params={"product_id": pid})
        if r.status_code != 200:
            return False, f"/api/forecast-visualization => {r.status_code}"
        # synchronized daily/weekly
        for ep in ("/api/forecast/daily", "/api/forecast/weekly"):
            r = s.get(f"{BASE_URL}{ep}", params={"product_id": pid})
            if r.status_code != 200:
                return False, f"{ep} => {r.status_code}"
    else:
        # If no products, still consider endpoints pass since product-specific ones can't be tested
        pass
    return True, "GET endpoints OK"

# 4) Product CRUD
created_product_id = None

def product_crud():
    global created_product_id
    # Create
    name = f"TEST_SWEEP_{int(time.time())}"
    payload = {
        "name": name,
        "category": "Test",
        "unit_cost": 123.45,
        "current_stock": 7
    }
    r = s.post(f"{BASE_URL}/api/products", json=payload)
    if r.status_code not in (200, 201):
        return False, f"CREATE => {r.status_code} {r.text[:120]}"
    data = r.json()
    created_product_id = data.get("product", {}).get("id") or data.get("id")
    if not created_product_id:
        return False, f"CREATE => missing id in response"

    # GET by id
    r = s.get(f"{BASE_URL}/api/products/{created_product_id}")
    if r.status_code != 200:
        return False, f"GET => {r.status_code}"

    # UPDATE
    upd = {
        "name": name + "_UPD",
        "category": "Test",
        "unit_cost": 200.0,
        "current_stock": 9
    }
    r = s.put(f"{BASE_URL}/api/products/{created_product_id}", json=upd)
    if r.status_code != 200:
        return False, f"PUT => {r.status_code} {r.text[:120]}"

    # GET sales-count (should work even if zero)
    r = s.get(f"{BASE_URL}/api/products/{created_product_id}/sales-count")
    if r.status_code != 200:
        return False, f"sales-count => {r.status_code}"

    # DELETE
    r = s.delete(f"{BASE_URL}/api/products/{created_product_id}")
    if r.status_code != 200:
        return False, f"DELETE => {r.status_code} {r.text[:200]}"

    return True, f"CRUD OK (id={created_product_id})"

# 5) Inventory adjust (+1 then -1) on existing product 2 if present

def inventory_adjust():
    # Try to find any existing product id
    pid = _get_any_product_id()
    temp_id = None
    if not pid:
        # Create a temp product to test inventory adjustment
        name = f"TEMP_INV_{int(time.time())}"
        payload = {"name": name, "category": "Test", "unit_cost": 50.0, "current_stock": 0}
        r = s.post(f"{BASE_URL}/api/products", json=payload)
        if r.status_code not in (200, 201):
            return False, f"prep create product => {r.status_code}"
        temp = r.json()
        pid = temp.get("product", {}).get("id") or temp.get("id")
        temp_id = pid
        if not pid:
            return False, "prep create product => missing id"

    # +1 add
    r = s.post(f"{BASE_URL}/api/inventory/adjust", json={"product_id": pid, "quantity": 1, "operation": "add", "reason": "sweep +1"})
    if r.status_code != 200:
        return False, f"adjust add => {r.status_code} {r.text[:120]}"
    # -1 remove
    r = s.post(f"{BASE_URL}/api/inventory/adjust", json={"product_id": pid, "quantity": 1, "operation": "remove", "reason": "sweep -1"})
    if r.status_code != 200:
        return False, f"adjust remove => {r.status_code} {r.text[:120]}"
    # history
    r = s.get(f"{BASE_URL}/api/inventory/history")
    if r.status_code != 200:
        return False, f"history => {r.status_code}"

    # Cleanup temp product if created
    if temp_id:
        s.delete(f"{BASE_URL}/api/products/{temp_id}")
    return True, "adjust/revert OK"

# 6) Forecast endpoints for known product id (2)

def forecasts():
    # legacy
    r = s.get(f"{BASE_URL}/api/forecast/2")
    if r.status_code != 200:
        return False, f"/forecast/<id> => {r.status_code}"
    # daily aggregate (requires query params for week/month? Accept bare 200)
    r = s.get(f"{BASE_URL}/api/forecast/daily?product_id=2")
    if r.status_code != 200:
        return False, f"/forecast/daily => {r.status_code}"
    # weekly
    r = s.get(f"{BASE_URL}/api/forecast/weekly?product_id=2")
    if r.status_code != 200:
        return False, f"/forecast/weekly => {r.status_code}"
    # vs-actual
    r = s.get(f"{BASE_URL}/api/forecast-vs-actual/2")
    if r.status_code != 200:
        return False, f"/forecast-vs-actual => {r.status_code}"
    return True, "forecast endpoints OK"

if __name__ == "__main__":
    print("Starting system sweep...")
    check("login", do_login)
    check("pages", check_pages)
    check("GET endpoints", check_get_endpoints)
    check("product CRUD", product_crud)
    check("inventory adjust", inventory_adjust)
    check("forecasts", forecasts)

    print("\nRESULTS:")
    passed = 0
    for name, ok, info in results:
        status = "PASS" if ok else "FAIL"
        print(f"- {name:18} {status:4} - {info}")
        if ok: passed += 1
    print(f"\nSummary: {passed}/{len(results)} checks passed")
