import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

# ACS variable codes to fetch
ACS_VARIABLES = {
    'B01001_001E': 'total_population',
    'B01002_001E': 'median_age',
    'B19013_001E': 'median_household_income',
    'B19301_001E': 'per_capita_income',
    'B25077_001E': 'median_home_value',
    'B25064_001E': 'median_gross_rent',
    'B25001_001E': 'total_housing_units',
    'B25002_002E': 'occupied_housing_units',
    'B25003_002E': 'owner_occupied',
    'B25003_003E': 'renter_occupied',
    'B23025_002E': 'labor_force',
    'B23025_005E': 'unemployed',
    'B15003_022E': 'bachelors_degree',
    'B15003_023E': 'masters_degree',
    'B15003_025E': 'doctorate_degree',
}

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def fetch_acs_data(vintage, geo_level, state_fips=None, retry_count=3):
    """Fetch ACS data with retry logic"""
    base_url = f"https://api.census.gov/data/{vintage}/acs/acs5"
    
    var_list = ','.join(ACS_VARIABLES.keys()) + ',NAME'
    
    if geo_level == 'state':
        url = f"{base_url}?get={var_list}&for=state:*"
    elif geo_level == 'county':
        if state_fips:
            url = f"{base_url}?get={var_list}&for=county:*&in=state:{state_fips}"
        else:
            url = f"{base_url}?get={var_list}&for=county:*&in=state:*"
    else:
        return None
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url, timeout=60)
            
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
            print(f"    Request failed: {e}")
            time.sleep(10)
    
    return None

def safe_int(value):
    if value is None or value == '' or value == 'null' or value == '-':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def safe_float(value):
    if value is None or value == '' or value == 'null' or value == '-':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def ingest_acs_data(cur, data, vintage, geo_level):
    """Insert ACS data into database"""
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
            geo_name = row[col_map['NAME']] if 'NAME' in col_map else None
            
            cur.execute("""
                INSERT INTO acs_data (
                    vintage, geo_level, state_fips, county_fips, geo_name,
                    total_population, median_age,
                    median_household_income, per_capita_income,
                    median_home_value, median_gross_rent,
                    total_housing_units, occupied_housing_units,
                    owner_occupied, renter_occupied,
                    labor_force, unemployed,
                    bachelors_degree, masters_degree, doctorate_degree
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                vintage,
                geo_level,
                state_fips,
                county_fips,
                geo_name,
                safe_int(row[col_map['B01001_001E']]),
                safe_float(row[col_map['B01002_001E']]),
                safe_int(row[col_map['B19013_001E']]),
                safe_int(row[col_map['B19301_001E']]),
                safe_int(row[col_map['B25077_001E']]),
                safe_int(row[col_map['B25064_001E']]),
                safe_int(row[col_map['B25001_001E']]),
                safe_int(row[col_map['B25002_002E']]),
                safe_int(row[col_map['B25003_002E']]),
                safe_int(row[col_map['B25003_003E']]),
                safe_int(row[col_map['B23025_002E']]),
                safe_int(row[col_map['B23025_005E']]),
                safe_int(row[col_map['B15003_022E']]),
                safe_int(row[col_map['B15003_023E']]),
                safe_int(row[col_map['B15003_025E']]),
            ))
            inserted += 1
        except Exception as e:
            continue
    
    return inserted

def update_metadata(cur, vintage, row_count):
    """Record ingestion in metadata"""
    cur.execute("""
        INSERT INTO dataset_metadata (dataset_name, vintage, api_endpoint, description, row_count)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (dataset_name, vintage) 
        DO UPDATE SET row_count = %s, ingested_at = CURRENT_TIMESTAMP
    """, (
        'acs5',
        vintage,
        f'https://api.census.gov/data/{vintage}/acs/acs5',
        'American Community Survey 5-Year Estimates',
        row_count,
        row_count
    ))

def main():
    vintages = [2022, 2021, 2020, 2019, 2018, 2015, 2010, 2009]
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("CENSUS DATA INGESTION - American Community Survey (ACS 5-Year)")
    print("=" * 60)
    print(f"\nYears to process: {vintages}")
    print("Fetching: Population, Income, Housing, Employment, Education\n")
    
    for vintage in vintages:
        print(f"\n>>> Processing {vintage}...")
        total_rows = 0
        
        # State-level data
        print(f"  Fetching state-level data...")
        time.sleep(2)  # Rate limiting
        state_data = fetch_acs_data(vintage, 'state')
        if state_data:
            count = ingest_acs_data(cur, state_data, vintage, 'state')
            total_rows += count
            print(f"  ✓ Inserted {count} state rows")
        else:
            print(f"  ✗ Failed to fetch state data")
        
        # County-level data
        print(f"  Fetching county-level data...")
        time.sleep(2)  # Rate limiting
        county_data = fetch_acs_data(vintage, 'county')
        if county_data:
            count = ingest_acs_data(cur, county_data, vintage, 'county')
            total_rows += count
            print(f"  ✓ Inserted {count} county rows")
        else:
            print(f"  ✗ Failed to fetch county data")
        
        # Commit and update metadata
        if total_rows > 0:
            update_metadata(cur, vintage, total_rows)
            conn.commit()
            print(f"  ✓ Total for {vintage}: {total_rows} rows")
        
        # Longer delay between years
        time.sleep(5)
    
    # Summary
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    
    cur.execute("""
        SELECT vintage, row_count 
        FROM dataset_metadata 
        WHERE dataset_name = 'acs5' 
        ORDER BY vintage DESC
    """)
    print("\nACS 5-Year datasets:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM acs_data")
    total = cur.fetchone()[0]
    print(f"\nTotal rows in acs_data: {total:,}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()