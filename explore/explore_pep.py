import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

print("=" * 60)
print("EXPLORING POPULATION ESTIMATES PROGRAM (PEP)")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# Test different PEP endpoints to find what works
print("\n>>> Testing various PEP endpoints...\n")

test_endpoints = [
    ("2021 Population", "https://api.census.gov/data/2021/pep/population", "NAME,POP_2021", "state:*"),
    ("2019 Population", "https://api.census.gov/data/2019/pep/population", "NAME,POP", "state:*"),
    ("2019 CharAgeGroups", "https://api.census.gov/data/2019/pep/charagegroups", "NAME,POP", "state:*"),
    ("2018 Population", "https://api.census.gov/data/2018/pep/population", "NAME,POP", "state:*"),
]

working_endpoints = []

for name, base_url, get_vars, geo in test_endpoints:
    url = f"{base_url}?get={get_vars}&for={geo}&key={API_KEY}"
    print(f"Testing {name}...")
    print(f"  URL: {url[:80]}...")
    
    response = requests.get(url)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                print(f"  ✓ Success! Headers: {data[0]}")
                print(f"    Sample: {data[1]}")
                working_endpoints.append((name, base_url))
            else:
                print(f"  ✗ Unexpected response format")
        except Exception as e:
            print(f"  ✗ Parse error: {e}")
            print(f"    Response: {response.text[:200]}")
    else:
        print(f"  ✗ Error: {response.text[:100]}")
    
    time.sleep(1)
    print()

# Check variables for a working endpoint
if working_endpoints:
    print("=" * 60)
    print(f">>> Checking variables for {working_endpoints[0][0]}...")
    print("=" * 60)
    
    var_url = f"{working_endpoints[0][1]}/variables.json"
    var_response = requests.get(var_url)
    
    if var_response.status_code == 200:
        variables = var_response.json().get('variables', {})
        print(f"\nTotal variables: {len(variables)}")
        print("\nPopulation-related variables:")
        for var_name, var_info in variables.items():
            label = var_info.get('label', '')
            if 'pop' in var_name.lower() or 'pop' in label.lower():
                print(f"  {var_name}: {label}")
    
    # Check geography
    print("\n>>> Checking geography levels...")
    geo_url = f"{working_endpoints[0][1]}/geography.json"
    geo_response = requests.get(geo_url)
    
    if geo_response.status_code == 200:
        geo_data = geo_response.json()
        print("\nAvailable geographies:")
        for geo in geo_data.get('fips', []):
            print(f"  {geo.get('name')}")

# Test county-level
print("\n" + "=" * 60)
print(">>> Testing county-level data...")
print("=" * 60)

county_url = f"https://api.census.gov/data/2019/pep/population?get=NAME,POP&for=county:*&in=state:06&key={API_KEY}"
print(f"\nTesting California counties...")
county_response = requests.get(county_url)
print(f"Status: {county_response.status_code}")

if county_response.status_code == 200:
    try:
        data = county_response.json()
        print(f"Total counties: {len(data) - 1}")
        print(f"Headers: {data[0]}")
        print(f"Sample: {data[1:4]}")
    except Exception as e:
        print(f"Parse error: {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"\nWorking endpoints found: {len(working_endpoints)}")
for name, url in working_endpoints:
    print(f"  ✓ {name}: {url}")