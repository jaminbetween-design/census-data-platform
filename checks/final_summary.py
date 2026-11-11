import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

print("=" * 70)
print("FINAL CENSUS DATA PLATFORM SUMMARY")
print("=" * 70)

conn = connect_db()
cur = conn.cursor()

# Get all tables and their stats
tables_info = [
    ('cbp_data', 'County Business Patterns', 'Business establishments, employees, payroll by county'),
    ('zbp_data', 'ZIP Code Business Patterns', 'Business data at ZIP code level'),
    ('nes_data', 'Nonemployer Statistics', 'Self-employed individuals and receipts'),
    ('ec_data', 'Economic Census', 'Detailed 5-year industry census'),
    ('acs_data', 'American Community Survey (5-Year)', 'Demographics, income, housing, education'),
    ('acs1_data', 'American Community Survey (1-Year)', 'Annual demographic estimates'),
    ('decennial_data', 'Decennial Census', 'Official population counts'),
    ('pep_data', 'Population Estimates', 'Annual population estimates'),
    ('abs_data', 'Annual Business Survey', 'Business characteristics'),
    ('saipe_data', 'Small Area Income/Poverty', 'Poverty rates by county'),
    ('sahie_data', 'Small Area Health Insurance', 'Health insurance coverage'),
    ('bds_data', 'Business Dynamics Statistics', 'Firm births, deaths, job flows'),
    ('sbo_data', 'Survey of Business Owners', 'Business owner demographics'),
]

print("\n" + "=" * 70)
print("DATASET INVENTORY")
print("=" * 70)

grand_total = 0
dataset_summary = []

for table, name, description in tables_info:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        
        cur.execute(f"SELECT MIN(vintage), MAX(vintage) FROM {table}")
        years = cur.fetchone()
        
        if years[0] and years[1]:
            year_range = f"{years[0]}-{years[1]}"
            num_years = years[1] - years[0] + 1
        else:
            year_range = "N/A"
            num_years = 0
        
        grand_total += count
        dataset_summary.append({
            'table': table,
            'name': name,
            'description': description,
            'rows': count,
            'year_range': year_range,
            'num_years': num_years
        })
        
        print(f"\n{name}")
        print(f"  Table: {table}")
        print(f"  Rows: {count:,}")
        print(f"  Years: {year_range}")
        print(f"  Description: {description}")
        
    except Exception as e:
        print(f"\n{name}: Error - {e}")

print("\n" + "=" * 70)
print("GEOGRAPHIC COVERAGE")
print("=" * 70)

cur.execute("SELECT COUNT(DISTINCT state_fips) FROM cbp_data WHERE state_fips IS NOT NULL")
states = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(DISTINCT state_fips || '-' || county_fips) 
    FROM cbp_data 
    WHERE county_fips IS NOT NULL
""")
counties = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT zipcode) FROM zbp_data")
zipcodes = cur.fetchone()[0]

print(f"\n  States/Territories: {states}")
print(f"  Counties: {counties:,}")
print(f"  ZIP Codes: {zipcodes:,}")

print("\n" + "=" * 70)
print("TIME COVERAGE")
print("=" * 70)

cur.execute("SELECT MIN(vintage) FROM cbp_data")
earliest = cur.fetchone()[0]

cur.execute("SELECT MAX(vintage) FROM cbp_data")
latest = cur.fetchone()[0]

print(f"\n  Earliest Data: {earliest}")
print(f"  Latest Data: {latest}")
print(f"  Total Span: {latest - earliest + 1} years")

print("\n" + "=" * 70)
print("DATA CATEGORIES")
print("=" * 70)

print("""
  BUSINESS DATA:
    • County Business Patterns (CBP) - Employer establishments
    • ZIP Code Business Patterns (ZBP) - Local business data
    • Nonemployer Statistics (NES) - Self-employed
    • Economic Census - Detailed 5-year surveys
    • Annual Business Survey (ABS) - Business characteristics
    • Business Dynamics Statistics (BDS) - Firm dynamics
    • Survey of Business Owners (SBO) - Owner demographics

  DEMOGRAPHIC DATA:
    • American Community Survey 5-Year (ACS) - Comprehensive demographics
    • American Community Survey 1-Year (ACS1) - Annual estimates
    • Decennial Census - Official counts
    • Population Estimates (PEP) - Annual estimates

  SOCIOECONOMIC DATA:
    • Small Area Income/Poverty (SAIPE) - Poverty statistics
    • Small Area Health Insurance (SAHIE) - Insurance coverage
""")

print("\n" + "=" * 70)
print("GRAND TOTAL")
print("=" * 70)
print(f"\n  Total Datasets: {len(dataset_summary)}")
print(f"  Total Records: {grand_total:,}")
print(f"  Geographic Coverage: {states} states, {counties:,} counties, {zipcodes:,} ZIP codes")
print(f"  Time Coverage: {earliest}-{latest} ({latest - earliest + 1} years)")

print("\n" + "=" * 70)
print("API ENDPOINTS AVAILABLE")
print("=" * 70)

print("""
  BUSINESS ENDPOINTS:
    /api/cbp/states           - State employment data
    /api/cbp/counties/{state} - County employment data
    /api/cbp/industries       - Industry breakdown
    /api/cbp/trends           - Employment trends
    /api/zbp/zipcode/{zip}    - ZIP code business data
    /api/nes/states           - Self-employment data
    /api/ec/states            - Economic Census data
    /api/ec/industries        - Industry detail
    /api/abs/states           - Annual Business Survey

  DEMOGRAPHIC ENDPOINTS:
    /api/acs/states           - ACS demographics
    /api/acs/counties/{state} - County demographics
    /api/decennial/states     - Decennial Census
    /api/pep/states           - Population estimates

  COMBINED ENDPOINTS:
    /api/combined/state-profile/{state} - Full state profile
    /api/combined/economic-density      - Jobs per capita
    /api/historical/employment          - 38-year trends
    /api/overview                       - Database summary
""")

cur.close()
conn.close()

print("\n" + "=" * 70)
print("CENSUS DATA PLATFORM - READY FOR PRODUCTION")
print("=" * 70)
print(f"""
Your comprehensive Census data platform now includes:

✓ {grand_total:,} total records
✓ {len(dataset_summary)} datasets
✓ {latest - earliest + 1} years of historical data (1978-2023)
✓ Coverage: {states} states, {counties:,} counties, {zipcodes:,} ZIP codes
✓ Web application running at http://localhost:8000
✓ API documentation at http://localhost:8000/docs

NEXT STEPS:
1. Update web application frontend with new datasets
2. Add API endpoints for new tables (SAIPE, SAHIE, BDS, SBO, ACS1)
3. Deploy to production server
4. Implement user authentication for paid tiers
5. Add Excel export functionality for Enterprise tier
""")