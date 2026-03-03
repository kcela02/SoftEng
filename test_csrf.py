#!/usr/bin/env python
"""Test CSRF token handling for login endpoint"""
import requests
import json
import re

BASE_URL = 'http://127.0.0.1:5000'
session = requests.Session()

print("=" * 60)
print("Testing CSRF Protection & Login")
print("=" * 60)

# Step 1: GET login page to get CSRF token
print("\n1. Getting login page to extract CSRF token...")
response = session.get(f'{BASE_URL}/login')
print(f"   Status: {response.status_code}")

# Extract CSRF token from meta tag using regex
csrf_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', response.text)
csrf_token = csrf_match.group(1) if csrf_match else None

if csrf_token:
    print(f"   ✓ CSRF Token found: {csrf_token[:20]}...")
else:
    print("   ✗ No CSRF token found in page!")

# Step 2: Try login with CSRF token in header
print("\n2. Attempting login with valid credentials...")
login_data = {
    'username': 'admin',
    'password': 'admin123'
}

headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token if csrf_token else ''
}

response = session.post(
    f'{BASE_URL}/login',
    json=login_data,
    headers=headers
)

print(f"   Status: {response.status_code}")
try:
    data = response.json()
    print(f"   Response data: {data}")
    
    if response.status_code == 200 or response.status_code == 302:
        if isinstance(data, dict):
            if data.get('success'):
                print(f"   ✓ Login successful!")
                print(f"   Message: {data.get('message')}")
            else:
                print(f"   ✗ Login failed: {data.get('message')}")
        else:
            print(f"   Response: {data}")
    elif response.status_code == 400:
        print(f"   ✗ Bad request (CSRF issue): {data}")
    else:
        print(f"   ? Status {response.status_code}: {data}")
except Exception as e:
    print(f"   Response text: {response.text[:500]}")
    print(f"   Error parsing: {str(e)}")

print("\n" + "=" * 60)
