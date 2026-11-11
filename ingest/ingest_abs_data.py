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
    if value is None or value == '' or value == 'null' or value == 'D' or value == 'S' or value == 'N':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def get_naics_field(vintage):
    if vintage >= 2022:
        return 'NAICS2022'
    else:
        return 'NAICS2017'

def fetch_abs_data(vintage, naics_field):
    """Fetch ABS state-level data"""
    url = f"https://api.census.gov/data/{vintage}/abscs?get=NAME,{naics_field},EMP,PAYANN,RCPTOT&for=state:*&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    Status {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"    Error: {e}")
    return None

def ingest_abs_data(cur, data, vintage, naics_field):
    """Insert ABS data"""
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
            naics = row[col_map[naics_field]].strip() if row[col_map[naics_field]] else None
            
            batch.append((
                vintage,
                'state',
                state_fips,
                row[col_map['NAME']],
                naics,
                None,  # establishments not in this endpoint
                safe_int(row[col_map.get('EMP')]) if 'EMP' in col_map else None,
                safe_int(row[col_map.get('PAYANN')]) if 'PAYANN' in col_map else None,
                safe_int(row[col_map.get('RCPTOT')]) if 'RCPTOT' in col_map else None
            ))
            
            if len(batch) >= 5000:
                cur.executemany("""
                    INSERT INTO abs_data (vintage, geo_level, state_fips, geo_name, naics_code, 
                                         establishments, employees, annual_payroll, receipts)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, batch)
                inserted += len(batch)
                batch = []
                
        except Exception as e:
            continue
    
    if batch:
        cur.executemany("""
            INSERT INTO abs_data (vintage, geo_level, state_fips, geo_name, naics_code, 
                                 establishments, employees, annual_payroll, receipts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        'abs',
        vintage,
        f'https://api.census.gov/data/{vintage}/abscs',
        'Annual Business Survey',
        row_count,
        row_count
    ))

def main():
    if not API_KEY:
        print("ERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
        return
    
    vintages = [2023, 2022, 2021, 2020, 2019, 2018, 2017]
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("ANNUAL BUSINESS SURVEY (ABS) INGESTION")
    print("=" * 60)
    print(f"\nYears to process: {vintages}\n")
    
    successful = []
    failed = []
    
    for vintage in vintages:
        print(f"\n>>> Processing {vintage}...")
        naics_field = get_naics_field(vintage)
        print(f"    Using NAICS field: {naics_field}")
        
        data = fetch_abs_data(vintage, naics_field)
        if data and len(data) > 1:
            count = ingest_abs_data(cur, data, vintage, naics_field)
            update_metadata(cur, vintage, count)
            conn.commit()
            print(f"  ✓ Inserted {count:,} rows")
            successful.append(vintage)
        else:
            print(f"  ✗ Failed to fetch data")
            failed.append(vintage)
        
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 60)
    print("ABS INGESTION COMPLETE")
    print("=" * 60)
    
    print(f"\nSuccessful: {successful}")
    if failed:
        print(f"Failed: {failed}")
    
    cur.execute("""
        SELECT vintage, row_count 
        FROM dataset_metadata 
        WHERE dataset_name = 'abs' 
        ORDER BY vintage DESC
    """)
    print("\nABS datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM abs_data")
    print(f"\nTotal rows in abs_data: {cur.fetchone()[0]:,}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()