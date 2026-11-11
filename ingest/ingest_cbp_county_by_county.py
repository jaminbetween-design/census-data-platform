import requests
import psycopg2
import time
import json
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

PROGRESS_FILE = "data/cbp_county_progress.json"

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def load_progress():
    """Load progress from file if exists"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed": {}}

def save_progress(progress):
    """Save progress to file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def get_county_list(cur):
    """Get list of all unique state-county combinations from existing data"""
    cur.execute("""
        SELECT DISTINCT state_fips, county_fips, geo_name
        FROM cbp_data 
        WHERE geo_level = 'county' 
          AND state_fips IS NOT NULL 
          AND county_fips IS NOT NULL
        ORDER BY state_fips, county_fips
    """)
    return cur.fetchall()

def fetch_county_data(vintage, state_fips, county_fips):
    """Fetch data for a single county"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = f"?get=ESTAB,EMP,PAYANN,NAICS2007&for=county:{county_fips}&in=state:{state_fips}"
    
    try:
        response = requests.get(url + params, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def safe_int(value):
    if value is None or value == '' or value == 'null':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def ingest_county_data(cur, data, vintage, geo_name):
    """Insert county data"""
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
        except:
            continue
    
    return inserted

def update_metadata(cur, vintage):
    """Update row count in metadata"""
    cur.execute("SELECT COUNT(*) FROM cbp_data WHERE vintage = %s", (vintage,))
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
    print("CENSUS DATA INGESTION - County-by-County (2008-2011)")
    print("=" * 60)
    print("This will take approximately 1-2 hours.")
    print("Progress is saved - you can interrupt and resume.\n")
    
    # Load progress
    progress = load_progress()
    
    # Get county list from existing data
    print("Loading county list from existing data...")
    counties = get_county_list(cur)
    print(f"Found {len(counties):,} counties to process\n")
    
    total_counties = len(counties)
    total_api_calls = total_counties * len(vintages)
    
    for vintage in vintages:
        vintage_key = str(vintage)
        if vintage_key not in progress["completed"]:
            progress["completed"][vintage_key] = []
        
        completed_counties = set(progress["completed"][vintage_key])
        remaining = [(s, c, n) for s, c, n in counties if f"{s}-{c}" not in completed_counties]
        
        if not remaining:
            print(f">>> {vintage}: Already complete, skipping")
            continue
        
        print(f"\n>>> Processing {vintage}...")
        print(f"    {len(remaining):,} counties remaining ({len(completed_counties):,} already done)")
        
        rows_added = 0
        errors = 0
        start_time = time.time()
        
        for i, (state_fips, county_fips, geo_name) in enumerate(remaining):
            # Fetch and ingest
            data = fetch_county_data(vintage, state_fips, county_fips)
            
            if data:
                count = ingest_county_data(cur, data, vintage, geo_name)
                rows_added += count
            else:
                errors += 1
            
            # Mark as completed
            county_key = f"{state_fips}-{county_fips}"
            progress["completed"][vintage_key].append(county_key)
            
            # Commit and save progress every 50 counties
            if (i + 1) % 50 == 0:
                conn.commit()
                save_progress(progress)
                
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                remaining_count = len(remaining) - (i + 1)
                eta_seconds = remaining_count / rate if rate > 0 else 0
                eta_minutes = eta_seconds / 60
                
                print(f"    Progress: {i + 1:,}/{len(remaining):,} counties | "
                      f"{rows_added:,} rows | "
                      f"ETA: {eta_minutes:.1f} min")
            
            # Rate limiting
            time.sleep(0.25)
        
        # Final commit for this vintage
        conn.commit()
        save_progress(progress)
        update_metadata(cur, vintage)
        conn.commit()
        
        elapsed = time.time() - start_time
        print(f"    ✓ Completed {vintage}: {rows_added:,} rows added in {elapsed/60:.1f} min")
        if errors:
            print(f"      ({errors} counties had no data)")
    
    # Clean up progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    
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