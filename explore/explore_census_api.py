import requests
import json

# Fetch the Census API discovery endpoint
url = "https://api.census.gov/data.json"

response = requests.get(url)
data = response.json()

# Save the full response for reference
with open("data/census_api_discovery.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"Total datasets available: {len(data['dataset'])}")
print("\n--- First 10 datasets ---\n")

for dataset in data['dataset'][:10]:
    title = dataset.get('title', 'No title')
    description = dataset.get('description', 'No description')[:100]
    print(f"Title: {title}")
    print(f"Description: {description}...")
    print("-" * 50)