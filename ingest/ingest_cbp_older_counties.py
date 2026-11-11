import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

STATE_FIPS = [
    '01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15',
    '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27',
    '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39',
    '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53',
    '54', '55', '56', '72'
]

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
    """Load county names from existing data"""
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

def fetch_county_data_by_state(vintage, state_fips):
    """Fetch county-level data for a single state"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = f"?get=ESTAB,EMP,PAYANN,NAICS2007&for=county:*&in=state:{state_fips}"
    
    response = requests.get(url + params)
    
    if response.status_code != 200:
        return None
    
    return response.json()

def safe_int(value):
    if value is None or value == '' or value == 'null':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

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

def update_metadata(cur, vintage):
    """Update row count in metadata"""
    cur.execute("""
        SELECT COUNT(*) FROM cbp_data WHERE vintage = %s
    """, (vintage,))
    total = cur.fetchone()[0]
    
    cur.execute("""
        UPDATE dataset_metadata 
        SET row_count = %s, ingested_at = CURRENT_TIMESTAMP
        WHERE dataset_name = 'cbp' AND vintage = %s
    """, (total, vintage))

def main():
    vintages = [2011, 2010, 2009, 2008]
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("CENSUS DATA INGESTION - County Data (2008-2011)")
    print("=" * 60)
    print("Fetching county data state-by-state to avoid API limits")
    
    # Load county names
    print("\nLoading county name reference...")
    county_map = load_county_names(cur)
    print(f"Loaded {len(county_map):,} county name mappings\n")
    
    for vintage in vintages:
        print(f"\n>>> Processing {vintage} county data...")
        total_rows = 0
        failed_states = []
        
        for i, state_fips in enumerate(STATE_FIPS):
            state_name = STATE_NAMES.get(state_fips, state_fips)
            
            data = fetch_county_data_by_state(vintage, state_fips)
            
            if data:
                count = ingest_county_data(cur, data, vintage, county_map)
                total_rows += count
                # Progress indicator every 10 states
                if (i + 1) % 10 == 0:
                    print(f"  Processed {i + 1}/{len(STATE_FIPS)} states ({total_rows:,} rows so far)")
            else:
                failed_states.append(state_name)
            
            # Small delay to be nice to API
            time.sleep(0.2)
        
        # Commit and update metadata
        conn.commit()
        update_metadata(cur, vintage)
        conn.commit()
        
        print(f"  ✓ Completed {vintage}: {total_rows:,} county rows added")
        if failed_states:
            print(f"    Failed states: {failed_states}")
        
        time.sleep(1)
    
    # Final summary
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    
    cur.execute("""
        SELECT vintage, row_count 
        FROM dataset_metadata 
        WHERE dataset_name = 'cbp' 
        ORDER BY vintage DESC
    """)
    print("\nAll CBP datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM cbp_data")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in cbp_data: {total:,}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()