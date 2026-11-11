import requests
import psycopg2
import time
import json
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

PROGRESS_FILE = "data/zbp_progress.json"

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

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed": {}}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def fetch_zbp_data(vintage, state_fips, retry_count=3):
    """Fetch ZBP data for a state"""
    # ZIP codes starting with state's first two digits (approximate)
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = f"?get=ZIPCODE,ESTAB,EMP,PAYANN,NAICS2017&for=zipcode:*&in=state:{state_fips}&key={API_KEY}"
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url + params, timeout=120)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 30
                print(f"      Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            elif response.status_code == 400:
                # May not support state filtering for ZIP, try without
                return None
            else:
                print(f"      Error {response.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"      Request error: {e}")
            time.sleep(5)
    
    return None

def fetch_zbp_all(vintage, retry_count=3):
    """Fetch all ZBP data at once"""
    url = f"https://api.census.gov/data/{vintage}/cbp"
    params = f"?get=ZIPCODE,ESTAB,EMP,PAYANN,NAICS2017&for=zipcode:*&key={API_KEY}"
    
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
                print(f"    Error {response.status_code}: {response.text[:200]}")
                time.sleep(10)
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

def ingest_zbp_data(cur, data, vintage):
    """Insert ZBP data"""
    if not data or len(data) < 2:
        return 0
    
    headers = data[0]
    rows = data[1:]
    col_map = {col: idx for idx, col in enumerate(headers)}
    
    inserted = 0
    batch = []
    
    for row in rows:
        try:
            zipcode = row[col_map['ZIPCODE']]
            naics = row[col_map['NAICS2017']].strip() if row[col_map['NAICS2017']] else None
            
            batch.append((
                vintage,
                zipcode,
                naics,
                safe_int(row[col_map['ESTAB']]),
                safe_int(row[col_map['EMP']]),
                safe_int(row[col_map['PAYANN']])
            ))
            
            # Batch insert every 5000 rows
            if len(batch) >= 5000:
                cur.executemany("""
                    INSERT INTO zbp_data (vintage, zipcode, naics_code, establishments, employees, annual_payroll)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, batch)
                inserted += len(batch)
                batch = []
                
        except Exception as e:
            continue
    
    # Insert remaining
    if batch:
        cur.executemany("""
            INSERT INTO zbp_data (vintage, zipcode, naics_code, establishments, employees, annual_payroll)
            VALUES (%s, %s, %s, %s, %s, %s)
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
        'zbp',
        vintage,
        f'https://api.census.gov/data/{vintage}/cbp',
        'ZIP Code Business Patterns',
        row_count,
        row_count
    ))

def main():
    if not API_KEY:
        print("ERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
        return
    
    vintages = [2023, 2022, 2021, 2020, 2019, 2018]
    
    conn = connect_db()
    cur = conn.cursor()
    
    progress = load_progress()
    
    print("=" * 60)
    print("ZIP CODE BUSINESS PATTERNS INGESTION")
    print("=" * 60)
    print(f"\nYears to process: {vintages}")
    print("This will take 30-60 minutes due to data volume.\n")
    
    for vintage in vintages:
        vintage_key = str(vintage)
        
        if vintage_key in progress["completed"]:
            print(f"\n>>> {vintage}: Already completed, skipping")
            continue
        
        print(f"\n>>> Processing {vintage}...")
        start_time = time.time()
        
        # Try to fetch all at once
        print(f"  Fetching all ZIP code data...")
        data = fetch_zbp_all(vintage)
        
        if data:
            print(f"  Received {len(data) - 1:,} rows, inserting...")
            row_count = ingest_zbp_data(cur, data, vintage)
            
            update_metadata(cur, vintage, row_count)
            conn.commit()
            
            progress["completed"][vintage_key] = True
            save_progress(progress)
            
            elapsed = time.time() - start_time
            print(f"  ✓ Completed {vintage}: {row_count:,} rows in {elapsed:.1f}s")
        else:
            print(f"  ✗ Failed to fetch data for {vintage}")
        
        # Delay between years
        time.sleep(5)
    
    # Clean up progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    
    # Summary
    print("\n" + "=" * 60)
    print("ZBP INGESTION COMPLETE")
    print("=" * 60)
    
    cur.execute("""
        SELECT vintage, row_count 
        FROM dataset_metadata 
        WHERE dataset_name = 'zbp' 
        ORDER BY vintage DESC
    """)
    print("\nZBP datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM zbp_data")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in zbp_data: {total:,}")
    
    # Database summary
    print("\n" + "=" * 60)
    print("COMPLETE DATABASE SUMMARY")
    print("=" * 60)
    
    cur.execute("SELECT COUNT(*) FROM cbp_data")
    cbp_total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM acs_data")
    acs_total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM zbp_data")
    zbp_total = cur.fetchone()[0]
    
    print(f"\n  CBP (County Business Patterns): {cbp_total:,} rows")
    print(f"  ACS (American Community Survey): {acs_total:,} rows")
    print(f"  ZBP (ZIP Code Business Patterns): {zbp_total:,} rows")
    print(f"  ----------------------------------------")
    print(f"  TOTAL: {cbp_total + acs_total + zbp_total:,} rows")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()