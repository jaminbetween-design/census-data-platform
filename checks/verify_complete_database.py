import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def main():
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 70)
    print("CENSUS DATA PLATFORM - COMPREHENSIVE DATA VERIFICATION")
    print("=" * 70)
    
    # =========================================================================
    # SECTION 1: DATABASE OVERVIEW
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 1: DATABASE OVERVIEW")
    print("=" * 70)
    
    # Total rows by dataset
    print("\n>>> Total Rows by Dataset:\n")
    datasets = [
        ('cbp_data', 'County Business Patterns'),
        ('zbp_data', 'ZIP Code Business Patterns'),
        ('nes_data', 'Nonemployer Statistics'),
        ('acs_data', 'American Community Survey')
    ]
    
    total_rows = 0
    for table, name in datasets:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        total_rows += count
        print(f"  {name:<35} {count:>15,} rows")
    
    print(f"  {'-' * 50}")
    print(f"  {'TOTAL':<35} {total_rows:>15,} rows")
    
    # Year coverage by dataset
    print("\n>>> Year Coverage by Dataset:\n")
    for table, name in datasets:
        cur.execute(f"SELECT MIN(vintage), MAX(vintage), COUNT(DISTINCT vintage) FROM {table}")
        min_yr, max_yr, num_yrs = cur.fetchone()
        print(f"  {name:<35} {min_yr}-{max_yr} ({num_yrs} years)")
    
    # Geographic coverage
    print("\n>>> Geographic Coverage:\n")
    
    cur.execute("SELECT COUNT(DISTINCT state_fips) FROM cbp_data WHERE state_fips IS NOT NULL")
    states = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT county_fips || state_fips) FROM cbp_data WHERE county_fips IS NOT NULL")
    counties = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT zipcode) FROM zbp_data")
    zipcodes = cur.fetchone()[0]
    
    print(f"  States/Territories: {states}")
    print(f"  Counties: {counties:,}")
    print(f"  ZIP Codes: {zipcodes:,}")
    
    # =========================================================================
    # SECTION 2: COUNTY BUSINESS PATTERNS (CBP) ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 2: COUNTY BUSINESS PATTERNS (Employers)")
    print("=" * 70)
    
    # National employment trend
    print("\n>>> National Employment Trend (All Industries):\n")
    cur.execute("""
        SELECT vintage, 
               SUM(employees) as total_emp,
               SUM(establishments) as total_estab,
               SUM(annual_payroll) as total_payroll
        FROM cbp_data
        WHERE geo_level = 'state' AND naics_code = '00'
        GROUP BY vintage
        ORDER BY vintage
    """)
    
    print(f"  {'Year':<8} {'Employees':>15} {'Establishments':>15} {'Payroll ($B)':>15}")
    print(f"  {'-' * 53}")
    
    results = cur.fetchall()
    for row in results:
        payroll_b = row[3] / 1000000 if row[3] else 0
        print(f"  {row[0]:<8} {row[1]:>15,} {row[2]:>15,} {payroll_b:>15,.1f}")
    
    # Calculate growth
    if len(results) >= 2:
        first_emp = results[0][1]
        last_emp = results[-1][1]
        growth = ((last_emp - first_emp) / first_emp) * 100
        print(f"\n  Employment growth {results[0][0]}-{results[-1][0]}: {growth:+.1f}%")
    
    # Top 10 states by employment (most recent year)
    print("\n>>> Top 10 States by Employment (2023):\n")
    cur.execute("""
        SELECT geo_name, employees, establishments, annual_payroll
        FROM cbp_data
        WHERE vintage = 2023 AND geo_level = 'state' AND naics_code = '00'
        ORDER BY employees DESC
        LIMIT 10
    """)
    
    print(f"  {'State':<25} {'Employees':>15} {'Establishments':>15} {'Avg Wage ($)':>12}")
    print(f"  {'-' * 67}")
    for row in cur.fetchall():
        avg_wage = (row[3] * 1000 / row[1]) if row[1] else 0
        print(f"  {row[0]:<25} {row[1]:>15,} {row[2]:>15,} {avg_wage:>12,.0f}")
    
    # Top industries nationally
    print("\n>>> Top 10 Industries by Employment (2023, National):\n")
    cur.execute("""
        SELECT naics_code, SUM(employees) as emp, SUM(establishments) as estab
        FROM cbp_data
        WHERE vintage = 2023 AND geo_level = 'state' 
          AND LENGTH(naics_code) = 2 AND naics_code != '00'
        GROUP BY naics_code
        ORDER BY emp DESC
        LIMIT 10
    """)
    
    naics_labels = {
        '11': 'Agriculture', '21': 'Mining', '22': 'Utilities',
        '23': 'Construction', '31': 'Manufacturing', '32': 'Manufacturing',
        '33': 'Manufacturing', '42': 'Wholesale Trade', '44': 'Retail Trade',
        '45': 'Retail Trade', '48': 'Transportation', '49': 'Warehousing',
        '51': 'Information', '52': 'Finance/Insurance', '53': 'Real Estate',
        '54': 'Professional Svcs', '55': 'Management', '56': 'Admin/Support',
        '61': 'Education', '62': 'Health Care', '71': 'Arts/Entertainment',
        '72': 'Accommodation/Food', '81': 'Other Services', '99': 'Unclassified'
    }
    
    print(f"  {'NAICS':<8} {'Industry':<25} {'Employees':>15} {'Establishments':>15}")
    print(f"  {'-' * 63}")
    for row in cur.fetchall():
        label = naics_labels.get(row[0], 'Unknown')
        print(f"  {row[0]:<8} {label:<25} {row[1]:>15,} {row[2]:>15,}")
    
    # =========================================================================
    # SECTION 3: ZIP CODE BUSINESS PATTERNS ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 3: ZIP CODE BUSINESS PATTERNS")
    print("=" * 70)
    
    # ZIP code coverage
    print("\n>>> ZIP Code Coverage by Year:\n")
    cur.execute("""
        SELECT vintage, COUNT(DISTINCT zipcode) as zip_count, SUM(establishments) as total_estab
        FROM zbp_data
        WHERE naics_code = '00'
        GROUP BY vintage
        ORDER BY vintage DESC
    """)
    
    print(f"  {'Year':<8} {'ZIP Codes':>12} {'Establishments':>18}")
    print(f"  {'-' * 38}")
    for row in cur.fetchall():
        print(f"  {row[0]:<8} {row[1]:>12,} {row[2]:>18,}")
    
    # Top ZIP codes by establishments
    print("\n>>> Top 10 ZIP Codes by Establishments (2023):\n")
    cur.execute("""
        SELECT zipcode, establishments, employees, annual_payroll
        FROM zbp_data
        WHERE vintage = 2023 AND naics_code = '00'
        ORDER BY establishments DESC
        LIMIT 10
    """)
    
    print(f"  {'ZIP Code':<12} {'Establishments':>15} {'Employees':>15} {'Payroll ($M)':>15}")
    print(f"  {'-' * 57}")
    for row in cur.fetchall():
        payroll_m = row[3] / 1000 if row[3] else 0
        emp = row[2] if row[2] else 0
        print(f"  {row[0]:<12} {row[1]:>15,} {emp:>15,} {payroll_m:>15,.1f}")
    
    # =========================================================================
    # SECTION 4: NONEMPLOYER STATISTICS ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 4: NONEMPLOYER STATISTICS (Self-Employed)")
    print("=" * 70)
    
    # National trend
    print("\n>>> National Self-Employment Trend:\n")
    cur.execute("""
        SELECT vintage, 
               SUM(establishments) as total_estab,
               SUM(receipts) as total_receipts
        FROM nes_data
        WHERE geo_level = 'state' AND naics_code = '00'
        GROUP BY vintage
        ORDER BY vintage
    """)
    
    print(f"  {'Year':<8} {'Self-Employed':>18} {'Receipts ($B)':>18}")
    print(f"  {'-' * 44}")
    for row in cur.fetchall():
        receipts_b = row[2] / 1000000 if row[2] else 0
        print(f"  {row[0]:<8} {row[1]:>18,} {receipts_b:>18,.1f}")
    
    # Top states for self-employment
    print("\n>>> Top 10 States by Self-Employment (2023):\n")
    cur.execute("""
        SELECT geo_name, establishments, receipts
        FROM nes_data
        WHERE vintage = 2023 AND geo_level = 'state' AND naics_code = '00'
        ORDER BY establishments DESC
        LIMIT 10
    """)
    
    print(f"  {'State':<25} {'Self-Employed':>15} {'Receipts ($B)':>15}")
    print(f"  {'-' * 55}")
    for row in cur.fetchall():
        receipts_b = row[2] / 1000000 if row[2] else 0
        print(f"  {row[0]:<25} {row[1]:>15,} {receipts_b:>15,.1f}")
    
    # =========================================================================
    # SECTION 5: DEMOGRAPHIC DATA (ACS) ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 5: DEMOGRAPHIC DATA (ACS)")
    print("=" * 70)
    
    # National population trend
    print("\n>>> National Population Trend:\n")
    cur.execute("""
        SELECT vintage, SUM(total_population) as pop
        FROM acs_data
        WHERE geo_level = 'state'
        GROUP BY vintage
        ORDER BY vintage
    """)
    
    print(f"  {'Year':<8} {'Population':>18}")
    print(f"  {'-' * 26}")
    for row in cur.fetchall():
        print(f"  {row[0]:<8} {row[1]:>18,}")
    
    # State demographics comparison (2023)
    print("\n>>> State Demographics Comparison (2023):\n")
    cur.execute("""
        SELECT geo_name, total_population, median_household_income, median_age
        FROM acs_data
        WHERE vintage = 2023 AND geo_level = 'state'
        ORDER BY total_population DESC
        LIMIT 10
    """)
    
    print(f"  {'State':<25} {'Population':>15} {'Med Income':>15} {'Med Age':>10}")
    print(f"  {'-' * 65}")
    for row in cur.fetchall():
        income = row[2] if row[2] else 0
        age = row[3] if row[3] else 0
        print(f"  {row[0]:<25} {row[1]:>15,} ${income:>14,} {age:>10.1f}")
    
    # =========================================================================
    # SECTION 6: COMBINED ANALYSES
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 6: COMBINED ANALYSES (Cross-Dataset)")
    print("=" * 70)
    
    # Total business activity (employers + self-employed)
    print("\n>>> Total Business Activity: Employers + Self-Employed (2021):\n")
    cur.execute("""
        SELECT 
            c.geo_name,
            c.establishments as employer_estab,
            c.employees,
            n.establishments as self_employed,
            c.establishments + n.establishments as total_business
        FROM cbp_data c
        JOIN nes_data n ON c.state_fips = n.state_fips 
                        AND c.vintage = n.vintage
                        AND c.geo_level = n.geo_level
        WHERE c.vintage = 2021 
          AND c.geo_level = 'state'
          AND c.naics_code = '00'
          AND n.naics_code = '00'
        ORDER BY total_business DESC
        LIMIT 10
    """)
    
    print(f"  {'State':<25} {'Employers':>12} {'Employees':>12} {'Self-Emp':>12} {'Total Biz':>12}")
    print(f"  {'-' * 73}")
    for row in cur.fetchall():
        print(f"  {row[0]:<25} {row[1]:>12,} {row[2]:>12,} {row[3]:>12,} {row[4]:>12,}")
    
    # Economic density (jobs + business per capita)
    print("\n>>> Economic Density by State (2022):\n")
    print("  (Employees + Self-Employed per 100 residents)\n")
    cur.execute("""
        SELECT 
            a.geo_name,
            a.total_population,
            c.employees,
            n.establishments as self_employed,
            ROUND(100.0 * (c.employees + n.establishments) / NULLIF(a.total_population, 0), 1) as economic_density
        FROM acs_data a
        JOIN cbp_data c ON a.state_fips = c.state_fips AND a.vintage = c.vintage
        JOIN nes_data n ON a.state_fips = n.state_fips AND a.vintage = n.vintage
        WHERE a.vintage = 2022
          AND a.geo_level = 'state'
          AND c.geo_level = 'state'
          AND n.geo_level = 'state'
          AND c.naics_code = '00'
          AND n.naics_code = '00'
        ORDER BY economic_density DESC
        LIMIT 10
    """)
    
    print(f"  {'State':<25} {'Population':>15} {'Employees':>12} {'Self-Emp':>12} {'Density':>10}")
    print(f"  {'-' * 74}")
    for row in cur.fetchall():
        print(f"  {row[0]:<25} {row[1]:>15,} {row[2]:>12,} {row[3]:>12,} {row[4]:>10}")
    
    # Income vs Business Activity correlation
    print("\n>>> High Income Counties: Business Characteristics (2022):\n")
    cur.execute("""
        SELECT 
            a.geo_name,
            a.median_household_income,
            c.establishments,
            c.employees,
            n.establishments as self_employed
        FROM acs_data a
        JOIN cbp_data c ON a.state_fips = c.state_fips 
                        AND a.county_fips = c.county_fips
                        AND a.vintage = c.vintage
        JOIN nes_data n ON a.state_fips = n.state_fips 
                        AND a.county_fips = n.county_fips
                        AND a.vintage = n.vintage
        WHERE a.vintage = 2022
          AND a.geo_level = 'county'
          AND c.geo_level = 'county'
          AND n.geo_level = 'county'
          AND c.naics_code = '00'
          AND n.naics_code = '00'
          AND a.median_household_income IS NOT NULL
        ORDER BY a.median_household_income DESC
        LIMIT 10
    """)
    
    print(f"  {'County':<40} {'Med Income':>12} {'Employers':>10} {'Self-Emp':>10}")
    print(f"  {'-' * 72}")
    for row in cur.fetchall():
        print(f"  {row[0]:<40} ${row[1]:>11,} {row[2]:>10,} {row[3]:>10,}")
    
    # =========================================================================
    # SECTION 7: DATA QUALITY CHECK
    # =========================================================================
    print("\n" + "=" * 70)
    print("SECTION 7: DATA QUALITY CHECK")
    print("=" * 70)
    
    # Check for nulls in key fields
    print("\n>>> Null Value Analysis:\n")
    
    cur.execute("SELECT COUNT(*) FROM cbp_data WHERE employees IS NULL")
    cbp_null_emp = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cbp_data")
    cbp_total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM acs_data WHERE total_population IS NULL")
    acs_null_pop = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM acs_data")
    acs_total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM nes_data WHERE establishments IS NULL")
    nes_null = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM nes_data")
    nes_total = cur.fetchone()[0]
    
    print(f"  CBP employees NULL: {cbp_null_emp:,} / {cbp_total:,} ({100*cbp_null_emp/cbp_total:.1f}%)")
    print(f"  ACS population NULL: {acs_null_pop:,} / {acs_total:,} ({100*acs_null_pop/acs_total:.1f}%)")
    print(f"  NES establishments NULL: {nes_null:,} / {nes_total:,} ({100*nes_null/nes_total:.1f}%)")
    
    # Record counts by vintage
    print("\n>>> Records by Vintage (All Datasets):\n")
    cur.execute("""
        SELECT 'CBP' as dataset, vintage, COUNT(*) as records FROM cbp_data GROUP BY vintage
        UNION ALL
        SELECT 'ZBP', vintage, COUNT(*) FROM zbp_data GROUP BY vintage
        UNION ALL
        SELECT 'NES', vintage, COUNT(*) FROM nes_data GROUP BY vintage
        UNION ALL
        SELECT 'ACS', vintage, COUNT(*) FROM acs_data GROUP BY vintage
        ORDER BY vintage DESC, dataset
    """)
    
    results = cur.fetchall()
    current_year = None
    print(f"  {'Year':<8} {'CBP':>15} {'ZBP':>15} {'NES':>15} {'ACS':>15}")
    print(f"  {'-' * 68}")
    
    # Reorganize for display
    year_data = {}
    for dataset, vintage, count in results:
        if vintage not in year_data:
            year_data[vintage] = {}
        year_data[vintage][dataset] = count
    
    for year in sorted(year_data.keys(), reverse=True):
        cbp = year_data[year].get('CBP', 0)
        zbp = year_data[year].get('ZBP', 0)
        nes = year_data[year].get('NES', 0)
        acs = year_data[year].get('ACS', 0)
        print(f"  {year:<8} {cbp:>15,} {zbp:>15,} {nes:>15,} {acs:>15,}")
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    print(f"""
    DATABASE READY FOR WEB APPLICATION
    
    Total Records: {total_rows:,}
    
    Datasets:
    • County Business Patterns (CBP): Employer establishments, employees, payroll
    • ZIP Code Business Patterns (ZBP): Business data at ZIP code level
    • Nonemployer Statistics (NES): Self-employed individuals and receipts
    • American Community Survey (ACS): Demographics, income, housing, education
    
    Geographic Coverage:
    • {states} States/Territories
    • {counties:,} Counties
    • {zipcodes:,} ZIP Codes
    
    Time Coverage: 2008-2023 (varies by dataset)
    
    Key Analysis Capabilities:
    • Employment trends by industry, geography, and time
    • Business establishment patterns at county and ZIP level
    • Self-employment and gig economy analysis
    • Demographic correlations with economic activity
    • Local market sizing and competitive analysis
    """)
    
    cur.close()
    conn.close()
    
    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()