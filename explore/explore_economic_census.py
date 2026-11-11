import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

print("=" * 60)
print("EXPLORING ECONOMIC CENSUS")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# Find Economic Census datasets
print("\n>>> Finding Economic Census datasets...")
discovery_url = "https://api.census.gov/data.json"
disc_response = requests.get(discovery_url)
datasets = disc_response.json().get('dataset', [])

ec_datasets = []
for ds in datasets:
    title = ds.get('title', '')
    if 'Economic Census' in title or 'ecn' in str(ds.get('c_dataset', [])).lower():
        vintage = ds.get('c_vintage')
        endpoint = ds.get('distribution', [{}])[0].get('accessURL', '')
        ec_datasets.append({
            'year': vintage,
            'title': title,
            'endpoint': endpoint
        })

ec_datasets.sort(key=lambda x: x['year'] if x['year'] else 0, reverse=True)
print(f"\nFound {len(ec_datasets)} Economic Census datasets:\n")

# Show unique years
years = sorted(set(ds['year'] for ds in ec_datasets if ds['year']), reverse=True)
print(f"Available years: {years}")

print("\nSample datasets:")
for ds in ec_datasets[:10]:
    print(f"  {ds['year']}: {ds['title'][:60]}...")
    print(f"         {ds['endpoint']}")

# Test 2017 Economic Census (most recent complete)
print("\n" + "=" * 60)
print(">>> Testing 2017 Economic Census...")
print("=" * 60)

# Check variables
time.sleep(2)
var_url = "https://api.census.gov/data/2017/ecnbasic/variables.json"
print(f"\nFetching variables from: {var_url}")
var_response = requests.get(var_url)
print(f"Status: {var_response.status_code}")

if var_response.status_code == 200:
    variables = var_response.json().get('variables', {})
    print(f"Total variables: {len(variables)}")
    
    print("\nKey variables:")
    key_terms = ['ESTAB', 'EMP', 'PAYANN', 'RCPTOT', 'NAICS', 'NAME', 'GEO']
    for var_name, var_info in variables.items():
        label = var_info.get('label', '')
        for term in key_terms:
            if term in var_name.upper():
                print(f"  {var_name}: {label}")
                break
else:
    print(f"Error: {var_response.text[:200]}")

# Check geography
print("\n>>> Checking geography levels...")
time.sleep(1)
geo_url = "https://api.census.gov/data/2017/ecnbasic/geography.json"
geo_response = requests.get(geo_url)

if geo_response.status_code == 200:
    geo_data = geo_response.json()
    print("\nAvailable geographies:")
    for geo in geo_data.get('fips', []):
        print(f"  {geo.get('name')}")

# Test API call
print("\n>>> Testing API call...")
time.sleep(2)

test_url = f"https://api.census.gov/data/2017/ecnbasic?get=NAME,NAICS2017,NAICS2017_LABEL,ESTAB,EMP,PAYANN,RCPTOT&for=state:*&NAICS2017=00&key={API_KEY}"
print(f"URL: {test_url[:80]}...")

response = requests.get(test_url)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"\nSample rows:")
        for row in data[1:5]:
            print(f"  {row}")
        print(f"\nTotal rows: {len(data) - 1}")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Response: {response.text[:300]}")
else:
    print(f"Error: {response.text[:300]}")

# Test 2012 Economic Census
print("\n" + "=" * 60)
print(">>> Testing 2012 Economic Census...")
print("=" * 60)
time.sleep(2)

test_url_2012 = f"https://api.census.gov/data/2012/ecnbasic?get=NAME,NAICS2012,NAICS2012_TTL,ESTAB,EMP,PAYANN,RCPTOT&for=state:*&NAICS2012=00&key={API_KEY}"
print(f"URL: {test_url_2012[:80]}...")

response_2012 = requests.get(test_url_2012)
print(f"Status: {response_2012.status_code}")

if response_2012.status_code == 200:
    try:
        data = response_2012.json()
        print(f"Headers: {data[0]}")
        print(f"Sample: {data[1:3]}")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Response: {response_2012.text[:300]}")
else:
    print(f"Error: {response_2012.text[:300]}")