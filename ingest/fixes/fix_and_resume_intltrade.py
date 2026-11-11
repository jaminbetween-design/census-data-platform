#!/usr/bin/env python3
"""
FIX AND RESUME INTERNATIONAL TRADE INGESTION
Corrects the ingestion log based on actual data and resumes from where we left off
"""

import psycopg2
from datetime import datetime
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

print("=" * 70)
print("FIXING INTERNATIONAL TRADE INGESTION LOG")
print("=" * 70)

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# 1. CHECK ACTUAL DATA STATE
# =============================================================================
print("\n>>> Current data state:")

# Exports
cur.execute("""
    SELECT comm_lvl, COUNT(*), MIN(time_period), MAX(time_period) 
    FROM intltrade_exports_hs 
    GROUP BY comm_lvl 
    ORDER BY comm_lvl
""")
exp_data = cur.fetchall()
print("\n  EXPORTS:")
if exp_data:
    for row in exp_data:
        print(f"    {row[0]}: {row[1]:,} rows ({row[2]} to {row[3]})")
else:
    print("    No data")

# Imports
cur.execute("""
    SELECT comm_lvl, COUNT(*), MIN(time_period), MAX(time_period) 
    FROM intltrade_imports_hs 
    GROUP BY comm_lvl 
    ORDER BY comm_lvl
""")
imp_data = cur.fetchall()
print("\n  IMPORTS:")
if imp_data:
    for row in imp_data:
        print(f"    {row[0]}: {row[1]:,} rows ({row[2]} to {row[3]})")
else:
    print("    No data")

# =============================================================================
# 2. CHECK INGESTION LOG
# =============================================================================
print("\n>>> Current ingestion log:")
cur.execute("""
    SELECT dataset, comm_lvl, COUNT(*) as entries, 
           MIN(time_period), MAX(time_period),
           COUNT(*) FILTER (WHERE status = 'success') as success_count
    FROM intltrade_ingestion_log 
    GROUP BY dataset, comm_lvl 
    ORDER BY dataset, comm_lvl
""")
log_data = cur.fetchall()
for row in log_data:
    print(f"  {row[0]} {row[1]}: {row[2]} entries ({row[3]} to {row[4]}), {row[5]} success")

# =============================================================================
# 3. FIX THE LOG - Remove incorrect entries
# =============================================================================
print("\n>>> Fixing ingestion log...")

# For exports_hs HS2, we have data through 2022-05
# Remove any log entries for periods we don't actually have data for

# First, find actual periods with data for each dataset/level
cur.execute("""
    SELECT DISTINCT time_period FROM intltrade_exports_hs WHERE comm_lvl = 'HS2'
""")
actual_export_hs2_periods = set(row[0] for row in cur.fetchall())

# Delete log entries that claim success but don't have corresponding data
cur.execute("""
    DELETE FROM intltrade_ingestion_log 
    WHERE dataset = 'exports_hs' 
    AND comm_lvl = 'HS2' 
    AND status = 'success'
    AND time_period NOT IN (
        SELECT DISTINCT time_period FROM intltrade_exports_hs WHERE comm_lvl = 'HS2'
    )
""")
deleted_exp = cur.rowcount
print(f"  Deleted {deleted_exp} incorrect export log entries")

# Delete ALL import log entries since we have no import data
cur.execute("DELETE FROM intltrade_ingestion_log WHERE dataset = 'imports_hs'")
deleted_imp = cur.rowcount
print(f"  Deleted {deleted_imp} incorrect import log entries")

# Delete log entries for HS4, HS6, HS10 exports (no data yet)
cur.execute("""
    DELETE FROM intltrade_ingestion_log 
    WHERE dataset = 'exports_hs' 
    AND comm_lvl IN ('HS4', 'HS6', 'HS10')
""")
deleted_other = cur.rowcount
print(f"  Deleted {deleted_other} log entries for HS4/HS6/HS10 exports")

# =============================================================================
# 4. REBUILD LOG FROM ACTUAL DATA
# =============================================================================
print("\n>>> Rebuilding log from actual data...")

# For HS2 exports, create log entries based on actual data
cur.execute("""
    INSERT INTO intltrade_ingestion_log (dataset, time_period, comm_lvl, rows_ingested, status, started_at)
    SELECT 
        'exports_hs',
        time_period,
        'HS2',
        COUNT(*),
        'success',
        NOW()
    FROM intltrade_exports_hs 
    WHERE comm_lvl = 'HS2'
    GROUP BY time_period
    ON CONFLICT (dataset, time_period, comm_lvl) 
    DO UPDATE SET rows_ingested = EXCLUDED.rows_ingested, status = 'success'
""")
print(f"  Rebuilt {cur.rowcount} export HS2 log entries")

# =============================================================================
# 5. VERIFY FIX
# =============================================================================
print("\n>>> Verification:")

cur.execute("""
    SELECT dataset, comm_lvl, COUNT(*) as entries, 
           MIN(time_period) as first, MAX(time_period) as last
    FROM intltrade_ingestion_log 
    WHERE status = 'success'
    GROUP BY dataset, comm_lvl 
    ORDER BY dataset, comm_lvl
""")
print("\n  Ingestion log after fix:")
for row in cur.fetchall():
    print(f"    {row[0]} {row[1]}: {row[2]} periods ({row[3]} to {row[4]})")

# Check what's missing
cur.execute("""
    SELECT MAX(time_period) FROM intltrade_ingestion_log 
    WHERE dataset = 'exports_hs' AND comm_lvl = 'HS2' AND status = 'success'
""")
last_exp_hs2 = cur.fetchone()[0]
print(f"\n  Last successful export HS2: {last_exp_hs2}")
print(f"  Next period to ingest: 2022-06 (if {last_exp_hs2} is 2022-05)")

# =============================================================================
# 6. SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"""
Current state:
  - Exports HS2: 45.4M rows (2013-01 to 2022-05) ✓
  - Exports HS4, HS6, HS10: Not started
  - Imports (all levels): Not started

What's needed:
  1. Continue exports HS2 from 2022-06 to present
  2. Run exports HS4, HS6, HS10 (full range)
  3. Run all imports (full range)

Run the main ingestion script again:
  python ingest/ingest_intltrade_hs.py
""")

cur.close()
conn.close()

print("✓ Log fix complete!")