import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

print("=" * 70)
print("EXPLORING REMAINING CENSUS DATASETS")
print("=" * 70)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# Get all datasets
discovery_url = "https://api.census.gov/data.json"
disc_response = requests.get(discovery_url)
datasets = disc_response.json().get('dataset', [])

print(f"\nTotal datasets in Census API: {len(datasets)}")

# What we already have
already_have_keywords = [
    'business patterns', 'cbp', 'zbp',
    'nonemployer', 'nes',
    'economic census', 'ecn',
    'american community survey', 'acs',
    'population estimates', 'pep',
    'decennial', 'dec',
    'annual business survey', 'abs',
    'saipe', 'poverty',
    'sahie', 'health insurance',
    'business dynamics', 'bds',
    'survey of business owners', 'sbo',
    'current population survey', 'cps'
]

def is_already_have(title, endpoint):
    title_lower = title.lower()
    endpoint_lower = endpoint.lower()
    for kw in already_have_keywords:
        if kw in title_lower or kw in endpoint_lower:
            return True
    return False

# Find datasets we don't have
new_datasets = []
for ds in datasets:
    title = ds.get('title', '')
    endpoint = ds.get('distribution', [{}])[0].get('accessURL', '')
    vintage = ds.get('c_vintage')
    
    if not is_already_have(title, endpoint):
        new_datasets.append({
            'title': title,
            'endpoint': endpoint,
            'vintage': vintage
        })

# Group by category
categories = {}
for ds in new_datasets:
    title = ds['title'].lower()
    endpoint = ds['endpoint'].lower()
    
    if 'trade' in title or 'intltrade' in endpoint:
        cat = 'International Trade'
    elif 'manufactur' in title or '/asm' in endpoint:
        cat = 'Annual Survey of Manufactures'
    elif 'commodity' in title or 'cfs' in endpoint:
        cat = 'Commodity Flow Survey'
    elif 'qwi' in endpoint or 'workforce' in title:
        cat = 'Quarterly Workforce Indicators'
    elif 'lehd' in endpoint:
        cat = 'LEHD'
    elif 'housing' in title or 'rhfs' in endpoint:
        cat = 'Housing'
    elif 'eits' in endpoint:
        cat = 'Economic Indicators'
    elif 'public' in title or 'gov' in title:
        cat = 'Public Sector'
    elif 'retail' in title or 'wholesale' in title:
        cat = 'Retail/Wholesale'
    elif 'service' in title:
        cat = 'Service Industries'
    else:
        cat = 'Other'
    
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(ds)

print("\n" + "=" * 70)
print("DATASETS WE DON'T HAVE YET (by category)")
print("=" * 70)

for cat in sorted(categories.keys(), key=lambda x: -len(categories[x])):
    items = categories[cat]
    years = sorted(set(i['vintage'] for i in items if i['vintage']))
    year_str = f"{min(years)}-{max(years)}" if len(years) > 1 else str(years[0]) if years else "timeseries"
    print(f"\n{cat}: {len(items)} datasets ({year_str})")
    
    # Show first 3 endpoints
    for item in items[:3]:
        print(f"  {item['vintage'] or 'TS'}: {item['endpoint'][:70]}...")

# Test promising datasets
print("\n" + "=" * 70)
print("TESTING PROMISING DATASETS")
print("=" * 70)

test_configs = [
    {
        'name': 'Annual Survey of Manufactures (ASM)',
        'url': f"https://api.census.gov/data/timeseries/asm/state?get=NAICS2017,EMP,PAYANN,VALADD&for=state:*&YEAR=2021&key={API_KEY}"
    },
    {
        'name': 'Quarterly Services Survey',
        'url': f"https://api.census.gov/data/timeseries/qss?get=data_type_code,cell_value&time=2023-Q1&category_code=TOTAL&key={API_KEY}"
    },
    {
        'name': 'Annual Retail Trade Survey',
        'url': f"https://api.census.gov/data/timeseries/arts?get=NAICS2017,SALES,ESTAB&for=us:*&YEAR=2021&key={API_KEY}"
    },
    {
        'name': 'Annual Wholesale Trade Survey',
        'url': f"https://api.census.gov/data/timeseries/awts?get=NAICS2017,SALES&for=us:*&YEAR=2021&key={API_KEY}"
    },
    {
        'name': 'Service Annual Survey',
        'url': f"https://api.census.gov/data/timeseries/sas?get=NAICS2017,RCPTOT,YEAR&for=us:*&YEAR=2021&key={API_KEY}"
    },
    {
        'name': 'Quarterly Financial Report (Manufacturing)',
        'url': f"https://api.census.gov/data/timeseries/eits/qfr?get=data_type_code,cell_value&time=2023-Q1&category_code=310&seasonally_adj=no&key={API_KEY}"
    },
    {
        'name': 'Monthly Retail Trade',
        'url': f"https://api.census.gov/data/timeseries/eits/marts?get=data_type_code,cell_value&time=2023-12&category_code=44X72&seasonally_adj=yes&key={API_KEY}"
    },
    {
        'name': 'New Residential Construction',
        'url': f"https://api.census.gov/data/timeseries/eits/resconst?get=data_type_code,cell_value&time=2023-12&category_code=TOTAL&seasonally_adj=yes&key={API_KEY}"
    },
    {
        'name': 'Housing Vacancies',
        'url': f"https://api.census.gov/data/timeseries/eits/hv?get=data_type_code,cell_value&time=2023-Q4&category_code=US&seasonally_adj=no&key={API_KEY}"
    },
    {
        'name': 'Advance Monthly Sales for Retail',
        'url': f"https://api.census.gov/data/timeseries/eits/advm3?get=data_type_code,cell_value&time=2023-12&category_code=44X72&seasonally_adj=yes&key={API_KEY}"
    },
]

working = []
for config in test_configs:
    print(f"\n>>> Testing {config['name']}...")
    print(f"    URL: {config['url'][:60]}...")
    
    try:
        response = requests.get(config['url'], timeout=60)
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 200 and response.text:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 1:
                    print(f"    ✓ Success!")
                    print(f"      Headers: {data[0]}")
                    print(f"      Sample: {data[1]}")
                    print(f"      Rows: {len(data) - 1}")
                    working.append(config['name'])
                else:
                    print(f"    Empty or invalid response")
            except Exception as e:
                print(f"    Parse error: {e}")
        elif response.status_code == 204:
            print(f"    No content (query may need adjustment)")
        else:
            print(f"    Error: {response.text[:100]}")
    except Exception as e:
        print(f"    Request error: {e}")
    
    time.sleep(1)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\nWorking datasets ready to add:")
for name in working:
    print(f"  ✓ {name}")

print(f"\nTotal new datasets found: {len(new_datasets)}")
print(f"Working datasets: {len(working)}")