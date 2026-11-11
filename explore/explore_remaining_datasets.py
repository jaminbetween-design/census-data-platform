import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

print("=" * 60)
print("COMPREHENSIVE CENSUS API DATASET EXPLORATION")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# Get all datasets
discovery_url = "https://api.census.gov/data.json"
disc_response = requests.get(discovery_url)
datasets = disc_response.json().get('dataset', [])

print(f"\nTotal datasets in Census API: {len(datasets)}")

# What we already have
already_have = [
    'County Business Patterns',
    'ZIP Code Business Patterns',  
    'Nonemployer Statistics',
    'American Community Survey',
    'Population Estimates',
    'Economic Census',
    'Decennial Census',
    'Annual Business Survey'
]

# Categorize all datasets
categories = {}
for ds in datasets:
    title = ds.get('title', '')
    vintage = ds.get('c_vintage')
    endpoint = ds.get('distribution', [{}])[0].get('accessURL', '')
    
    # Skip if no endpoint
    if not endpoint:
        continue
    
    # Categorize
    if 'Business Patterns' in title:
        cat = 'Business Patterns (HAVE)'
    elif 'Economic Census' in title:
        cat = 'Economic Census (HAVE)'
    elif 'American Community Survey' in title:
        cat = 'ACS (HAVE)'
    elif 'Population Estimates' in title or '/pep/' in endpoint:
        cat = 'Population Estimates (HAVE)'
    elif 'Nonemployer' in title:
        cat = 'Nonemployer (HAVE)'
    elif 'Decennial' in title or '/dec/' in endpoint:
        cat = 'Decennial (HAVE)'
    elif 'Annual Business Survey' in title or '/abs' in endpoint:
        cat = 'ABS (HAVE)'
    elif 'Survey of Business Owners' in title or '/sbo' in endpoint:
        cat = 'Survey of Business Owners'
    elif 'Business Dynamics' in title or '/bds' in endpoint:
        cat = 'Business Dynamics Statistics'
    elif 'International Trade' in title or '/trade' in endpoint:
        cat = 'International Trade'
    elif 'Small Area Income' in title or '/saipe' in endpoint:
        cat = 'Small Area Income/Poverty'
    elif 'Small Area Health' in title or '/sahie' in endpoint:
        cat = 'Small Area Health Insurance'
    elif 'Annual Survey of Manufactures' in title or '/asm' in endpoint:
        cat = 'Annual Survey of Manufactures'
    elif 'Commodity Flow' in title or '/cfs' in endpoint:
        cat = 'Commodity Flow Survey'
    elif 'Public Sector' in title or '/pub' in endpoint:
        cat = 'Public Sector (Government)'
    elif 'Housing' in title:
        cat = 'Housing Surveys'
    elif 'Quarterly' in title or '/qwi' in endpoint:
        cat = 'Quarterly Workforce Indicators'
    elif 'LEHD' in title or '/lehd' in endpoint:
        cat = 'LEHD (Employment Dynamics)'
    elif 'Health Insurance' in title:
        cat = 'Health Insurance'
    elif 'Poverty' in title:
        cat = 'Poverty Statistics'
    elif 'Language' in title:
        cat = 'Language Statistics'
    else:
        cat = 'Other'
    
    if cat not in categories:
        categories[cat] = []
    categories[cat].append({
        'year': vintage,
        'title': title[:60],
        'endpoint': endpoint
    })

# Show categories we DON'T have yet
print("\n" + "=" * 60)
print("DATASETS WE DON'T HAVE YET")
print("=" * 60)

new_datasets = {}
for cat, items in sorted(categories.items(), key=lambda x: -len(x[1])):
    if '(HAVE)' not in cat:
        years = sorted(set(i['year'] for i in items if i['year']))
        year_str = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0]) if years else "N/A"
        print(f"\n{cat}: {len(items)} datasets ({year_str})")
        new_datasets[cat] = items
        
        # Show sample endpoints
        for item in items[:3]:
            print(f"  {item['year']}: {item['endpoint']}")

# Test promising new datasets
print("\n" + "=" * 60)
print("TESTING NEW DATASETS")
print("=" * 60)

test_configs = [
    {
        'name': 'Survey of Business Owners (2012)',
        'url': f"https://api.census.gov/data/2012/sbo?get=NAME,NAICS2012,FIRMPDEMP,RCPPDEMP,EMP&for=state:*&key={API_KEY}"
    },
    {
        'name': 'Small Area Income/Poverty (2022)',
        'url': f"https://api.census.gov/data/timeseries/poverty/saipe?get=NAME,SAEPOVALL_PT,SAEPOVRTALL_PT,YEAR&for=state:*&YEAR=2022&key={API_KEY}"
    },
    {
        'name': 'Small Area Health Insurance (2022)',
        'url': f"https://api.census.gov/data/timeseries/healthins/sahie?get=NAME,NUI_PT,NIC_PT,YEAR&for=state:*&YEAR=2022&key={API_KEY}"
    },
    {
        'name': 'Annual Survey of Manufactures (2021)',
        'url': f"https://api.census.gov/data/2021/asm/state?get=NAICS2017,EMP,PAYANN,VALADD&for=state:*&key={API_KEY}"
    },
    {
        'name': 'Business Dynamics Statistics',
        'url': f"https://api.census.gov/data/timeseries/bds?get=NAME,YEAR,FIRM,ESTAB,EMP&for=state:*&YEAR=2021&key={API_KEY}"
    },
    {
        'name': 'Quarterly Workforce Indicators',
        'url': f"https://api.census.gov/data/timeseries/qwi/sa?get=Emp,EarnS&for=state:01&year=2022&quarter=1&key={API_KEY}"
    },
    {
        'name': 'Public Sector Employment (2022)',
        'url': f"https://api.census.gov/data/2022/apes?get=NAME,EMP,PAYROLL&for=state:*&key={API_KEY}"
    },
]

working = []
for config in test_configs:
    print(f"\n>>> Testing {config['name']}...")
    print(f"    URL: {config['url'][:70]}...")
    
    try:
        response = requests.get(config['url'], timeout=60)
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    print(f"    ✓ Success! Headers: {data[0]}")
                    print(f"      Sample: {data[1]}")
                    print(f"      Rows: {len(data) - 1}")
                    working.append(config['name'])
            except Exception as e:
                print(f"    Parse error: {e}")
                print(f"    Response: {response.text[:200]}")
        else:
            print(f"    Error: {response.text[:150]}")
    except Exception as e:
        print(f"    Request error: {e}")
    
    time.sleep(2)

print("\n" + "=" * 60)
print("SUMMARY - DATASETS READY TO ADD")
print("=" * 60)
print(f"\nWorking datasets: {working}")
print("""
RECOMMENDED ORDER:
1. Small Area Income/Poverty (SAIPE) - poverty rates by county
2. Small Area Health Insurance (SAHIE) - uninsured rates
3. Business Dynamics Statistics (BDS) - firm births/deaths
4. Survey of Business Owners (SBO) - owner demographics
5. Annual Survey of Manufactures (ASM) - manufacturing detail
6. Public Sector Employment - government employment
""")