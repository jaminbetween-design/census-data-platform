import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def get_naics_field(vintage):
    """Determine which NAICS field to use based on vintage"""
    # Check available variables for this vintage
    url = f"https://api.census.gov/data/{vintage}/cbp/variables.json"
    response = requests.get(url)
    
    if response.status_code != 200:
        return None, None
    
    variables = response.json().get('variables', {})
    
    # Check for NAICS fields in order of preference
    if 'NAICS2017' in variables:
        return 'NAICS2017', variables
    elif 'NAICS2012' in variables:
        return 'NAICS2012', variables
    elif 'NAICS2007' in variables:
        return 'NAICS2007', variables
    elif 'NAICS' in variables:
        return 'NAICS', variables
    else:
        return None, variables

def fetch_cbp_state_data(vintage, naics_field):
    """Fetch state-level CBP data for a given year"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = f"?get=ESTAB,EMP,PAYANN,{naics_field},NAME&for=state:*"
    
    response = requests.get(url + params)
    
    if response.status_code != 200:
        print(f"    Error fetching state data: {response.status_code}")
        return None
    
    return response.json()

def fetch_cbp_county_data(vintage, naics_field):
    """Fetch county-level CBP data for a given year"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = f"?get=ESTAB,EMP,PAYANN,{naics_field},NAME&for=county:*&in=state:*"
    
    response = requests.get(url + params)
    
    if response.status_code != 200:
        print(f"    Error fetching county data: {response.status_code}")
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

def ingest_data(cur, data, vintage, geo_level, naics_field):
    """Insert data rows into cbp_data table"""
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
                row[col_map[naics_field]],
                safe_int(row[col_map['ESTAB']]),
                safe_int(row[col_map['EMP']]),
                safe_int(row[col_map['PAYANN']])
            ))
            inserted += 1
        except Exception as e:
            continue
    
    return inserted

def update_metadata(cur, vintage, row_count, naics_field):
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
        f'County Business Patterns (using {naics_field})',
        row_count,
        row_count
    ))

def main():
    # Years to ingest (excluding 2018-2021 which we already have)
    vintages = [2023, 2022, 2017, 2016, 2015, 2014, 2013, 2012, 2011, 2010]
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("CENSUS DATA INGESTION - County Business Patterns (Expanded)")
    print("=" * 60)
    print(f"\nYears to process: {vintages}")
    print("This may take 15-20 minutes for all years.\n")
    
    successful = []
    failed = []
    
    for vintage in vintages:
        print(f"\n>>> Processing {vintage}...")
        
        # Determine NAICS field for this vintage
        naics_field, variables = get_naics_field(vintage)
        
        if not naics_field:
            print(f"  ✗ Could not determine NAICS field for {vintage}, skipping")
            failed.append(vintage)
            continue
        
        print(f"  Using NAICS field: {naics_field}")
        
        total_rows = 0
        
        # Fetch and ingest state-level data
        print(f"  Fetching state-level data...")
        state_data = fetch_cbp_state_data(vintage, naics_field)
        if state_data:
            count = ingest_data(cur, state_data, vintage, 'state', naics_field)
            total_rows += count
            print(f"  ✓ Inserted {count:,} state-level rows")
        else:
            print(f"  ✗ Failed to fetch state data")
        
        # Fetch and ingest county-level data
        print(f"  Fetching county-level data...")
        county_data = fetch_cbp_county_data(vintage, naics_field)
        if county_data:
            count = ingest_data(cur, county_data, vintage, 'county', naics_field)
            total_rows += count
            print(f"  ✓ Inserted {count:,} county-level rows")
        else:
            print(f"  ✗ Failed to fetch county data")
        
        # Update metadata and commit
        if total_rows > 0:
            update_metadata(cur, vintage, total_rows, naics_field)
            conn.commit()
            print(f"  ✓ Total for {vintage}: {total_rows:,} rows")
            successful.append(vintage)
        else:
            failed.append(vintage)
        
        # Be nice to the API
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    
    print(f"\nSuccessfully ingested: {successful}")
    if failed:
        print(f"Failed/skipped: {failed}")
    
    cur.execute("""
        SELECT vintage, row_count 
        FROM dataset_metadata 
        WHERE dataset_name = 'cbp' 
        ORDER BY vintage DESC
    """)
    print("\nAll ingested CBP datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM cbp_data")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in cbp_data: {total:,}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()