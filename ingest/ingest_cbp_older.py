import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

# State FIPS to name mapping
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

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def load_county_names(cur):
    """Load county names from existing data to build reference"""
    cur.execute("""
        SELECT DISTINCT state_fips, county_fips, geo_name 
        FROM cbp_data 
        WHERE geo_level = 'county' AND geo_name IS NOT NULL
    """)
    county_map = {}
    for row in cur.fetchall():
        key = f"{row[0]}-{row[1]}"
        county_map[key] = row[2]
    return county_map

def fetch_cbp_state_data(vintage):
    """Fetch state-level CBP data for older years"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = "?get=ESTAB,EMP,PAYANN,NAICS2007&for=state:*"
    
    response = requests.get(url + params)
    
    if response.status_code != 200:
        print(f"    Error fetching state data: {response.status_code}")
        return None
    
    return response.json()

def fetch_cbp_county_data(vintage):
    """Fetch county-level CBP data for older years"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = "?get=ESTAB,EMP,PAYANN,NAICS2007&for=county:*&in=state:*"
    
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

def ingest_state_data(cur, data, vintage):
    """Insert state-level data"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    for row in rows:
        try:
            state_fips = row[col_map['state']]
            naics_raw = row[col_map['NAICS2007']].strip()
            
            cur.execute("""
                INSERT INTO cbp_data 
                (vintage, geo_level, state_fips, county_fips, geo_name, 
                 naics_code, establishments, employees, annual_payroll)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                vintage,
                'state',
                state_fips,
                None,
                STATE_NAMES.get(state_fips, f'State {state_fips}'),
                naics_raw,
                safe_int(row[col_map['ESTAB']]),
                safe_int(row[col_map['EMP']]),
                safe_int(row[col_map['PAYANN']])
            ))
            inserted += 1
        except Exception as e:
            continue
    
    return inserted

def ingest_county_data(cur, data, vintage, county_map):
    """Insert county-level data"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    for row in rows:
        try:
            state_fips = row[col_map['state']]
            county_fips = row[col_map['county']]
            naics_raw = row[col_map['NAICS2007']].strip()
            
            # Look up county name from our reference
            county_key = f"{state_fips}-{county_fips}"
            geo_name = county_map.get(county_key, f"County {county_fips}, {STATE_NAMES.get(state_fips, 'Unknown')}")
            
            cur.execute("""
                INSERT INTO cbp_data 
                (vintage, geo_level, state_fips, county_fips, geo_name, 
                 naics_code, establishments, employees, annual_payroll)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                vintage,
                'county',
                state_fips,
                county_fips,
                geo_name,
                naics_raw,
                safe_int(row[col_map['ESTAB']]),
                safe_int(row[col_map['EMP']]),
                safe_int(row[col_map['PAYANN']])
            ))
            inserted += 1
        except Exception as e:
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
        'County Business Patterns (using NAICS2007)',
        row_count,
        row_count
    ))

def main():
    vintages = [2011, 2010, 2009, 2008]
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("CENSUS DATA INGESTION - County Business Patterns (2008-2011)")
    print("=" * 60)
    
    # Load county names from existing data
    print("\nLoading county name reference from existing data...")
    county_map = load_county_names(cur)
    print(f"Loaded {len(county_map):,} county name mappings")
    
    successful = []
    failed = []
    
    for vintage in vintages:
        print(f"\n>>> Processing {vintage}...")
        total_rows = 0
        
        # State-level data
        print(f"  Fetching state-level data...")
        state_data = fetch_cbp_state_data(vintage)
        if state_data:
            count = ingest_state_data(cur, state_data, vintage)
            total_rows += count
            print(f"  ✓ Inserted {count:,} state-level rows")
        else:
            print(f"  ✗ Failed to fetch state data")
        
        # County-level data
        print(f"  Fetching county-level data...")
        county_data = fetch_cbp_county_data(vintage)
        if county_data:
            count = ingest_county_data(cur, county_data, vintage, county_map)
            total_rows += count
            print(f"  ✓ Inserted {count:,} county-level rows")
        else:
            print(f"  ✗ Failed to fetch county data")
        
        if total_rows > 0:
            update_metadata(cur, vintage, total_rows)
            conn.commit()
            print(f"  ✓ Total for {vintage}: {total_rows:,} rows")
            successful.append(vintage)
        else:
            failed.append(vintage)
        
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