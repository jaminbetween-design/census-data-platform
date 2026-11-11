#!/usr/bin/env python3
"""
HOUSEHOLD PULSE SURVEY - FINAL EXPLORATION
Understanding HPS variable structure for ingestion
"""

import requests
import json
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ["CENSUS_API_KEY"]

print("=" * 70)
print("HOUSEHOLD PULSE SURVEY - FINAL EXPLORATION")
print("=" * 70)

# =============================================================================
# 1. HPS - Get all variable names properly
# =============================================================================
print("\n" + "=" * 60)
print("1. HPS - UNDERSTANDING VARIABLE STRUCTURE")
print("=" * 60)

var_url = "https://api.census.gov/data/timeseries/hps/variables.json"
try:
    response = requests.get(var_url, timeout=60)
    if response.status_code == 200:
        variables = response.json().get('variables', {})
        
        # Separate by type
        total_vars = [v for v in variables.keys() if '_TOTAL' in v]
        rate_vars = [v for v in variables.keys() if '_RATE' in v]
        univ_vars = [v for v in variables.keys() if '_UNIV' in v]
        other_vars = [v for v in variables.keys() if v not in total_vars + rate_vars + univ_vars]
        
        print(f"\nTOTAL variables ({len(total_vars)}):")
        for v in sorted(total_vars)[:10]:
            print(f"  {v}")
        
        print(f"\nRATE variables ({len(rate_vars)}):")
        for v in sorted(rate_vars)[:10]:
            print(f"  {v}")
        
        print(f"\nUNIV variables ({len(univ_vars)}):")
        for v in sorted(univ_vars)[:10]:
            print(f"  {v}")
        
        print(f"\nOther variables ({len(other_vars)}):")
        for v in sorted(other_vars):
            print(f"  {v}")
            
except Exception as e:
    print(f"Error: {e}")

# =============================================================================
# 2. Test HPS with actual variable names from the API
# =============================================================================
print("\n" + "=" * 60)
print("2. TEST HPS VARIABLE RETRIEVAL")
print("=" * 60)

# Try different variable combinations
test_queries = [
    # Basic query
    "NAME,SURVEY_YEAR,WEEK,COL_START_DATE,UNITS_TOTAL",
    # Try some indicator variables  
    "NAME,WEEK,ANXIOUS_TOTAL,ANXIOUS_RATE",
    "NAME,WEEK,FOODSCARCE_TOTAL,FOODSCARCE_RATE",
    "NAME,WEEK,EXPENSE_TOTAL,EXPENSE_RATE",
    # Try without suffix
    "NAME,WEEK,ANXIOUS,DOWN,FOODSCARCE",
    # Get all available in one state
    "NAME,SURVEY_YEAR,WEEK,YR_WEEK_NUM,COL_START_DATE,COL_END_DATE,SUMLEVEL",
]

for query in test_queries:
    url = f"https://api.census.gov/data/timeseries/hps?get={query}&for=state:01&time=2020&key={API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        print(f"\nQuery: {query[:60]}...")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Headers: {data[0]}")
            print(f"  Rows: {len(data)-1}")
            if len(data) > 1:
                print(f"  Sample: {data[1]}")
        else:
            print(f"  Error: {response.text[:100]}")
    except Exception as e:
        print(f"  Error: {e}")

# =============================================================================
# 3. Get HPS with many indicator variables at once
# =============================================================================
print("\n" + "=" * 60)
print("3. HPS - GET ALL INDICATORS FOR ONE STATE/WEEK")
print("=" * 60)

# Build list of all TOTAL and RATE variables
var_url = "https://api.census.gov/data/timeseries/hps/variables.json"
response = requests.get(var_url, timeout=60)
variables = response.json().get('variables', {})

total_vars = [v for v in variables.keys() if '_TOTAL' in v and v != 'UNITS_TOTAL']
rate_vars = [v for v in variables.keys() if '_RATE' in v]

print(f"\nFound {len(total_vars)} _TOTAL indicator variables")
print(f"Found {len(rate_vars)} _RATE indicator variables")

# Try getting a batch of TOTAL variables
batch_vars = ','.join(['NAME', 'WEEK', 'UNITS_TOTAL'] + total_vars[:10])
url = f"https://api.census.gov/data/timeseries/hps?get={batch_vars}&for=state:01&time=2020&key={API_KEY}"
print(f"\nTrying batch of 10 TOTAL vars...")
try:
    response = requests.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data)-1}")
        if len(data) > 1:
            print(f"Sample: {data[1]}")
    else:
        print(f"Error: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Try getting ALL indicator variables
all_indicator_vars = ['NAME', 'SURVEY_YEAR', 'WEEK', 'YR_WEEK_NUM', 'COL_START_DATE', 'COL_END_DATE', 'UNITS_TOTAL'] + total_vars + rate_vars
print(f"\nTrying ALL {len(all_indicator_vars)} variables...")
url = f"https://api.census.gov/data/timeseries/hps?get={','.join(all_indicator_vars)}&for=state:01&time=2020&key={API_KEY}"
try:
    response = requests.get(url, timeout=60)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Headers ({len(data[0])}): {data[0][:10]}...")
        print(f"Rows: {len(data)-1}")
    else:
        print(f"Error: {response.text[:300]}")
except Exception as e:
    print(f"Error: {e}")

# =============================================================================
# 4. Get HHPULSE full data structure
# =============================================================================
print("\n" + "=" * 60)
print("4. HHPULSE - FULL DATA FOR ALL CYCLES")
print("=" * 60)

# Get all measures for all cycles
all_measures = set()
for cycle in ['01', '02', '03', '04', '05', '06', '07', '08', '09']:
    url = f"https://api.census.gov/data/timeseries/hhpulse?get=MEASURE_NAME&for=us:1&time=2024&CYCLE={cycle}&key={API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            measures = set(row[0] for row in data[1:])
            all_measures.update(measures)
    except:
        pass

print(f"\nAll unique MEASURE_NAMEs across all cycles ({len(all_measures)}):")
for m in sorted(all_measures):
    print(f"  {m}")

# Get count by geography type
print("\n>>> HHPULSE data by geography level...")
for geo, geo_val in [('us', '1'), ('state', '*')]:
    url = f"https://api.census.gov/data/timeseries/hhpulse?get=NAME,MEASURE_NAME&for={geo}:{geo_val}&time=2024&CYCLE=01&key={API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"  {geo}: {len(data)-1} rows")
    except:
        pass

# Try MSA level
url = f"https://api.census.gov/data/timeseries/hhpulse?get=NAME,MEASURE_NAME&for=metropolitan%20statistical%20area/micropolitan%20statistical%20area:*&time=2024&CYCLE=01&key={API_KEY}"
try:
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        data = response.json()
        print(f"  MSA: {len(data)-1} rows")
    else:
        print(f"  MSA: Status {response.status_code}")
except Exception as e:
    print(f"  MSA: Error")

# =============================================================================
# 5. SUMMARY FOR INGESTION PLANNING
# =============================================================================
print("\n" + "=" * 70)
print("SUMMARY FOR INGESTION")
print("=" * 70)

print("""
HHPULSE (High Frequency Social and Economic Data):
- Years: 2024 only
- Cycles: 01-09 (and counting)
- Geography: US, State (51), MSA
- Structure: Each row is a MEASURE (indicator) with TOTAL, RATE, UNIVERSE
- Variables: NAME, SURVEY_YEAR, CYCLE, PHASE, MEASURE_NAME, MEASURE_LABEL, 
            TOTAL, RATE, UNITS_TOTAL, UNIVERSE, COL_START_DATE, COL_END_DATE
- Estimated rows: ~6,000 (state) + ~100 (US) + ~MSAs per cycle

HPS (COVID-19 Pandemic and Recovery):
- Years: 2020-2023
- Weeks: 01-62+ (varies by year)
- Geography: US, State (51), MSA (15)
- Structure: Wide format - each indicator is a column (INDICATOR_TOTAL, INDICATOR_RATE)
- ~50+ indicators per row
- Estimated rows: ~3,200 (state) + ~60 (US) + ~945 (MSA)
""")

print("=" * 70)