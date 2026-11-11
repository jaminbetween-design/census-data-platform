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

print("=" * 60)
print("EXPLORING ABS VARIABLES")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# Check ABS variables
print("\n>>> Checking 2021 ABS variables...")
var_url = "https://api.census.gov/data/2021/abscs/variables.json"
response = requests.get(var_url)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    variables = response.json().get('variables', {})
    print(f"Total variables: {len(variables)}")
    
    print("\nAll variables:")
    for var_name, var_info in sorted(variables.items()):
        label = var_info.get('label', '')
        print(f"  {var_name}: {label}")

# Test queries with correct variables
print("\n>>> Testing ABS queries...")
time.sleep(1)

test_urls = [
    f"https://api.census.gov/data/2021/abscs?get=NAME,NAICS2017,EMP,PAYANN&for=state:*&key={API_KEY}",
    f"https://api.census.gov/data/2021/abscs?get=NAME,NAICS2017,EMP,PAYANN,FIRMPDEMP&for=state:*&key={API_KEY}",
    f"https://api.census.gov/data/2021/abscs?get=NAME,NAICS2017,EMP&for=state:*&key={API_KEY}",
]

for url in test_urls:
    print(f"\nTesting: {url[:70]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                print(f"  ✓ Headers: {data[0]}")
                print(f"    Sample: {data[1]}")
                print(f"    Total rows: {len(data) - 1}")
        except Exception as e:
            print(f"  Parse error: {e}")
    else:
        print(f"  Error: {response.text[:100]}")
    
    time.sleep(1)

# Now ingest with correct variables
print("\n" + "=" * 60)
print("INGESTING ABS DATA")
print("=" * 60)

conn = connect_db()
cur = conn.cursor()

vintages = [2021, 2020, 2019, 2018, 2017]
successful = []

for vintage in vintages:
    print(f"\n>>> Processing {vintage}...")
    
    naics_field = 'NAICS2017'
    url = f"https://api.census.gov/data/{vintage}/abscs?get=NAME,{naics_field},EMP,PAYANN&for=state:*&key={API_KEY}"
    
    response = requests.get(url, timeout=120)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            headers = data[0]
            rows = data[1:]
            col_map = {col: idx for idx, col in enumerate(headers)}
            
            inserted = 0
            for row in rows:
                try:
                    cur.execute("""
                        INSERT INTO abs_data (vintage, geo_level, state_fips, geo_name, naics_code, 
                                             employees, annual_payroll)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        vintage,
                        'state',
                        row[col_map.get('state')],
                        row[col_map['NAME']],
                        row[col_map[naics_field]],
                        safe_int(row[col_map.get('EMP')]),
                        safe_int(row[col_map.get('PAYANN')])
                    ))
                    inserted += 1
                except:
                    pass
            
            conn.commit()
            print(f"  ✓ Inserted {inserted:,} rows")
            successful.append(vintage)
            
            # Update metadata
            cur.execute("""
                INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (dataset_name, vintage) 
                DO UPDATE SET row_count = %s, ingested_at = CURRENT_TIMESTAMP
            """, ('abs', vintage, f'https://api.census.gov/data/{vintage}/abscs', 'Annual Business Survey', inserted, inserted))
            conn.commit()
            
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print(f"  Failed: {response.text[:100]}")
    
    time.sleep(2)

# Summary
print("\n" + "=" * 60)
print("ABS SUMMARY")
print("=" * 60)

cur.execute("SELECT vintage, COUNT(*) FROM abs_data GROUP BY vintage ORDER BY vintage DESC")
print("\nABS datasets:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]:,} rows")

cur.execute("SELECT COUNT(*) FROM abs_data")
print(f"\nTotal abs_data rows: {cur.fetchone()[0]:,}")

cur.close()
conn.close()