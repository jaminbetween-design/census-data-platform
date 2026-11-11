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
        return int(float(str(value).replace(',', '')))
    except (ValueError, TypeError, AttributeError):
        return None

print("=" * 60)
print("FIXING BDS AND ADDING MORE DATASETS")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# 1. FIX BUSINESS DYNAMICS STATISTICS (BDS)
# =============================================================================
print("\n>>> Exploring BDS API structure...")

# Check variables
var_url = "https://api.census.gov/data/timeseries/bds/variables.json"
response = requests.get(var_url)
if response.status_code == 200:
    variables = response.json().get('variables', {})
    print(f"BDS variables: {len(variables)}")
    print("Key variables:")
    for var_name, var_info in list(variables.items())[:20]:
        print(f"  {var_name}: {var_info.get('label', '')}")

# Test different query formats
print("\n>>> Testing BDS queries...")
test_urls = [
    f"https://api.census.gov/data/timeseries/bds?get=NAME,YEAR,FIRM,ESTAB,EMP&for=nation:*&YEAR=2021&key={API_KEY}",
    f"https://api.census.gov/data/timeseries/bds?get=YEAR,FIRM,ESTAB,EMP&for=us:*&YEAR=2021&key={API_KEY}",
    f"https://api.census.gov/data/timeseries/bds/firms?get=YEAR,FIRMS,ESTABS,EMP&for=us:*&YEAR=2021&key={API_KEY}",
]

for url in test_urls:
    print(f"\nTesting: {url[:70]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"  Headers: {data[0]}")
            if len(data) > 1:
                print(f"  Sample: {data[1]}")
                print(f"  Rows: {len(data) - 1}")
        except Exception as e:
            print(f"  Error: {e}")
            print(f"  Response: {response.text[:200]}")
    time.sleep(1)

# Try the firms endpoint
print("\n>>> Trying BDS firms endpoint...")
firms_url = f"https://api.census.gov/data/timeseries/bds/firms?get=YEAR,FIRMS,ESTABS,EMP,DENOM,FIRMDEATH_FIRMS,ESTABS_ENTRY,ESTABS_EXIT,JOB_CREATION,JOB_DESTRUCTION&for=state:*&YEAR=2021&key={API_KEY}"
response = requests.get(firms_url, timeout=60)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Sample: {data[1] if len(data) > 1 else 'No data'}")
        print(f"Rows: {len(data) - 1}")
        
        # If successful, ingest BDS data
        if len(data) > 1:
            print("\n>>> Ingesting BDS data...")
            
            # Clear existing
            cur.execute("DELETE FROM bds_data")
            
            bds_years = list(range(2021, 1977, -1))
            bds_total = 0
            
            for year in bds_years:
                url = f"https://api.census.gov/data/timeseries/bds/firms?get=YEAR,FIRMS,ESTABS,EMP,FIRMDEATH_FIRMS,JOB_CREATION,JOB_DESTRUCTION&for=state:*&YEAR={year}&key={API_KEY}"
                
                try:
                    resp = requests.get(url, timeout=60)
                    if resp.status_code == 200:
                        year_data = resp.json()
                        if len(year_data) > 1:
                            headers = year_data[0]
                            rows = year_data[1:]
                            col_map = {col: idx for idx, col in enumerate(headers)}
                            
                            for row in rows:
                                cur.execute("""
                                    INSERT INTO bds_data (vintage, geo_level, state_fips, firms, establishments, employees, firm_deaths, job_creation, job_destruction)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    year, 'state',
                                    row[col_map.get('state')],
                                    safe_int(row[col_map.get('FIRMS')]),
                                    safe_int(row[col_map.get('ESTABS')]),
                                    safe_int(row[col_map.get('EMP')]),
                                    safe_int(row[col_map.get('FIRMDEATH_FIRMS')]),
                                    safe_int(row[col_map.get('JOB_CREATION')]),
                                    safe_int(row[col_map.get('JOB_DESTRUCTION')])
                                ))
                            bds_total += len(rows)
                            print(f"  {year}: ✓ {len(rows)} rows")
                except Exception as e:
                    print(f"  {year}: ✗ {e}")
                
                time.sleep(0.5)
            
            print(f"\n✓ BDS total: {bds_total:,} rows")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Response: {response.text[:300]}")

# =============================================================================
# 2. COMMODITY FLOW SURVEY (CFS)
# =============================================================================
print("\n" + "=" * 60)
print("2. EXPLORING COMMODITY FLOW SURVEY (CFS)")
print("=" * 60)

cfs_url = f"https://api.census.gov/data/2017/cfs?get=NAICS2012,SCTG,SHIPMT_VALUE,SHIPMT_WGHT&for=state:*&key={API_KEY}"
print(f"Testing: {cfs_url[:70]}...")

response = requests.get(cfs_url, timeout=60)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        
        # Create and ingest CFS
        print("\n>>> Creating CFS table and ingesting...")
        
        cur.execute("DROP TABLE IF EXISTS cfs_data CASCADE;")
        cur.execute("""
            CREATE TABLE cfs_data (
                id SERIAL PRIMARY KEY,
                vintage INTEGER NOT NULL,
                state_fips VARCHAR(2),
                naics_code VARCHAR(10),
                commodity_code VARCHAR(10),
                shipment_value BIGINT,
                shipment_weight BIGINT,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("CREATE INDEX idx_cfs_vintage ON cfs_data(vintage);")
        cur.execute("CREATE INDEX idx_cfs_state ON cfs_data(state_fips);")
        
        cfs_years = [2017, 2012]
        cfs_total = 0
        
        for year in cfs_years:
            naics_field = 'NAICS2012' if year <= 2017 else 'NAICS2017'
            url = f"https://api.census.gov/data/{year}/cfs?get={naics_field},SCTG,SHIPMT_VALUE,SHIPMT_WGHT&for=state:*&key={API_KEY}"
            
            resp = requests.get(url, timeout=120)
            if resp.status_code == 200:
                year_data = resp.json()
                if len(year_data) > 1:
                    headers = year_data[0]
                    rows = year_data[1:]
                    col_map = {col: idx for idx, col in enumerate(headers)}
                    
                    for row in rows:
                        cur.execute("""
                            INSERT INTO cfs_data (vintage, state_fips, naics_code, commodity_code, shipment_value, shipment_weight)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            year,
                            row[col_map.get('state')],
                            row[col_map.get(naics_field)],
                            row[col_map.get('SCTG')],
                            safe_int(row[col_map.get('SHIPMT_VALUE')]),
                            safe_int(row[col_map.get('SHIPMT_WGHT')])
                        ))
                    cfs_total += len(rows)
                    print(f"  {year}: ✓ {len(rows):,} rows")
            
            time.sleep(2)
        
        print(f"\n✓ CFS total: {cfs_total:,} rows")
    except Exception as e:
        print(f"Error: {e}")

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("COMPLETE DATABASE SUMMARY")
print("=" * 60)

tables = [
    'cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 
    'ec_data', 'decennial_data', 'abs_data', 'saipe_data', 
    'sahie_data', 'bds_data', 'sbo_data', 'cfs_data'
]

grand_total = 0
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        grand_total += count
        
        cur.execute(f"SELECT MIN(vintage), MAX(vintage) FROM {table}")
        years = cur.fetchone()
        if years[0] and years[1]:
            year_str = f"{years[0]}-{years[1]}" if years[0] != years[1] else str(years[0])
        else:
            year_str = "N/A"
        
        print(f"  {table}: {count:,} rows ({year_str})")
    except Exception as e:
        print(f"  {table}: Not found or error")

print(f"  ----------------------------------------")
print(f"  TOTAL: {grand_total:,} rows")

cur.close()
conn.close()