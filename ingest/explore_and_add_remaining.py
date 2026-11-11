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

def safe_float(value):
    if value is None or value == '' or value == 'null' or value == 'N' or value == 'D' or value == 'S':
        return None
    try:
        return float(str(value).replace(',', ''))
    except:
        return None

print("=" * 70)
print("DEEP EXPLORATION AND INGESTION OF REMAINING DATASETS")
print("=" * 70)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# 1. ANNUAL SURVEY OF MANUFACTURES (ASM) - Explore variables first
# =============================================================================
print("\n" + "=" * 60)
print("1. ANNUAL SURVEY OF MANUFACTURES (ASM)")
print("=" * 60)

# Check ASM variables
print("\n>>> Exploring ASM endpoints...")
asm_endpoints = [
    "https://api.census.gov/data/timeseries/asm/state",
    "https://api.census.gov/data/timeseries/asm/industry", 
    "https://api.census.gov/data/timeseries/asm/area2017",
]

for endpoint in asm_endpoints:
    var_url = f"{endpoint}/variables.json"
    print(f"\nChecking {endpoint}...")
    response = requests.get(var_url, timeout=30)
    if response.status_code == 200:
        variables = response.json().get('variables', {})
        print(f"  Variables: {len(variables)}")
        # Show key variables
        for var_name in list(variables.keys())[:10]:
            label = variables[var_name].get('label', '')
            print(f"    {var_name}: {label[:50]}")
    time.sleep(0.5)

# Test ASM with correct variables
print("\n>>> Testing ASM queries...")
asm_tests = [
    f"https://api.census.gov/data/timeseries/asm/state?get=EMP,PAYANN,VALADD,YEAR&for=state:*&YEAR=2021&NAICS=31-33&key={API_KEY}",
    f"https://api.census.gov/data/timeseries/asm/state?get=EMP,PAYANN,YEAR&for=state:*&YEAR=2021&key={API_KEY}",
    f"https://api.census.gov/data/timeseries/asm/industry?get=EMP,PAYANN,NAICS,YEAR&for=us:*&YEAR=2021&key={API_KEY}",
]

for url in asm_tests:
    print(f"\nTesting: {url[:65]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                print(f"  ✓ Headers: {data[0]}")
                print(f"    Rows: {len(data) - 1}")
        except:
            print(f"  Response: {response.text[:150]}")
    else:
        print(f"  Error: {response.text[:100]}")
    time.sleep(1)

# =============================================================================
# 2. QUARTERLY WORKFORCE INDICATORS (QWI)
# =============================================================================
print("\n" + "=" * 60)
print("2. QUARTERLY WORKFORCE INDICATORS (QWI)")
print("=" * 60)

# Test QWI
qwi_url = f"https://api.census.gov/data/timeseries/qwi/sa?get=Emp,EarnS,EmpS&for=state:*&year=2022&quarter=1&key={API_KEY}"
print(f"\nTesting: {qwi_url[:65]}...")
response = requests.get(qwi_url, timeout=60)
print(f"  Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        if isinstance(data, list) and len(data) > 1:
            print(f"  ✓ Headers: {data[0]}")
            print(f"    Sample: {data[1]}")
            print(f"    Rows: {len(data) - 1}")
            
            # Create QWI table and ingest
            print("\n>>> Creating QWI table and ingesting data...")
            
            cur.execute("DROP TABLE IF EXISTS qwi_data CASCADE;")
            cur.execute("""
                CREATE TABLE qwi_data (
                    id SERIAL PRIMARY KEY,
                    year INTEGER NOT NULL,
                    quarter INTEGER NOT NULL,
                    state_fips VARCHAR(2),
                    employment INTEGER,
                    earnings INTEGER,
                    emp_stable INTEGER,
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("CREATE INDEX idx_qwi_year ON qwi_data(year);")
            cur.execute("CREATE INDEX idx_qwi_state ON qwi_data(state_fips);")
            
            qwi_total = 0
            
            # Get data for multiple years and quarters
            for year in range(2022, 2000, -1):
                for quarter in [1, 2, 3, 4]:
                    url = f"https://api.census.gov/data/timeseries/qwi/sa?get=Emp,EarnS,EmpS&for=state:*&year={year}&quarter={quarter}&key={API_KEY}"
                    
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
                                        INSERT INTO qwi_data (year, quarter, state_fips, employment, earnings, emp_stable)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """, (
                                        year, quarter,
                                        row[col_map.get('state')],
                                        safe_int(row[col_map.get('Emp')]),
                                        safe_int(row[col_map.get('EarnS')]),
                                        safe_int(row[col_map.get('EmpS')])
                                    ))
                                qwi_total += len(rows)
                    except:
                        pass
                    
                    time.sleep(0.2)
                
                if qwi_total > 0 and year % 5 == 0:
                    print(f"    {year}: {qwi_total:,} total rows so far")
                    conn.commit()
            
            print(f"\n  ✓ QWI total: {qwi_total:,} rows")
    except Exception as e:
        print(f"  Error: {e}")

# =============================================================================
# 3. GOVERNMENT FINANCES (GOVS)
# =============================================================================
print("\n" + "=" * 60)
print("3. GOVERNMENT FINANCES")
print("=" * 60)

govs_url = f"https://api.census.gov/data/timeseries/govs?get=NAME,AGG_DESC,AMOUNT&for=state:*&YEAR=2021&key={API_KEY}"
print(f"\nTesting: {govs_url[:65]}...")
response = requests.get(govs_url, timeout=60)
print(f"  Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        if isinstance(data, list) and len(data) > 1:
            print(f"  ✓ Headers: {data[0]}")
            print(f"    Sample: {data[1]}")
            print(f"    Rows: {len(data) - 1}")
    except Exception as e:
        print(f"  Parse error: {e}")

# =============================================================================
# 4. INTERNATIONAL TRADE
# =============================================================================
print("\n" + "=" * 60)
print("4. INTERNATIONAL TRADE")
print("=" * 60)

trade_tests = [
    f"https://api.census.gov/data/timeseries/intltrade/exports/hs?get=CTY_CODE,CTY_NAME,ALL_VAL_MO&COMM_LVL=TOTAL&time=2023-01&key={API_KEY}",
    f"https://api.census.gov/data/timeseries/intltrade/imports/hs?get=CTY_CODE,CTY_NAME,GEN_VAL_MO&COMM_LVL=TOTAL&time=2023-01&key={API_KEY}",
    f"https://api.census.gov/data/2017/intltrade/imp_exp?get=CTY_CODE,CTY_NAME,IYR,IVAL&for=state:*&key={API_KEY}",
]

for url in trade_tests:
    print(f"\nTesting: {url[:60]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                print(f"  ✓ Headers: {data[0]}")
                print(f"    Sample: {data[1]}")
                print(f"    Rows: {len(data) - 1}")
        except:
            print(f"  Response: {response.text[:100]}")
    time.sleep(1)

# =============================================================================
# 5. PUBLIC SCHOOL FINANCES
# =============================================================================
print("\n" + "=" * 60)
print("5. PUBLIC SCHOOL FINANCES")
print("=" * 60)

school_url = f"https://api.census.gov/data/2012/pubschlfin?get=NAME,TOTALREV,TFEDREV,TSTREV,TLOCREV&for=state:*&key={API_KEY}"
print(f"\nTesting: {school_url[:65]}...")
response = requests.get(school_url, timeout=60)
print(f"  Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        if isinstance(data, list) and len(data) > 1:
            print(f"  ✓ Headers: {data[0]}")
            print(f"    Sample: {data[1]}")
            print(f"    Rows: {len(data) - 1}")
    except Exception as e:
        print(f"  Error: {e}")

# =============================================================================
# 6. COMMODITY FLOW SURVEY
# =============================================================================
print("\n" + "=" * 60)
print("6. COMMODITY FLOW SURVEY (CFS)")
print("=" * 60)

cfs_tests = [
    f"https://api.census.gov/data/2017/cfs?get=NAICS2012_TTL,SHIPMT_VALUE,SHIPMT_WGHT&for=state:*&key={API_KEY}",
    f"https://api.census.gov/data/2012/cfs?get=NAICS2012_TTL,SHIPMT_VALUE&for=state:*&key={API_KEY}",
]

for url in cfs_tests:
    print(f"\nTesting: {url[:60]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                print(f"  ✓ Headers: {data[0]}")
                print(f"    Rows: {len(data) - 1}")
        except:
            print(f"  Response: {response.text[:100]}")
    time.sleep(1)

# =============================================================================
# 7. RENTAL HOUSING FINANCE SURVEY (RHFS)
# =============================================================================
print("\n" + "=" * 60)
print("7. RENTAL HOUSING FINANCE SURVEY")
print("=" * 60)

rhfs_url = f"https://api.census.gov/data/2021/rhfs?get=TOTUNITS,BUILT,TENURE&for=us:*&key={API_KEY}"
print(f"\nTesting: {rhfs_url[:65]}...")
response = requests.get(rhfs_url, timeout=60)
print(f"  Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        if isinstance(data, list) and len(data) > 1:
            print(f"  ✓ Headers: {data[0]}")
            print(f"    Sample: {data[1]}")
            print(f"    Rows: {len(data) - 1}")
    except Exception as e:
        print(f"  Error: {e}")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("COMPLETE DATABASE SUMMARY")
print("=" * 60)

tables = [
    'cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 
    'ec_data', 'decennial_data', 'abs_data', 'saipe_data', 
    'sahie_data', 'bds_data', 'sbo_data', 'acs1_data', 'cps_data', 'qwi_data'
]

grand_total = 0
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        grand_total += count
        print(f"  {table}: {count:,} rows")
    except:
        print(f"  {table}: Not found")

print(f"  ----------------------------------------")
print(f"  TOTAL: {grand_total:,} rows")

cur.close()
conn.close()