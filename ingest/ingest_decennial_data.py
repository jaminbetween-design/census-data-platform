import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

STATE_FIPS = [
    '01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15',
    '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27',
    '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39',
    '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53',
    '54', '55', '56', '72'
]

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def safe_int(value):
    if value is None or value == '' or value == 'null':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def fetch_2020_state():
    """Fetch 2020 Decennial state data"""
    url = f"https://api.census.gov/data/2020/dec/pl?get=NAME,P1_001N,H1_001N,H1_002N,H1_003N&for=state:*&key={API_KEY}"
    response = requests.get(url, timeout=60)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_2020_county():
    """Fetch 2020 Decennial county data"""
    url = f"https://api.census.gov/data/2020/dec/pl?get=NAME,P1_001N,H1_001N,H1_002N,H1_003N&for=county:*&in=state:*&key={API_KEY}"
    response = requests.get(url, timeout=120)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_2010_state():
    """Fetch 2010 Decennial state data"""
    url = f"https://api.census.gov/data/2010/dec/pl?get=NAME,P001001,H001001,H003001,H003003&for=state:*&key={API_KEY}"
    response = requests.get(url, timeout=60)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_2010_county():
    """Fetch 2010 Decennial county data"""
    url = f"https://api.census.gov/data/2010/dec/pl?get=NAME,P001001,H001001,H003001,H003003&for=county:*&in=state:*&key={API_KEY}"
    response = requests.get(url, timeout=120)
    if response.status_code == 200:
        return response.json()
    return None

def ingest_2020_data(cur, data, geo_level):
    """Insert 2020 Decennial data"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    for row in rows:
        try:
            state_fips = row[col_map.get('state')] if 'state' in col_map else None
            county_fips = row[col_map.get('county')] if 'county' in col_map else None
            
            cur.execute("""
                INSERT INTO decennial_data (vintage, geo_level, state_fips, county_fips, geo_name, 
                                           total_population, housing_units, occupied_housing, vacant_housing)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                2020,
                geo_level,
                state_fips,
                county_fips,
                row[col_map['NAME']],
                safe_int(row[col_map['P1_001N']]),
                safe_int(row[col_map['H1_001N']]),
                safe_int(row[col_map['H1_002N']]),
                safe_int(row[col_map['H1_003N']])
            ))
            inserted += 1
        except Exception as e:
            continue
    
    return inserted

def ingest_2010_data(cur, data, geo_level):
    """Insert 2010 Decennial data"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    for row in rows:
        try:
            state_fips = row[col_map.get('state')] if 'state' in col_map else None
            county_fips = row[col_map.get('county')] if 'county' in col_map else None
            
            cur.execute("""
                INSERT INTO decennial_data (vintage, geo_level, state_fips, county_fips, geo_name, 
                                           total_population, housing_units, occupied_housing, vacant_housing)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                2010,
                geo_level,
                state_fips,
                county_fips,
                row[col_map['NAME']],
                safe_int(row[col_map['P001001']]),
                safe_int(row[col_map['H001001']]),
                safe_int(row[col_map['H003001']]),
                safe_int(row[col_map['H003003']])
            ))
            inserted += 1
        except Exception as e:
            continue
    
    return inserted

def update_metadata(cur, vintage, row_count):
    cur.execute("""
        INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (dataset_name, vintage) 
        DO UPDATE SET row_count = %s, ingested_at = CURRENT_TIMESTAMP
    """, (
        'decennial',
        vintage,
        f'https://api.census.gov/data/{vintage}/dec/pl',
        'Decennial Census',
        row_count,
        row_count
    ))

def main():
    if not API_KEY:
        print("ERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
        return
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("DECENNIAL CENSUS INGESTION (2010, 2020)")
    print("=" * 60)
    
    # 2020 Census
    print("\n>>> Processing 2020 Decennial Census...")
    total_2020 = 0
    
    print("  Fetching state-level data...")
    state_data = fetch_2020_state()
    if state_data:
        count = ingest_2020_data(cur, state_data, 'state')
        total_2020 += count
        print(f"  ✓ Inserted {count} state rows")
    else:
        print("  ✗ Failed to fetch state data")
    
    time.sleep(2)
    
    print("  Fetching county-level data...")
    county_data = fetch_2020_county()
    if county_data:
        count = ingest_2020_data(cur, county_data, 'county')
        total_2020 += count
        print(f"  ✓ Inserted {count} county rows")
    else:
        print("  ✗ Failed to fetch county data")
    
    update_metadata(cur, 2020, total_2020)
    conn.commit()
    print(f"  ✓ Total for 2020: {total_2020:,} rows")
    
    time.sleep(3)
    
    # 2010 Census
    print("\n>>> Processing 2010 Decennial Census...")
    total_2010 = 0
    
    print("  Fetching state-level data...")
    state_data = fetch_2010_state()
    if state_data:
        count = ingest_2010_data(cur, state_data, 'state')
        total_2010 += count
        print(f"  ✓ Inserted {count} state rows")
    else:
        print("  ✗ Failed to fetch state data")
    
    time.sleep(2)
    
    print("  Fetching county-level data...")
    county_data = fetch_2010_county()
    if county_data:
        count = ingest_2010_data(cur, county_data, 'county')
        total_2010 += count
        print(f"  ✓ Inserted {count} county rows")
    else:
        print("  ✗ Failed to fetch county data")
    
    update_metadata(cur, 2010, total_2010)
    conn.commit()
    print(f"  ✓ Total for 2010: {total_2010:,} rows")
    
    # Summary
    print("\n" + "=" * 60)
    print("DECENNIAL CENSUS INGESTION COMPLETE")
    print("=" * 60)
    
    cur.execute("SELECT vintage, COUNT(*) FROM decennial_data GROUP BY vintage ORDER BY vintage")
    print("\nDecennial Census datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM decennial_data")
    print(f"\nTotal rows in decennial_data: {cur.fetchone()[0]:,}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()