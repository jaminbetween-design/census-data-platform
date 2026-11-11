#!/usr/bin/env python3
"""
ECONOMIC INDICATORS TIME SERIES (EITS) - COMPLETE INGESTION
Based on Census Bureau Economic Indicator Time Series API User Guide

This script ingests ALL data from ALL Economic Indicator datasets.
"""

import requests
import psycopg2
import time
from urllib.parse import quote_plus
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def safe_float(value):
    """Safely convert value to float, handling Census data codes"""
    if value is None or value == '' or value == 'null':
        return None
    if value in ('N', 'D', 'S', 'NA', 'X', 'Z', '-'):
        return None
    try:
        return float(str(value).replace(',', ''))
    except:
        return None

print("=" * 70)
print("ECONOMIC INDICATORS TIME SERIES - COMPLETE INGESTION")
print("=" * 70)

if not API_KEY:
    print("\n⚠️  CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    print("   Get a key at: https://api.census.gov/data/key_signup.html")
    exit(1)

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# CREATE TABLE
# =============================================================================
cur.execute("DROP TABLE IF EXISTS econ_indicators_data CASCADE;")
cur.execute("""
    CREATE TABLE econ_indicators_data (
        id SERIAL PRIMARY KEY,
        indicator_code VARCHAR(20) NOT NULL,
        indicator_name VARCHAR(100),
        time_period VARCHAR(30),
        time_slot_id VARCHAR(20),
        cell_value NUMERIC(20,4),
        data_type_code VARCHAR(50),
        category_code VARCHAR(100),
        seasonally_adj VARCHAR(10),
        error_data VARCHAR(50),
        geo_level_code VARCHAR(20),
        state_fips VARCHAR(2),
        program_code VARCHAR(20),
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_econ_indicator_code ON econ_indicators_data(indicator_code);")
cur.execute("CREATE INDEX idx_econ_time ON econ_indicators_data(time_period);")
cur.execute("CREATE INDEX idx_econ_category ON econ_indicators_data(category_code);")
cur.execute("CREATE INDEX idx_econ_datatype ON econ_indicators_data(data_type_code);")
print("✓ Created econ_indicators_data table")

# =============================================================================
# INDICATOR CONFIGURATIONS FROM APPENDIX A OF THE USER GUIDE
# =============================================================================
INDICATORS = [
    # Monthly Indicators
    {
        'code': 'advm3',
        'name': 'Advance Report on Durable Goods',
        'start_year': 1992,
        'frequency': 'monthly',
        'requires_for': True,
        'for_value': 'us:*'
    },
    {
        'code': 'ftd',
        'name': 'International Trade',
        'start_year': 1992,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'm3',
        'name': 'Manufacturers Shipments Inventories Orders',
        'start_year': 1992,
        'frequency': 'monthly',
        'requires_for': True,
        'for_value': 'us:*'
    },
    {
        'code': 'marts',
        'name': 'Advance Monthly Retail Sales',
        'start_year': 1992,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'mhs',
        'name': 'Manufactured Homes Survey (1959-2014)',
        'start_year': 1959,
        'end_year': 2014,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'mhs2',
        'name': 'Manufactured Housing Survey (2014-Present)',
        'start_year': 2014,
        'frequency': 'monthly',
        'requires_for': True,
        'for_value': 'us:*'
    },
    {
        'code': 'mrts',
        'name': 'Monthly Retail Trade and Food Services',
        'start_year': 1992,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'mtis',
        'name': 'Manufacturing and Trade Inventories and Sales',
        'start_year': 1992,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'mwts',
        'name': 'Monthly Wholesale Trade Sales and Inventories',
        'start_year': 1992,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'resconst',
        'name': 'New Residential Construction',
        'start_year': 1959,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'ressales',
        'name': 'New Home Sales',
        'start_year': 1963,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'vip',
        'name': 'Construction Spending',
        'start_year': 2002,
        'frequency': 'monthly',
        'requires_for': False,
        'for_value': None
    },
    
    # Quarterly Indicators
    {
        'code': 'hv',
        'name': 'Housing Vacancies and Homeownership',
        'start_year': 1956,
        'frequency': 'quarterly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'qfr',
        'name': 'Quarterly Financial Report',
        'start_year': 2000,
        'frequency': 'quarterly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'qpr',
        'name': 'Quarterly Survey of Public Pensions',
        'start_year': 1968,
        'frequency': 'quarterly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'qss',
        'name': 'Quarterly Services Survey',
        'start_year': 2003,
        'frequency': 'quarterly',
        'requires_for': False,
        'for_value': None
    },
    {
        'code': 'qtax',
        'name': 'Quarterly Summary of State and Local Taxes',
        'start_year': 1992,
        'frequency': 'quarterly',
        'requires_for': False,
        'for_value': None,
        'has_state_data': True
    },
    {
        'code': 'bfs',
        'name': 'Business Formation Statistics',
        'start_year': 2004,
        'frequency': 'quarterly',
        'requires_for': True,
        'for_value': 'us:*',
        'has_state_data': True
    },
]

# =============================================================================
# INGESTION FUNCTION
# =============================================================================
def ingest_indicator(indicator, cur, conn):
    """Ingest all data for a single indicator"""
    code = indicator['code']
    name = indicator['name']
    start_year = indicator['start_year']
    end_year = indicator.get('end_year', 2024)
    frequency = indicator['frequency']
    requires_for = indicator['requires_for']
    for_value = indicator.get('for_value')
    has_state_data = indicator.get('has_state_data', False)
    
    print(f"\n{'='*60}")
    print(f"Processing: {name} ({code})")
    print(f"Years: {start_year}-{end_year}, Frequency: {frequency}")
    print(f"{'='*60}")
    
    total_rows = 0
    
    # Process year by year to avoid timeout issues with large datasets
    for year in range(end_year, start_year - 1, -1):
        # Build URL based on the official API guide format
        base_url = f"https://api.census.gov/data/timeseries/eits/{code}"
        
        # Variables to retrieve
        get_vars = "cell_value,time_slot_id,error_data,category_code,seasonally_adj,data_type_code"
        
        # Build query string
        url = f"{base_url}?get={get_vars}"
        
        # Add 'for' parameter if required
        if requires_for and for_value:
            url += f"&for={for_value}"
        
        # Add time parameter
        url += f"&time={year}"
        
        # Add API key
        url += f"&key={API_KEY}"
        
        try:
            response = requests.get(url, timeout=180)
            
            if response.status_code == 200 and response.text and response.text.strip():
                try:
                    data = response.json()
                    
                    if isinstance(data, list) and len(data) > 1:
                        headers = [h.lower() if h else h for h in data[0]]
                        rows = data[1:]
                        
                        # Create column map
                        col_map = {col: idx for idx, col in enumerate(headers) if col}
                        
                        for row in rows:
                            # Extract values using column map
                            time_val = None
                            if 'time' in col_map:
                                time_val = row[col_map['time']]
                            else:
                                time_val = str(year)
                            
                            cur.execute("""
                                INSERT INTO econ_indicators_data 
                                (indicator_code, indicator_name, time_period, time_slot_id, 
                                 cell_value, data_type_code, category_code, seasonally_adj, 
                                 error_data, geo_level_code)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                code,
                                name,
                                time_val,
                                row[col_map.get('time_slot_id')] if 'time_slot_id' in col_map else None,
                                safe_float(row[col_map.get('cell_value')]) if 'cell_value' in col_map else None,
                                row[col_map.get('data_type_code')] if 'data_type_code' in col_map else None,
                                row[col_map.get('category_code')] if 'category_code' in col_map else None,
                                row[col_map.get('seasonally_adj')] if 'seasonally_adj' in col_map else None,
                                row[col_map.get('error_data')] if 'error_data' in col_map else None,
                                row[col_map.get('us')] if 'us' in col_map else 'US'
                            ))
                        
                        year_rows = len(rows)
                        total_rows += year_rows
                        if year_rows > 0:
                            print(f"  {year}: ✓ {year_rows:,} rows")
                        
                except Exception as e:
                    print(f"  {year}: Parse error - {str(e)[:50]}")
            elif response.status_code == 204:
                # No content - skip silently
                pass
            elif response.status_code == 400:
                # Bad request - might be invalid year
                pass
            else:
                if response.status_code not in (204, 400):
                    print(f"  {year}: Status {response.status_code}")
                    
        except requests.exceptions.Timeout:
            print(f"  {year}: Timeout")
        except Exception as e:
            print(f"  {year}: Error - {str(e)[:50]}")
        
        # Commit periodically
        if year % 5 == 0:
            conn.commit()
        
        time.sleep(0.3)  # Rate limiting
    
    conn.commit()
    
    # Also get state-level data for indicators that support it
    if has_state_data:
        print(f"\n  >>> Getting state-level data for {code}...")
        state_rows = ingest_state_data(code, name, start_year, end_year, cur, conn)
        total_rows += state_rows
    
    return total_rows

def ingest_state_data(code, name, start_year, end_year, cur, conn):
    """Ingest state-level data for QTAX and BFS"""
    total_rows = 0
    
    for year in range(end_year, start_year - 1, -1):
        # For state data, use geo_level_code=* according to the guide
        base_url = f"https://api.census.gov/data/timeseries/eits/{code}"
        get_vars = "cell_value,time_slot_id,error_data,category_code,seasonally_adj,data_type_code,geo_level_code"
        
        url = f"{base_url}?get={get_vars}&geo_level_code=*&time={year}&key={API_KEY}"
        
        try:
            response = requests.get(url, timeout=180)
            
            if response.status_code == 200 and response.text:
                data = response.json()
                
                if isinstance(data, list) and len(data) > 1:
                    headers = [h.lower() if h else h for h in data[0]]
                    rows = data[1:]
                    col_map = {col: idx for idx, col in enumerate(headers) if col}
                    
                    for row in rows:
                        time_val = row[col_map.get('time')] if 'time' in col_map else str(year)
                        geo_level = row[col_map.get('geo_level_code')] if 'geo_level_code' in col_map else None
                        
                        # Skip US level (already captured)
                        if geo_level == 'US':
                            continue
                        
                        cur.execute("""
                            INSERT INTO econ_indicators_data 
                            (indicator_code, indicator_name, time_period, time_slot_id, 
                             cell_value, data_type_code, category_code, seasonally_adj, 
                             error_data, geo_level_code, state_fips)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            code,
                            name + ' (State)',
                            time_val,
                            row[col_map.get('time_slot_id')] if 'time_slot_id' in col_map else None,
                            safe_float(row[col_map.get('cell_value')]) if 'cell_value' in col_map else None,
                            row[col_map.get('data_type_code')] if 'data_type_code' in col_map else None,
                            row[col_map.get('category_code')] if 'category_code' in col_map else None,
                            row[col_map.get('seasonally_adj')] if 'seasonally_adj' in col_map else None,
                            row[col_map.get('error_data')] if 'error_data' in col_map else None,
                            geo_level,
                            geo_level if geo_level and len(geo_level) == 2 else None
                        ))
                    
                    year_rows = len(rows)
                    total_rows += year_rows
                    if year_rows > 0:
                        print(f"    {year} (state): ✓ {year_rows:,} rows")
                        
        except Exception as e:
            pass
        
        if year % 5 == 0:
            conn.commit()
        
        time.sleep(0.3)
    
    conn.commit()
    return total_rows

# =============================================================================
# MAIN INGESTION LOOP
# =============================================================================
grand_total = 0

for indicator in INDICATORS:
    try:
        rows = ingest_indicator(indicator, cur, conn)
        grand_total += rows
        print(f"\n  Total for {indicator['code']}: {rows:,} rows")
    except Exception as e:
        print(f"\n  ✗ Failed: {e}")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("ECONOMIC INDICATORS INGESTION SUMMARY")
print("=" * 70)

# Count by indicator
cur.execute("""
    SELECT indicator_code, indicator_name, 
           COUNT(*) as rows,
           MIN(time_period) as min_time,
           MAX(time_period) as max_time
    FROM econ_indicators_data 
    GROUP BY indicator_code, indicator_name
    ORDER BY rows DESC
""")

print("\nRows by indicator:")
for row in cur.fetchall():
    print(f"  {row[0]:10} ({row[1][:35]:35}): {row[2]:>10,} rows  ({row[3]} to {row[4]})")

cur.execute("SELECT COUNT(*) FROM econ_indicators_data")
total = cur.fetchone()[0]
print(f"\n{'='*70}")
print(f"TOTAL ECONOMIC INDICATORS DATA: {total:,} rows")
print(f"{'='*70}")

# =============================================================================
# FULL DATABASE SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("COMPLETE DATABASE SUMMARY")
print("=" * 70)

tables = [
    'cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 
    'ec_data', 'decennial_data', 'abs_data', 'saipe_data', 
    'sahie_data', 'bds_data', 'sbo_data', 'acs1_data', 'cps_data',
    'econ_indicators_data'
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

print("\n✓ Economic Indicators ingestion complete!")