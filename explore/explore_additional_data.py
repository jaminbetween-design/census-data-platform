import requests
import json

print("=" * 60)
print("EXPLORING ADDITIONAL CENSUS DATASETS")
print("=" * 60)

# 1. ZIP Code Business Patterns
print("\n>>> ZIP Code Business Patterns (ZBP)")
print("-" * 40)
zbp_url = "https://api.census.gov/data/2021/zbp"
var_response = requests.get(f"{zbp_url}/variables.json")
if var_response.status_code == 200:
    zbp_vars = var_response.json().get('variables', {})
    print(f"Variables available: {len(zbp_vars)}")
    key_vars = ['ESTAB', 'EMP', 'PAYANN', 'ZIPCODE', 'NAICS2017']
    for v in key_vars:
        status = "✓" if v in zbp_vars else "✗"
        print(f"  {status} {v}")
    
    # Test call
    test_url = f"{zbp_url}?get=ZIPCODE,ESTAB,NAICS2017&for=zipcode:90210"
    test_resp = requests.get(test_url)
    if test_resp.status_code == 200:
        print(f"  Sample data for 90210: {test_resp.json()[:3]}")

# 2. Check what ACS years are available
print("\n>>> ACS 5-Year Available Vintages")
print("-" * 40)
discovery_url = "https://api.census.gov/data.json"
disc_response = requests.get(discovery_url)
datasets = disc_response.json().get('dataset', [])

acs5_years = set()
for ds in datasets:
    title = ds.get('title', '')
    if 'American Community Survey: 5-Year' in title:
        vintage = ds.get('c_vintage')
        if vintage:
            acs5_years.add(vintage)

print(f"All ACS 5-Year years: {sorted(acs5_years)}")

# 3. Economic Census
print("\n>>> Economic Census")
print("-" * 40)
ec_years = []
for ds in datasets:
    title = ds.get('title', '')
    if 'Economic Census' in title:
        vintage = ds.get('c_vintage')
        if vintage and vintage not in ec_years:
            ec_years.append(vintage)
            if len(ec_years) <= 5:
                print(f"  {vintage}: {title[:60]}...")

# 4. Population Estimates
print("\n>>> Population Estimates Program")
print("-" * 40)
pep_years = []
for ds in datasets:
    title = ds.get('title', '')
    c_dataset = ds.get('c_dataset', [])
    if 'pep' in str(c_dataset).lower() or 'Population Estimates' in title:
        vintage = ds.get('c_vintage')
        if vintage and vintage >= 2015:
            pep_years.append(vintage)

print(f"Available years (2015+): {sorted(set(pep_years))}")

# 5. Nonemployer Statistics
print("\n>>> Nonemployer Statistics (NES)")
print("-" * 40)
nes_count = 0
for ds in datasets:
    title = ds.get('title', '')
    if 'Nonemployer' in title:
        nes_count += 1
        if nes_count <= 3:
            vintage = ds.get('c_vintage')
            print(f"  {vintage}: {title[:60]}...")

print(f"Total NES datasets: {nes_count}")

# Summary recommendation
print("\n" + "=" * 60)
print("RECOMMENDATION SUMMARY")
print("=" * 60)
print("""
1. ZIP Code Business Patterns (ZBP)
   - More granular than county (41,000+ ZIP codes)
   - Same variables as CBP (establishments, employees, payroll)
   - Great for local market analysis
   
2. ACS Additional Years (2011-2014)
   - Fill gap in demographic coverage
   - May need adjusted variable list
   
3. Nonemployer Statistics (NES)
   - Self-employed/sole proprietors without employees
   - Complements CBP which only covers employers
   
4. Population Estimates
   - Annual population estimates between Census years
   - More current than ACS for population counts
""")