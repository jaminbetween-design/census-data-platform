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
    if value is None or value == '' or value == 'null' or value == 'N' or value == 'D' or value == 'S' or value == '0':
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

print("=" * 60)
print("ADDING CPS BASIC MONTHLY + FIXING BDS")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# =============================================================================
# 1. FIX BDS - Add State Level Data
# =============================================================================
print("\n" + "=" * 60)
print("1. FIXING BDS - ADDING STATE LEVEL DATA")
print("=" * 60)

# Drop and recreate with better structure
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
        job_creation INTEGER,
        job_destruction INTEGER,
        net_job_creation INTEGER,
        firm_deaths INTEGER,
        estab_entries INTEGER,
        estab_exits INTEGER,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_bds_vintage ON bds_data(vintage);")
cur.execute("CREATE INDEX idx_bds_state ON bds_data(state_fips);")
print("✓ Created bds_data table")

# State name mapping
STATE_NAMES = {
    '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
    '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
    '11': 'District of Columbia', '12': 'Florida', '13': 'Georgia', '15': 'Hawaii',
    '16': 'Idaho', '17': 'Illinois', '18': 'Indiana', '19': 'Iowa',
    '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine',
    '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
    '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska',
    '32': 'Nevada', '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico',
    '36': 'New York', '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio',
    '40': 'Oklahoma', '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island',
    '45': 'South Carolina', '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas',
    '49': 'Utah', '50': 'Vermont', '51': 'Virginia', '53': 'Washington',
    '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming', '72': 'Puerto Rico'
}

bds_total = 0

# Get state-level data for each year
for year in range(2023, 1977, -1):
    # State level query
    url = f"https://api.census.gov/data/timeseries/bds?get=FIRM,ESTAB,EMP,JOB_CREATION,JOB_DESTRUCTION,NET_JOB_CREATION,FIRMDEATH_FIRM,ESTABS_ENTRY,ESTABS_EXIT&for=state:*&YEAR={year}&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                headers = data[0]
                rows = data[1:]
                col_map = {col: idx for idx, col in enumerate(headers)}
                
                for row in rows:
                    state_fips = row[col_map.get('state')]
                    cur.execute("""
                        INSERT INTO bds_data (vintage, geo_level, state_fips, geo_name, firms, establishments, employees, 
                                             job_creation, job_destruction, net_job_creation, firm_deaths, estab_entries, estab_exits)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        year, 'state', state_fips,
                        STATE_NAMES.get(state_fips, f"State {state_fips}"),
                        safe_int(row[col_map.get('FIRM')]),
                        safe_int(row[col_map.get('ESTAB')]),
                        safe_int(row[col_map.get('EMP')]),
                        safe_int(row[col_map.get('JOB_CREATION')]),
                        safe_int(row[col_map.get('JOB_DESTRUCTION')]),
                        safe_int(row[col_map.get('NET_JOB_CREATION')]),
                        safe_int(row[col_map.get('FIRMDEATH_FIRM')]),
                        safe_int(row[col_map.get('ESTABS_ENTRY')]),
                        safe_int(row[col_map.get('ESTABS_EXIT')])
                    ))
                bds_total += len(rows)
                print(f"  {year}: ✓ {len(rows)} state rows")
        else:
            print(f"  {year}: Status {response.status_code}")
    except Exception as e:
        print(f"  {year}: ✗ {e}")
    
    time.sleep(0.5)

# Also add national totals
print("\n  Adding national totals...")
for year in range(2023, 1977, -1):
    url = f"https://api.census.gov/data/timeseries/bds?get=FIRM,ESTAB,EMP,JOB_CREATION,JOB_DESTRUCTION,NET_JOB_CREATION&for=us:*&YEAR={year}&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                row = data[1]
                headers = data[0]
                col_map = {col: idx for idx, col in enumerate(headers)}
                
                cur.execute("""
                    INSERT INTO bds_data (vintage, geo_level, geo_name, firms, establishments, employees, 
                                         job_creation, job_destruction, net_job_creation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    year, 'national', 'United States',
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

print(f"\n✓ BDS total: {bds_total:,} rows")

# =============================================================================
# 2. CPS BASIC MONTHLY
# =============================================================================
print("\n" + "=" * 60)
print("2. CURRENT POPULATION SURVEY (CPS) BASIC MONTHLY")
print("=" * 60)

# Create CPS table
cur.execute("DROP TABLE IF EXISTS cps_data CASCADE;")
cur.execute("""
    CREATE TABLE cps_data (
        id SERIAL PRIMARY KEY,
        year INTEGER NOT NULL,
        month VARCHAR(3) NOT NULL,
        state_fips VARCHAR(2),
        geo_name VARCHAR(255),
        labor_force_status VARCHAR(10),
        weight NUMERIC(15,2),
        record_count INTEGER DEFAULT 1,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_cps_year ON cps_data(year);")
cur.execute("CREATE INDEX idx_cps_state ON cps_data(state_fips);")
cur.execute("CREATE INDEX idx_cps_month ON cps_data(month);")
print("✓ Created cps_data table")

months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
cps_total = 0

# CPS has data from 1989-2025
years_to_try = list(range(2025, 1988, -1))

for year in years_to_try:
    year_count = 0
    for month in months:
        url = f"https://api.census.gov/data/{year}/cps/basic/{month}?get=PEMLR,PWSSWGT,GESTFIPS&for=state:*&key={API_KEY}"
        
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    headers = data[0]
                    rows = data[1:]
                    col_map = {col: idx for idx, col in enumerate(headers)}
                    
                    # Aggregate by state and labor force status
                    state_data = {}
                    for row in rows:
                        state_fips = row[col_map.get('state')] or row[col_map.get('GESTFIPS')]
                        lf_status = row[col_map.get('PEMLR')]
                        weight = safe_float(row[col_map.get('PWSSWGT')]) or 0
                        
                        key = (state_fips, lf_status)
                        if key not in state_data:
                            state_data[key] = {'count': 0, 'weight': 0}
                        state_data[key]['count'] += 1
                        state_data[key]['weight'] += weight
                    
                    # Insert aggregated data
                    for (state_fips, lf_status), vals in state_data.items():
                        cur.execute("""
                            INSERT INTO cps_data (year, month, state_fips, geo_name, labor_force_status, weight, record_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            year, month, state_fips,
                            STATE_NAMES.get(state_fips, f"State {state_fips}"),
                            lf_status, vals['weight'], vals['count']
                        ))
                    
                    year_count += len(state_data)
                    cps_total += len(state_data)
        except Exception as e:
            pass
        
        time.sleep(0.3)
    
    if year_count > 0:
        print(f"  {year}: ✓ {year_count:,} aggregated records")
    
    # Commit periodically
    if year % 5 == 0:
        conn.commit()

print(f"\n✓ CPS total: {cps_total:,} rows")

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("COMPLETE DATABASE SUMMARY")
print("=" * 60)

tables = [
    'cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 
    'ec_data', 'decennial_data', 'abs_data', 'saipe_data', 
    'sahie_data', 'bds_data', 'sbo_data', 'acs1_data', 'cps_data'
]

grand_total = 0
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        grand_total += count
        
        cur.execute(f"SELECT MIN(vintage), MAX(vintage) FROM {table}" if table != 'cps_data' 
                   else f"SELECT MIN(year), MAX(year) FROM {table}")
        years = cur.fetchone()
        if years[0] and years[1]:
            year_str = f"{years[0]}-{years[1]}" if years[0] != years[1] else str(years[0])
        else:
            year_str = "N/A"
        
        print(f"  {table}: {count:,} rows ({year_str})")
    except Exception as e:
        print(f"  {table}: Error - {e}")

print(f"  ----------------------------------------")
print(f"  TOTAL: {grand_total:,} rows")

cur.close()
conn.close()