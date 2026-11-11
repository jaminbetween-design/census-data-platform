import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def fetch_nes_state_data(vintage, retry_count=3):
    """Fetch state-level NES data"""
    url = f"https://api.census.gov/data/{vintage}/nonemp"
    params = f"?get=NAICS2017,NESTAB,NRCPTOT,NAME&for=state:*&key={API_KEY}"
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url + params, timeout=120)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 30
                print(f"    Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    Error {response.status_code}: {response.text[:100]}")
                return None
        except Exception as e:
            print(f"    Request error: {e}")
            time.sleep(5)
    return None

def fetch_nes_county_data(vintage, retry_count=3):
    """Fetch county-level NES data"""
    url = f"https://api.census.gov/data/{vintage}/nonemp"
    params = f"?get=NAICS2017,NESTAB,NRCPTOT,NAME&for=county:*&in=state:*&key={API_KEY}"
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url + params, timeout=300)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 60
                print(f"    Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    Error {response.status_code}: {response.text[:100]}")
                return None
        except Exception as e:
            print(f"    Request error: {e}")
            time.sleep(10)
    return None

def safe_int(value):
    if value is None or value == '' or value == 'null':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def ingest_nes_data(cur, data, vintage, geo_level):
    """Insert NES data"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    batch = []
    
    for row in rows:
        try:
            state_fips = row[col_map.get('state')] if 'state' in col_map else None
            county_fips = row[col_map.get('county')] if 'county' in col_map else None
            geo_name = row[col_map['NAME']] if 'NAME' in col_map else None
            naics = row[col_map['NAICS2017']].strip() if row[col_map['NAICS2017']] else None
            
            batch.append((
                vintage,
                geo_level,
                state_fips,
                county_fips,
                geo_name,
                naics,
                safe_int(row[col_map['NESTAB']]),
                safe_int(row[col_map['NRCPTOT']])
            ))
            
            if len(batch) >= 5000:
                cur.executemany("""
                    INSERT INTO nes_data (vintage, geo_level, state_fips, county_fips, geo_name, naics_code, establishments, receipts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, batch)
                inserted += len(batch)
                batch = []
                
        except Exception as e:
            continue
    
    if batch:
        cur.executemany("""
            INSERT INTO nes_data (vintage, geo_level, state_fips, county_fips, geo_name, naics_code, establishments, receipts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, batch)
        inserted += len(batch)
    
    return inserted

def update_metadata(cur, vintage, row_count):
    cur.execute("""
        INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (dataset_name, vintage) 
        DO UPDATE SET row_count = %s, ingested_at = CURRENT_TIMESTAMP
    """, (
        'nes',
        vintage,
        f'https://api.census.gov/data/{vintage}/nonemp',
        'Nonemployer Statistics',
        row_count,
        row_count
    ))

def main():
    if not API_KEY:
        print("ERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
        return
    
    vintages = [2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012]
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("NONEMPLOYER STATISTICS (NES) INGESTION")
    print("=" * 60)
    print(f"\nYears to process: {vintages}\n")
    
    successful = []
    failed = []
    
    for vintage in vintages:
        print(f"\n>>> Processing {vintage}...")
        total_rows = 0
        
        # State-level
        print(f"  Fetching state-level data...")
        state_data = fetch_nes_state_data(vintage)
        if state_data:
            count = ingest_nes_data(cur, state_data, vintage, 'state')
            total_rows += count
            print(f"  ✓ Inserted {count:,} state rows")
        else:
            print(f"  ✗ Failed to fetch state data")
        
        time.sleep(2)
        
        # County-level
        print(f"  Fetching county-level data...")
        county_data = fetch_nes_county_data(vintage)
        if county_data:
            count = ingest_nes_data(cur, county_data, vintage, 'county')
            total_rows += count
            print(f"  ✓ Inserted {count:,} county rows")
        else:
            print(f"  ✗ Failed to fetch county data")
        
        if total_rows > 0:
            update_metadata(cur, vintage, total_rows)
            conn.commit()
            print(f"  ✓ Total for {vintage}: {total_rows:,} rows")
            successful.append(vintage)
        else:
            failed.append(vintage)
        
        time.sleep(3)
    
    # Summary
    print("\n" + "=" * 60)
    print("NES INGESTION COMPLETE")
    print("=" * 60)
    
    print(f"\nSuccessful: {successful}")
    if failed:
        print(f"Failed: {failed}")
    
    cur.execute("""
        SELECT vintage, row_count 
        FROM dataset_metadata 
        WHERE dataset_name = 'nes' 
        ORDER BY vintage DESC
    """)
    print("\nNES datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM nes_data")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in nes_data: {total:,}")
    
    # Full database summary
    print("\n" + "=" * 60)
    print("COMPLETE DATABASE SUMMARY")
    print("=" * 60)
    
    cur.execute("SELECT COUNT(*) FROM cbp_data")
    cbp_total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM acs_data")
    acs_total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM zbp_data")
    zbp_total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM nes_data")
    nes_total = cur.fetchone()[0]
    
    print(f"\n  CBP (County Business Patterns): {cbp_total:,} rows")
    print(f"  ACS (American Community Survey): {acs_total:,} rows")
    print(f"  ZBP (ZIP Code Business Patterns): {zbp_total:,} rows")
    print(f"  NES (Nonemployer Statistics): {nes_total:,} rows")
    print(f"  ----------------------------------------")
    print(f"  TOTAL: {cbp_total + acs_total + zbp_total + nes_total:,} rows")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()