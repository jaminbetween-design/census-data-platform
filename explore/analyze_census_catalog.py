import json
from collections import Counter

# Load the saved discovery data
with open("data/census_api_discovery.json", "r") as f:
    data = json.load(f)

datasets = data['dataset']

# Analyze one dataset in detail to see all available fields
print("=== SAMPLE DATASET STRUCTURE ===\n")
sample = datasets[0]
for key, value in sample.items():
    if isinstance(value, str) and len(value) > 100:
        print(f"{key}: {value[:100]}...")
    elif isinstance(value, list) and len(value) > 3:
        print(f"{key}: {value[:3]} ... ({len(value)} items)")
    else:
        print(f"{key}: {value}")

print("\n" + "=" * 60)
print("=== DATASET CATEGORIES ===\n")

# Extract program/survey types from titles
programs = []
for ds in datasets:
    title = ds.get('title', '')
    # Try to extract the program name (usually after the colon)
    if ':' in title:
        program = title.split(':')[-1].strip()
        programs.append(program)

program_counts = Counter(programs).most_common(20)
print("Top 20 dataset types:")
for program, count in program_counts:
    print(f"  {program}: {count}")

print("\n" + "=" * 60)
print("=== VINTAGE (YEAR) DISTRIBUTION ===\n")

# Extract vintages
vintages = [ds.get('c_vintage') for ds in datasets if ds.get('c_vintage')]
vintage_counts = Counter(vintages).most_common(20)
print("Top 20 years by dataset count:")
for vintage, count in vintage_counts:
    print(f"  {vintage}: {count}")

print("\n" + "=" * 60)
print("=== API ENDPOINTS SAMPLE ===\n")

# Show API access URLs for first 5 datasets
for ds in datasets[:5]:
    title = ds.get('title', 'No title')
    api_url = ds.get('distribution', [{}])[0].get('accessURL', 'No URL')
    print(f"{title}")
    print(f"  API: {api_url}\n")