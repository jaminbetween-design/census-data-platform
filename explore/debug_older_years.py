import requests
import json

def check_year(vintage):
    print(f"\n{'=' * 60}")
    print(f"Checking {vintage}")
    print('=' * 60)
    
    # Check if CBP exists for this year
    base_url = f"https://api.census.gov/data/{vintage}/cbp"
    
    # Get variables
    var_url = f"{base_url}/variables.json"
    var_response = requests.get(var_url)
    
    if var_response.status_code != 200:
        print(f"Variables endpoint failed: {var_response.status_code}")
        return
    
    variables = var_response.json().get('variables', {})
    
    # Find available fields
    print(f"\nAvailable variables ({len(variables)} total):")
    key_fields = ['ESTAB', 'EMP', 'PAYANN', 'NAME', 'NAICS', 'NAICS2007', 'NAICS2012', 'NAICS2017']
    for field in key_fields:
        if field in variables:
            print(f"  ✓ {field}")
        else:
            print(f"  ✗ {field}")
    
    # Show all NAICS-related fields
    naics_fields = [k for k in variables.keys() if 'NAICS' in k.upper()]
    print(f"\nAll NAICS fields found: {naics_fields}")
    
    # Try a simple API call
    print(f"\nTesting API calls:")
    
    # Try with different NAICS fields
    for naics_field in naics_fields:
        test_url = f"{base_url}?get=ESTAB,EMP,NAME,{naics_field}&for=state:01"
        response = requests.get(test_url)
        print(f"  {naics_field}: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"    Sample: {data[:2]}")
        else:
            print(f"    Error: {response.text[:200]}")

# Check problematic years
for year in [2011, 2010, 2009, 2008]:
    check_year(year)