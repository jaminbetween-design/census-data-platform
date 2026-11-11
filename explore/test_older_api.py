import requests

vintage = 2011
base_url = f"https://api.census.gov/data/{vintage}/cbp"

# Test without NAME, using NAICS2007_TTL for industry description
test_url = f"{base_url}?get=ESTAB,EMP,PAYANN,NAICS2007,NAICS2007_TTL&for=state:01"
response = requests.get(test_url)
print(f"Without NAME: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Headers: {data[0]}")
    print(f"Sample rows:")
    for row in data[1:5]:
        print(f"  {row}")

# Check geography variables
print("\n--- Checking geography info ---")
geo_url = f"{base_url}/geography.json"
geo_response = requests.get(geo_url)
geo_data = geo_response.json()
print(f"Geography levels: {[g['name'] for g in geo_data.get('fips', [])]}")