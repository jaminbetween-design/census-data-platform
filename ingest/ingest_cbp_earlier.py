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
    if value is None or value == '' or value == 'null' or value == 'D' or value == 'S' or value == 'N':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

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

print("=" * 60)
print("EXPLORING EARLIER CBP YEARS (1986-2007)")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# Test different years to understand structure
test_years = [2007, 2005, 2000, 1995, 1990, 1986]

print("\n>>> Testing CBP endpoints by year...")

working_configs = {}

for year in test_years:
    print(f"\n--- Testing {year} ---")
    time.sleep(1)
    
    # Try different variable combinations
    test_configs = [
        {'vars': 'NAICS,ESTAB,EMP,PAYANN', 'naics_field': 'NAICS'},
        {'vars': 'NAICS2007,ESTAB,EMP,PAYANN', 'naics_field': 'NAICS2007'},
        {'vars': 'NAICS2002,ESTAB,EMP,PAYANN', 'naics_field': 'NAICS2002'},
        {'vars': 'NAICS1997,ESTAB,EMP,PAYANN', 'naics_field': 'NAICS1997'},
        {'vars': 'SIC,ESTAB,EMP,PAYANN', 'naics_field': 'SIC'},
    ]
    
    for config in test_configs:
        url = f"https://api.census.gov/data/{year}/cbp?get={config['vars']}&for=state:06&key={API_KEY}"
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    print(f"  ✓ {config['naics_field']}: Headers={data[0]}, rows={len(data)-1}")
                    working_configs[year] = config
                    break
            except:
                pass
    
    if year not in working_configs:
        print(f"  ✗ No working configuration found")

print("\n" + "=" * 60)
print("WORKING CONFIGURATIONS")
print("=" * 60)
for year, config in sorted(working_configs.items()):
    print(f"  {year}: {config['naics_field']}")

# Now ingest the data
print("\n" + "=" * 60)
print("INGESTING EARLIER CBP YEARS")
print("=" * 60)

conn = connect_db()
cur = conn.cursor()

# Years to process (excluding those we already have 2008+)
years_to_process = list(range(2007, 1985, -1))

successful = []
failed = []

for year in years_to_process:
    print(f"\n>>> Processing {year}...")
    
    # Determine NAICS/SIC field based on year
    if year >= 2003:
        naics_field = 'NAICS2002'
        vars_str = f'{naics_field},ESTAB,EMP,PAYANN'
    elif year >= 1998:
        naics_field = 'NAICS1997'
        vars_str = f'{naics_field},ESTAB,EMP,PAYANN'
    else:
        naics_field = 'SIC'
        vars_str = f'{naics_field},ESTAB,EMP,PAYANN'
    
    # Try state-level first
    state_url = f"https://api.census.gov/data/{year}/cbp?get={vars_str}&for=state:*&key={API_KEY}"
    response = requests.get(state_url, timeout=120)
    
    if response.status_code != 200:
        # Try alternative field names
        alt_fields = ['NAICS', 'NAICS2007', 'NAICS2002', 'NAICS1997', 'SIC']
        for alt in alt_fields:
            if alt != naics_field:
                alt_url = f"https://api.census.gov/data/{year}/cbp?get={alt},ESTAB,EMP,PAYANN&for=state:*&key={API_KEY}"
                response = requests.get(alt_url, timeout=120)
                if response.status_code == 200:
                    naics_field = alt
                    break
    
    if response.status_code == 200:
        try:
            data = response.json()
            headers = data[0]
            rows = data[1:]
            col_map = {col: idx for idx, col in enumerate(headers)}
            
            state_count = 0
            for row in rows:
                try:
                    state_fips = row[col_map.get('state')]
                    geo_name = STATE_NAMES.get(state_fips, f"State {state_fips}")
                    
                    cur.execute("""
                        INSERT INTO cbp_data (vintage, geo_level, state_fips, geo_name, naics_code, 
                                             establishments, employees, annual_payroll)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        year,
                        'state',
                        state_fips,
                        geo_name,
                        row[col_map[naics_field]],
                        safe_int(row[col_map.get('ESTAB')]),
                        safe_int(row[col_map.get('EMP')]),
                        safe_int(row[col_map.get('PAYANN')])
                    ))
                    state_count += 1
                except Exception as e:
                    pass
            
            conn.commit()
            print(f"  ✓ State-level: {state_count:,} rows ({naics_field})")
            
            # Update metadata
            cur.execute("""
                INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (dataset_name, vintage) 
                DO UPDATE SET row_count = row_count + %s, ingested_at = CURRENT_TIMESTAMP
            """, ('cbp', year, f'https://api.census.gov/data/{year}/cbp', 'County Business Patterns', state_count, state_count))
            conn.commit()
            
            successful.append(year)
            
        except Exception as e:
            print(f"  Error parsing: {e}")
            failed.append(year)
    else:
        print(f"  ✗ Failed: Status {response.status_code}")
        failed.append(year)
    
    time.sleep(1)

# Summary
print("\n" + "=" * 60)
print("CBP EARLIER YEARS SUMMARY")
print("=" * 60)

print(f"\nSuccessful: {len(successful)} years")
print(f"Failed: {len(failed)} years - {failed}")

cur.execute("""
    SELECT vintage, COUNT(*) as rows
    FROM cbp_data
    GROUP BY vintage
    ORDER BY vintage
""")
print("\nAll CBP years in database:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]:,} rows")

cur.execute("SELECT COUNT(*) FROM cbp_data")
print(f"\nTotal CBP rows: {cur.fetchone()[0]:,}")

# Full database summary
print("\n" + "=" * 60)
print("COMPLETE DATABASE SUMMARY")
print("=" * 60)

tables = ['cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 'ec_data', 'decennial_data', 'abs_data']
grand_total = 0

for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        grand_total += count
        print(f"  {table}: {count:,} rows")
    except:
        pass

print(f"  ----------------------------------------")
print(f"  TOTAL: {grand_total:,} rows")

cur.close()
conn.close()