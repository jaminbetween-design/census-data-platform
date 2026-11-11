import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def safe_int(value):
    if value is None or value == '' or value == 'null' or value == 'N' or value == 'D' or value == 'S':
        return None
    try:
        return int(float(value.replace(',', '')))
    except (ValueError, TypeError, AttributeError):
        return None

def safe_float(value):
    if value is None or value == '' or value == 'null' or value == 'N' or value == 'D' or value == 'S':
        return None
    try:
        return float(value.replace(',', ''))
    except (ValueError, TypeError, AttributeError):
        return None

print("=" * 60)
print("ADDING NEW DATASETS TO MASTER DATABASE")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# 1. SMALL AREA INCOME AND POVERTY ESTIMATES (SAIPE)
# =============================================================================
print("\n" + "=" * 60)
print("1. SMALL AREA INCOME AND POVERTY ESTIMATES (SAIPE)")
print("=" * 60)

# Create table
cur.execute("DROP TABLE IF EXISTS saipe_data CASCADE;")
cur.execute("""
    CREATE TABLE saipe_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        county_fips VARCHAR(3),
        geo_name VARCHAR(255),
        poverty_count INTEGER,
        poverty_rate NUMERIC(5,2),
        median_household_income INTEGER,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_saipe_vintage ON saipe_data(vintage);")
cur.execute("CREATE INDEX idx_saipe_state ON saipe_data(state_fips);")
print("✓ Created saipe_data table")

# Ingest data for multiple years
saipe_years = list(range(2022, 1999, -1))
saipe_total = 0

for year in saipe_years:
    # State level
    state_url = f"https://api.census.gov/data/timeseries/poverty/saipe?get=NAME,SAEPOVALL_PT,SAEPOVRTALL_PT,SAEMHI_PT&for=state:*&YEAR={year}&key={API_KEY}"
    
    try:
        response = requests.get(state_url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            headers = data[0]
            rows = data[1:]
            col_map = {col: idx for idx, col in enumerate(headers)}
            
            for row in rows:
                cur.execute("""
                    INSERT INTO saipe_data (vintage, geo_level, state_fips, geo_name, poverty_count, poverty_rate, median_household_income)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    year, 'state',
                    row[col_map.get('state')],
                    row[col_map['NAME']],
                    safe_int(row[col_map.get('SAEPOVALL_PT')]),
                    safe_float(row[col_map.get('SAEPOVRTALL_PT')]),
                    safe_int(row[col_map.get('SAEMHI_PT')])
                ))
            saipe_total += len(rows)
            
            # County level
            county_url = f"https://api.census.gov/data/timeseries/poverty/saipe?get=NAME,SAEPOVALL_PT,SAEPOVRTALL_PT,SAEMHI_PT&for=county:*&YEAR={year}&key={API_KEY}"
            county_response = requests.get(county_url, timeout=120)
            
            if county_response.status_code == 200:
                county_data = county_response.json()
                county_rows = county_data[1:]
                col_map = {col: idx for idx, col in enumerate(county_data[0])}
                
                for row in county_rows:
                    cur.execute("""
                        INSERT INTO saipe_data (vintage, geo_level, state_fips, county_fips, geo_name, poverty_count, poverty_rate, median_household_income)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        year, 'county',
                        row[col_map.get('state')],
                        row[col_map.get('county')],
                        row[col_map['NAME']],
                        safe_int(row[col_map.get('SAEPOVALL_PT')]),
                        safe_float(row[col_map.get('SAEPOVRTALL_PT')]),
                        safe_int(row[col_map.get('SAEMHI_PT')])
                    ))
                saipe_total += len(county_rows)
            
            print(f"  {year}: ✓ State + County data")
    except Exception as e:
        print(f"  {year}: ✗ Error - {e}")
    
    time.sleep(1)

print(f"\n✓ SAIPE total rows: {saipe_total:,}")

# =============================================================================
# 2. SMALL AREA HEALTH INSURANCE ESTIMATES (SAHIE)
# =============================================================================
print("\n" + "=" * 60)
print("2. SMALL AREA HEALTH INSURANCE ESTIMATES (SAHIE)")
print("=" * 60)

cur.execute("DROP TABLE IF EXISTS sahie_data CASCADE;")
cur.execute("""
    CREATE TABLE sahie_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        county_fips VARCHAR(3),
        geo_name VARCHAR(255),
        uninsured_count INTEGER,
        insured_count INTEGER,
        uninsured_rate NUMERIC(5,2),
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_sahie_vintage ON sahie_data(vintage);")
cur.execute("CREATE INDEX idx_sahie_state ON sahie_data(state_fips);")
print("✓ Created sahie_data table")

sahie_years = list(range(2022, 2005, -1))
sahie_total = 0

for year in sahie_years:
    state_url = f"https://api.census.gov/data/timeseries/healthins/sahie?get=NAME,NUI_PT,NIC_PT,PCTUI_PT&for=state:*&YEAR={year}&key={API_KEY}"
    
    try:
        response = requests.get(state_url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            headers = data[0]
            rows = data[1:]
            col_map = {col: idx for idx, col in enumerate(headers)}
            
            for row in rows:
                cur.execute("""
                    INSERT INTO sahie_data (vintage, geo_level, state_fips, geo_name, uninsured_count, insured_count, uninsured_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    year, 'state',
                    row[col_map.get('state')],
                    row[col_map['NAME']],
                    safe_int(row[col_map.get('NUI_PT')]),
                    safe_int(row[col_map.get('NIC_PT')]),
                    safe_float(row[col_map.get('PCTUI_PT')])
                ))
            sahie_total += len(rows)
            
            # County level
            county_url = f"https://api.census.gov/data/timeseries/healthins/sahie?get=NAME,NUI_PT,NIC_PT,PCTUI_PT&for=county:*&YEAR={year}&key={API_KEY}"
            county_response = requests.get(county_url, timeout=120)
            
            if county_response.status_code == 200:
                county_data = county_response.json()
                county_rows = county_data[1:]
                col_map = {col: idx for idx, col in enumerate(county_data[0])}
                
                for row in county_rows:
                    cur.execute("""
                        INSERT INTO sahie_data (vintage, geo_level, state_fips, county_fips, geo_name, uninsured_count, insured_count, uninsured_rate)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        year, 'county',
                        row[col_map.get('state')],
                        row[col_map.get('county')],
                        row[col_map['NAME']],
                        safe_int(row[col_map.get('NUI_PT')]),
                        safe_int(row[col_map.get('NIC_PT')]),
                        safe_float(row[col_map.get('PCTUI_PT')])
                    ))
                sahie_total += len(county_rows)
            
            print(f"  {year}: ✓ State + County data")
    except Exception as e:
        print(f"  {year}: ✗ Error - {e}")
    
    time.sleep(1)

print(f"\n✓ SAHIE total rows: {sahie_total:,}")

# =============================================================================
# 3. BUSINESS DYNAMICS STATISTICS (BDS)
# =============================================================================
print("\n" + "=" * 60)
print("3. BUSINESS DYNAMICS STATISTICS (BDS)")
print("=" * 60)

cur.execute("DROP TABLE IF EXISTS bds_data CASCADE;")
cur.execute("""
    CREATE TABLE bds_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        geo_name VARCHAR(255),
        firms INTEGER,
        establishments INTEGER,
        employees INTEGER,
        firm_births INTEGER,
        firm_deaths INTEGER,
        job_creation INTEGER,
        job_destruction INTEGER,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_bds_vintage ON bds_data(vintage);")
cur.execute("CREATE INDEX idx_bds_state ON bds_data(state_fips);")
print("✓ Created bds_data table")

bds_years = list(range(2021, 1977, -1))
bds_total = 0

for year in bds_years:
    url = f"https://api.census.gov/data/timeseries/bds?get=NAME,FIRM,ESTAB,EMP,FIRMDEATH_FIRM,FIRMDEATH_EMP&for=state:*&YEAR={year}&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            headers = data[0]
            rows = data[1:]
            col_map = {col: idx for idx, col in enumerate(headers)}
            
            for row in rows:
                cur.execute("""
                    INSERT INTO bds_data (vintage, geo_level, state_fips, geo_name, firms, establishments, employees, firm_deaths, job_destruction)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    year, 'state',
                    row[col_map.get('state')],
                    row[col_map['NAME']],
                    safe_int(row[col_map.get('FIRM')]),
                    safe_int(row[col_map.get('ESTAB')]),
                    safe_int(row[col_map.get('EMP')]),
                    safe_int(row[col_map.get('FIRMDEATH_FIRM')]),
                    safe_int(row[col_map.get('FIRMDEATH_EMP')])
                ))
            bds_total += len(rows)
            print(f"  {year}: ✓ {len(rows)} rows")
    except Exception as e:
        print(f"  {year}: ✗ Error - {e}")
    
    time.sleep(0.5)

print(f"\n✓ BDS total rows: {bds_total:,}")

# =============================================================================
# 4. SURVEY OF BUSINESS OWNERS (SBO) - 2012
# =============================================================================
print("\n" + "=" * 60)
print("4. SURVEY OF BUSINESS OWNERS (SBO)")
print("=" * 60)

cur.execute("DROP TABLE IF EXISTS sbo_data CASCADE;")
cur.execute("""
    CREATE TABLE sbo_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        geo_name VARCHAR(255),
        naics_code VARCHAR(10),
        firms INTEGER,
        receipts BIGINT,
        employees INTEGER,
        payroll BIGINT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_sbo_vintage ON sbo_data(vintage);")
cur.execute("CREATE INDEX idx_sbo_state ON sbo_data(state_fips);")
print("✓ Created sbo_data table")

sbo_url = f"https://api.census.gov/data/2012/sbo/cs?get=NAME,NAICS2012,FIRMPDEMP,RCPPDEMP,EMP,PAYANN&for=state:*&key={API_KEY}"

try:
    response = requests.get(sbo_url, timeout=120)
    if response.status_code == 200:
        data = response.json()
        headers = data[0]
        rows = data[1:]
        col_map = {col: idx for idx, col in enumerate(headers)}
        
        sbo_total = 0
        for row in rows:
            cur.execute("""
                INSERT INTO sbo_data (vintage, geo_level, state_fips, geo_name, naics_code, firms, receipts, employees, payroll)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                2012, 'state',
                row[col_map.get('state')],
                row[col_map['NAME']],
                row[col_map.get('NAICS2012')],
                safe_int(row[col_map.get('FIRMPDEMP')]),
                safe_int(row[col_map.get('RCPPDEMP')]),
                safe_int(row[col_map.get('EMP')]),
                safe_int(row[col_map.get('PAYANN')])
            ))
            sbo_total += 1
        
        print(f"  2012: ✓ {sbo_total:,} rows")
except Exception as e:
    print(f"  Error: {e}")
    sbo_total = 0

print(f"\n✓ SBO total rows: {sbo_total:,}")

# =============================================================================
# UPDATE METADATA
# =============================================================================
print("\n" + "=" * 60)
print("UPDATING METADATA")
print("=" * 60)

metadata_updates = [
    ('saipe', 'https://api.census.gov/data/timeseries/poverty/saipe', 'Small Area Income and Poverty Estimates'),
    ('sahie', 'https://api.census.gov/data/timeseries/healthins/sahie', 'Small Area Health Insurance Estimates'),
    ('bds', 'https://api.census.gov/data/timeseries/bds', 'Business Dynamics Statistics'),
    ('sbo', 'https://api.census.gov/data/2012/sbo', 'Survey of Business Owners'),
]

for dataset, endpoint, desc in metadata_updates:
    cur.execute(f"SELECT MIN(vintage), MAX(vintage), COUNT(*) FROM {dataset}_data")
    result = cur.fetchone()
    if result and result[2] > 0:
        cur.execute("""
            INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (dataset_name, vintage) 
            DO UPDATE SET row_count = EXCLUDED.row_count, ingested_at = CURRENT_TIMESTAMP
        """, (dataset, result[1], endpoint, desc, result[2]))
        print(f"  ✓ {dataset}: {result[0]}-{result[1]}, {result[2]:,} rows")

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("COMPLETE DATABASE SUMMARY")
print("=" * 60)

tables = [
    'cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 
    'ec_data', 'decennial_data', 'abs_data', 'saipe_data', 
    'sahie_data', 'bds_data', 'sbo_data'
]

grand_total = 0
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        grand_total += count
        
        cur.execute(f"SELECT MIN(vintage), MAX(vintage) FROM {table}")
        years = cur.fetchone()
        year_str = f"{years[0]}-{years[1]}" if years[0] != years[1] else str(years[0])
        
        print(f"  {table}: {count:,} rows ({year_str})")
    except Exception as e:
        print(f"  {table}: Error - {e}")

print(f"  ----------------------------------------")
print(f"  TOTAL: {grand_total:,} rows")

cur.close()
conn.close()

print("\n✓ All new datasets added successfully!")