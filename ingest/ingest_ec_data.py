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
    if value is None or value == '' or value == 'null' or value == 'N' or value == 'D' or value == 'S':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def fetch_ec_state_data(vintage, naics_field):
    """Fetch state-level Economic Census data"""
    url = f"https://api.census.gov/data/{vintage}/ecnbasic"
    params = f"?get=NAME,{naics_field},ESTAB,EMP,PAYANN,RCPTOT&for=state:*&key={API_KEY}"
    
    try:
        response = requests.get(url + params, timeout=120)
        if response.status_code == 200 and response.text:
            return response.json()
    except Exception as e:
        print(f"    Error: {e}")
    return None

def fetch_ec_county_data(vintage, naics_field, state_fips):
    """Fetch county-level Economic Census data for a state"""
    url = f"https://api.census.gov/data/{vintage}/ecnbasic"
    params = f"?get=NAME,{naics_field},ESTAB,EMP,PAYANN,RCPTOT&for=county:*&in=state:{state_fips}&key={API_KEY}"
    
    try:
        response = requests.get(url + params, timeout=120)
        if response.status_code == 200 and response.text:
            return response.json()
    except Exception as e:
        pass
    return None

def ingest_ec_data(cur, data, vintage, geo_level, naics_field):
    """Insert Economic Census data"""
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
            naics = row[col_map[naics_field]].strip() if row[col_map[naics_field]] else None
            
            batch.append((
                vintage,
                geo_level,
                state_fips,
                county_fips,
                row[col_map['NAME']],
                naics,
                safe_int(row[col_map['ESTAB']]),
                safe_int(row[col_map['EMP']]),
                safe_int(row[col_map['PAYANN']]),
                safe_int(row[col_map.get('RCPTOT')]) if 'RCPTOT' in col_map else None
            ))
            
            if len(batch) >= 5000:
                cur.executemany("""
                    INSERT INTO ec_data (vintage, geo_level, state_fips, county_fips, geo_name, naics_code, establishments, employees, annual_payroll, receipts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, batch)
                inserted += len(batch)
                batch = []
                
        except Exception as e:
            continue
    
    if batch:
        cur.executemany("""
            INSERT INTO ec_data (vintage, geo_level, state_fips, county_fips, geo_name, naics_code, establishments, employees, annual_payroll, receipts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        'ec',
        vintage,
        f'https://api.census.gov/data/{vintage}/ecnbasic',
        'Economic Census',
        row_count,
        row_count
    ))

STATE_FIPS = [
    '01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15',
    '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27',
    '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39',
    '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53',
    '54', '55', '56', '72'
]

def main():
    if not API_KEY:
        print("ERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
        return
    
    # Economic Census years and their NAICS fields
    vintages = [
        (2022, 'NAICS2022'),
        (2017, 'NAICS2017'),
        (2012, 'NAICS2012'),
    ]
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("ECONOMIC CENSUS INGESTION")
    print("=" * 60)
    print(f"\nYears to process: {[v[0] for v in vintages]}\n")
    
    for vintage, naics_field in vintages:
        print(f"\n>>> Processing {vintage} Economic Census...")
        print(f"    Using NAICS field: {naics_field}")
        total_rows = 0
        
        # State-level data
        print(f"  Fetching state-level data...")
        state_data = fetch_ec_state_data(vintage, naics_field)
        if state_data:
            count = ingest_ec_data(cur, state_data, vintage, 'state', naics_field)
            total_rows += count
            print(f"  ✓ Inserted {count:,} state rows")
        else:
            print(f"  ✗ Failed to fetch state data")
        
        conn.commit()
        time.sleep(2)
        
        # County-level data (state by state)
        print(f"  Fetching county-level data...")
        county_rows = 0
        failed_states = 0
        
        for i, state_fips in enumerate(STATE_FIPS):
            county_data = fetch_ec_county_data(vintage, naics_field, state_fips)
            if county_data and len(county_data) > 1:
                count = ingest_ec_data(cur, county_data, vintage, 'county', naics_field)
                county_rows += count
            else:
                failed_states += 1
            
            if (i + 1) % 10 == 0:
                conn.commit()
                print(f"    Processed {i + 1}/{len(STATE_FIPS)} states ({county_rows:,} rows)...")
            
            time.sleep(0.3)
        
        total_rows += county_rows
        print(f"  ✓ Inserted {county_rows:,} county rows")
        if failed_states > 0:
            print(f"    ({failed_states} states had no county data)")
        
        update_metadata(cur, vintage, total_rows)
        conn.commit()
        print(f"  ✓ Total for {vintage}: {total_rows:,} rows")
        
        time.sleep(3)
    
    # Summary
    print("\n" + "=" * 60)
    print("ECONOMIC CENSUS INGESTION COMPLETE")
    print("=" * 60)
    
    cur.execute("""
        SELECT vintage, row_count 
        FROM dataset_metadata 
        WHERE dataset_name = 'ec' 
        ORDER BY vintage DESC
    """)
    print("\nEconomic Census datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM ec_data")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in ec_data: {total:,}")
    
    # Full database summary
    print("\n" + "=" * 60)
    print("COMPLETE DATABASE SUMMARY")
    print("=" * 60)
    
    tables = ['cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 'ec_data']
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