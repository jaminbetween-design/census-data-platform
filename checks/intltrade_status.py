#!/usr/bin/env python3
"""
INTERNATIONAL TRADE DATA - STATUS CHECK
Detailed analysis of what's already in the database
"""

import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

print("=" * 70)
print("INTERNATIONAL TRADE DATA - STATUS CHECK")
print("=" * 70)

conn = connect_db()
cur = conn.cursor()

# =============================================================================
# 1. OVERALL COUNTS
# =============================================================================
print("\n" + "=" * 70)
print("1. OVERALL TABLE COUNTS")
print("=" * 70)

cur.execute("SELECT COUNT(*) FROM intltrade_exports_hs")
exp_total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM intltrade_imports_hs")
imp_total = cur.fetchone()[0]

print(f"\n  intltrade_exports_hs: {exp_total:,} rows")
print(f"  intltrade_imports_hs: {imp_total:,} rows")
print(f"  TOTAL: {exp_total + imp_total:,} rows")

# =============================================================================
# 2. EXPORTS BY COMMODITY LEVEL
# =============================================================================
print("\n" + "=" * 70)
print("2. EXPORTS BY COMMODITY LEVEL")
print("=" * 70)

cur.execute("""
    SELECT 
        comm_lvl,
        COUNT(*) as rows,
        COUNT(DISTINCT time_period) as periods,
        MIN(time_period) as first_period,
        MAX(time_period) as last_period,
        COUNT(DISTINCT cty_code) as countries,
        COUNT(DISTINCT hs_code) as hs_codes
    FROM intltrade_exports_hs
    GROUP BY comm_lvl
    ORDER BY comm_lvl
""")
results = cur.fetchall()

if results:
    print(f"\n  {'Level':<8} {'Rows':>15} {'Periods':>10} {'First':>10} {'Last':>10} {'Countries':>10} {'HS Codes':>10}")
    print(f"  {'-'*8} {'-'*15} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    for row in results:
        print(f"  {row[0]:<8} {row[1]:>15,} {row[2]:>10} {row[3]:>10} {row[4]:>10} {row[5]:>10} {row[6]:>10}")
else:
    print("\n  No export data found")

# =============================================================================
# 3. IMPORTS BY COMMODITY LEVEL
# =============================================================================
print("\n" + "=" * 70)
print("3. IMPORTS BY COMMODITY LEVEL")
print("=" * 70)

cur.execute("""
    SELECT 
        comm_lvl,
        COUNT(*) as rows,
        COUNT(DISTINCT time_period) as periods,
        MIN(time_period) as first_period,
        MAX(time_period) as last_period,
        COUNT(DISTINCT cty_code) as countries,
        COUNT(DISTINCT hs_code) as hs_codes
    FROM intltrade_imports_hs
    GROUP BY comm_lvl
    ORDER BY comm_lvl
""")
results = cur.fetchall()

if results:
    print(f"\n  {'Level':<8} {'Rows':>15} {'Periods':>10} {'First':>10} {'Last':>10} {'Countries':>10} {'HS Codes':>10}")
    print(f"  {'-'*8} {'-'*15} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    for row in results:
        print(f"  {row[0]:<8} {row[1]:>15,} {row[2]:>10} {row[3]:>10} {row[4]:>10} {row[5]:>10} {row[6]:>10}")
else:
    print("\n  No import data found")

# =============================================================================
# 4. EXPORTS - DETAILED PERIOD COVERAGE
# =============================================================================
print("\n" + "=" * 70)
print("4. EXPORTS - PERIOD COVERAGE BY YEAR")
print("=" * 70)

cur.execute("""
    SELECT 
        comm_lvl,
        EXTRACT(YEAR FROM TO_DATE(time_period, 'YYYY-MM'))::INTEGER as year,
        COUNT(DISTINCT time_period) as months,
        SUM(CASE WHEN all_val_mo IS NOT NULL THEN 1 ELSE 0 END) as rows_with_value
    FROM intltrade_exports_hs
    GROUP BY comm_lvl, EXTRACT(YEAR FROM TO_DATE(time_period, 'YYYY-MM'))
    ORDER BY comm_lvl, year
""")
results = cur.fetchall()

if results:
    current_lvl = None
    for row in results:
        if row[0] != current_lvl:
            current_lvl = row[0]
            print(f"\n  {current_lvl}:")
        print(f"    {row[1]}: {row[2]:>2} months, {row[3]:>10,} data rows")

# =============================================================================
# 5. EXPORTS - MISSING PERIODS CHECK
# =============================================================================
print("\n" + "=" * 70)
print("5. EXPORTS - MISSING PERIODS (Expected: 2013-01 to 2025-10)")
print("=" * 70)

# Generate expected periods
from datetime import date
from dateutil.relativedelta import relativedelta

expected = []
current = date(2013, 1, 1)
end = date(2025, 10, 1)  # Last month with data
while current <= end:
    expected.append(f"{current.year}-{current.month:02d}")
    current += relativedelta(months=1)

for comm_lvl in ['HS2', 'HS4', 'HS6', 'HS10']:
    cur.execute("""
        SELECT DISTINCT time_period 
        FROM intltrade_exports_hs 
        WHERE comm_lvl = %s
    """, (comm_lvl,))
    actual = set(row[0] for row in cur.fetchall())
    missing = [p for p in expected if p not in actual]
    
    if missing:
        print(f"\n  {comm_lvl}: {len(missing)} missing periods")
        if len(missing) <= 20:
            print(f"    Missing: {', '.join(missing)}")
        else:
            print(f"    First missing: {missing[0]}")
            print(f"    Last missing: {missing[-1]}")
    else:
        print(f"\n  {comm_lvl}: Complete! All {len(expected)} periods present")

# =============================================================================
# 6. IMPORTS - MISSING PERIODS CHECK
# =============================================================================
print("\n" + "=" * 70)
print("6. IMPORTS - MISSING PERIODS")
print("=" * 70)

for comm_lvl in ['HS2', 'HS4', 'HS6', 'HS10']:
    cur.execute("""
        SELECT DISTINCT time_period 
        FROM intltrade_imports_hs 
        WHERE comm_lvl = %s
    """, (comm_lvl,))
    actual = set(row[0] for row in cur.fetchall())
    missing = [p for p in expected if p not in actual]
    
    if len(actual) == 0:
        print(f"\n  {comm_lvl}: No data - all {len(expected)} periods missing")
    elif missing:
        print(f"\n  {comm_lvl}: {len(actual)} periods present, {len(missing)} missing")
        if len(missing) <= 10:
            print(f"    Missing: {', '.join(missing)}")
    else:
        print(f"\n  {comm_lvl}: Complete! All {len(expected)} periods present")

# =============================================================================
# 7. INGESTION LOG STATUS
# =============================================================================
print("\n" + "=" * 70)
print("7. INGESTION LOG STATUS")
print("=" * 70)

cur.execute("""
    SELECT 
        dataset,
        comm_lvl,
        status,
        COUNT(*) as entries,
        MIN(time_period) as first,
        MAX(time_period) as last
    FROM intltrade_ingestion_log
    GROUP BY dataset, comm_lvl, status
    ORDER BY dataset, comm_lvl, status
""")
results = cur.fetchall()

if results:
    print(f"\n  {'Dataset':<15} {'Level':<6} {'Status':<10} {'Entries':>8} {'First':>10} {'Last':>10}")
    print(f"  {'-'*15} {'-'*6} {'-'*10} {'-'*8} {'-'*10} {'-'*10}")
    for row in results:
        print(f"  {row[0]:<15} {row[1]:<6} {row[2]:<10} {row[3]:>8} {row[4]:>10} {row[5]:>10}")
else:
    print("\n  No ingestion log entries")

# =============================================================================
# 8. SAMPLE DATA CHECK
# =============================================================================
print("\n" + "=" * 70)
print("8. SAMPLE DATA (First 5 export rows)")
print("=" * 70)

cur.execute("""
    SELECT time_period, hs_code, comm_lvl, cty_code, cty_name, all_val_mo
    FROM intltrade_exports_hs
    ORDER BY time_period, hs_code
    LIMIT 5
""")
results = cur.fetchall()

if results:
    print(f"\n  {'Period':<10} {'HS Code':<12} {'Level':<6} {'Country':<6} {'Country Name':<25} {'Value':>15}")
    print(f"  {'-'*10} {'-'*12} {'-'*6} {'-'*6} {'-'*25} {'-'*15}")
    for row in results:
        val = f"{row[5]:,}" if row[5] else "NULL"
        cty_name = (row[4] or "")[:25]
        print(f"  {row[0]:<10} {row[1]:<12} {row[2]:<6} {row[3] or '-':<6} {cty_name:<25} {val:>15}")

# =============================================================================
# 9. SUMMARY & RECOMMENDATIONS
# =============================================================================
print("\n" + "=" * 70)
print("9. SUMMARY & RECOMMENDATIONS")
print("=" * 70)

print(f"""
CURRENT STATE:
  - Exports: {exp_total:,} rows
  - Imports: {imp_total:,} rows
  - Total: {exp_total + imp_total:,} rows
""")

# Determine what's missing
cur.execute("SELECT COUNT(DISTINCT time_period) FROM intltrade_exports_hs WHERE comm_lvl = 'HS2'")
exp_hs2_periods = cur.fetchone()[0]

if exp_total > 0 and imp_total == 0:
    print("""RECOMMENDATION:
  You have substantial export data. Rather than reset, we should:
  1. Keep existing export data
  2. Fix the ingestion log to reflect actual data
  3. Run the robust script to:
     - Fill in any missing export periods
     - Ingest all import data (which is currently empty)
  
  This will preserve the ~45M+ export rows you already have.
""")
elif exp_total == 0 and imp_total == 0:
    print("""RECOMMENDATION:
  No data present. Run the robust ingestion script:
    python ingest/ingest_intltrade_robust.py
""")
else:
    print("""RECOMMENDATION:
  Run the robust ingestion script to fill in gaps:
    python ingest/ingest_intltrade_robust.py
""")

cur.close()
conn.close()

print("=" * 70)
print("STATUS CHECK COMPLETE")
print("=" * 70)