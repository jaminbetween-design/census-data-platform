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
        val = int(float(str(value).replace(',', '')))
        return val if val != 0 else None  # BDS returns 0 for suppressed data
    except:
        return None

print("=" * 60)
print("COMPREHENSIVE BDS INGESTION")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# Drop and recreate BDS table
cur.execute("DROP TABLE IF EXISTS bds_data CASCADE;")
cur.execute("""
    CREATE TABLE bds_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        county_fips VARCHAR(5),
        cbsa_code VARCHAR(5),
        geo_name VARCHAR(255),
        firms INTEGER,
        establishments INTEGER,
        employees INTEGER,
        job_creation INTEGER,
        job_destruction INTEGER,
        net_job_creation INTEGER,
        job_creation_rate NUMERIC(8,4),
        job_destruction_rate NUMERIC(8,4),
        firm_deaths INTEGER,
        estab_entries INTEGER,
        estab_exits INTEGER,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_bds_vintage ON bds_data(vintage);")
cur.execute("CREATE INDEX idx_bds_state ON bds_data(state_fips);")
cur.execute("CREATE INDEX idx_bds_geo_level ON bds_data(geo_level);")
print("✓ Created bds_data table")

# State codes from the uploaded file
STATES = [
    ('01', 'Alabama'), ('02', 'Alaska'), ('04', 'Arizona'), ('05', 'Arkansas'),
    ('06', 'California'), ('08', 'Colorado'), ('09', 'Connecticut'), ('10', 'Delaware'),
    ('11', 'District of Columbia'), ('12', 'Florida'), ('13', 'Georgia'), ('15', 'Hawaii'),
    ('16', 'Idaho'), ('17', 'Illinois'), ('18', 'Indiana'), ('19', 'Iowa'),
    ('20', 'Kansas'), ('21', 'Kentucky'), ('22', 'Louisiana'), ('23', 'Maine'),
    ('24', 'Maryland'), ('25', 'Massachusetts'), ('26', 'Michigan'), ('27', 'Minnesota'),
    ('28', 'Mississippi'), ('29', 'Missouri'), ('30', 'Montana'), ('31', 'Nebraska'),
    ('32', 'Nevada'), ('33', 'New Hampshire'), ('34', 'New Jersey'), ('35', 'New Mexico'),
    ('36', 'New York'), ('37', 'North Carolina'), ('38', 'North Dakota'), ('39', 'Ohio'),
    ('40', 'Oklahoma'), ('41', 'Oregon'), ('42', 'Pennsylvania'), ('44', 'Rhode Island'),
    ('45', 'South Carolina'), ('46', 'South Dakota'), ('47', 'Tennessee'), ('48', 'Texas'),
    ('49', 'Utah'), ('50', 'Vermont'), ('51', 'Virginia'), ('53', 'Washington'),
    ('54', 'West Virginia'), ('55', 'Wisconsin'), ('56', 'Wyoming')
]

bds_total = 0
years = list(range(2023, 1977, -1))

# =============================================================================
# 1. NATIONAL DATA
# =============================================================================
print("\n>>> Adding National Data...")

for year in years:
    url = f"https://api.census.gov/data/timeseries/bds?get=FIRM,ESTAB,EMP,JOB_CREATION,JOB_DESTRUCTION,NET_JOB_CREATION,JOB_CREATION_RATE,JOB_DESTRUCTION_RATE&for=us:1&YEAR={year}&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                headers = data[0]
                row = data[1]
                col_map = {col: idx for idx, col in enumerate(headers)}
                
                cur.execute("""
                    INSERT INTO bds_data (vintage, geo_level, geo_name, firms, establishments, employees, 
                                         job_creation, job_destruction, net_job_creation, job_creation_rate, job_destruction_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    year, 'national', 'United States',
                    safe_int(row[col_map.get('FIRM')]),
                    safe_int(row[col_map.get('ESTAB')]),
                    safe_int(row[col_map.get('EMP')]),
                    safe_int(row[col_map.get('JOB_CREATION')]),
                    safe_int(row[col_map.get('JOB_DESTRUCTION')]),
                    safe_int(row[col_map.get('NET_JOB_CREATION')]),
                    safe_int(row[col_map.get('JOB_CREATION_RATE')]),
                    safe_int(row[col_map.get('JOB_DESTRUCTION_RATE')])
                ))
                bds_total += 1
    except Exception as e:
        pass
    
    time.sleep(0.2)

print(f"  ✓ National: {bds_total} rows")
conn.commit()

# =============================================================================
# 2. STATE DATA - Query each state individually
# =============================================================================
print("\n>>> Adding State Data (state by state)...")

state_total = 0
for state_fips, state_name in STATES:
    state_count = 0
    
    for year in years:
        url = f"https://api.census.gov/data/timeseries/bds?get=FIRM,ESTAB,EMP,JOB_CREATION,JOB_DESTRUCTION,NET_JOB_CREATION,JOB_CREATION_RATE,JOB_DESTRUCTION_RATE&for=state:{state_fips}&YEAR={year}&key={API_KEY}"
        
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    headers = data[0]
                    row = data[1]
                    col_map = {col: idx for idx, col in enumerate(headers)}
                    
                    cur.execute("""
                        INSERT INTO bds_data (vintage, geo_level, state_fips, geo_name, firms, establishments, employees, 
                                             job_creation, job_destruction, net_job_creation, job_creation_rate, job_destruction_rate)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        year, 'state', state_fips, state_name,
                        safe_int(row[col_map.get('FIRM')]),
                        safe_int(row[col_map.get('ESTAB')]),
                        safe_int(row[col_map.get('EMP')]),
                        safe_int(row[col_map.get('JOB_CREATION')]),
                        safe_int(row[col_map.get('JOB_DESTRUCTION')]),
                        safe_int(row[col_map.get('NET_JOB_CREATION')]),
                        safe_int(row[col_map.get('JOB_CREATION_RATE')]),
                        safe_int(row[col_map.get('JOB_DESTRUCTION_RATE')])
                    ))
                    state_count += 1
        except:
            pass
        
        time.sleep(0.15)
    
    state_total += state_count
    print(f"  {state_name}: {state_count} years")
    conn.commit()

bds_total += state_total
print(f"\n  ✓ State total: {state_total} rows")

# =============================================================================
# 3. COUNTY DATA - Using wildcard (if supported)
# =============================================================================
print("\n>>> Testing County Data...")

# Test if county wildcard works
test_url = f"https://api.census.gov/data/timeseries/bds?get=FIRM,ESTAB,EMP&for=county:*&YEAR=2023&key={API_KEY}"
response = requests.get(test_url, timeout=120)
print(f"  County wildcard test: Status {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"  Headers: {data[0]}")
        print(f"  Rows: {len(data) - 1}")
        
        if len(data) > 10:  # Has substantial data
            print("\n>>> Adding County Data for all years...")
            county_total = 0
            
            for year in years:
                url = f"https://api.census.gov/data/timeseries/bds?get=FIRM,ESTAB,EMP,JOB_CREATION,JOB_DESTRUCTION,NET_JOB_CREATION&for=county:*&YEAR={year}&key={API_KEY}"
                
                try:
                    resp = requests.get(url, timeout=180)
                    if resp.status_code == 200:
                        year_data = resp.json()
                        if len(year_data) > 1:
                            headers = year_data[0]
                            rows = year_data[1:]
                            col_map = {col: idx for idx, col in enumerate(headers)}
                            
                            for row in rows:
                                cur.execute("""
                                    INSERT INTO bds_data (vintage, geo_level, state_fips, county_fips, firms, establishments, employees, 
                                                         job_creation, job_destruction, net_job_creation)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    year, 'county',
                                    row[col_map.get('state')],
                                    row[col_map.get('county')],
                                    safe_int(row[col_map.get('FIRM')]),
                                    safe_int(row[col_map.get('ESTAB')]),
                                    safe_int(row[col_map.get('EMP')]),
                                    safe_int(row[col_map.get('JOB_CREATION')]),
                                    safe_int(row[col_map.get('JOB_DESTRUCTION')]),
                                    safe_int(row[col_map.get('NET_JOB_CREATION')])
                                ))
                            county_total += len(rows)
                            print(f"    {year}: ✓ {len(rows):,} county rows")
                            conn.commit()
                except Exception as e:
                    print(f"    {year}: ✗ {e}")
                
                time.sleep(1)
            
            bds_total += county_total
            print(f"\n  ✓ County total: {county_total:,} rows")
    except Exception as e:
        print(f"  Parse error: {e}")
else:
    print(f"  County wildcard not supported")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("BDS INGESTION COMPLETE")
print("=" * 60)

cur.execute("SELECT geo_level, COUNT(*) FROM bds_data GROUP BY geo_level ORDER BY geo_level")
print("\nBDS by geography level:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]:,} rows")

cur.execute("SELECT COUNT(*) FROM bds_data")
total = cur.fetchone()[0]
print(f"\nTotal BDS rows: {total:,}")

cur.execute("SELECT MIN(vintage), MAX(vintage) FROM bds_data")
years_range = cur.fetchone()
print(f"Years: {years_range[0]}-{years_range[1]}")

# Full database summary
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
        print(f"  {table}: {count:,} rows")
    except:
        print(f"  {table}: Not found")

print(f"  ----------------------------------------")
print(f"  TOTAL: {grand_total:,} rows")

cur.close()
conn.close()