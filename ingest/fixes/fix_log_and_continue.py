#!/usr/bin/env python3
"""
FIX INGESTION LOG AND CONTINUE INTERNATIONAL TRADE INGESTION
Preserves existing 61M+ export rows and continues with missing data
"""

import psycopg2
from datetime import date
from dateutil.relativedelta import relativedelta
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

print("=" * 70)
print("FIX INGESTION LOG - PRESERVE EXISTING DATA")
print("=" * 70)

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# 1. CLEAR INCORRECT LOG ENTRIES
# =============================================================================
print("\n>>> Step 1: Clear incorrect ingestion log entries...")

# Delete all log entries - we'll rebuild from actual data
cur.execute("DELETE FROM intltrade_ingestion_log")
print(f"  Cleared {cur.rowcount} log entries")

# =============================================================================
# 2. REBUILD LOG FOR EXPORTS HS2 FROM ACTUAL DATA
# =============================================================================
print("\n>>> Step 2: Rebuild log for exports HS2 from actual data...")

cur.execute("""
    INSERT INTO intltrade_ingestion_log (dataset, time_period, comm_lvl, rows_ingested, status, started_at, completed_at)
    SELECT 
        'exports_hs',
        time_period,
        'HS2',
        COUNT(*),
        'success',
        NOW(),
        NOW()
    FROM intltrade_exports_hs
    WHERE comm_lvl = 'HS2'
    GROUP BY time_period
""")
print(f"  Created {cur.rowcount} log entries for exports HS2")

# =============================================================================
# 3. VERIFY THE FIX
# =============================================================================
print("\n>>> Step 3: Verify log status...")

cur.execute("""
    SELECT dataset, comm_lvl, COUNT(*) as periods, MIN(time_period), MAX(time_period)
    FROM intltrade_ingestion_log
    WHERE status = 'success'
    GROUP BY dataset, comm_lvl
""")
for row in cur.fetchall():
    print(f"  {row[0]} {row[1]}: {row[2]} periods ({row[3]} to {row[4]})")

# =============================================================================
# 4. SHOW WHAT WILL BE INGESTED
# =============================================================================
print("\n>>> Step 4: What the robust script will now ingest...")

# Generate all expected periods
expected = []
current = date(2013, 1, 1)
end = date.today()
while current <= end:
    expected.append(f"{current.year}-{current.month:02d}")
    current += relativedelta(months=1)

# Check what's missing for each dataset/level
datasets = [
    ('exports_hs', 'HS2'),
    ('exports_hs', 'HS4'),
    ('exports_hs', 'HS6'),
    ('exports_hs', 'HS10'),
    ('imports_hs', 'HS2'),
    ('imports_hs', 'HS4'),
    ('imports_hs', 'HS6'),
    ('imports_hs', 'HS10'),
]

print(f"\n  Expected periods: {len(expected)} (2013-01 to {expected[-1]})")
print(f"\n  {'Dataset':<15} {'Level':<6} {'Complete':>10} {'Missing':>10}")
print(f"  {'-'*15} {'-'*6} {'-'*10} {'-'*10}")

total_missing = 0
for dataset, comm_lvl in datasets:
    cur.execute("""
        SELECT time_period FROM intltrade_ingestion_log
        WHERE dataset = %s AND comm_lvl = %s AND status = 'success'
    """, (dataset, comm_lvl))
    complete = set(row[0] for row in cur.fetchall())
    missing = len(expected) - len(complete)
    total_missing += missing
    print(f"  {dataset:<15} {comm_lvl:<6} {len(complete):>10} {missing:>10}")

print(f"\n  Total periods to ingest: {total_missing}")
print(f"  Estimated API calls: {total_missing * 10} (10 chunks per period)")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("READY TO CONTINUE INGESTION")
print("=" * 70)
print(f"""
Current data preserved:
  - Exports HS2: 61,358,741 rows (153 periods)

What will be ingested:
  - Exports HS2: ~1 period (2025-10 if available)
  - Exports HS4: ~{len(expected)} periods (full range)
  - Exports HS6: ~{len(expected)} periods (full range)
  - Exports HS10: ~{len(expected)} periods (full range)
  - Imports HS2: ~{len(expected)} periods (full range)
  - Imports HS4: ~{len(expected)} periods (full range)
  - Imports HS6: ~{len(expected)} periods (full range)
  - Imports HS10: ~{len(expected)} periods (full range)

Next step - run the robust ingestion script:
  
  # Option 1: Run in foreground (see output directly)
  python ingest/ingest_intltrade_robust.py
  
  # Option 2: Run in background (can close terminal)
  nohup python -u ingest/ingest_intltrade_robust.py > intltrade_ingestion.log 2>&1 &
  
  # Monitor background process:
  tail -f intltrade_ingestion.log
""")

cur.close()
conn.close()

print("✓ Log fix complete!")