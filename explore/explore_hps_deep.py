#!/usr/bin/env python3
"""
HOUSEHOLD PULSE SURVEY - DEEP VARIABLE EXPLORATION
"""

import requests
import json
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ["CENSUS_API_KEY"]

print("=" * 70)
print("HOUSEHOLD PULSE SURVEY - DEEP VARIABLE EXPLORATION")
print("=" * 70)

# =============================================================================
# 1. GET ALL HHPULSE VARIABLES
# =============================================================================
print("\n" + "=" * 60)
print("1. HHPULSE - ALL VARIABLES")
print("=" * 60)

var_url = "https://api.census.gov/data/timeseries/hhpulse/variables.json"
try:
    response = requests.get(var_url, timeout=60)
    if response.status_code == 200:
        variables = response.json().get('variables', {})
        print(f"\nTotal variables: {len(variables)}")
        
        # Categorize variables
        predicates = []
        data_vars = []
        
        for var_name, var_info in variables.items():
            pred_type = var_info.get('predicateType', '')
            if pred_type:
                predicates.append((var_name, var_info.get('label', ''), pred_type))
            else:
                data_vars.append((var_name, var_info.get('label', '')))
        
        print("\nPredicate variables (for filtering):")
        for name, label, ptype in predicates:
            print(f"  {name:20} ({ptype:15}): {label[:50]}")
        
        print("\nData variables (for retrieval):")
        for name, label in data_vars:
            print(f"  {name:25}: {label[:50]}")
except Exception as e:
    print(f"Error: {e}")

# =============================================================================
# 2. GET ALL HPS VARIABLES  
# =============================================================================
print("\n" + "=" * 60)
print("2. HPS - ALL VARIABLES")
print("=" * 60)

var_url = "https://api.census.gov/data/timeseries/hps/variables.json"
try:
    response = requests.get(var_url, timeout=60)
    if response.status_code == 200:
        variables = response.json().get('variables', {})
        print(f"\nTotal variables: {len(variables)}")
        
        # Categorize
        predicates = []
        total_vars = []
        rate_vars = []
        univ_vars = []
        other_vars = []
        
        for var_name, var_info in variables.items():
            label = var_info.get('label', '')
            pred_type = var_info.get('predicateType', '')
            
            if pred_type:
                predicates.append((var_name, label, pred_type))
            elif var_name.endswith('_TOTAL'):
                total_vars.append((var_name, label))
            elif var_name.endswith('_RATE'):
                rate_vars.append((var_name, label))
            elif var_name.endswith('_UNIV'):
                univ_vars.append((var_name, label))
            else:
                other_vars.append((var_name, label))
        
        print(f"\nPredicate variables ({len(predicates)}):")
        for name, label, ptype in predicates[:10]:
            print(f"  {name:20} ({ptype}): {label[:40]}")
        
        print(f"\n_TOTAL variables (counts) ({len(total_vars)}):")
        for name, label in total_vars[:15]:
            print(f"  {name:30}: {label[:45]}")
        if len(total_vars) > 15:
            print(f"  ... and {len(total_vars) - 15} more")
        
        print(f"\n_RATE variables (percentages) ({len(rate_vars)}):")
        for name, label in rate_vars[:15]:
            print(f"  {name:30}: {label[:45]}")
        if len(rate_vars) > 15:
            print(f"  ... and {len(rate_vars) - 15} more")
        
        print(f"\n_UNIV variables (universe/denominators) ({len(univ_vars)}):")
        for name, label in univ_vars[:10]:
            print(f"  {name:30}: {label[:45]}")
        if len(univ_vars) > 10:
            print(f"  ... and {len(univ_vars) - 10} more")
        
        print(f"\nOther variables ({len(other_vars)}):")
        for name, label in other_vars:
            print(f"  {name:30}: {label[:45]}")
            
except Exception as e:
    print(f"Error: {e}")

# =============================================================================
# 3. TEST HHPULSE DATA RETRIEVAL
# =============================================================================
print("\n" + "=" * 60)
print("3. TEST HHPULSE DATA RETRIEVAL")
print("=" * 60)

# Try getting actual measure data
print("\n>>> Testing HHPULSE with MEASURE variables...")
test_vars = "NAME,SURVEY_YEAR,CYCLE,PHASE,MEASURE_NAME,MEASURE_LABEL,TOTAL,RATE,UNITS_TOTAL,UNIVERSE"
url = f"https://api.census.gov/data/timeseries/hhpulse?get={test_vars}&for=state:01&time=2024&CYCLE=01&key={API_KEY}"
try:
    response = requests.get(url, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        print(f"\nSample rows:")
        for row in data[1:8]:
            print(f"  {row}")
        
        # Get unique measure names
        if len(data) > 1:
            measure_idx = data[0].index('MEASURE_NAME') if 'MEASURE_NAME' in data[0] else -1
            if measure_idx >= 0:
                measures = set(row[measure_idx] for row in data[1:])
                print(f"\nUnique MEASURE_NAMEs ({len(measures)}):")
                for m in sorted(list(measures))[:20]:
                    print(f"    {m}")
    else:
        print(f"Error: {response.text[:300]}")
except Exception as e:
    print(f"Error: {e}")

# =============================================================================
# 4. TEST HPS DATA RETRIEVAL - Get key indicator variables
# =============================================================================
print("\n" + "=" * 60)
print("4. TEST HPS DATA RETRIEVAL")
print("=" * 60)

# Build a query with key variables
print("\n>>> Testing HPS with key indicator variables...")
# Use variables we saw in the variable list
test_vars = "NAME,SURVEY_YEAR,WEEK,COL_START_DATE,COL_END_DATE,ANXIOUS_TOTAL,ANXIOUS_RATE,ANXIOUS_UNIV,DOWN_TOTAL,DOWN_RATE"
url = f"https://api.census.gov/data/timeseries/hps?get={test_vars}&for=state:*&time=2020&key={API_KEY}"
try:
    response = requests.get(url, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        print(f"\nSample rows:")
        for row in data[1:5]:
            print(f"  {row}")
    else:
        print(f"Error: {response.text[:300]}")
except Exception as e:
    print(f"Error: {e}")

# Test getting more variables
print("\n>>> Testing HPS with more indicator variables...")
test_vars = "NAME,WEEK,FOODSEC_TOTAL,FOODSEC_RATE,MORTCONF_TOTAL,MORTCONF_RATE,VACCINE_TOTAL,VACCINE_RATE"
url = f"https://api.census.gov/data/timeseries/hps?get={test_vars}&for=state:01&time=2021&key={API_KEY}"
try:
    response = requests.get(url, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        print(f"Sample: {data[1:3]}")
    else:
        print(f"Error: {response.text[:300]}")
except Exception as e:
    print(f"Error: {e}")

# =============================================================================
# 5. COUNT TOTAL DATA AVAILABLE
# =============================================================================
print("\n" + "=" * 60)
print("5. ESTIMATE TOTAL DATA SIZE")
print("=" * 60)

# HHPULSE - count by cycle
print("\n>>> HHPULSE data volume by year/cycle...")
total_hhpulse = 0
for year in [2024]:  # Only 2024 has data
    for cycle in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
        url = f"https://api.census.gov/data/timeseries/hhpulse?get=NAME&for=state:*&time={year}&CYCLE={cycle}&key={API_KEY}"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                rows = len(data) - 1
                if rows > 0:
                    total_hhpulse += rows
                    print(f"  {year} Cycle {cycle}: {rows} rows")
        except:
            pass

print(f"\nTotal HHPULSE (state level): ~{total_hhpulse} rows")

# HPS - count by year
print("\n>>> HPS data volume by year...")
total_hps = 0
for year in [2020, 2021, 2022, 2023]:
    url = f"https://api.census.gov/data/timeseries/hps?get=NAME,WEEK&for=state:*&time={year}&key={API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            rows = len(data) - 1
            total_hps += rows
            weeks = set(row[1] for row in data[1:])
            print(f"  {year}: {rows} rows ({len(weeks)} weeks)")
    except:
        pass

print(f"\nTotal HPS (state level): ~{total_hps} rows")

# Also check national and MSA levels
print("\n>>> Checking national and MSA level data...")

# National level
url = f"https://api.census.gov/data/timeseries/hps?get=NAME,WEEK&for=us:1&time=2020&key={API_KEY}"
try:
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        data = response.json()
        print(f"HPS National 2020: {len(data)-1} rows")
except:
    pass

# MSA level
url = f"https://api.census.gov/data/timeseries/hps?get=NAME,WEEK&for=metropolitan%20statistical%20area/micropolitan%20statistical%20area:*&time=2020&key={API_KEY}"
try:
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        data = response.json()
        print(f"HPS MSA 2020: {len(data)-1} rows")
    else:
        print(f"HPS MSA: Status {response.status_code}")
except Exception as e:
    print(f"HPS MSA: Error - {e}")

print("\n" + "=" * 70)
print("EXPLORATION COMPLETE")
print("=" * 70)