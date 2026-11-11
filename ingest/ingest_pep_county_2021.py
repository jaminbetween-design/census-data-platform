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
    if value is None or value == '' or value == 'null':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def safe_float(value):
    if value is None or value == '' or value == 'null':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

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
    
    conn = connect_db()
    cur = conn.cursor()
    
    print("=" * 60)
    print("PEP 2021 COUNTY DATA - State by State")
    print("=" * 60)
    
    # First, test what works
    print("\n>>> Testing 2021 county endpoint...")
    
    # Try different URL formats
    test_urls = [
        f"https://api.census.gov/data/2021/pep/population?get=NAME,POP_2020,POP_2021&for=county:*&in=state:06&key={API_KEY}",
        f"https://api.census.gov/data/2021/pep/population?get=NAME,POP_2021&for=county:*&in=state:06&key={API_KEY}",
    ]
    
    working_url = None
    for url in test_urls:
        print(f"  Testing: {url[:70]}...")
        response = requests.get(url, timeout=60)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    print(f"  ✓ Success! Headers: {data[0]}")
                    print(f"    Sample: {data[1]}")
                    working_url = url.replace("state:06", "state:{state}")
                    break
            except:
                pass
        time.sleep(1)
    
    if not working_url:
        print("\n  ✗ Could not find working endpoint for 2021 county data")
        print("    Skipping 2021 county ingestion")
        return
    
    print(f"\n>>> Ingesting county data state by state...")
    
    total_2020 = 0
    total_2021 = 0
    
    for i, state_fips in enumerate(STATE_FIPS):
        url = working_url.replace("{state}", state_fips)
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            try:
                data = response.json()
                headers = data[0]
                rows = data[1:]
                col_map = {col: idx for idx, col in enumerate(headers)}
                
                for row in rows:
                    county_fips = row[col_map.get('county')]
                    geo_name = row[col_map['NAME']]
                    
                    # Insert 2020 if available
                    if 'POP_2020' in col_map:
                        cur.execute("""
                            INSERT INTO pep_data (vintage, geo_level, state_fips, county_fips, geo_name, population)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (2020, 'county', state_fips, county_fips, geo_name, safe_int(row[col_map['POP_2020']])))
                        total_2020 += 1
                    
                    # Insert 2021
                    if 'POP_2021' in col_map:
                        cur.execute("""
                            INSERT INTO pep_data (vintage, geo_level, state_fips, county_fips, geo_name, population)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (2021, 'county', state_fips, county_fips, geo_name, safe_int(row[col_map['POP_2021']])))
                        total_2021 += 1
                
            except Exception as e:
                print(f"  Error processing state {state_fips}: {e}")
        
        if (i + 1) % 10 == 0:
            conn.commit()
            print(f"  Processed {i + 1}/{len(STATE_FIPS)} states...")
        
        time.sleep(0.3)
    
    conn.commit()
    
    print(f"\n✓ Added {total_2020:,} county rows for 2020")
    print(f"✓ Added {total_2021:,} county rows for 2021")
    
    # Update metadata
    cur.execute("SELECT vintage, COUNT(*) FROM pep_data GROUP BY vintage ORDER BY vintage")
    print("\nPEP data by year:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} rows")
    
    cur.execute("SELECT COUNT(*) FROM pep_data")
    print(f"\nTotal PEP rows: {cur.fetchone()[0]:,}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()