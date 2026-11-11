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
print("INGESTING EARLIER CBP YEARS (1986-2007) - FIXED")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

conn = connect_db()
cur = conn.cursor()

# Configuration for each year range
def get_config(year):
    if year >= 2003:
        return 'NAICS2002'
    elif year >= 1998:
        return 'NAICS1997'
    else:
        return 'SIC'

years_to_process = list(range(2007, 1985, -1))
successful = []
failed = []

for year in years_to_process:
    print(f"\n>>> Processing {year}...")
    
    # Try multiple field configurations
    configs_to_try = [get_config(year), 'NAICS', 'NAICS2007', 'NAICS2002', 'NAICS1997', 'SIC']
    
    data = None
    used_field = None
    
    for field in configs_to_try:
        url = f"https://api.census.gov/data/{year}/cbp?get={field},ESTAB,EMP,PAYANN&for=state:*&key={API_KEY}"
        
        try:
            response = requests.get(url, timeout=120)
            if response.status_code == 200:
                test_data = response.json()
                if isinstance(test_data, list) and len(test_data) > 1:
                    data = test_data
                    used_field = field
                    break
        except:
            pass
        
        time.sleep(0.5)
    
    if data and len(data) > 1:
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
                    row[col_map[used_field]],
                    safe_int(row[col_map.get('ESTAB')]),
                    safe_int(row[col_map.get('EMP')]),
                    safe_int(row[col_map.get('PAYANN')])
                ))
                state_count += 1
            except Exception as e:
                pass
        
        conn.commit()
        print(f"  ✓ State-level: {state_count:,} rows ({used_field})")
        
        # Update metadata - fixed SQL
        cur.execute("""
            INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (dataset_name, vintage) 
            DO UPDATE SET row_count = EXCLUDED.row_count, ingested_at = CURRENT_TIMESTAMP
        """, ('cbp', year, f'https://api.census.gov/data/{year}/cbp', 'County Business Patterns', state_count))
        conn.commit()
        
        successful.append((year, state_count))
    else:
        print(f"  ✗ No data found")
        failed.append(year)
    
    time.sleep(1)

# Summary
print("\n" + "=" * 60)
print("CBP EARLIER YEARS SUMMARY")
print("=" * 60)

print(f"\nSuccessful: {len(successful)} years")
for year, count in successful:
    print(f"  {year}: {count:,} rows")

if failed:
    print(f"\nFailed: {failed}")

# CBP year summary
cur.execute("""
    SELECT vintage, COUNT(*) as rows
    FROM cbp_data
    GROUP BY vintage
    ORDER BY vintage
""")
print("\nAll CBP years in database:")
total_cbp = 0
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]:,} rows")
    total_cbp += row[1]
print(f"  Total: {total_cbp:,}")

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