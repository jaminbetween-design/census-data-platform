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
    if value is None or value == '' or value == 'null':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

print("=" * 60)
print("FIXING 2010 DECENNIAL CENSUS")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# First, explore 2010 variables
print("\n>>> Exploring 2010 Decennial Census variables...")

var_url = "https://api.census.gov/data/2010/dec/sf1/variables.json"
response = requests.get(var_url)
print(f"Variables endpoint status: {response.status_code}")

if response.status_code == 200:
    variables = response.json().get('variables', {})
    print(f"Total variables: {len(variables)}")
    
    print("\nPopulation/Housing variables:")
    for var_name, var_info in list(variables.items())[:50]:
        label = var_info.get('label', '')
        if 'total' in label.lower() or 'population' in label.lower() or 'housing' in label.lower():
            print(f"  {var_name}: {label}")

# Test different endpoints
print("\n>>> Testing 2010 API endpoints...")

test_urls = [
    ("SF1", f"https://api.census.gov/data/2010/dec/sf1?get=NAME,P001001,H001001&for=state:*&key={API_KEY}"),
    ("PL", f"https://api.census.gov/data/2010/dec/pl?get=NAME,P001001,H001001&for=state:*&key={API_KEY}"),
    ("Summary", f"https://api.census.gov/data/2010/dec/summary?get=NAME,P001001&for=state:*&key={API_KEY}"),
]

working_endpoint = None
for name, url in test_urls:
    print(f"\nTesting {name}: {url[:60]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                print(f"  ✓ Success! Headers: {data[0]}")
                print(f"    Sample: {data[1]}")
                working_endpoint = (name, url)
                break
        except Exception as e:
            print(f"  Parse error: {e}")
            print(f"  Response: {response.text[:200]}")
    
    time.sleep(1)

# If we found a working endpoint, ingest the data
if working_endpoint:
    print(f"\n>>> Ingesting 2010 data using {working_endpoint[0]} endpoint...")
    
    conn = connect_db()
    cur = conn.cursor()
    
    # State level
    print("  Fetching state-level data...")
    state_url = f"https://api.census.gov/data/2010/dec/sf1?get=NAME,P001001,H001001,H003001,H003003&for=state:*&key={API_KEY}"
    response = requests.get(state_url, timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        headers = data[0]
        rows = data[1:]
        col_map = {col: idx for idx, col in enumerate(headers)}
        
        inserted = 0
        for row in rows:
            try:
                cur.execute("""
                    INSERT INTO decennial_data (vintage, geo_level, state_fips, geo_name, 
                                               total_population, housing_units, occupied_housing, vacant_housing)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    2010,
                    'state',
                    row[col_map.get('state')],
                    row[col_map['NAME']],
                    safe_int(row[col_map['P001001']]),
                    safe_int(row[col_map['H001001']]),
                    safe_int(row[col_map.get('H003001')]) if 'H003001' in col_map else None,
                    safe_int(row[col_map.get('H003003')]) if 'H003003' in col_map else None
                ))
                inserted += 1
            except Exception as e:
                print(f"    Error: {e}")
        
        conn.commit()
        print(f"  ✓ Inserted {inserted} state rows")
    
    time.sleep(2)
    
    # County level
    print("  Fetching county-level data...")
    county_url = f"https://api.census.gov/data/2010/dec/sf1?get=NAME,P001001,H001001,H003001,H003003&for=county:*&in=state:*&key={API_KEY}"
    response = requests.get(county_url, timeout=120)
    
    if response.status_code == 200:
        data = response.json()
        headers = data[0]
        rows = data[1:]
        col_map = {col: idx for idx, col in enumerate(headers)}
        
        inserted = 0
        for row in rows:
            try:
                cur.execute("""
                    INSERT INTO decennial_data (vintage, geo_level, state_fips, county_fips, geo_name, 
                                               total_population, housing_units, occupied_housing, vacant_housing)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    2010,
                    'county',
                    row[col_map.get('state')],
                    row[col_map.get('county')],
                    row[col_map['NAME']],
                    safe_int(row[col_map['P001001']]),
                    safe_int(row[col_map['H001001']]),
                    safe_int(row[col_map.get('H003001')]) if 'H003001' in col_map else None,
                    safe_int(row[col_map.get('H003003')]) if 'H003003' in col_map else None
                ))
                inserted += 1
            except Exception as e:
                pass
        
        conn.commit()
        print(f"  ✓ Inserted {inserted} county rows")
    
    # Update metadata
    cur.execute("SELECT COUNT(*) FROM decennial_data WHERE vintage = 2010")
    count_2010 = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (dataset_name, vintage) 
        DO UPDATE SET row_count = %s, ingested_at = CURRENT_TIMESTAMP
    """, ('decennial', 2010, 'https://api.census.gov/data/2010/dec/sf1', 'Decennial Census', count_2010, count_2010))
    conn.commit()
    
    # Summary
    print("\n" + "=" * 60)
    print("DECENNIAL CENSUS SUMMARY")
    print("=" * 60)
    
    cur.execute("SELECT vintage, COUNT(*) FROM decennial_data GROUP BY vintage ORDER BY vintage")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM decennial_data")
    print(f"\nTotal decennial_data rows: {cur.fetchone()[0]:,}")
    
    cur.close()
    conn.close()

else:
    print("\n✗ Could not find working 2010 endpoint")