import requests
import json

print("=" * 60)
print("EXPLORING ACS (American Community Survey) API")
print("=" * 60)

# ACS has multiple products - let's check what's available
# ACS 1-Year: Annual estimates for areas with 65,000+ population
# ACS 5-Year: 5-year estimates for all areas including small geographies

# Check 2022 ACS 5-Year (most comprehensive)
base_url = "https://api.census.gov/data/2022/acs/acs5"

# Get available variables
print("\n>>> Fetching ACS 5-Year variable list...")
var_url = f"{base_url}/variables.json"
response = requests.get(var_url)
variables = response.json().get('variables', {})
print(f"Total variables available: {len(variables):,}")

# Key demographic variables we want
key_vars = {
    'B01001_001E': 'Total Population',
    'B01002_001E': 'Median Age',
    'B19013_001E': 'Median Household Income',
    'B19301_001E': 'Per Capita Income',
    'B25077_001E': 'Median Home Value',
    'B25064_001E': 'Median Gross Rent',
    'B23025_002E': 'Labor Force',
    'B23025_005E': 'Unemployed',
    'B15003_022E': 'Bachelors Degree',
    'B15003_023E': 'Masters Degree',
    'B15003_025E': 'Doctorate Degree',
    'B25001_001E': 'Total Housing Units',
    'B25002_002E': 'Occupied Housing Units',
    'B25003_002E': 'Owner Occupied',
    'B25003_003E': 'Renter Occupied',
}

print("\n>>> Checking key demographic variables:")
for var_code, description in key_vars.items():
    if var_code in variables:
        print(f"  ✓ {var_code}: {description}")
    else:
        print(f"  ✗ {var_code}: {description} (NOT FOUND)")

# Check geography levels
print("\n>>> Available geography levels:")
geo_url = f"{base_url}/geography.json"
geo_response = requests.get(geo_url)
geography = geo_response.json()

for geo in geography.get('fips', [])[:15]:
    name = geo.get('name', 'Unknown')
    print(f"  {name}")

# Test API call - get population and income by state
print("\n>>> Testing API call (Population & Income by State):")
test_vars = "B01001_001E,B19013_001E,NAME"
test_url = f"{base_url}?get={test_vars}&for=state:*"

test_response = requests.get(test_url)
if test_response.status_code == 200:
    data = test_response.json()
    print(f"Headers: {data[0]}")
    print("\nSample data (first 5 states):")
    for row in data[1:6]:
        pop = int(row[0]) if row[0] else 0
        income = int(row[1]) if row[1] else 0
        print(f"  {row[2]}: Pop={pop:,}, Median Income=${income:,}")
else:
    print(f"Error: {test_response.status_code}")

# Check available years
print("\n>>> Checking ACS 5-Year available vintages:")
discovery_url = "https://api.census.gov/data.json"
disc_response = requests.get(discovery_url)
datasets = disc_response.json().get('dataset', [])

acs5_years = []
for ds in datasets:
    title = ds.get('title', '')
    if 'American Community Survey: 5-Year' in title and 'Detailed Tables' in title:
        vintage = ds.get('c_vintage')
        if vintage:
            acs5_years.append(vintage)

acs5_years = sorted(set(acs5_years))
print(f"Available years: {acs5_years}")

# Save variable list for reference
print("\n>>> Saving full variable list to data/acs_variables.json...")
with open("data/acs_variables.json", "w") as f:
    json.dump(variables, f, indent=2)

print("\nExploration complete!")