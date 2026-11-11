#!/usr/bin/env python3
"""
HOUSEHOLD PULSE SURVEY - COMPLETE INGESTION
Ingests both HPS and HHPULSE endpoints into the master database

Data Structure:
- HHPULSE: Long format - each row is one measure (13 measures × geographies × cycles)
- HPS: Wide format - each row has 32+ indicators as columns (need to query in batches of <50)
"""

import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def safe_float(value):
    """Safely convert value to float"""
    if value is None or value == '' or value == 'null' or value == 'None':
        return None
    try:
        return float(str(value).replace(',', '').replace('%', ''))
    except:
        return None

def safe_int(value):
    """Safely convert value to int"""
    if value is None or value == '' or value == 'null' or value == 'None':
        return None
    try:
        return int(float(str(value).replace(',', '')))
    except:
        return None

print("=" * 70)
print("HOUSEHOLD PULSE SURVEY - COMPLETE INGESTION")
print("=" * 70)

if not API_KEY:
    print("\n⚠️  CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit(1)

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# 1. CREATE TABLES
# =============================================================================
print("\n>>> Creating tables...")

# HHPULSE table (long format - one row per measure)
cur.execute("DROP TABLE IF EXISTS hhpulse_data CASCADE;")
cur.execute("""
    CREATE TABLE hhpulse_data (
        id SERIAL PRIMARY KEY,
        survey_year INTEGER,
        cycle VARCHAR(5),
        phase VARCHAR(10),
        geo_level VARCHAR(20),
        geo_name VARCHAR(255),
        state_fips VARCHAR(2),
        cbsa_code VARCHAR(10),
        measure_name VARCHAR(50),
        measure_label VARCHAR(255),
        measure_description TEXT,
        total_count BIGINT,
        rate NUMERIC(10,4),
        units_total BIGINT,
        universe BIGINT,
        col_start_date VARCHAR(50),
        col_end_date VARCHAR(50),
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_hhpulse_year ON hhpulse_data(survey_year);")
cur.execute("CREATE INDEX idx_hhpulse_cycle ON hhpulse_data(cycle);")
cur.execute("CREATE INDEX idx_hhpulse_measure ON hhpulse_data(measure_name);")
cur.execute("CREATE INDEX idx_hhpulse_state ON hhpulse_data(state_fips);")
print("  ✓ Created hhpulse_data table")

# HPS table (normalized - one row per indicator per geography per week)
cur.execute("DROP TABLE IF EXISTS hps_data CASCADE;")
cur.execute("""
    CREATE TABLE hps_data (
        id SERIAL PRIMARY KEY,
        survey_year INTEGER,
        week VARCHAR(5),
        yr_week_num VARCHAR(10),
        geo_level VARCHAR(20),
        geo_name VARCHAR(255),
        state_fips VARCHAR(2),
        cbsa_code VARCHAR(10),
        indicator_name VARCHAR(50),
        total_count BIGINT,
        rate NUMERIC(10,4),
        universe BIGINT,
        units_total BIGINT,
        col_start_date VARCHAR(50),
        col_end_date VARCHAR(50),
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_hps_year ON hps_data(survey_year);")
cur.execute("CREATE INDEX idx_hps_week ON hps_data(week);")
cur.execute("CREATE INDEX idx_hps_indicator ON hps_data(indicator_name);")
cur.execute("CREATE INDEX idx_hps_state ON hps_data(state_fips);")
print("  ✓ Created hps_data table")

# =============================================================================
# 2. INGEST HHPULSE DATA (High Frequency Social and Economic Data)
# =============================================================================
print("\n" + "=" * 60)
print("INGESTING HHPULSE DATA")
print("=" * 60)

hhpulse_total = 0

# Variables to retrieve
hhpulse_vars = "NAME,SURVEY_YEAR,CYCLE,PHASE,MEASURE_NAME,MEASURE_LABEL,MEASURE_DESCRIPTION,TOTAL,RATE,UNITS_TOTAL,UNIVERSE,COL_START_DATE,COL_END_DATE"

# Geographic levels
geo_levels = [
    ('us', '1', 'national'),
    ('state', '*', 'state'),
    ('metropolitan%20statistical%20area/micropolitan%20statistical%20area', '*', 'msa')
]

# Only 2024 data available, cycles 01-12 (may expand)
for cycle in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
    for geo_type, geo_val, geo_level in geo_levels:
        url = f"https://api.census.gov/data/timeseries/hhpulse?get={hhpulse_vars}&for={geo_type}:{geo_val}&time=2024&CYCLE={cycle}&key={API_KEY}"
        
        try:
            response = requests.get(url, timeout=120)
            
            if response.status_code == 200 and response.text:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 1:
                    headers = data[0]
                    rows = data[1:]
                    col_map = {col: idx for idx, col in enumerate(headers)}
                    
                    for row in rows:
                        # Determine state/cbsa from response
                        state_fips = None
                        cbsa_code = None
                        
                        if 'state' in col_map:
                            state_fips = row[col_map['state']]
                        if 'metropolitan statistical area/micropolitan statistical area' in col_map:
                            cbsa_code = row[col_map['metropolitan statistical area/micropolitan statistical area']]
                        
                        cur.execute("""
                            INSERT INTO hhpulse_data 
                            (survey_year, cycle, phase, geo_level, geo_name, state_fips, cbsa_code,
                             measure_name, measure_label, measure_description, total_count, rate,
                             units_total, universe, col_start_date, col_end_date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            safe_int(row[col_map.get('SURVEY_YEAR')]) if 'SURVEY_YEAR' in col_map else 2024,
                            row[col_map.get('CYCLE')] if 'CYCLE' in col_map else cycle,
                            row[col_map.get('PHASE')] if 'PHASE' in col_map else None,
                            geo_level,
                            row[col_map.get('NAME')] if 'NAME' in col_map else None,
                            state_fips,
                            cbsa_code,
                            row[col_map.get('MEASURE_NAME')] if 'MEASURE_NAME' in col_map else None,
                            row[col_map.get('MEASURE_LABEL')] if 'MEASURE_LABEL' in col_map else None,
                            row[col_map.get('MEASURE_DESCRIPTION')] if 'MEASURE_DESCRIPTION' in col_map else None,
                            safe_int(row[col_map.get('TOTAL')]) if 'TOTAL' in col_map else None,
                            safe_float(row[col_map.get('RATE')]) if 'RATE' in col_map else None,
                            safe_int(row[col_map.get('UNITS_TOTAL')]) if 'UNITS_TOTAL' in col_map else None,
                            safe_int(row[col_map.get('UNIVERSE')]) if 'UNIVERSE' in col_map else None,
                            row[col_map.get('COL_START_DATE')] if 'COL_START_DATE' in col_map else None,
                            row[col_map.get('COL_END_DATE')] if 'COL_END_DATE' in col_map else None
                        ))
                    
                    hhpulse_total += len(rows)
                    print(f"  Cycle {cycle} {geo_level:8}: ✓ {len(rows):,} rows")
                    conn.commit()
                    
        except Exception as e:
            if 'timeout' not in str(e).lower():
                pass  # Skip printing errors for missing cycles
        
        time.sleep(0.3)

print(f"\n✓ HHPULSE total: {hhpulse_total:,} rows")

# =============================================================================
# 3. INGEST HPS DATA (COVID-19 Pandemic and Recovery)
# =============================================================================
print("\n" + "=" * 60)
print("INGESTING HPS DATA")
print("=" * 60)

# First, get all available indicator variables
var_url = "https://api.census.gov/data/timeseries/hps/variables.json"
response = requests.get(var_url, timeout=60)
variables = response.json().get('variables', {})

# Extract indicator base names (remove _TOTAL, _RATE, _UNIV suffixes)
total_vars = sorted([v for v in variables.keys() if v.endswith('_TOTAL') and v != 'UNITS_TOTAL'])
rate_vars = sorted([v for v in variables.keys() if v.endswith('_RATE')])
univ_vars = sorted([v for v in variables.keys() if v.endswith('_UNIV')])

# Get base indicator names
indicator_bases = set()
for v in total_vars:
    indicator_bases.add(v.replace('_TOTAL', ''))
for v in rate_vars:
    indicator_bases.add(v.replace('_RATE', ''))

indicator_bases = sorted(indicator_bases)
print(f"Found {len(indicator_bases)} unique indicators: {indicator_bases[:5]}...")

hps_total = 0

# Years and geographic levels
years = [2020, 2021, 2022, 2023]
geo_levels_hps = [
    ('us', '1', 'national'),
    ('state', '*', 'state'),
    ('metropolitan%20statistical%20area/micropolitan%20statistical%20area', '*', 'msa')
]

# Base variables for each query
base_vars = ['NAME', 'SURVEY_YEAR', 'WEEK', 'YR_WEEK_NUM', 'COL_START_DATE', 'COL_END_DATE', 'UNITS_TOTAL']

# Process in batches (API limit is 50 variables per query)
# We'll query each indicator separately to normalize the data
for year in years:
    print(f"\n>>> Processing {year}...")
    
    for geo_type, geo_val, geo_level in geo_levels_hps:
        # First, get the base data to know what weeks/rows exist
        base_url = f"https://api.census.gov/data/timeseries/hps?get={','.join(base_vars)}&for={geo_type}:{geo_val}&time={year}&key={API_KEY}"
        
        try:
            response = requests.get(base_url, timeout=120)
            
            if response.status_code == 200 and response.text:
                base_data = response.json()
                
                if len(base_data) > 1:
                    base_headers = base_data[0]
                    base_rows = base_data[1:]
                    base_col_map = {col: idx for idx, col in enumerate(base_headers)}
                    
                    # Now query each indicator and insert normalized data
                    # Query in batches of indicators to be efficient
                    batch_size = 12  # ~12 indicators × 3 vars = 36 + 7 base = 43 < 50
                    
                    for batch_start in range(0, len(indicator_bases), batch_size):
                        batch_indicators = indicator_bases[batch_start:batch_start + batch_size]
                        
                        # Build variable list for this batch
                        batch_vars = base_vars.copy()
                        for ind in batch_indicators:
                            if f"{ind}_TOTAL" in total_vars:
                                batch_vars.append(f"{ind}_TOTAL")
                            if f"{ind}_RATE" in rate_vars:
                                batch_vars.append(f"{ind}_RATE")
                            if f"{ind}_UNIV" in univ_vars:
                                batch_vars.append(f"{ind}_UNIV")
                        
                        batch_url = f"https://api.census.gov/data/timeseries/hps?get={','.join(batch_vars)}&for={geo_type}:{geo_val}&time={year}&key={API_KEY}"
                        
                        try:
                            batch_response = requests.get(batch_url, timeout=120)
                            
                            if batch_response.status_code == 200:
                                batch_data = batch_response.json()
                                
                                if len(batch_data) > 1:
                                    headers = batch_data[0]
                                    rows = batch_data[1:]
                                    col_map = {col: idx for idx, col in enumerate(headers)}
                                    
                                    for row in rows:
                                        # Get geographic identifiers
                                        state_fips = None
                                        cbsa_code = None
                                        
                                        if 'state' in col_map:
                                            state_fips = row[col_map['state']]
                                        if 'metropolitan statistical area/micropolitan statistical area' in col_map:
                                            cbsa_code = row[col_map['metropolitan statistical area/micropolitan statistical area']]
                                        
                                        # Insert one row per indicator
                                        for ind in batch_indicators:
                                            total_col = f"{ind}_TOTAL"
                                            rate_col = f"{ind}_RATE"
                                            univ_col = f"{ind}_UNIV"
                                            
                                            total_val = safe_int(row[col_map[total_col]]) if total_col in col_map else None
                                            rate_val = safe_float(row[col_map[rate_col]]) if rate_col in col_map else None
                                            univ_val = safe_int(row[col_map[univ_col]]) if univ_col in col_map else None
                                            
                                            # Only insert if we have some data
                                            if total_val is not None or rate_val is not None:
                                                cur.execute("""
                                                    INSERT INTO hps_data 
                                                    (survey_year, week, yr_week_num, geo_level, geo_name, 
                                                     state_fips, cbsa_code, indicator_name, total_count, 
                                                     rate, universe, units_total, col_start_date, col_end_date)
                                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                                """, (
                                                    safe_int(row[col_map.get('SURVEY_YEAR')]) if 'SURVEY_YEAR' in col_map else year,
                                                    row[col_map.get('WEEK')] if 'WEEK' in col_map else None,
                                                    row[col_map.get('YR_WEEK_NUM')] if 'YR_WEEK_NUM' in col_map else None,
                                                    geo_level,
                                                    row[col_map.get('NAME')] if 'NAME' in col_map else None,
                                                    state_fips,
                                                    cbsa_code,
                                                    ind,
                                                    total_val,
                                                    rate_val,
                                                    univ_val,
                                                    safe_int(row[col_map.get('UNITS_TOTAL')]) if 'UNITS_TOTAL' in col_map else None,
                                                    row[col_map.get('COL_START_DATE')] if 'COL_START_DATE' in col_map else None,
                                                    row[col_map.get('COL_END_DATE')] if 'COL_END_DATE' in col_map else None
                                                ))
                                                hps_total += 1
                                    
                                    conn.commit()
                                    
                        except Exception as e:
                            pass
                        
                        time.sleep(0.2)
                    
                    print(f"  {year} {geo_level:8}: ✓ processed")
                    
        except Exception as e:
            print(f"  {year} {geo_level}: Error - {str(e)[:50]}")
        
        time.sleep(0.3)

print(f"\n✓ HPS total: {hps_total:,} rows")

# =============================================================================
# 4. SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("HOUSEHOLD PULSE SURVEY INGESTION SUMMARY")
print("=" * 70)

# HHPULSE summary
cur.execute("""
    SELECT survey_year, cycle, geo_level, COUNT(*) as rows,
           COUNT(DISTINCT measure_name) as measures
    FROM hhpulse_data 
    GROUP BY survey_year, cycle, geo_level
    ORDER BY survey_year, cycle, geo_level
""")
print("\nHHPULSE by cycle and geography:")
for row in cur.fetchall():
    print(f"  {row[0]} Cycle {row[1]} {row[2]:10}: {row[3]:>6,} rows ({row[4]} measures)")

cur.execute("SELECT COUNT(*), COUNT(DISTINCT measure_name), COUNT(DISTINCT cycle) FROM hhpulse_data")
hhpulse_stats = cur.fetchone()
print(f"\nHHPULSE Total: {hhpulse_stats[0]:,} rows, {hhpulse_stats[1]} measures, {hhpulse_stats[2]} cycles")

# HPS summary
cur.execute("""
    SELECT survey_year, geo_level, COUNT(*) as rows,
           COUNT(DISTINCT indicator_name) as indicators,
           COUNT(DISTINCT week) as weeks
    FROM hps_data 
    GROUP BY survey_year, geo_level
    ORDER BY survey_year, geo_level
""")
print("\nHPS by year and geography:")
for row in cur.fetchall():
    print(f"  {row[0]} {row[1]:10}: {row[2]:>8,} rows ({row[3]} indicators, {row[4]} weeks)")

cur.execute("SELECT COUNT(*), COUNT(DISTINCT indicator_name), COUNT(DISTINCT week) FROM hps_data")
hps_stats = cur.fetchone()
print(f"\nHPS Total: {hps_stats[0]:,} rows, {hps_stats[1]} indicators, {hps_stats[2]} weeks")

# =============================================================================
# 5. COMPLETE DATABASE SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("COMPLETE DATABASE SUMMARY")
print("=" * 70)

tables = [
    'cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 
    'ec_data', 'decennial_data', 'abs_data', 'saipe_data', 
    'sahie_data', 'bds_data', 'sbo_data', 'acs1_data', 'cps_data',
    'econ_indicators_data', 'hhpulse_data', 'hps_data'
]

db_total = 0
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        db_total += count
        print(f"  {table:25}: {count:>12,} rows")
    except:
        print(f"  {table:25}: Not found")

print(f"  {'-'*40}")
print(f"  {'TOTAL':25}: {db_total:>12,} rows")

cur.close()
conn.close()

print("\n✓ Household Pulse Survey ingestion complete!")