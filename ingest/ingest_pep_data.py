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

def safe_float(value):
    if value is None or value == '' or value == 'null':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def fetch_pep_2021_state():
    """Fetch 2021 state population estimates"""
    url = f"https://api.census.gov/data/2021/pep/population?get=NAME,POP_2020,POP_2021,NPOPCHG_2021,PPOPCHG_2021,DENSITY_2021&for=state:*&key={API_KEY}"
    response = requests.get(url, timeout=60)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_pep_2021_county():
    """Fetch 2021 county population estimates"""
    url = f"https://api.census.gov/data/2021/pep/population?get=NAME,POP_2020,POP_2021,NPOPCHG_2021,PPOPCHG_2021,DENSITY_2021&for=county:*&in=state:*&key={API_KEY}"
    response = requests.get(url, timeout=120)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_pep_2019_state():
    """Fetch 2019 state population estimates"""
    url = f"https://api.census.gov/data/2019/pep/population?get=NAME,POP,DENSITY&for=state:*&key={API_KEY}"
    response = requests.get(url, timeout=60)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_pep_2019_county():
    """Fetch 2019 county population estimates"""
    url = f"https://api.census.gov/data/2019/pep/population?get=NAME,POP,DENSITY&for=county:*&in=state:*&key={API_KEY}"
    response = requests.get(url, timeout=120)
    if response.status_code == 200:
        return response.json()
    return None

def ingest_pep_2021(cur, data, geo_level):
    """Insert 2021 PEP data"""
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
            
            # Insert 2020 data point
            cur.execute("""
                INSERT INTO pep_data (vintage, geo_level, state_fips, county_fips, geo_name, population, density)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                2020,
                geo_level,
                state_fips,
                county_fips,
                row[col_map['NAME']],
                safe_int(row[col_map['POP_2020']]),
                safe_float(row[col_map['DENSITY_2021']])  # Use 2021 density as approximation
            ))
            inserted += 1
            
            # Insert 2021 data point
            cur.execute("""
                INSERT INTO pep_data (vintage, geo_level, state_fips, county_fips, geo_name, population, population_change, percent_change, density)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                2021,
                geo_level,
                state_fips,
                county_fips,
                row[col_map['NAME']],
                safe_int(row[col_map['POP_2021']]),
                safe_int(row[col_map['NPOPCHG_2021']]),
                safe_float(row[col_map['PPOPCHG_2021']]),
                safe_float(row[col_map['DENSITY_2021']])
            ))
            inserted += 1
            
        except Exception as e:
            continue
    
    return inserted

def ingest_pep_2019(cur, data, geo_level):
    """Insert 2019 PEP data"""
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
                INSERT INTO pep_data (vintage, geo_level, state_fips, county_fips, geo_name, population, density)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                2019,
                geo_level,
                state_fips,
                county_fips,
                row[col_map['NAME']],
                safe_int(row[col_map['POP']]),
                safe_float(row[col_map.get('DENSITY')]) if 'DENSITY' in col_map else None
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
        'pep',
        vintage,
        f'https://api.census.gov/data/{vintage}/pep/population',
        'Population Estimates Program',
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
    print("POPULATION ESTIMATES PROGRAM (PEP) INGESTION")
    print("=" * 60)
    
    total_rows = 0
    
    # 2021 Data (includes 2020 baseline)
    print("\n>>> Processing 2021 estimates (includes 2020 baseline)...")
    
    print("  Fetching state-level data...")
    state_data = fetch_pep_2021_state()
    if state_data:
        count = ingest_pep_2021(cur, state_data, 'state')
        total_rows += count
        print(f"  ✓ Inserted {count} state rows")
    else:
        print("  ✗ Failed to fetch state data")
    
    time.sleep(2)
    
    print("  Fetching county-level data...")
    county_data = fetch_pep_2021_county()
    if county_data:
        count = ingest_pep_2021(cur, county_data, 'county')
        total_rows += count
        print(f"  ✓ Inserted {count} county rows")
    else:
        print("  ✗ Failed to fetch county data")
    
    conn.commit()
    
    # 2019 Data
    print("\n>>> Processing 2019 estimates...")
    time.sleep(2)
    
    print("  Fetching state-level data...")
    state_data = fetch_pep_2019_state()
    if state_data:
        count = ingest_pep_2019(cur, state_data, 'state')
        total_rows += count
        print(f"  ✓ Inserted {count} state rows")
    else:
        print("  ✗ Failed to fetch state data")
    
    time.sleep(2)
    
    print("  Fetching county-level data...")
    county_data = fetch_pep_2019_county()
    if county_data:
        count = ingest_pep_2019(cur, county_data, 'county')
        total_rows += count
        print(f"  ✓ Inserted {count} county rows")
    else:
        print("  ✗ Failed to fetch county data")
    
    conn.commit()
    
    # Update metadata
    cur.execute("SELECT vintage, COUNT(*) FROM pep_data GROUP BY vintage")
    for row in cur.fetchall():
        update_metadata(cur, row[0], row[1])
    conn.commit()
    
    # Summary
    print("\n" + "=" * 60)
    print("PEP INGESTION COMPLETE")
    print("=" * 60)
    
    cur.execute("""
        SELECT vintage, COUNT(*) as rows
        FROM pep_data
        GROUP BY vintage
        ORDER BY vintage
    """)
    print("\nPEP datasets by year:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM pep_data")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in pep_data: {total:,}")
    
    # Full database summary
    print("\n" + "=" * 60)
    print("COMPLETE DATABASE SUMMARY")
    print("=" * 60)
    
    tables = ['cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data']
    grand_total = 0
    
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        grand_total += count
        print(f"  {table}: {count:,} rows")
    
    print(f"  ----------------------------------------")
    print(f"  TOTAL: {grand_total:,} rows")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()