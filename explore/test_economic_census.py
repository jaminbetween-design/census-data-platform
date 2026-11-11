import requests
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

print("=" * 60)
print("TESTING ECONOMIC CENSUS QUERY FORMATS")
print("=" * 60)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

# Try different query formats for 2017
print("\n>>> Testing various 2017 Economic Census queries...\n")

test_queries = [
    # Without NAICS filter
    f"https://api.census.gov/data/2017/ecnbasic?get=NAME,NAICS2017,ESTAB,EMP,PAYANN,RCPTOT&for=state:06&key={API_KEY}",
    # With different NAICS formats
    f"https://api.census.gov/data/2017/ecnbasic?get=NAME,NAICS2017,ESTAB,EMP,PAYANN&for=state:06&NAICS2017=72&key={API_KEY}",
    f"https://api.census.gov/data/2017/ecnbasic?get=NAME,NAICS2017,ESTAB,EMP&for=state:*&key={API_KEY}",
    # Try ecnsummary instead of ecnbasic
    f"https://api.census.gov/data/2017/ecn/basic?get=NAME,NAICS2017,ESTAB,EMP&for=state:06&key={API_KEY}",
]

for i, url in enumerate(test_queries):
    print(f"Test {i+1}: {url[:70]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200 and response.text:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                print(f"  ✓ Success!")
                print(f"    Headers: {data[0]}")
                print(f"    Sample: {data[1]}")
                print(f"    Total rows: {len(data) - 1}")
        except Exception as e:
            print(f"  Parse error: {e}")
            print(f"  Response: {response.text[:200]}")
    elif response.status_code == 204:
        print(f"  No content returned")
    else:
        print(f"  Error: {response.text[:150]}")
    
    time.sleep(1)
    print()

# Try 2022 Economic Census
print("=" * 60)
print(">>> Testing 2022 Economic Census...\n")

test_2022 = [
    f"https://api.census.gov/data/2022/ecnbasic?get=NAME,NAICS2022,ESTAB,EMP,PAYANN&for=state:*&key={API_KEY}",
    f"https://api.census.gov/data/2022/ecnbasic?get=NAME,NAICS2022,ESTAB,EMP&for=state:06&key={API_KEY}",
    f"https://api.census.gov/data/2022/ecnbasic?get=NAME,ESTAB,EMP&for=state:06&NAICS2022=72&key={API_KEY}",
]

for i, url in enumerate(test_2022):
    print(f"Test {i+1}: {url[:70]}...")
    response = requests.get(url, timeout=60)
    print(f"  Status: {response.status_code}")
    
    if response.status_code == 200 and response.text:
        try:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                print(f"  ✓ Success!")
                print(f"    Headers: {data[0]}")
                print(f"    Sample: {data[1]}")
        except Exception as e:
            print(f"  Parse error: {e}")
    elif response.status_code == 204:
        print(f"  No content returned")
    else:
        print(f"  Error: {response.text[:150]}")
    
    time.sleep(1)
    print()

# Check examples from API
print("=" * 60)
print(">>> Checking API examples...\n")

examples_url = "https://api.census.gov/data/2017/ecnbasic/examples.json"
response = requests.get(examples_url)
print(f"Examples status: {response.status_code}")

if response.status_code == 200:
    examples = response.json()
    print(f"Examples structure: {type(examples)}")
    if isinstance(examples, dict):
        print(f"Keys: {list(examples.keys())}")
        if 'get' in examples:
            print(f"Suggested GET vars: {examples['get']}")
        if 'predicates' in examples:
            print(f"Predicates: {examples['predicates']}")