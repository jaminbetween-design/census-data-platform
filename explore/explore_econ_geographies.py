import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def safe_float(value):
    if value is None or value == '' or value == 'null' or value == 'N' or value == 'D' or value == 'S' or value == 'NA':
        return None
    try:
        return float(str(value).replace(',', ''))
    except:
        return None

print("=" * 70)
print("ECONOMIC INDICATORS - EXPLORING GEOGRAPHIES")
print("=" * 70)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# First, let's explore what geographies are available for each indicator
INDICATORS = [
    'hv', 'resconst', 'ressales', 'marts', 'mrts', 'mwts', 
    'vip', 'm3', 'advm3', 'mtis', 'ftd', 'qfr', 'qss', 'qtax', 'qpr', 'bfs', 'mhs2'
]

print("\n>>> Checking available geographies for each indicator...")

for code in INDICATORS:
    geo_url = f"https://api.census.gov/data/timeseries/eits/{code}/geography.json"
    
    try:
        response = requests.get(geo_url, timeout=30)
        if response.status_code == 200:
            geo_data = response.json()
            geos = geo_data.get('fips', [])
            geo_names = [g.get('name', '') for g in geos]
            print(f"  {code}: {geo_names}")
        else:
            print(f"  {code}: No geography endpoint (national only)")
    except Exception as e:
        print(f"  {code}: Error - {e}")
    
    time.sleep(0.3)

# Now let's check the variables for a few key indicators
print("\n>>> Checking variables for key indicators...")

for code in ['hv', 'resconst', 'marts', 'bfs']:
    var_url = f"https://api.census.gov/data/timeseries/eits/{code}/variables.json"
    
    try:
        response = requests.get(var_url, timeout=30)
        if response.status_code == 200:
            variables = response.json().get('variables', {})
            print(f"\n  {code} variables ({len(variables)} total):")
            for var_name in list(variables.keys())[:15]:
                label = variables[var_name].get('label', '')[:50]
                print(f"    {var_name}: {label}")
    except:
        pass
    
    time.sleep(0.3)

# Test different geography queries
print("\n>>> Testing geography queries...")

test_queries = [
    # Housing Vacancies - try different geo levels
    (f"https://api.census.gov/data/timeseries/eits/hv?get=cell_value,data_type_code,time_slot_id,category_code&time=2023&key={API_KEY}", "HV national"),
    (f"https://api.census.gov/data/timeseries/eits/hv?get=cell_value,data_type_code,time_slot_id,category_code&for=state:*&time=2023&key={API_KEY}", "HV by state"),
    (f"https://api.census.gov/data/timeseries/eits/hv?get=cell_value,data_type_code,time_slot_id,category_code&for=region:*&time=2023&key={API_KEY}", "HV by region"),
    
    # New Residential Construction
    (f"https://api.census.gov/data/timeseries/eits/resconst?get=cell_value,data_type_code,time_slot_id,category_code&time=2023&key={API_KEY}", "ResConst national"),
    (f"https://api.census.gov/data/timeseries/eits/resconst?get=cell_value,data_type_code,time_slot_id,category_code&for=state:*&time=2023&key={API_KEY}", "ResConst by state"),
    (f"https://api.census.gov/data/timeseries/eits/resconst?get=cell_value,data_type_code,time_slot_id,category_code&for=region:*&time=2023&key={API_KEY}", "ResConst by region"),
    
    # Business Formation Statistics
    (f"https://api.census.gov/data/timeseries/eits/bfs?get=cell_value,data_type_code,time_slot_id,category_code&time=2023&key={API_KEY}", "BFS national"),
    (f"https://api.census.gov/data/timeseries/eits/bfs?get=cell_value,data_type_code,time_slot_id,category_code&for=state:*&time=2023&key={API_KEY}", "BFS by state"),
    
    # Retail Trade
    (f"https://api.census.gov/data/timeseries/eits/marts?get=cell_value,data_type_code,time_slot_id,category_code&time=2023&key={API_KEY}", "Retail national"),
    (f"https://api.census.gov/data/timeseries/eits/marts?get=cell_value,data_type_code,time_slot_id,category_code&for=state:*&time=2023&key={API_KEY}", "Retail by state"),
    
    # Quarterly Taxes - likely has state data
    (f"https://api.census.gov/data/timeseries/eits/qtax?get=cell_value,data_type_code,time_slot_id,category_code&time=2023&key={API_KEY}", "QTax national"),
    (f"https://api.census.gov/data/timeseries/eits/qtax?get=cell_value,data_type_code,time_slot_id,category_code&for=state:*&time=2023&key={API_KEY}", "QTax by state"),
]

working_geo_queries = []

for url, desc in test_queries:
    print(f"\n  Testing {desc}...")
    print(f"    URL: {url[:70]}...")
    
    try:
        response = requests.get(url, timeout=60)
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 200 and response.text:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    print(f"    ✓ Headers: {data[0]}")
                    print(f"      Rows: {len(data) - 1}")
                    working_geo_queries.append((url, desc, len(data) - 1))
            except:
                pass
    except Exception as e:
        print(f"    Error: {e}")
    
    time.sleep(0.5)

print("\n" + "=" * 70)
print("SUMMARY OF WORKING GEOGRAPHY QUERIES")
print("=" * 70)

for url, desc, rows in working_geo_queries:
    print(f"  ✓ {desc}: {rows} rows")

print(f"\nTotal working queries: {len(working_geo_queries)}")
print("\nNote: Most Economic Indicators are national-level only.")
print("State/regional breakdowns are limited to specific indicators.")