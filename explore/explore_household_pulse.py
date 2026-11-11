#!/usr/bin/env python3
"""
HOUSEHOLD PULSE SURVEY - API EXPLORATION
Explores both HPS endpoints to understand data structure
"""

import requests
import json
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ["CENSUS_API_KEY"]

print("=" * 70)
print("HOUSEHOLD PULSE SURVEY - API EXPLORATION")
print("=" * 70)

# =============================================================================
# 1. EXPLORE HHPULSE (High Frequency Social and Economic Data)
# =============================================================================
print("\n" + "=" * 60)
print("1. HHPULSE - High Frequency Social and Economic Data")
print("=" * 60)

# Get variables
print("\n>>> Fetching HHPULSE variables...")
var_url = "https://api.census.gov/data/timeseries/hhpulse/variables.json"
try:
    response = requests.get(var_url, timeout=60)
    if response.status_code == 200:
        variables = response.json().get('variables', {})
        print(f"Total variables: {len(variables)}")
        print("\nKey variables:")
        for var_name, var_info in list(variables.items())[:30]:
            label = var_info.get('label', '')[:60]
            print(f"  {var_name:20}: {label}")
    else:
        print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Get geography
print("\n>>> Fetching HHPULSE geography...")
geo_url = "https://api.census.gov/data/timeseries/hhpulse/geography.json"
try:
    response = requests.get(geo_url, timeout=60)
    if response.status_code == 200:
        geo_data = response.json()
        print(f"Geography data: {json.dumps(geo_data, indent=2)[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test example call from documentation
print("\n>>> Testing HHPULSE example call...")
test_url = f"https://api.census.gov/data/timeseries/hhpulse?get=SURVEY_YEAR,NAME&for=state:*&time=2024&CYCLE=01&key={API_KEY}"
try:
    response = requests.get(test_url, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        print(f"Sample: {data[1:4]}")
except Exception as e:
    print(f"Error: {e}")

# Test getting more variables
print("\n>>> Testing HHPULSE with more variables...")
test_url2 = f"https://api.census.gov/data/timeseries/hhpulse?get=NAME,SURVEY_YEAR,CYCLE,WEEK,TOPIC,INDICATOR,RESPONSE,ESTIMATE,STANDARD_ERROR&for=state:*&time=2024&CYCLE=01&key={API_KEY}"
try:
    response = requests.get(test_url2, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        print(f"Sample rows:")
        for row in data[1:5]:
            print(f"  {row}")
    else:
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test without CYCLE filter to see all data
print("\n>>> Testing HHPULSE for all cycles in 2024...")
test_url3 = f"https://api.census.gov/data/timeseries/hhpulse?get=NAME,SURVEY_YEAR,CYCLE&for=state:01&time=2024&key={API_KEY}"
try:
    response = requests.get(test_url3, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        # Get unique cycles
        cycles = set(row[2] for row in data[1:])
        print(f"Cycles in 2024: {sorted(cycles)}")
except Exception as e:
    print(f"Error: {e}")

# Test different years
print("\n>>> Testing HHPULSE available years...")
for year in [2020, 2021, 2022, 2023, 2024]:
    test_url = f"https://api.census.gov/data/timeseries/hhpulse?get=NAME,CYCLE&for=state:01&time={year}&key={API_KEY}"
    try:
        response = requests.get(test_url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            cycles = set(row[1] for row in data[1:]) if len(data) > 1 else set()
            print(f"  {year}: {len(data)-1} rows, Cycles: {sorted(cycles)[:10]}...")
        else:
            print(f"  {year}: Status {response.status_code}")
    except Exception as e:
        print(f"  {year}: Error")

# =============================================================================
# 2. EXPLORE HPS (COVID-19 Pandemic and Recovery)
# =============================================================================
print("\n" + "=" * 60)
print("2. HPS - COVID-19 Pandemic and Recovery")
print("=" * 60)

# Get variables
print("\n>>> Fetching HPS variables...")
var_url = "https://api.census.gov/data/timeseries/hps/variables.json"
try:
    response = requests.get(var_url, timeout=60)
    if response.status_code == 200:
        variables = response.json().get('variables', {})
        print(f"Total variables: {len(variables)}")
        print("\nKey variables:")
        for var_name, var_info in list(variables.items())[:30]:
            label = var_info.get('label', '')[:60]
            print(f"  {var_name:20}: {label}")
    else:
        print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Get geography
print("\n>>> Fetching HPS geography...")
geo_url = "https://api.census.gov/data/timeseries/hps/geography.json"
try:
    response = requests.get(geo_url, timeout=60)
    if response.status_code == 200:
        geo_data = response.json()
        print(f"Geography data: {json.dumps(geo_data, indent=2)[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test example call from documentation
print("\n>>> Testing HPS example call...")
test_url = f"https://api.census.gov/data/timeseries/hps?get=NAME,SURVEY_YEAR&for=state:*&time=2020&key={API_KEY}"
try:
    response = requests.get(test_url, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        print(f"Sample: {data[1:4]}")
    else:
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test with more variables
print("\n>>> Testing HPS with more variables...")
test_url2 = f"https://api.census.gov/data/timeseries/hps?get=NAME,SURVEY_YEAR,WEEK,TOPIC,INDICATOR,RESPONSE,VALUE,STANDARD_ERROR&for=state:*&time=2020&key={API_KEY}"
try:
    response = requests.get(test_url2, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        print(f"Sample rows:")
        for row in data[1:5]:
            print(f"  {row}")
    else:
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test different years
print("\n>>> Testing HPS available years...")
for year in [2020, 2021, 2022, 2023, 2024]:
    test_url = f"https://api.census.gov/data/timeseries/hps?get=NAME,WEEK&for=state:01&time={year}&key={API_KEY}"
    try:
        response = requests.get(test_url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            weeks = set(row[1] for row in data[1:]) if len(data) > 1 else set()
            print(f"  {year}: {len(data)-1} rows, Weeks: {sorted(weeks)[:10]}...")
        else:
            print(f"  {year}: Status {response.status_code}")
    except Exception as e:
        print(f"  {year}: Error")

# =============================================================================
# 3. EXPLORE DETAILED STRUCTURE
# =============================================================================
print("\n" + "=" * 60)
print("3. DETAILED DATA STRUCTURE ANALYSIS")
print("=" * 60)

# For HHPULSE - get all available predicates/filters
print("\n>>> Analyzing HHPULSE data structure...")
test_url = f"https://api.census.gov/data/timeseries/hhpulse?get=NAME,SURVEY_YEAR,CYCLE,WEEK,TOPIC,INDICATOR,RESPONSE,ESTIMATE&for=us:1&time=2024&CYCLE=01&key={API_KEY}"
try:
    response = requests.get(test_url, timeout=60)
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Total rows: {len(data) - 1}")
        
        if len(data) > 1:
            # Analyze unique values
            headers = data[0]
            rows = data[1:]
            
            for i, header in enumerate(headers):
                if header in ['TOPIC', 'INDICATOR', 'RESPONSE', 'WEEK']:
                    unique_vals = set(row[i] for row in rows if row[i])
                    print(f"\n  Unique {header} values ({len(unique_vals)}):")
                    for val in sorted(list(unique_vals))[:15]:
                        print(f"    - {val}")
                    if len(unique_vals) > 15:
                        print(f"    ... and {len(unique_vals) - 15} more")
except Exception as e:
    print(f"Error: {e}")

# For HPS - get all available predicates/filters
print("\n>>> Analyzing HPS data structure...")
test_url = f"https://api.census.gov/data/timeseries/hps?get=NAME,SURVEY_YEAR,WEEK,TOPIC_CODE,INDICATOR_CODE,GROUP_CODE,RESPONSE_CODE,VALUE&for=us:1&time=2020&key={API_KEY}"
try:
    response = requests.get(test_url, timeout=60)
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Total rows: {len(data) - 1}")
        
        if len(data) > 1:
            headers = data[0]
            rows = data[1:]
            
            for i, header in enumerate(headers):
                if header in ['TOPIC_CODE', 'INDICATOR_CODE', 'GROUP_CODE', 'RESPONSE_CODE', 'WEEK']:
                    unique_vals = set(row[i] for row in rows if row[i])
                    print(f"\n  Unique {header} values ({len(unique_vals)}):")
                    for val in sorted(list(unique_vals))[:15]:
                        print(f"    - {val}")
                    if len(unique_vals) > 15:
                        print(f"    ... and {len(unique_vals) - 15} more")
    else:
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
print("EXPLORATION COMPLETE")
print("=" * 70)