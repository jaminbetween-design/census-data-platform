import requests

vintage = 2011
base_url = f"https://api.census.gov/data/{vintage}/cbp"

# Test different county query formats
queries = [
    "?get=ESTAB,EMP,PAYANN,NAICS2007&for=county:*&in=state:*",
    "?get=ESTAB,EMP,PAYANN,NAICS2007&for=county:*&in=state:01",
    "?get=ESTAB,EMP,PAYANN,NAICS2007&for=county:*",
    "?get=ESTAB,EMP,PAYANN,NAICS2007&for=county:001&in=state:01",
]

print("Testing county query formats for 2011:\n")
for query in queries:
    url = base_url + query
    response = requests.get(url)
    print(f"Query: {query}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Rows returned: {len(data) - 1}")
        print(f"Sample: {data[:2]}")
    else:
        print(f"Error: {response.text[:100]}")
    print()