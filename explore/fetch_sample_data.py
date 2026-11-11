import requests
import json

# First, let's see what the examples structure looks like
base_url = "https://api.census.gov/data/2021/cbp"

examples_url = f"{base_url}/examples.json"
examples_response = requests.get(examples_url)
examples = examples_response.json()

print("=== EXAMPLES STRUCTURE ===\n")
print(json.dumps(examples, indent=2)[:1000])

print("\n" + "=" * 60)
print("=== MAKING AN ACTUAL API CALL ===\n")

# Fetch number of establishments and employees by state
# get=ESTAB,EMP means we want establishment count and employee count
# for=state:* means all states
api_call = f"{base_url}?get=ESTAB,EMP,PAYANN,NAICS2017,NAME&for=state:*"

print(f"API URL: {api_call}\n")

response = requests.get(api_call)
data = response.json()

# First row is headers
headers = data[0]
print(f"Columns: {headers}\n")

print("First 10 rows of data:")
print("-" * 60)

for row in data[1:11]:
    print(row)

print(f"\n... Total rows returned: {len(data) - 1}")

# Let's also try county-level for one state (California = 06)
print("\n" + "=" * 60)
print("=== COUNTY-LEVEL DATA (California) ===\n")

county_call = f"{base_url}?get=ESTAB,EMP,PAYANN,NAME&for=county:*&in=state:06&NAICS2017=72"
print(f"API URL: {county_call}\n")
print("(NAICS 72 = Accommodation and Food Services)\n")

county_response = requests.get(county_call)
county_data = county_response.json()

print(f"Columns: {county_data[0]}\n")
print("First 10 California counties:")
print("-" * 60)

for row in county_data[1:11]:
    print(row)

print(f"\n... Total counties returned: {len(county_data) - 1}")