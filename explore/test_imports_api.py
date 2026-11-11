#!/usr/bin/env python3
"""
TEST IMPORTS API - Identify correct variables and test queries
"""

import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ["CENSUS_API_KEY"]

print("=" * 70)
print("TESTING IMPORTS HS API")
print("=" * 70)

# =============================================================================
# 1. Get available variables for imports/hs endpoint
# =============================================================================
print("\n>>> Fetching available variables...")
var_url = "https://api.census.gov/data/timeseries/intltrade/imports/hs/variables.json"
response = requests.get(var_url, timeout=60)

if response.status_code == 200:
    variables = response.json().get('variables', {})
    print(f"Total variables: {len(variables)}")
    
    # List all variables
    print("\nAll variables:")
    for var_name in sorted(variables.keys()):
        if not var_name.startswith('_'):
            var_info = variables[var_name]
            label = var_info.get('label', 'No label')[:60]
            print(f"  {var_name}: {label}")
else:
    print(f"Error fetching variables: {response.status_code}")

# =============================================================================
# 2. Test minimal query
# =============================================================================
print("\n" + "=" * 70)
print("TESTING MINIMAL QUERIES")
print("=" * 70)

# Test 1: Very basic query
print("\n>>> Test 1: Minimal query (just value and time)...")
url1 = f"https://api.census.gov/data/timeseries/intltrade/imports/hs?get=GEN_VAL_MO&time=2013-01&COMM_LVL=HS2&key={API_KEY}"
print(f"URL: {url1[:100]}...")
resp = requests.get(url1, timeout=60)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Rows: {len(data) - 1}")
    print(f"Sample: {data[:3]}")
else:
    print(f"Response: {resp.text[:300]}")

time.sleep(1)

# Test 2: Add commodity code
print("\n>>> Test 2: With commodity code...")
url2 = f"https://api.census.gov/data/timeseries/intltrade/imports/hs?get=I_COMMODITY,GEN_VAL_MO&time=2013-01&COMM_LVL=HS2&key={API_KEY}"
print(f"URL: {url2[:100]}...")
resp = requests.get(url2, timeout=60)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Rows: {len(data) - 1}")
    print(f"Sample: {data[:3]}")
else:
    print(f"Response: {resp.text[:300]}")

time.sleep(1)

# Test 3: Add country
print("\n>>> Test 3: With country...")
url3 = f"https://api.census.gov/data/timeseries/intltrade/imports/hs?get=I_COMMODITY,CTY_CODE,GEN_VAL_MO&time=2013-01&COMM_LVL=HS2&key={API_KEY}"
print(f"URL: {url3[:100]}...")
resp = requests.get(url3, timeout=60)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Rows: {len(data) - 1}")
    print(f"Sample: {data[:3]}")
else:
    print(f"Response: {resp.text[:300]}")

time.sleep(1)

# Test 4: Full query similar to exports
print("\n>>> Test 4: More complete query...")
url4 = f"https://api.census.gov/data/timeseries/intltrade/imports/hs?get=I_COMMODITY,I_COMMODITY_SDESC,CTY_CODE,CTY_NAME,GEN_VAL_MO,GEN_VAL_YR&time=2013-01&COMM_LVL=HS2&key={API_KEY}"
print(f"URL: {url4[:100]}...")
resp = requests.get(url4, timeout=60)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Rows: {len(data) - 1}")
    print(f"Headers: {data[0]}")
    print(f"Sample row: {data[1] if len(data) > 1 else 'None'}")
else:
    print(f"Response: {resp.text[:300]}")

time.sleep(1)

# Test 5: Add district (this might be causing issues)
print("\n>>> Test 5: With DISTRICT...")
url5 = f"https://api.census.gov/data/timeseries/intltrade/imports/hs?get=I_COMMODITY,CTY_CODE,DISTRICT,GEN_VAL_MO&time=2013-01&COMM_LVL=HS2&key={API_KEY}"
print(f"URL: {url5[:100]}...")
resp = requests.get(url5, timeout=60)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Rows: {len(data) - 1}")
else:
    print(f"Response: {resp.text[:300]}")

time.sleep(1)

# Test 6: Without DISTRICT
print("\n>>> Test 6: Without DISTRICT, with more fields...")
url6 = f"https://api.census.gov/data/timeseries/intltrade/imports/hs?get=I_COMMODITY,I_COMMODITY_SDESC,CTY_CODE,CTY_NAME,COMM_LVL,GEN_VAL_MO,GEN_VAL_YR,CON_VAL_MO,CON_VAL_YR&time=2013-01&COMM_LVL=HS2&key={API_KEY}"
print(f"URL: {url6[:100]}...")
resp = requests.get(url6, timeout=60)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Rows: {len(data) - 1}")
    print(f"Headers: {data[0]}")
else:
    print(f"Response: {resp.text[:300]}")

print("\n" + "=" * 70)
print("TESTS COMPLETE")
print("=" * 70)