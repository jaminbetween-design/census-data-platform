import requests
import json

# Let's look at a recent County Business Patterns dataset
base_url = "https://api.census.gov/data/2021/cbp"

# Fetch variables
print("=== FETCHING VARIABLES ===\n")
variables_url = f"{base_url}/variables.json"
var_response = requests.get(variables_url)
variables = var_response.json()

# Save for reference
with open("data/cbp_2021_variables.json", "w") as f:
    json.dump(variables, f, indent=2)

var_list = variables.get('variables', {})
print(f"Total variables: {len(var_list)}\n")

print("Sample variables:")
for i, (var_name, var_info) in enumerate(list(var_list.items())[:15]):
    label = var_info.get('label', 'No label')
    print(f"  {var_name}: {label}")

# Fetch geography levels
print("\n" + "=" * 60)
print("=== GEOGRAPHY LEVELS ===\n")

geo_url = f"{base_url}/geography.json"
geo_response = requests.get(geo_url)
geography = geo_response.json()

with open("data/cbp_2021_geography.json", "w") as f:
    json.dump(geography, f, indent=2)

for geo in geography.get('fips', []):
    name = geo.get('name', 'Unknown')
    requires = geo.get('requires', [])
    print(f"  {name}")
    if requires:
        print(f"    Requires: {requires}")

# Fetch example API calls
print("\n" + "=" * 60)
print("=== EXAMPLE API CALLS ===\n")

examples_url = f"{base_url}/examples.json"
examples_response = requests.get(examples_url)
examples = examples_response.json()

for example in examples[:5]:
    print(f"  {example}\n")