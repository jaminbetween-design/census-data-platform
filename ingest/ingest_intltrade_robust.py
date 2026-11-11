#!/usr/bin/env python3
"""
INTERNATIONAL TRADE DATA - ROBUST INGESTION SCRIPT
Uses wildcard strategy for ALL queries to avoid cardinality/timeout issues

Strategy:
- Query one HS chapter (0*, 1*, 2*, ..., 9*) at a time
- Longer timeouts (300s)
- Better error recovery
- Detailed progress logging
- Can be left running unattended
"""

import requests
import psycopg2
import time
import sys
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

# =============================================================================
# CONFIGURATION
# =============================================================================
API_KEY = os.environ["CENSUS_API_KEY"]

# Timing
REQUEST_TIMEOUT = 300      # 5 minutes per request
DELAY_BETWEEN_CALLS = 1.0  # 1 second between API calls
DELAY_AFTER_ERROR = 60     # 1 minute after errors
MAX_RETRIES = 5            # More retries for robustness

# HS Chapter prefixes (0-9)
HS_PREFIXES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

# =============================================================================
# DATABASE
# =============================================================================
def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

# =============================================================================
# HELPERS
# =============================================================================
def safe_int(value):
    if value is None or value == '' or value == 'null' or value == '-':
        return None
    try:
        return int(value)
    except:
        return None

def safe_str(value, max_len=None):
    if value is None or value == '' or value == 'null':
        return None
    s = str(value).strip()
    if max_len:
        s = s[:max_len]
    return s if s else None

def get_time_periods(start_year=2013, start_month=1):
    """Generate list of YYYY-MM periods from start to ~2 months ago (data lag)"""
    periods = []
    current = date(start_year, start_month, 1)
    # Data is typically ~6 weeks behind, so stop at 2 months ago
    end = date.today() - relativedelta(months=2)
    
    while current <= end:
        periods.append(f"{current.year}-{current.month:02d}")
        current += relativedelta(months=1)
    
    return periods

def log_msg(msg):
    """Print timestamped message"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {msg}", flush=True)

# =============================================================================
# INGESTION TRACKING
# =============================================================================
def get_completed_periods(cur, dataset, comm_lvl):
    """Get set of periods that have been fully ingested"""
    cur.execute("""
        SELECT time_period FROM intltrade_ingestion_log 
        WHERE dataset = %s AND comm_lvl = %s AND status = 'success'
    """, (dataset, comm_lvl))
    return set(row[0] for row in cur.fetchall())

def mark_period_complete(cur, conn, dataset, time_period, comm_lvl, rows):
    """Mark a period as successfully ingested"""
    cur.execute("""
        INSERT INTO intltrade_ingestion_log 
        (dataset, time_period, comm_lvl, rows_ingested, status, started_at, completed_at)
        VALUES (%s, %s, %s, %s, 'success', NOW(), NOW())
        ON CONFLICT (dataset, time_period, comm_lvl) 
        DO UPDATE SET rows_ingested = %s, status = 'success', completed_at = NOW()
    """, (dataset, time_period, comm_lvl, rows, rows))
    conn.commit()

def mark_period_failed(cur, conn, dataset, time_period, comm_lvl, error):
    """Mark a period as failed"""
    cur.execute("""
        INSERT INTO intltrade_ingestion_log 
        (dataset, time_period, comm_lvl, rows_ingested, status, error_message, started_at)
        VALUES (%s, %s, %s, 0, 'failed', %s, NOW())
        ON CONFLICT (dataset, time_period, comm_lvl) 
        DO UPDATE SET status = 'failed', error_message = %s, completed_at = NOW()
    """, (dataset, time_period, comm_lvl, error[:500], error[:500]))
    conn.commit()

# =============================================================================
# API FUNCTIONS
# =============================================================================
def fetch_exports_chunk(time_period, comm_lvl, hs_prefix):
    """Fetch export data for one HS prefix"""
    base_url = "https://api.census.gov/data/timeseries/intltrade/exports/hs"
    
    # Core variables that work reliably
    get_vars = [
        "E_COMMODITY", "E_COMMODITY_SDESC",
        "CTY_CODE", "CTY_NAME",
        "COMM_LVL", "SUMMARY_LVL",
        "ALL_VAL_MO", "ALL_VAL_YR"
    ]
    
    url = f"{base_url}?get={','.join(get_vars)}&time={time_period}&COMM_LVL={comm_lvl}&E_COMMODITY={hs_prefix}*&key={API_KEY}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return None  # No data
            elif response.status_code == 429:
                log_msg(f"      Rate limited, waiting {DELAY_AFTER_ERROR}s...")
                time.sleep(DELAY_AFTER_ERROR)
            elif response.status_code == 500:
                log_msg(f"      Server error 500, retry {attempt+1}/{MAX_RETRIES}...")
                time.sleep(DELAY_AFTER_ERROR)
            else:
                log_msg(f"      HTTP {response.status_code}, retry {attempt+1}/{MAX_RETRIES}...")
                time.sleep(DELAY_BETWEEN_CALLS * 2)
                
        except requests.exceptions.Timeout:
            log_msg(f"      Timeout, retry {attempt+1}/{MAX_RETRIES}...")
            time.sleep(DELAY_AFTER_ERROR)
        except requests.exceptions.ConnectionError as e:
            log_msg(f"      Connection error, retry {attempt+1}/{MAX_RETRIES}...")
            time.sleep(DELAY_AFTER_ERROR * 2)
        except Exception as e:
            log_msg(f"      Error: {str(e)[:100]}, retry {attempt+1}/{MAX_RETRIES}...")
            time.sleep(DELAY_AFTER_ERROR)
    
    return None  # All retries failed

def fetch_imports_chunk(time_period, comm_lvl, hs_prefix):
    """Fetch import data for one HS prefix"""
    base_url = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
    
    # Core variables - imports use different value fields
    get_vars = [
        "I_COMMODITY", "I_COMMODITY_SDESC",
        "CTY_CODE", "CTY_NAME",
        "COMM_LVL", "SUMMARY_LVL",
        "GEN_VAL_MO", "GEN_VAL_YR",
        "CON_VAL_MO", "CON_VAL_YR"
    ]
    
    url = f"{base_url}?get={','.join(get_vars)}&time={time_period}&COMM_LVL={comm_lvl}&I_COMMODITY={hs_prefix}*&key={API_KEY}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return None
            elif response.status_code == 429:
                log_msg(f"      Rate limited, waiting {DELAY_AFTER_ERROR}s...")
                time.sleep(DELAY_AFTER_ERROR)
            elif response.status_code == 500:
                log_msg(f"      Server error 500, retry {attempt+1}/{MAX_RETRIES}...")
                time.sleep(DELAY_AFTER_ERROR)
            else:
                log_msg(f"      HTTP {response.status_code}, retry {attempt+1}/{MAX_RETRIES}...")
                time.sleep(DELAY_BETWEEN_CALLS * 2)
                
        except requests.exceptions.Timeout:
            log_msg(f"      Timeout, retry {attempt+1}/{MAX_RETRIES}...")
            time.sleep(DELAY_AFTER_ERROR)
        except requests.exceptions.ConnectionError as e:
            log_msg(f"      Connection error, retry {attempt+1}/{MAX_RETRIES}...")
            time.sleep(DELAY_AFTER_ERROR * 2)
        except Exception as e:
            log_msg(f"      Error: {str(e)[:100]}, retry {attempt+1}/{MAX_RETRIES}...")
            time.sleep(DELAY_AFTER_ERROR)
    
    return None

# =============================================================================
# INSERT FUNCTIONS
# =============================================================================
def insert_exports(cur, data, time_period):
    """Insert export data"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col = {h: i for i, h in enumerate(headers)}
    
    year, month = time_period.split('-')
    inserted = 0
    
    for row in rows:
        try:
            hs_code = safe_str(row[col.get('E_COMMODITY')])
            if not hs_code or hs_code == '-':
                continue
            
            cur.execute("""
                INSERT INTO intltrade_exports_hs (
                    time_period, year, month,
                    hs_code, comm_lvl, hs_desc_short,
                    cty_code, cty_name,
                    summary_lvl,
                    all_val_mo, all_val_yr
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                time_period, int(year), int(month),
                hs_code,
                safe_str(row[col.get('COMM_LVL')]),
                safe_str(row[col.get('E_COMMODITY_SDESC')], 100),
                safe_str(row[col.get('CTY_CODE')]),
                safe_str(row[col.get('CTY_NAME')], 100),
                safe_str(row[col.get('SUMMARY_LVL')]),
                safe_int(row[col.get('ALL_VAL_MO')]),
                safe_int(row[col.get('ALL_VAL_YR')])
            ))
            inserted += 1
        except Exception as e:
            pass
    
    return inserted

def insert_imports(cur, data, time_period):
    """Insert import data"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col = {h: i for i, h in enumerate(headers)}
    
    year, month = time_period.split('-')
    inserted = 0
    
    for row in rows:
        try:
            hs_code = safe_str(row[col.get('I_COMMODITY')])
            if not hs_code or hs_code == '-':
                continue
            
            cur.execute("""
                INSERT INTO intltrade_imports_hs (
                    time_period, year, month,
                    hs_code, comm_lvl, hs_desc_short,
                    cty_code, cty_name,
                    summary_lvl,
                    gen_val_mo, gen_val_yr,
                    con_val_mo, con_val_yr
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                time_period, int(year), int(month),
                hs_code,
                safe_str(row[col.get('COMM_LVL')]),
                safe_str(row[col.get('I_COMMODITY_SDESC')], 100),
                safe_str(row[col.get('CTY_CODE')]),
                safe_str(row[col.get('CTY_NAME')], 100),
                safe_str(row[col.get('SUMMARY_LVL')]),
                safe_int(row[col.get('GEN_VAL_MO')]),
                safe_int(row[col.get('GEN_VAL_YR')]),
                safe_int(row[col.get('CON_VAL_MO')]),
                safe_int(row[col.get('CON_VAL_YR')])
            ))
            inserted += 1
        except Exception as e:
            pass
    
    return inserted

# =============================================================================
# MAIN INGESTION FUNCTIONS
# =============================================================================
def ingest_exports(cur, conn, time_periods, comm_lvl):
    """Ingest all export data for a commodity level"""
    log_msg(f"EXPORTS {comm_lvl}: Starting...")
    
    completed = get_completed_periods(cur, 'exports_hs', comm_lvl)
    pending = [p for p in time_periods if p not in completed]
    
    if not pending:
        log_msg(f"EXPORTS {comm_lvl}: All {len(time_periods)} periods complete")
        return 0
    
    log_msg(f"EXPORTS {comm_lvl}: {len(pending)} periods to process (already done: {len(completed)})")
    
    total = 0
    for i, period in enumerate(pending):
        period_rows = 0
        errors = []
        
        # Query each HS prefix
        for prefix in HS_PREFIXES:
            data = fetch_exports_chunk(period, comm_lvl, prefix)
            time.sleep(DELAY_BETWEEN_CALLS)
            
            if data:
                rows = insert_exports(cur, data, period)
                period_rows += rows
            elif data is None:
                # Could be no data or error - track it
                pass
        
        conn.commit()
        
        if period_rows > 0:
            mark_period_complete(cur, conn, 'exports_hs', period, comm_lvl, period_rows)
            total += period_rows
            log_msg(f"EXPORTS {comm_lvl}: {period} ✓ {period_rows:,} rows [{i+1}/{len(pending)}]")
        else:
            # Check if this is expected (future month) or an error
            if period > datetime.now().strftime('%Y-%m'):
                log_msg(f"EXPORTS {comm_lvl}: {period} - no data (future)")
            else:
                mark_period_failed(cur, conn, 'exports_hs', period, comm_lvl, "No data returned")
                log_msg(f"EXPORTS {comm_lvl}: {period} ✗ no data [{i+1}/{len(pending)}]")
    
    log_msg(f"EXPORTS {comm_lvl}: Complete - {total:,} total rows")
    return total

def ingest_imports(cur, conn, time_periods, comm_lvl):
    """Ingest all import data for a commodity level"""
    log_msg(f"IMPORTS {comm_lvl}: Starting...")
    
    completed = get_completed_periods(cur, 'imports_hs', comm_lvl)
    pending = [p for p in time_periods if p not in completed]
    
    if not pending:
        log_msg(f"IMPORTS {comm_lvl}: All {len(time_periods)} periods complete")
        return 0
    
    log_msg(f"IMPORTS {comm_lvl}: {len(pending)} periods to process (already done: {len(completed)})")
    
    total = 0
    for i, period in enumerate(pending):
        period_rows = 0
        
        # Query each HS prefix
        for prefix in HS_PREFIXES:
            data = fetch_imports_chunk(period, comm_lvl, prefix)
            time.sleep(DELAY_BETWEEN_CALLS)
            
            if data:
                rows = insert_imports(cur, data, period)
                period_rows += rows
        
        conn.commit()
        
        if period_rows > 0:
            mark_period_complete(cur, conn, 'imports_hs', period, comm_lvl, period_rows)
            total += period_rows
            log_msg(f"IMPORTS {comm_lvl}: {period} ✓ {period_rows:,} rows [{i+1}/{len(pending)}]")
        else:
            if period > datetime.now().strftime('%Y-%m'):
                log_msg(f"IMPORTS {comm_lvl}: {period} - no data (future)")
            else:
                mark_period_failed(cur, conn, 'imports_hs', period, comm_lvl, "No data returned")
                log_msg(f"IMPORTS {comm_lvl}: {period} ✗ no data [{i+1}/{len(pending)}]")
    
    log_msg(f"IMPORTS {comm_lvl}: Complete - {total:,} total rows")
    return total

# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 70)
    print("INTERNATIONAL TRADE DATA - ROBUST INGESTION")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Strategy: Wildcard queries (10 chunks per period)")
    print(f"Timeout: {REQUEST_TIMEOUT}s per request")
    print("=" * 70)
    
    conn = connect_db()
    cur = conn.cursor()
    
    # Time periods: Jan 2013 to present
    time_periods = get_time_periods(2013, 1)
    print(f"\nTime range: {time_periods[0]} to {time_periods[-1]} ({len(time_periods)} months)")
    
    # Commodity levels to process
    comm_levels = ['HS2', 'HS4', 'HS6', 'HS10']
    
    results = {}
    
    # ==========================================================================
    # EXPORTS
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: EXPORTS")
    print("=" * 70)
    
    for comm_lvl in comm_levels:
        print(f"\n{'─' * 50}")
        rows = ingest_exports(cur, conn, time_periods, comm_lvl)
        results[f'exports_{comm_lvl}'] = rows
    
    # ==========================================================================
    # IMPORTS
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: IMPORTS")
    print("=" * 70)
    
    for comm_lvl in comm_levels:
        print(f"\n{'─' * 50}")
        rows = ingest_imports(cur, conn, time_periods, comm_lvl)
        results[f'imports_{comm_lvl}'] = rows
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    # Get actual counts from database
    print("\nDatabase counts:")
    
    cur.execute("SELECT comm_lvl, COUNT(*) FROM intltrade_exports_hs GROUP BY comm_lvl ORDER BY comm_lvl")
    exp_counts = dict(cur.fetchall())
    
    cur.execute("SELECT comm_lvl, COUNT(*) FROM intltrade_imports_hs GROUP BY comm_lvl ORDER BY comm_lvl")
    imp_counts = dict(cur.fetchall())
    
    exp_total = sum(exp_counts.values())
    imp_total = sum(imp_counts.values())
    
    print("\n  EXPORTS:")
    for lvl in comm_levels:
        count = exp_counts.get(lvl, 0)
        print(f"    {lvl}: {count:,} rows")
    print(f"    Total: {exp_total:,} rows")
    
    print("\n  IMPORTS:")
    for lvl in comm_levels:
        count = imp_counts.get(lvl, 0)
        print(f"    {lvl}: {count:,} rows")
    print(f"    Total: {imp_total:,} rows")
    
    print(f"\n  GRAND TOTAL: {exp_total + imp_total:,} rows")
    
    # Time ranges
    cur.execute("SELECT MIN(time_period), MAX(time_period) FROM intltrade_exports_hs")
    exp_range = cur.fetchone()
    cur.execute("SELECT MIN(time_period), MAX(time_period) FROM intltrade_imports_hs")
    imp_range = cur.fetchone()
    
    print(f"\n  Time ranges:")
    print(f"    Exports: {exp_range[0] or 'None'} to {exp_range[1] or 'None'}")
    print(f"    Imports: {imp_range[0] or 'None'} to {imp_range[1] or 'None'}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    cur.close()
    conn.close()
    
    print("\n✓ Ingestion complete!")

if __name__ == "__main__":
    main()