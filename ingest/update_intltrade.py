#!/usr/bin/env python3
"""
INTERNATIONAL TRADE DATA - INCREMENTAL UPDATE SCRIPT
Run this monthly to add newly released trade data

The Census Bureau releases trade data on a monthly schedule:
- FT-900 release (usually around the 5th of each month)
- Data is typically ~6 weeks behind (e.g., December data released in early February)

Usage:
    python ingest/update_intltrade.py           # Check and ingest any new data
    python ingest/update_intltrade.py --force   # Force re-ingest last 3 months
"""

import requests
import psycopg2
import time
import argparse
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

# =============================================================================
# CONFIGURATION
# =============================================================================
API_KEY = os.environ.get("CENSUS_API_KEY")

BASE_DELAY = 0.5
RETRY_DELAY = 30
MAX_RETRIES = 3

# =============================================================================
# DATABASE CONNECTION
# =============================================================================
def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def safe_bigint(value):
    if value is None or value == '' or value == 'null' or value == '-':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_str(value, max_len=None):
    if value is None or value == '' or value == 'null':
        return None
    s = str(value).strip()
    if max_len:
        s = s[:max_len]
    return s if s else None

def check_api_availability(time_period, direction='exports'):
    """Check if data is available for a given time period"""
    base = f"https://api.census.gov/data/timeseries/intltrade/{direction}/hs"
    url = f"{base}?get=ALL_VAL_MO&time={time_period}&COMM_LVL=HS2&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return len(data) > 1
        return False
    except:
        return False

def get_latest_available_period():
    """Find the most recent month with available data"""
    current = date.today()
    
    # Start checking from 2 months ago (data is usually ~6 weeks behind)
    check_date = current - relativedelta(months=2)
    
    for _ in range(6):  # Check up to 6 months back
        period = f"{check_date.year}-{check_date.month:02d}"
        if check_api_availability(period):
            return period
        check_date -= relativedelta(months=1)
    
    return None

def get_ingested_periods(cur, table):
    """Get list of successfully ingested periods"""
    cur.execute(f"""
        SELECT DISTINCT time_period FROM {table} 
        ORDER BY time_period
    """)
    return [row[0] for row in cur.fetchall()]

def get_missing_periods(cur, table, start='2013-01'):
    """Find periods that haven't been ingested yet"""
    latest = get_latest_available_period()
    if not latest:
        print("  Could not determine latest available data")
        return []
    
    ingested = set(get_ingested_periods(cur, table))
    
    # Generate all periods from start to latest
    all_periods = []
    current = datetime.strptime(start, '%Y-%m').date()
    end = datetime.strptime(latest, '%Y-%m').date()
    
    while current <= end:
        period = f"{current.year}-{current.month:02d}"
        if period not in ingested:
            all_periods.append(period)
        current += relativedelta(months=1)
    
    return all_periods

# =============================================================================
# INGESTION FUNCTIONS (simplified from main script)
# =============================================================================
def fetch_and_insert_exports(cur, time_period, comm_lvl, prefix=None):
    """Fetch and insert export data"""
    base_url = "https://api.census.gov/data/timeseries/intltrade/exports/hs"
    
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
    
    if comm_lvl in ['HS6', 'HS10']:
        get_vars.extend(["UNIT_QY1", "UNIT_QY2", "QTY_1_MO", "QTY_1_MO_FLAG", "QTY_2_MO", "QTY_2_MO_FLAG"])
    
    url = f"{base_url}?get={','.join(get_vars)}&time={time_period}&COMM_LVL={comm_lvl}"
    if prefix:
        url += f"&E_COMMODITY={prefix}*"
    url += f"&key={API_KEY}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=180)
            if response.status_code == 200:
                data = response.json()
                if len(data) < 2:
                    return 0
                
                headers = data[0]
                rows = data[1:]
                col_map = {col: idx for idx, col in enumerate(headers)}
                year, month = time_period.split('-')
                
                inserted = 0
                for row in rows:
                    try:
                        hs_code = safe_str(row[col_map.get('E_COMMODITY')])
                        if not hs_code or hs_code == '-':
                            continue
                        
                        cur.execute("""
                            INSERT INTO intltrade_exports_hs (
                                time_period, year, month, hs_code, comm_lvl, hs_desc_short,
                                cty_code, cty_name, district, district_name, df, summary_lvl,
                                all_val_mo, all_val_yr, air_val_mo, air_val_yr,
                                ves_val_mo, ves_val_yr, air_wgt_mo, air_wgt_yr,
                                ves_wgt_mo, ves_wgt_yr, unit_qy1, unit_qy2,
                                qty_1_mo, qty_1_mo_flag, qty_2_mo, qty_2_mo_flag
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT DO NOTHING
                        """, (
                            time_period, int(year), int(month), hs_code,
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
                    except:
                        pass
                return inserted
            elif response.status_code == 204:
                return 0
            elif response.status_code == 429:
                time.sleep(RETRY_DELAY * (attempt + 1))
        except:
            time.sleep(RETRY_DELAY)
    return 0

def fetch_and_insert_imports(cur, time_period, comm_lvl, prefix=None):
    """Fetch and insert import data"""
    base_url = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
    
    get_vars = [
        "I_COMMODITY", "I_COMMODITY_SDESC",
        "CTY_CODE", "CTY_NAME", "CTY_SUBCODE",
        "DISTRICT", "DIST_NAME", "RP", "COMM_LVL", "SUMMARY_LVL",
        "GEN_VAL_MO", "GEN_VAL_YR", "CON_VAL_MO", "CON_VAL_YR",
        "AIR_VAL_MO", "AIR_VAL_YR", "VES_VAL_MO", "VES_VAL_YR",
        "AIR_WGT_MO", "AIR_WGT_YR", "VES_WGT_MO", "VES_WGT_YR"
    ]
    
    if comm_lvl in ['HS6', 'HS10']:
        get_vars.extend(["UNIT_QY1", "UNIT_QY2", "GEN_QY1_MO", "GEN_QY1_MO_FLAG", 
                         "GEN_QY2_MO", "GEN_QY2_MO_FLAG", "CAL_DUT_MO", "DUT_VAL_MO"])
    
    url = f"{base_url}?get={','.join(get_vars)}&time={time_period}&COMM_LVL={comm_lvl}"
    if prefix:
        url += f"&I_COMMODITY={prefix}*"
    url += f"&key={API_KEY}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=180)
            if response.status_code == 200:
                data = response.json()
                if len(data) < 2:
                    return 0
                
                headers = data[0]
                rows = data[1:]
                col_map = {col: idx for idx, col in enumerate(headers)}
                year, month = time_period.split('-')
                
                inserted = 0
                for row in rows:
                    try:
                        hs_code = safe_str(row[col_map.get('I_COMMODITY')])
                        if not hs_code or hs_code == '-':
                            continue
                        
                        cur.execute("""
                            INSERT INTO intltrade_imports_hs (
                                time_period, year, month, hs_code, comm_lvl, hs_desc_short,
                                cty_code, cty_name, cty_subcode, district, district_name,
                                rp, summary_lvl, gen_val_mo, gen_val_yr, con_val_mo, con_val_yr,
                                air_val_mo, air_val_yr, ves_val_mo, ves_val_yr,
                                air_wgt_mo, air_wgt_yr, ves_wgt_mo, ves_wgt_yr,
                                unit_qy1, unit_qy2, gen_qy1_mo, gen_qy1_mo_flag,
                                gen_qy2_mo, gen_qy2_mo_flag, cal_dut_mo, dut_val_mo
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT DO NOTHING
                        """, (
                            time_period, int(year), int(month), hs_code,
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
                    except:
                        pass
                return inserted
            elif response.status_code == 204:
                return 0
            elif response.status_code == 429:
                time.sleep(RETRY_DELAY * (attempt + 1))
        except:
            time.sleep(RETRY_DELAY)
    return 0

# =============================================================================
# MAIN UPDATE FUNCTION
# =============================================================================
def run_update(force_months=0):
    """Run incremental update"""
    print("=" * 70)
    print("INTERNATIONAL TRADE DATA - INCREMENTAL UPDATE")
    print("=" * 70)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not API_KEY:
        print("\n⚠️  ERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
        return
    
    conn = connect_db()
    cur = conn.cursor()
    
    # Find latest available data
    print("\n>>> Checking for new data...")
    latest = get_latest_available_period()
    print(f"    Latest available: {latest}")
    
    comm_levels = ['HS2', 'HS4', 'HS6', 'HS10']
    
    for direction, table in [('exports', 'intltrade_exports_hs'), ('imports', 'intltrade_imports_hs')]:
        print(f"\n>>> Checking {direction.upper()}...")
        
        if force_months > 0:
            # Force re-ingest last N months
            end = datetime.strptime(latest, '%Y-%m').date()
            periods = []
            for i in range(force_months):
                d = end - relativedelta(months=i)
                periods.append(f"{d.year}-{d.month:02d}")
            periods.reverse()
            
            # Delete existing data for these periods
            for period in periods:
                cur.execute(f"DELETE FROM {table} WHERE time_period = %s", (period,))
            conn.commit()
            print(f"    Force re-ingesting: {periods}")
        else:
            # Find missing periods
            periods = get_missing_periods(cur, table)
            if not periods:
                print(f"    {table}: Up to date!")
                continue
            print(f"    Missing periods: {periods}")
        
        for comm_lvl in comm_levels:
            print(f"\n    {comm_lvl}:", end="", flush=True)
            
            prefixes = ['0','1','2','3','4','5','6','7','8','9'] if comm_lvl == 'HS10' else [None]
            
            for period in periods:
                period_total = 0
                for prefix in prefixes:
                    if direction == 'exports':
                        rows = fetch_and_insert_exports(cur, period, comm_lvl, prefix)
                    else:
                        rows = fetch_and_insert_imports(cur, period, comm_lvl, prefix)
                    period_total += rows
                    time.sleep(BASE_DELAY)
                
                conn.commit()
                print(f" {period}:{period_total}", end="", flush=True)
            print()
    
    # Summary
    print("\n" + "=" * 70)
    print("UPDATE SUMMARY")
    print("=" * 70)
    
    cur.execute("SELECT COUNT(*), MIN(time_period), MAX(time_period) FROM intltrade_exports_hs")
    exp = cur.fetchone()
    cur.execute("SELECT COUNT(*), MIN(time_period), MAX(time_period) FROM intltrade_imports_hs")
    imp = cur.fetchone()
    
    print(f"  Exports: {exp[0]:,} rows ({exp[1]} to {exp[2]})")
    print(f"  Imports: {imp[0]:,} rows ({imp[1]} to {imp[2]})")
    print(f"  Total: {exp[0] + imp[0]:,} rows")
    
    cur.close()
    conn.close()
    
    print(f"\n✓ Update complete!")

# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update International Trade data')
    parser.add_argument('--force', type=int, default=0, 
                        help='Force re-ingest last N months (e.g., --force 3)')
    args = parser.parse_args()
    
    run_update(args.force)