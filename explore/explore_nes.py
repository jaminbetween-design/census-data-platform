import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ["CENSUS_API_KEY"]

print("=" * 60)
print("EXPLORING NONEMPLOYER STATISTICS (NES)")
print("=" * 60)

# Check what NES datasets exist
print("\n>>> Finding NES datasets...")
discovery_url = "https://api.census.gov/data.json"
disc_response = requests.get(discovery_url)
datasets = disc_response.json().get('dataset', [])

nes_datasets = []
for ds in datasets:
    title = ds.get('title', '')
    if 'Nonemployer' in title:
        vintage = ds.get('c_vintage')
        endpoint = ds.get('distribution', [{}])[0].get('accessURL', '')
        nes_datasets.append({
            'year': vintage,
            'title': title,
            'endpoint': endpoint
        })

nes_datasets.sort(key=lambda x: x['year'] if x['year'] else 0, reverse=True)
print(f"\nFound {len(nes_datasets)} NES datasets")
print("\nMost recent datasets:")
for ds in nes_datasets[:10]:
    print(f"  {ds['year']}: {ds['endpoint']}")

# Check variables for recent year
print("\n>>> Checking NES variables (2021)...")
time.sleep(2)

var_url = "https://api.census.gov/data/2021/nonemp/variables.json"
var_response = requests.get(var_url)

if var_response.status_code == 200:
    variables = var_response.json().get('variables', {})
    print(f"Total variables: {len(variables)}")
    
    print("\nKey variables:")
    for var_name, var_info in list(variables.items())[:15]:
        label = var_info.get('label', 'No label')
        print(f"  {var_name}: {label}")
else:
    print(f"Error: {var_response.status_code}")

# Check geography
print("\n>>> Checking geography levels...")
time.sleep(1)

geo_url = "https://api.census.gov/data/2021/nonemp/geography.json"
geo_response = requests.get(geo_url)

if geo_response.status_code == 200:
    geo_data = geo_response.json()
    for geo in geo_data.get('fips', []):
        print(f"  {geo.get('name')}")

# Test API call
print("\n>>> Testing NES API call...")
time.sleep(2)

test_url = f"https://api.census.gov/data/2021/nonemp?get=NAICS2017,NESTAB,NRCPTOT,GEO_ID,NAME&for=state:*&key={API_KEY}"
test_response = requests.get(test_url)

if test_response.status_code == 200:
    data = test_response.json()
    print(f"Headers: {data[0]}")
    print(f"\nSample rows:")
    for row in data[1:6]:
        print(f"  {row}")
    print(f"\nTotal rows: {len(data) - 1}")
else:
    print(f"Error: {test_response.status_code}")
    print(f"Response: {test_response.text[:300]}")

# Test county level
print("\n>>> Testing county-level query...")
time.sleep(2)

county_url = f"https://api.census.gov/data/2021/nonemp?get=NAICS2017,NESTAB,NRCPTOT,NAME&for=county:*&in=state:06&key={API_KEY}"
county_response = requests.get(county_url)

if county_response.status_code == 200:
    county_data = county_response.json()
    print(f"California counties: {len(county_data) - 1} rows")
    print(f"Sample: {county_data[1:3]}")
else:
    print(f"Error: {county_response.status_code}")