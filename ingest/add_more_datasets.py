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
    except:
        return None

print("=" * 60)
print("ADDING BDS (National) + MORE DATASETS")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# 1. BDS - National Level Time Series
# =============================================================================
print("\n>>> Adding BDS National Time Series...")

cur.execute("DROP TABLE IF EXISTS bds_data CASCADE;")
cur.execute("""
    CREATE TABLE bds_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) DEFAULT 'national',
        firms INTEGER,
        establishments INTEGER,
        employees INTEGER,
        job_creation INTEGER,
        job_destruction INTEGER,
        net_job_creation INTEGER,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_bds_vintage ON bds_data(vintage);")

bds_total = 0
for year in range(2021, 1977, -1):
    url = f"https://api.census.gov/data/timeseries/bds?get=YEAR,FIRM,ESTAB,EMP,JOB_CREATION,JOB_DESTRUCTION,NET_JOB_CREATION&for=us:*&YEAR={year}&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                headers = data[0]
                row = data[1]
                col_map = {col: idx for idx, col in enumerate(headers)}
                
                cur.execute("""
                    INSERT INTO bds_data (vintage, firms, establishments, employees, job_creation, job_destruction, net_job_creation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    year,
                    safe_int(row[col_map.get('FIRM')]),
                    safe_int(row[col_map.get('ESTAB')]),
                    safe_int(row[col_map.get('EMP')]),
                    safe_int(row[col_map.get('JOB_CREATION')]),
                    safe_int(row[col_map.get('JOB_DESTRUCTION')]),
                    safe_int(row[col_map.get('NET_JOB_CREATION')])
                ))
                bds_total += 1
    except:
        pass
    
    time.sleep(0.3)

print(f"✓ BDS: {bds_total} years of national data")

# =============================================================================
# 2. INTERNATIONAL TRADE
# =============================================================================
print("\n>>> Exploring International Trade...")

trade_endpoints = [
    f"https://api.census.gov/data/timeseries/intltrade/exports/hs?get=CTY_CODE,CTY_NAME,ALL_VAL_MO,ALL_VAL_YR&COMM_LVL=HS2&time=2023-01&key={API_KEY}",
    f"https://api.census.gov/data/timeseries/intltrade/imports/hs?get=CTY_CODE,CTY_NAME,GEN_VAL_MO,GEN_VAL_YR&COMM_LVL=HS2&time=2023-01&key={API_KEY}",
]

for url in trade_endpoints:
    print(f"\nTesting: {url[:60]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"  Headers: {data[0]}")
            print(f"  Rows: {len(data) - 1}")
        except Exception as e:
            print(f"  Error: {e}")
    time.sleep(1)

# =============================================================================
# 3. ECONOMIC INDICATORS (EITS)
# =============================================================================
print("\n>>> Exploring Economic Indicators...")

eits_endpoints = [
    ('Retail Sales', f"https://api.census.gov/data/timeseries/eits/marts?get=data_type_code,time_slot_id,cell_value,error_data&time=2023&category_code=44X72&seasonally_adj=yes&key={API_KEY}"),
    ('Housing Starts', f"https://api.census.gov/data/timeseries/eits/resconst?get=data_type_code,time_slot_id,cell_value&time=2023&category_code=TOTAL&seasonally_adj=yes&key={API_KEY}"),
    ('Construction Spending', f"https://api.census.gov/data/timeseries/eits/vip?get=data_type_code,time_slot_id,cell_value&time=2023&category_code=TOTAL&seasonally_adj=yes&key={API_KEY}"),
]

for name, url in eits_endpoints:
    print(f"\nTesting {name}: {url[:50]}...")
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
    time.sleep(1)

# =============================================================================
# 4. ACS 1-YEAR ESTIMATES (larger geographies)
# =============================================================================
print("\n>>> Adding ACS 1-Year Estimates...")

cur.execute("DROP TABLE IF EXISTS acs1_data CASCADE;")
cur.execute("""
    CREATE TABLE acs1_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        geo_name VARCHAR(255),
        total_population INTEGER,
        median_household_income INTEGER,
        median_age NUMERIC(5,2),
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_acs1_vintage ON acs1_data(vintage);")
cur.execute("CREATE INDEX idx_acs1_state ON acs1_data(state_fips);")

acs1_total = 0
for year in range(2023, 2004, -1):
    if year == 2020:  # ACS 1-year not released in 2020 due to COVID
        continue
    
    url = f"https://api.census.gov/data/{year}/acs/acs1?get=NAME,B01001_001E,B19013_001E,B01002_001E&for=state:*&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                headers = data[0]
                rows = data[1:]
                col_map = {col: idx for idx, col in enumerate(headers)}
                
                for row in rows:
                    cur.execute("""
                        INSERT INTO acs1_data (vintage, geo_level, state_fips, geo_name, total_population, median_household_income, median_age)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        year, 'state',
                        row[col_map.get('state')],
                        row[col_map['NAME']],
                        safe_int(row[col_map.get('B01001_001E')]),
                        safe_int(row[col_map.get('B19013_001E')]),
                        safe_int(row[col_map.get('B01002_001E')])
                    ))
                acs1_total += len(rows)
                print(f"  {year}: ✓ {len(rows)} rows")
    except Exception as e:
        print(f"  {year}: ✗ {e}")
    
    time.sleep(0.5)

print(f"\n✓ ACS 1-Year: {acs1_total:,} rows")

# =============================================================================
# 5. BUILDING PERMITS
# =============================================================================
print("\n>>> Exploring Building Permits...")

bp_url = f"https://api.census.gov/data/timeseries/eits/bps?get=data_type_code,time_slot_id,cell_value&for=state:*&time=2023&category_code=TOTAL&seasonally_adj=no&key={API_KEY}"
print(f"Testing: {bp_url[:60]}...")

response = requests.get(bp_url, timeout=60)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        
        if len(data) > 1:
            print("\n>>> Creating Building Permits table...")
            
            cur.execute("DROP TABLE IF EXISTS building_permits_data CASCADE;")
            cur.execute("""
                CREATE TABLE building_permits_data (
                    id SERIAL PRIMARY KEY,
                    vintage INTEGER NOT NULL,
                    state_fips VARCHAR(2),
                    permits INTEGER,
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("CREATE INDEX idx_bp_vintage ON building_permits_data(vintage);")
            
            bp_total = 0
            for year in range(2023, 2000, -1):
                url = f"https://api.census.gov/data/timeseries/eits/bps?get=cell_value&for=state:*&time={year}&category_code=TOTAL&data_type_code=BPPRIV&seasonally_adj=no&key={API_KEY}"
                
                try:
                    resp = requests.get(url, timeout=60)
                    if resp.status_code == 200:
                        year_data = resp.json()
                        if len(year_data) > 1:
                            for row in year_data[1:]:
                                cur.execute("""
                                    INSERT INTO building_permits_data (vintage, state_fips, permits)
                                    VALUES (%s, %s, %s)
                                """, (year, row[-1] if len(row) > 1 else None, safe_int(row[0])))
                            bp_total += len(year_data) - 1
                            print(f"  {year}: ✓ {len(year_data)-1} rows")
                except:
                    pass
                
                time.sleep(0.3)
            
            print(f"\n✓ Building Permits: {bp_total:,} rows")
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
    'sahie_data', 'bds_data', 'sbo_data', 'acs1_data', 'building_permits_data'
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
        print(f"  {table}: Not found")

print(f"  ----------------------------------------")
print(f"  TOTAL: {grand_total:,} rows")

cur.close()
conn.close()