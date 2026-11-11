import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def fetch_cbp_state_data(vintage):
    """Fetch state-level CBP data for a given year"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = "?get=ESTAB,EMP,PAYANN,NAICS2017,NAME&for=state:*"
    
    response = requests.get(url + params)
    
    if response.status_code != 200:
        print(f"  Error fetching {vintage}: {response.status_code}")
        return None
    
    return response.json()

def fetch_cbp_county_data(vintage):
    """Fetch county-level CBP data for a given year"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = "?get=ESTAB,EMP,PAYANN,NAICS2017,NAME&for=county:*&in=state:*"
    
    response = requests.get(url + params)
    
    if response.status_code != 200:
        print(f"  Error fetching county data {vintage}: {response.status_code}")
        return None
    
    return response.json()

def safe_int(value):
    """Convert to int, handling nulls and non-numeric values"""
    if value is None or value == '' or value == 'null':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def ingest_data(cur, data, vintage, geo_level):
    """Insert data rows into cbp_data table"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    
    # Find column indexes
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    for row in rows:
        try:
            state_fips = row[col_map.get('state')] if 'state' in col_map else None
            county_fips = row[col_map.get('county')] if 'county' in col_map else None
            
            cur.execute("""
                INSERT INTO cbp_data 
                (vintage, geo_level, state_fips, county_fips, geo_name, 
                 naics_code, establishments, employees, annual_payroll)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                vintage,
                geo_level,
                state_fips,
                county_fips,
                row[col_map['NAME']],
                row[col_map['NAICS2017']],
                safe_int(row[col_map['ESTAB']]),
                safe_int(row[col_map['EMP']]),
                safe_int(row[col_map['PAYANN']])
            ))
            inserted += 1
        except Exception as e:
            # Skip problematic rows but continue
            continue
    
    return inserted

def update_metadata(cur, vintage, row_count):
    """Record the ingestion in metadata table"""
    cur.execute("""
        INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (dataset_name, vintage) 
        DO UPDATE SET row_count = %s, ingested_at = CURRENT_TIMESTAMP
    """, (
        'cbp',
        vintage,
        f'https://api.census.gov/data/{vintage}/cbp',
        'County Business Patterns',
        row_count,
        row_count
    ))

def main():
    # Start with recent years that have NAICS2017 codes
    vintages = [2021, 2020, 2019, 2018]
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("CENSUS DATA INGESTION - County Business Patterns")
    print("=" * 60)
    
    for vintage in vintages:
        print(f"\n>>> Processing {vintage}...")
        total_rows = 0
        
        # Fetch and ingest state-level data
        print(f"  Fetching state-level data...")
        state_data = fetch_cbp_state_data(vintage)
        if state_data:
            count = ingest_data(cur, state_data, vintage, 'state')
            total_rows += count
            print(f"  ✓ Inserted {count:,} state-level rows")
        
        # Fetch and ingest county-level data
        print(f"  Fetching county-level data...")
        county_data = fetch_cbp_county_data(vintage)
        if county_data:
            count = ingest_data(cur, county_data, vintage, 'county')
            total_rows += count
            print(f"  ✓ Inserted {count:,} county-level rows")
        
        # Update metadata
        update_metadata(cur, vintage, total_rows)
        conn.commit()
        
        print(f"  ✓ Total for {vintage}: {total_rows:,} rows")
        
        # Be nice to the API
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    
    cur.execute("SELECT vintage, row_count FROM dataset_metadata WHERE dataset_name = 'cbp' ORDER BY vintage DESC")
    print("\nIngested datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM cbp_data")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in cbp_data: {total:,}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()