import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

print("=" * 60)
print("EXPLORING ADDITIONAL CENSUS DATASETS")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# Get all datasets
discovery_url = "https://api.census.gov/data.json"
disc_response = requests.get(discovery_url)
datasets = disc_response.json().get('dataset', [])

print(f"\nTotal datasets in Census API: {len(datasets)}")

# Categorize datasets
categories = {}
for ds in datasets:
    title = ds.get('title', '')
    vintage = ds.get('c_vintage')
    
    # Categorize by keywords
    if 'Business Patterns' in title:
        cat = 'Business Patterns'
    elif 'Economic Census' in title:
        cat = 'Economic Census'
    elif 'American Community Survey' in title:
        cat = 'ACS'
    elif 'Population Estimates' in title or 'pep' in str(ds.get('c_dataset', [])).lower():
        cat = 'Population Estimates'
    elif 'Nonemployer' in title:
        cat = 'Nonemployer Statistics'
    elif 'Decennial' in title or 'dec' in str(ds.get('c_dataset', [])).lower():
        cat = 'Decennial Census'
    elif 'Business Dynamics' in title:
        cat = 'Business Dynamics'
    elif 'Annual Business Survey' in title or 'abs' in str(ds.get('c_dataset', [])).lower():
        cat = 'Annual Business Survey'
    elif 'Survey of Business Owners' in title:
        cat = 'Survey of Business Owners'
    elif 'International Trade' in title:
        cat = 'International Trade'
    elif 'Housing' in title:
        cat = 'Housing'
    else:
        cat = 'Other'
    
    if cat not in categories:
        categories[cat] = []
    categories[cat].append({
        'year': vintage,
        'title': title,
        'endpoint': ds.get('distribution', [{}])[0].get('accessURL', '')
    })

print("\n>>> Datasets by Category:\n")
for cat, items in sorted(categories.items(), key=lambda x: -len(x[1])):
    years = sorted(set(i['year'] for i in items if i['year']))
    year_range = f"{min(years)}-{max(years)}" if years else "N/A"
    print(f"  {cat}: {len(items)} datasets ({year_range})")

# Explore promising datasets we haven't ingested
print("\n" + "=" * 60)
print("EXPLORING NEW DATASETS")
print("=" * 60)

# 1. Annual Business Survey (ABS)
print("\n>>> Annual Business Survey (ABS)...")
abs_datasets = [ds for ds in datasets if 'Annual Business Survey' in ds.get('title', '')]
if abs_datasets:
    years = sorted(set(ds.get('c_vintage') for ds in abs_datasets if ds.get('c_vintage')))
    print(f"  Available years: {years}")
    
    # Test API
    time.sleep(1)
    test_url = f"https://api.census.gov/data/2021/abscs?get=NAME,NAICS2017,EMP,PAYANN,RCPSZFI&for=state:*&key={API_KEY}"
    response = requests.get(test_url)
    print(f"  Test status: {response.status_code}")
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"  ✓ Headers: {data[0]}")
            print(f"  ✓ Sample: {data[1] if len(data) > 1 else 'No data'}")
        except:
            print(f"  Response: {response.text[:200]}")

# 2. Business Dynamics Statistics (BDS)
print("\n>>> Business Dynamics Statistics (BDS)...")
bds_datasets = [ds for ds in datasets if 'Business Dynamics' in ds.get('title', '')]
if bds_datasets:
    years = sorted(set(ds.get('c_vintage') for ds in bds_datasets if ds.get('c_vintage')))
    print(f"  Available years: {years}")
    print(f"  Sample endpoints:")
    for ds in bds_datasets[:3]:
        print(f"    {ds.get('c_vintage')}: {ds.get('distribution', [{}])[0].get('accessURL', '')}")

# 3. Decennial Census
print("\n>>> Decennial Census...")
dec_datasets = [ds for ds in datasets if 'Decennial' in ds.get('title', '') or 'dec/' in ds.get('distribution', [{}])[0].get('accessURL', '')]
if dec_datasets:
    years = sorted(set(ds.get('c_vintage') for ds in dec_datasets if ds.get('c_vintage')))
    print(f"  Available years: {years}")
    
    # Test 2020 Decennial
    time.sleep(1)
    test_url = f"https://api.census.gov/data/2020/dec/pl?get=NAME,P1_001N&for=state:*&key={API_KEY}"
    response = requests.get(test_url)
    print(f"  2020 PL test status: {response.status_code}")
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"  ✓ Headers: {data[0]}")
            print(f"  ✓ Sample: {data[1] if len(data) > 1 else 'No data'}")
        except:
            print(f"  Response: {response.text[:200]}")

# 4. Survey of Business Owners
print("\n>>> Survey of Business Owners (SBO)...")
sbo_datasets = [ds for ds in datasets if 'Survey of Business Owners' in ds.get('title', '')]
if sbo_datasets:
    years = sorted(set(ds.get('c_vintage') for ds in sbo_datasets if ds.get('c_vintage')))
    print(f"  Available years: {years}")

# 5. County Business Patterns - Earlier years
print("\n>>> Checking for earlier CBP years...")
cbp_datasets = [ds for ds in datasets if 'County Business Patterns' in ds.get('title', '')]
cbp_years = sorted(set(ds.get('c_vintage') for ds in cbp_datasets if ds.get('c_vintage')))
print(f"  All available CBP years: {cbp_years}")
print(f"  Years before 2008: {[y for y in cbp_years if y and y < 2008]}")

print("\n" + "=" * 60)
print("RECOMMENDATIONS")
print("=" * 60)
print("""
Based on exploration, here are datasets to consider adding:

1. DECENNIAL CENSUS (2020, 2010)
   - Official population counts
   - Very detailed demographics
   - Available at block level
   
2. ANNUAL BUSINESS SURVEY (ABS) 
   - Business owner demographics
   - Company characteristics
   - 2017-2021 available

3. BUSINESS DYNAMICS STATISTICS (BDS)
   - Firm births and deaths
   - Job creation/destruction
   - Longitudinal data

4. EARLIER CBP YEARS (1986-2007)
   - Extend historical coverage
   - May have different API structure

5. SURVEY OF BUSINESS OWNERS (SBO)
   - Business owner characteristics
   - 2012 available
""")