import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
cur = conn.cursor()

print("=" * 60)
print("ACS DATA VERIFICATION")
print("=" * 60)

# Row counts
print("\n>>> Row counts by vintage and geo level:\n")
cur.execute("""
    SELECT vintage, geo_level, COUNT(*) as rows
    FROM acs_data
    GROUP BY vintage, geo_level
    ORDER BY vintage DESC, geo_level
""")
for row in cur.fetchall():
    print(f"  {row[0]} {row[1]}: {row[2]:,}")

# Top 10 states by population (2022)
print("\n" + "=" * 60)
print(">>> Top 10 states by population (2022):\n")
cur.execute("""
    SELECT geo_name, total_population, median_household_income, median_age
    FROM acs_data
    WHERE vintage = 2022 AND geo_level = 'state'
    ORDER BY total_population DESC
    LIMIT 10
""")
print(f"  {'State':<25} {'Population':>15} {'Median Income':>15} {'Median Age':>12}")
print("  " + "-" * 67)
for row in cur.fetchall():
    print(f"  {row[0]:<25} {row[1]:>15,} ${row[2]:>14,} {row[3]:>12}")

# Wealthiest counties
print("\n" + "=" * 60)
print(">>> Top 10 counties by median household income (2022):\n")
cur.execute("""
    SELECT geo_name, median_household_income, median_home_value, total_population
    FROM acs_data
    WHERE vintage = 2022 AND geo_level = 'county' AND median_household_income IS NOT NULL
    ORDER BY median_household_income DESC
    LIMIT 10
""")
print(f"  {'County':<40} {'Med Income':>12} {'Home Value':>15} {'Population':>12}")
print("  " + "-" * 79)
for row in cur.fetchall():
    home_val = f"${row[2]:,}" if row[2] else "N/A"
    print(f"  {row[0]:<40} ${row[1]:>11,} {home_val:>15} {row[3]:>12,}")

# Education leaders
print("\n" + "=" * 60)
print(">>> Top 10 states by % population with Bachelor's+ (2022):\n")
cur.execute("""
    SELECT geo_name, 
           total_population,
           bachelors_degree + masters_degree + doctorate_degree as higher_ed,
           ROUND(100.0 * (bachelors_degree + masters_degree + doctorate_degree) / NULLIF(total_population, 0), 1) as pct
    FROM acs_data
    WHERE vintage = 2022 AND geo_level = 'state'
    ORDER BY pct DESC
    LIMIT 10
""")
print(f"  {'State':<30} {'Population':>15} {'Higher Ed':>12} {'%':>8}")
print("  " + "-" * 65)
for row in cur.fetchall():
    print(f"  {row[0]:<30} {row[1]:>15,} {row[2]:>12,} {row[3]:>8}%")

# Combined query: Business + Demographics
print("\n" + "=" * 60)
print(">>> COMBINED ANALYSIS: Top counties by jobs per capita (2022):\n")
cur.execute("""
    SELECT 
        a.geo_name,
        a.total_population,
        c.employees,
        ROUND(1.0 * c.employees / NULLIF(a.total_population, 0), 2) as jobs_per_capita,
        a.median_household_income
    FROM acs_data a
    JOIN cbp_data c ON a.state_fips = c.state_fips 
                    AND a.county_fips = c.county_fips
    WHERE a.vintage = 2022 
      AND c.vintage = 2022
      AND a.geo_level = 'county'
      AND c.geo_level = 'county'
      AND c.naics_code = '00'
      AND a.total_population > 50000
    ORDER BY jobs_per_capita DESC
    LIMIT 10
""")
print(f"  {'County':<35} {'Population':>12} {'Employees':>12} {'Jobs/Cap':>10} {'Med Income':>12}")
print("  " + "-" * 81)
for row in cur.fetchall():
    print(f"  {row[0]:<35} {row[1]:>12,} {row[2]:>12,} {row[3]:>10} ${row[4]:>11,}")

cur.close()
conn.close()

print("\n" + "=" * 60)
print("Verification complete!")
print("=" * 60)