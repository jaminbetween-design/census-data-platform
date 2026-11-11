import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
cur = conn.cursor()

print("=" * 60)
print("DATA VERIFICATION QUERIES")
print("=" * 60)

# 1. Basic counts
print("\n>>> Row counts by vintage and geo level:\n")
cur.execute("""
    SELECT vintage, geo_level, COUNT(*) as rows
    FROM cbp_data
    GROUP BY vintage, geo_level
    ORDER BY vintage DESC, geo_level
""")
for row in cur.fetchall():
    print(f"  {row[0]} {row[1]}: {row[2]:,}")

# 2. Sample business query: Top 10 states by total employment (2021)
print("\n" + "=" * 60)
print(">>> Top 10 states by employment (2021, all industries):\n")
cur.execute("""
    SELECT geo_name, 
           SUM(employees) as total_emp,
           SUM(establishments) as total_estab,
           SUM(annual_payroll) as total_payroll
    FROM cbp_data
    WHERE vintage = 2021 
      AND geo_level = 'state'
      AND naics_code = '00'
    GROUP BY geo_name
    ORDER BY total_emp DESC
    LIMIT 10
""")
print(f"  {'State':<25} {'Employees':>15} {'Establishments':>15} {'Payroll ($M)':>15}")
print("  " + "-" * 70)
for row in cur.fetchall():
    payroll_millions = row[3] / 1000 if row[3] else 0
    print(f"  {row[0]:<25} {row[1]:>15,} {row[2]:>15,} {payroll_millions:>15,.0f}")

# 3. Industry breakdown for California
print("\n" + "=" * 60)
print(">>> California: Top 10 industries by employment (2021):\n")
cur.execute("""
    SELECT naics_code, geo_name, employees, establishments
    FROM cbp_data
    WHERE vintage = 2021 
      AND geo_level = 'state'
      AND state_fips = '06'
      AND LENGTH(naics_code) = 2
      AND naics_code != '00'
    ORDER BY employees DESC
    LIMIT 10
""")
# NAICS sector codes
naics_labels = {
    '11': 'Agriculture', '21': 'Mining', '22': 'Utilities',
    '23': 'Construction', '31': 'Manufacturing', '32': 'Manufacturing',
    '33': 'Manufacturing', '42': 'Wholesale Trade', '44': 'Retail Trade',
    '45': 'Retail Trade', '48': 'Transportation', '49': 'Warehousing',
    '51': 'Information', '52': 'Finance/Insurance', '53': 'Real Estate',
    '54': 'Professional Services', '55': 'Management', '56': 'Admin/Support',
    '61': 'Education', '62': 'Health Care', '71': 'Arts/Entertainment',
    '72': 'Accommodation/Food', '81': 'Other Services', '99': 'Unclassified'
}
print(f"  {'NAICS':<8} {'Sector':<25} {'Employees':>12} {'Establishments':>15}")
print("  " + "-" * 60)
for row in cur.fetchall():
    label = naics_labels.get(row[0], 'Unknown')
    print(f"  {row[0]:<8} {label:<25} {row[2]:>12,} {row[3]:>15,}")

# 4. County comparison
print("\n" + "=" * 60)
print(">>> Texas: Top 10 counties by establishments (2021):\n")
cur.execute("""
    SELECT geo_name, establishments, employees, annual_payroll
    FROM cbp_data
    WHERE vintage = 2021 
      AND geo_level = 'county'
      AND state_fips = '48'
      AND naics_code = '00'
    ORDER BY establishments DESC
    LIMIT 10
""")
print(f"  {'County':<35} {'Estab':>10} {'Employees':>12} {'Payroll ($M)':>15}")
print("  " + "-" * 72)
for row in cur.fetchall():
    payroll_m = row[3] / 1000 if row[3] else 0
    print(f"  {row[0]:<35} {row[1]:>10,} {row[2]:>12,} {payroll_m:>15,.0f}")

# 5. Year-over-year comparison
print("\n" + "=" * 60)
print(">>> National employment trend (all industries):\n")
cur.execute("""
    SELECT vintage, 
           SUM(employees) as total_emp,
           SUM(establishments) as total_estab
    FROM cbp_data
    WHERE geo_level = 'state' AND naics_code = '00'
    GROUP BY vintage
    ORDER BY vintage
""")
print(f"  {'Year':<8} {'Total Employees':>18} {'Total Establishments':>22}")
print("  " + "-" * 48)
for row in cur.fetchall():
    print(f"  {row[0]:<8} {row[1]:>18,} {row[2]:>22,}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("Data verification complete!")
print("=" * 60)