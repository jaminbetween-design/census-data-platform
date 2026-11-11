#!/usr/bin/env python3
"""
US CENSUS INTERNATIONAL TRADE DATA - HS INGESTION SCRIPT
Ingests Monthly International Trade Datasets (MITD) - HS endpoints
January 2013 to present

Features:
- Handles HS2, HS4, HS6, HS10 commodity levels
- Uses wildcard strategy to avoid cardinality errors
- Tracks ingestion progress for incremental updates
- Supports resuming from last successful ingestion
"""

import requests
import psycopg2
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

# =============================================================================
# CONFIGURATION
# =============================================================================
API_KEY = os.environ.get("CENSUS_API_KEY")

BASE_DELAY = 0.5          # Seconds between API calls
RETRY_DELAY = 30          # Seconds to wait on rate limit
MAX_RETRIES = 3           # Max retries per request

# =============================================================================
# DATABASE CONNECTION
# =============================================================================
def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def safe_int(value):
    """Convert to int, handling nulls and non-numeric values"""
    if value is None or value == '' or value == 'null' or value == '-':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_bigint(value):
    """Convert to bigint for large values"""
    if value is None or value == '' or value == 'null' or value == '-':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_str(value, max_len=None):
    """Clean string value"""
    if value is None or value == '' or value == 'null':
        return None
    s = str(value).strip()
    if max_len:
        s = s[:max_len]
    return s if s else None

def get_time_periods(start_year=2013, start_month=1, end_date=None):
    """Generate list of YYYY-MM time periods from start to present"""
    if end_date is None:
        end_date = date.today()
    
    periods = []
    current = date(start_year, start_month, 1)
    
    while current <= end_date:
        periods.append(f"{current.year}-{current.month:02d}")
        current += relativedelta(months=1)
    
    return periods

def get_last_ingested_period(cur, dataset, comm_lvl):
    """Get the most recent successfully ingested time period"""
    cur.execute("""
        SELECT MAX(time_period) FROM intltrade_ingestion_log 
        WHERE dataset = %s AND comm_lvl = %s AND status = 'success'
    """, (dataset, comm_lvl))
    result = cur.fetchone()[0]
    return result

def log_ingestion(cur, dataset, time_period, comm_lvl, rows, status, error=None):
    """Log ingestion attempt"""
    cur.execute("""
        INSERT INTO intltrade_ingestion_log 
        (dataset, time_period, comm_lvl, rows_ingested, status, error_message, started_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (dataset, time_period, comm_lvl) 
        DO UPDATE SET rows_ingested = %s, status = %s, error_message = %s, 
                      completed_at = CURRENT_TIMESTAMP
    """, (dataset, time_period, comm_lvl, rows, status, error, datetime.now(),
          rows, status, error))

# =============================================================================
# API FETCH FUNCTIONS
# =============================================================================
def fetch_exports_hs(time_period, comm_lvl, hs_prefix=None):
    """
    Fetch export HS data for a specific time period and commodity level.
    Uses wildcard prefix for HS10 to avoid cardinality issues.
    """
    base_url = "https://api.census.gov/data/timeseries/intltrade/exports/hs"
    
    # Variables to fetch (limited set for HS endpoint)
    get_vars = [
        "E_COMMODITY", "E_COMMODITY_SDESC", 
        "CTY_CODE", "CTY_NAME",
        "DISTRICT", "DIST_NAME",
        "DF", "COMM_LVL", "SUMMARY_LVL",
        "ALL_VAL_MO", "ALL_VAL_YR",
        "AIR_VAL_MO", "AIR_VAL_YR",
        "VES_VAL_MO", "VES_VAL_YR",
        "AIR_WGT_MO", "AIR_WGT_YR",
        "VES_WGT_MO", "VES_WGT_YR"
    ]
    
    # Add quantity fields only for detailed HS levels
    if comm_lvl in ['HS6', 'HS10']:
        get_vars.extend([
            "UNIT_QY1", "UNIT_QY2",
            "QTY_1_MO", "QTY_1_MO_FLAG",
            "QTY_2_MO", "QTY_2_MO_FLAG"
        ])
    
    url = f"{base_url}?get={','.join(get_vars)}&time={time_period}&COMM_LVL={comm_lvl}"
    
    # Add HS prefix wildcard for large datasets
    if hs_prefix:
        url += f"&E_COMMODITY={hs_prefix}*"
    
    url += f"&key={API_KEY}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=180)
            
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 204:
                # No data for this combination
                return None
            elif response.status_code == 429:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"      Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"      Error {response.status_code}: {response.text[:200]}")
                time.sleep(BASE_DELAY)
                
        except requests.exceptions.Timeout:
            print(f"      Timeout, retrying...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"      Exception: {e}")
            time.sleep(BASE_DELAY)
    
    return None

def fetch_imports_hs(time_period, comm_lvl, hs_prefix=None):
    """
    Fetch import HS data for a specific time period and commodity level.
    Uses wildcard prefix for HS10 to avoid cardinality issues.
    """
    base_url = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
    
    # Variables to fetch
    get_vars = [
        "I_COMMODITY", "I_COMMODITY_SDESC",
        "CTY_CODE", "CTY_NAME",
        "DISTRICT", "DIST_NAME",
        "CTY_SUBCODE", "RP", "COMM_LVL", "SUMMARY_LVL",
        "GEN_VAL_MO", "GEN_VAL_YR",
        "CON_VAL_MO", "CON_VAL_YR",
        "AIR_VAL_MO", "AIR_VAL_YR",
        "VES_VAL_MO", "VES_VAL_YR",
        "AIR_WGT_MO", "AIR_WGT_YR",
        "VES_WGT_MO", "VES_WGT_YR"
    ]
    
    # Add quantity and duty fields for detailed levels
    if comm_lvl in ['HS6', 'HS10']:
        get_vars.extend([
            "UNIT_QY1", "UNIT_QY2",
            "GEN_QY1_MO", "GEN_QY1_MO_FLAG",
            "GEN_QY2_MO", "GEN_QY2_MO_FLAG",
            "CAL_DUT_MO", "DUT_VAL_MO"
        ])
    
    url = f"{base_url}?get={','.join(get_vars)}&time={time_period}&COMM_LVL={comm_lvl}"
    
    if hs_prefix:
        url += f"&I_COMMODITY={hs_prefix}*"
    
    url += f"&key={API_KEY}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=180)
            
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 204:
                return None
            elif response.status_code == 429:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"      Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"      Error {response.status_code}: {response.text[:200]}")
                time.sleep(BASE_DELAY)
                
        except requests.exceptions.Timeout:
            print(f"      Timeout, retrying...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"      Exception: {e}")
            time.sleep(BASE_DELAY)
    
    return None

# =============================================================================
# DATA INSERTION FUNCTIONS
# =============================================================================
def insert_exports_hs(cur, data, time_period):
    """Insert export HS data into database"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    year, month = time_period.split('-')
    
    for row in rows:
        try:
            hs_code = safe_str(row[col_map.get('E_COMMODITY')])
            if not hs_code or hs_code == '-':
                continue
                
            cur.execute("""
                INSERT INTO intltrade_exports_hs (
                    time_period, year, month,
                    hs_code, comm_lvl, hs_desc_short,
                    cty_code, cty_name, district, district_name,
                    df, summary_lvl,
                    all_val_mo, all_val_yr,
                    air_val_mo, air_val_yr,
                    ves_val_mo, ves_val_yr,
                    air_wgt_mo, air_wgt_yr,
                    ves_wgt_mo, ves_wgt_yr,
                    unit_qy1, unit_qy2,
                    qty_1_mo, qty_1_mo_flag,
                    qty_2_mo, qty_2_mo_flag
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
            """, (
                time_period, int(year), int(month),
                hs_code,
                safe_str(row[col_map.get('COMM_LVL')]),
                safe_str(row[col_map.get('E_COMMODITY_SDESC')], 100),
                safe_str(row[col_map.get('CTY_CODE')]),
                safe_str(row[col_map.get('CTY_NAME')], 100),
                safe_str(row[col_map.get('DISTRICT')]),
                safe_str(row[col_map.get('DIST_NAME')], 100),
                safe_str(row[col_map.get('DF')]),
                safe_str(row[col_map.get('SUMMARY_LVL')]),
                safe_bigint(row[col_map.get('ALL_VAL_MO')]),
                safe_bigint(row[col_map.get('ALL_VAL_YR')]),
                safe_bigint(row[col_map.get('AIR_VAL_MO')]),
                safe_bigint(row[col_map.get('AIR_VAL_YR')]),
                safe_bigint(row[col_map.get('VES_VAL_MO')]),
                safe_bigint(row[col_map.get('VES_VAL_YR')]),
                safe_bigint(row[col_map.get('AIR_WGT_MO')]),
                safe_bigint(row[col_map.get('AIR_WGT_YR')]),
                safe_bigint(row[col_map.get('VES_WGT_MO')]),
                safe_bigint(row[col_map.get('VES_WGT_YR')]),
                safe_str(row[col_map.get('UNIT_QY1')]) if 'UNIT_QY1' in col_map else None,
                safe_str(row[col_map.get('UNIT_QY2')]) if 'UNIT_QY2' in col_map else None,
                safe_bigint(row[col_map.get('QTY_1_MO')]) if 'QTY_1_MO' in col_map else None,
                safe_str(row[col_map.get('QTY_1_MO_FLAG')]) if 'QTY_1_MO_FLAG' in col_map else None,
                safe_bigint(row[col_map.get('QTY_2_MO')]) if 'QTY_2_MO' in col_map else None,
                safe_str(row[col_map.get('QTY_2_MO_FLAG')]) if 'QTY_2_MO_FLAG' in col_map else None
            ))
            inserted += 1
        except Exception as e:
            # Skip problematic rows
            pass
    
    return inserted

def insert_imports_hs(cur, data, time_period):
    """Insert import HS data into database"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    year, month = time_period.split('-')
    
    for row in rows:
        try:
            hs_code = safe_str(row[col_map.get('I_COMMODITY')])
            if not hs_code or hs_code == '-':
                continue
                
            cur.execute("""
                INSERT INTO intltrade_imports_hs (
                    time_period, year, month,
                    hs_code, comm_lvl, hs_desc_short,
                    cty_code, cty_name, cty_subcode,
                    district, district_name, rp, summary_lvl,
                    gen_val_mo, gen_val_yr,
                    con_val_mo, con_val_yr,
                    air_val_mo, air_val_yr,
                    ves_val_mo, ves_val_yr,
                    air_wgt_mo, air_wgt_yr,
                    ves_wgt_mo, ves_wgt_yr,
                    unit_qy1, unit_qy2,
                    gen_qy1_mo, gen_qy1_mo_flag,
                    gen_qy2_mo, gen_qy2_mo_flag,
                    cal_dut_mo, dut_val_mo
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT DO NOTHING
            """, (
                time_period, int(year), int(month),
                hs_code,
                safe_str(row[col_map.get('COMM_LVL')]),
                safe_str(row[col_map.get('I_COMMODITY_SDESC')], 100),
                safe_str(row[col_map.get('CTY_CODE')]),
                safe_str(row[col_map.get('CTY_NAME')], 100),
                safe_str(row[col_map.get('CTY_SUBCODE')]),
                safe_str(row[col_map.get('DISTRICT')]),
                safe_str(row[col_map.get('DIST_NAME')], 100),
                safe_str(row[col_map.get('RP')]),
                safe_str(row[col_map.get('SUMMARY_LVL')]),
                safe_bigint(row[col_map.get('GEN_VAL_MO')]),
                safe_bigint(row[col_map.get('GEN_VAL_YR')]),
                safe_bigint(row[col_map.get('CON_VAL_MO')]),
                safe_bigint(row[col_map.get('CON_VAL_YR')]),
                safe_bigint(row[col_map.get('AIR_VAL_MO')]),
                safe_bigint(row[col_map.get('AIR_VAL_YR')]),
                safe_bigint(row[col_map.get('VES_VAL_MO')]),
                safe_bigint(row[col_map.get('VES_VAL_YR')]),
                safe_bigint(row[col_map.get('AIR_WGT_MO')]),
                safe_bigint(row[col_map.get('AIR_WGT_YR')]),
                safe_bigint(row[col_map.get('VES_WGT_MO')]),
                safe_bigint(row[col_map.get('VES_WGT_YR')]),
                safe_str(row[col_map.get('UNIT_QY1')]) if 'UNIT_QY1' in col_map else None,
                safe_str(row[col_map.get('UNIT_QY2')]) if 'UNIT_QY2' in col_map else None,
                safe_bigint(row[col_map.get('GEN_QY1_MO')]) if 'GEN_QY1_MO' in col_map else None,
                safe_str(row[col_map.get('GEN_QY1_MO_FLAG')]) if 'GEN_QY1_MO_FLAG' in col_map else None,
                safe_bigint(row[col_map.get('GEN_QY2_MO')]) if 'GEN_QY2_MO' in col_map else None,
                safe_str(row[col_map.get('GEN_QY2_MO_FLAG')]) if 'GEN_QY2_MO_FLAG' in col_map else None,
                safe_bigint(row[col_map.get('CAL_DUT_MO')]) if 'CAL_DUT_MO' in col_map else None,
                safe_bigint(row[col_map.get('DUT_VAL_MO')]) if 'DUT_VAL_MO' in col_map else None
            ))
            inserted += 1
        except Exception as e:
            pass
    
    return inserted

# =============================================================================
# MAIN INGESTION FUNCTIONS
# =============================================================================
def ingest_exports_hs(cur, conn, time_periods, comm_lvl, resume=True):
    """Ingest export HS data for given time periods and commodity level"""
    print(f"\n>>> Ingesting EXPORTS HS ({comm_lvl})...")
    
    # Check for resume point
    if resume:
        last_period = get_last_ingested_period(cur, 'exports_hs', comm_lvl)
        if last_period:
            print(f"    Resuming from {last_period}")
            time_periods = [p for p in time_periods if p > last_period]
    
    if not time_periods:
        print("    All periods already ingested")
        return 0
    
    total_rows = 0
    
    # For HS10, use wildcard prefixes to avoid cardinality issues
    prefixes = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] if comm_lvl == 'HS10' else [None]
    
    for period in time_periods:
        period_rows = 0
        print(f"    {period}...", end=" ", flush=True)
        
        try:
            for prefix in prefixes:
                data = fetch_exports_hs(period, comm_lvl, prefix)
                time.sleep(BASE_DELAY)
                
                if data:
                    rows = insert_exports_hs(cur, data, period)
                    period_rows += rows
            
            conn.commit()
            log_ingestion(cur, 'exports_hs', period, comm_lvl, period_rows, 'success')
            conn.commit()
            
            print(f"✓ {period_rows:,} rows")
            total_rows += period_rows
            
        except Exception as e:
            conn.rollback()
            log_ingestion(cur, 'exports_hs', period, comm_lvl, 0, 'failed', str(e))
            conn.commit()
            print(f"✗ Error: {e}")
    
    return total_rows

def ingest_imports_hs(cur, conn, time_periods, comm_lvl, resume=True):
    """Ingest import HS data for given time periods and commodity level"""
    print(f"\n>>> Ingesting IMPORTS HS ({comm_lvl})...")
    
    if resume:
        last_period = get_last_ingested_period(cur, 'imports_hs', comm_lvl)
        if last_period:
            print(f"    Resuming from {last_period}")
            time_periods = [p for p in time_periods if p > last_period]
    
    if not time_periods:
        print("    All periods already ingested")
        return 0
    
    total_rows = 0
    prefixes = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] if comm_lvl == 'HS10' else [None]
    
    for period in time_periods:
        period_rows = 0
        print(f"    {period}...", end=" ", flush=True)
        
        try:
            for prefix in prefixes:
                data = fetch_imports_hs(period, comm_lvl, prefix)
                time.sleep(BASE_DELAY)
                
                if data:
                    rows = insert_imports_hs(cur, data, period)
                    period_rows += rows
            
            conn.commit()
            log_ingestion(cur, 'imports_hs', period, comm_lvl, period_rows, 'success')
            conn.commit()
            
            print(f"✓ {period_rows:,} rows")
            total_rows += period_rows
            
        except Exception as e:
            conn.rollback()
            log_ingestion(cur, 'imports_hs', period, comm_lvl, 0, 'failed', str(e))
            conn.commit()
            print(f"✗ Error: {e}")
    
    return total_rows

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("INTERNATIONAL TRADE DATA INGESTION - HS ENDPOINTS")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check API key
    if not API_KEY:
        print("\n⚠️  ERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
        print("   Get a key at: https://api.census.gov/data/key_signup.html")
        exit(1)
    
    conn = connect_db()
    cur = conn.cursor()
    
    # Generate time periods (January 2013 to present)
    time_periods = get_time_periods(2013, 1)
    print(f"\nTime periods to process: {len(time_periods)} months")
    print(f"  From: {time_periods[0]} to {time_periods[-1]}")
    
    # Commodity levels to ingest (order: smaller to larger datasets)
    comm_levels = ['HS2', 'HS4', 'HS6', 'HS10']
    
    grand_total = 0
    
    # ==========================================================================
    # PHASE 1: HS2 (2-digit) - Smallest, good for testing
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: HS2 (2-digit commodity codes)")
    print("=" * 70)
    
    exports_hs2 = ingest_exports_hs(cur, conn, time_periods, 'HS2')
    imports_hs2 = ingest_imports_hs(cur, conn, time_periods, 'HS2')
    
    print(f"\n  HS2 Total: Exports={exports_hs2:,}, Imports={imports_hs2:,}")
    grand_total += exports_hs2 + imports_hs2
    
    # ==========================================================================
    # PHASE 2: HS4 (4-digit)
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: HS4 (4-digit commodity codes)")
    print("=" * 70)
    
    exports_hs4 = ingest_exports_hs(cur, conn, time_periods, 'HS4')
    imports_hs4 = ingest_imports_hs(cur, conn, time_periods, 'HS4')
    
    print(f"\n  HS4 Total: Exports={exports_hs4:,}, Imports={imports_hs4:,}")
    grand_total += exports_hs4 + imports_hs4
    
    # ==========================================================================
    # PHASE 3: HS6 (6-digit)
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: HS6 (6-digit commodity codes)")
    print("=" * 70)
    
    exports_hs6 = ingest_exports_hs(cur, conn, time_periods, 'HS6')
    imports_hs6 = ingest_imports_hs(cur, conn, time_periods, 'HS6')
    
    print(f"\n  HS6 Total: Exports={exports_hs6:,}, Imports={imports_hs6:,}")
    grand_total += exports_hs6 + imports_hs6
    
    # ==========================================================================
    # PHASE 4: HS10 (10-digit) - Largest dataset, uses wildcard strategy
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 4: HS10 (10-digit commodity codes)")
    print("=" * 70)
    print("Note: Using wildcard strategy (0-9 prefixes) to handle cardinality")
    
    exports_hs10 = ingest_exports_hs(cur, conn, time_periods, 'HS10')
    imports_hs10 = ingest_imports_hs(cur, conn, time_periods, 'HS10')
    
    print(f"\n  HS10 Total: Exports={exports_hs10:,}, Imports={imports_hs10:,}")
    grand_total += exports_hs10 + imports_hs10
    
    # ==========================================================================
    # FINAL SUMMARY
    # ==========================================================================
    print("\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    
    cur.execute("SELECT COUNT(*) FROM intltrade_exports_hs")
    exp_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM intltrade_imports_hs")
    imp_total = cur.fetchone()[0]
    
    print(f"\nTable counts:")
    print(f"  intltrade_exports_hs: {exp_total:,} rows")
    print(f"  intltrade_imports_hs: {imp_total:,} rows")
    print(f"  Total International Trade HS: {exp_total + imp_total:,} rows")
    
    # By commodity level
    print(f"\nBy commodity level:")
    for level in ['HS2', 'HS4', 'HS6', 'HS10']:
        cur.execute("SELECT COUNT(*) FROM intltrade_exports_hs WHERE comm_lvl = %s", (level,))
        exp = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM intltrade_imports_hs WHERE comm_lvl = %s", (level,))
        imp = cur.fetchone()[0]
        print(f"  {level}: Exports={exp:,}, Imports={imp:,}")
    
    # Time range
    cur.execute("SELECT MIN(time_period), MAX(time_period) FROM intltrade_exports_hs")
    exp_range = cur.fetchone()
    cur.execute("SELECT MIN(time_period), MAX(time_period) FROM intltrade_imports_hs")
    imp_range = cur.fetchone()
    
    print(f"\nTime range:")
    print(f"  Exports: {exp_range[0]} to {exp_range[1]}")
    print(f"  Imports: {imp_range[0]} to {imp_range[1]}")
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    cur.close()
    conn.close()
    
    print("\n✓ International Trade HS ingestion complete!")