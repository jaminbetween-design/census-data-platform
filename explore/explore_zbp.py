import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

print("=" * 60)
print("EXPLORING ZIP CODE BUSINESS PATTERNS")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    print("(The same key you used for the ACS ingestion)")
    exit()

time.sleep(2)

# Test via CBP endpoint for 2021 (ZIP data is available through CBP)
print("\n>>> Testing ZIP data via CBP endpoint (2021)...")
test_url = f"https://api.census.gov/data/2021/cbp?get=ZIPCODE,ESTAB,EMP,PAYANN,NAICS2017&for=zipcode:90210&key={API_KEY}"
print(f"URL: {test_url[:80]}...")

response = requests.get(test_url)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    try:
        data = response.json()
        print(f"Headers: {data[0]}")
        print(f"Rows: {len(data) - 1}")
        for row in data[1:5]:
            print(f"  {row}")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Response preview: {response.text[:300]}")
else:
    print(f"Error: {response.text[:300]}")

# Check how many ZIP codes are available
print("\n>>> Counting ZIP codes (this may take a moment)...")
time.sleep(2)

count_url = f"https://api.census.gov/data/2021/cbp?get=ZIPCODE,ESTAB&for=zipcode:*&NAICS2017=00&key={API_KEY}"
count_response = requests.get(count_url, timeout=120)
print(f"Status: {count_response.status_code}")

if count_response.status_code == 200:
    try:
        count_data = count_response.json()
        print(f"Total ZIP codes with data: {len(count_data) - 1:,}")
    except Exception as e:
        print(f"Parse error: {e}")
        print(f"Response preview: {count_response.text[:300]}")

# Check which years have ZIP data via CBP
print("\n>>> Testing ZIP availability across years...")
years_with_zip = []

for year in [2023, 2022, 2021, 2020, 2019, 2018, 2017]:
    time.sleep(1)
    test_url = f"https://api.census.gov/data/{year}/cbp?get=ZIPCODE,ESTAB&for=zipcode:90210&key={API_KEY}"
    resp = requests.get(test_url)
    if resp.status_code == 200:
        try:
            data = resp.json()
            if len(data) > 1:
                years_with_zip.append(year)
                print(f"  {year}: ✓ ZIP data available")
        except:
            print(f"  {year}: ✗ Parse error")
    else:
        print(f"  {year}: ✗ Not available ({resp.status_code})")

print(f"\nYears with ZIP code data: {years_with_zip}")