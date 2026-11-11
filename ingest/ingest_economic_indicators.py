import requests
import psycopg2
import time
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

API_KEY = os.environ.get("CENSUS_API_KEY")

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

def safe_float(value):
    if value is None or value == '' or value == 'null' or value == 'N' or value == 'D' or value == 'S' or value == 'NA':
        return None
    try:
        return float(str(value).replace(',', ''))
    except:
        return None

print("=" * 70)
print("ECONOMIC INDICATORS TIME SERIES INGESTION")
print("=" * 70)

if not API_KEY:
    print("\nERROR: CENSUS_API_KEY is not set. Copy .env.example to .env and add your key.")
    exit()

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

# Create Economic Indicators table
cur.execute("DROP TABLE IF EXISTS econ_indicators_data CASCADE;")
cur.execute("""
    CREATE TABLE econ_indicators_data (
        id SERIAL PRIMARY KEY,
        indicator_type VARCHAR(20) NOT NULL,
        indicator_name VARCHAR(100),
        time_period VARCHAR(20),
        year INTEGER,
        month INTEGER,
        quarter INTEGER,
        data_type_code VARCHAR(20),
        category_code VARCHAR(50),
        cell_value NUMERIC(20,4),
        error_data VARCHAR(50),
        seasonally_adj VARCHAR(5),
        time_slot_id VARCHAR(10),
        geo_level VARCHAR(20),
        state_fips VARCHAR(2),
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_econ_indicator ON econ_indicators_data(indicator_type);")
cur.execute("CREATE INDEX idx_econ_year ON econ_indicators_data(year);")
cur.execute("CREATE INDEX idx_econ_category ON econ_indicators_data(category_code);")
print("✓ Created econ_indicators_data table")

# Economic Indicator datasets to ingest
INDICATORS = [
    {
        'code': 'hv',
        'name': 'Housing Vacancies and Homeownership',
        'quarterly': True,
        'start_year': 1995,
        'end_year': 2024
    },
    {
        'code': 'resconst',
        'name': 'New Residential Construction',
        'quarterly': False,
        'start_year': 1959,
        'end_year': 2024
    },
    {
        'code': 'ressales',
        'name': 'New Home Sales',
        'quarterly': False,
        'start_year': 1963,
        'end_year': 2024
    },
    {
        'code': 'marts',
        'name': 'Advance Monthly Retail Sales',
        'quarterly': False,
        'start_year': 1992,
        'end_year': 2024
    },
    {
        'code': 'mrts',
        'name': 'Monthly Retail Trade',
        'quarterly': False,
        'start_year': 1992,
        'end_year': 2024
    },
    {
        'code': 'mwts',
        'name': 'Monthly Wholesale Trade',
        'quarterly': False,
        'start_year': 1992,
        'end_year': 2024
    },
    {
        'code': 'vip',
        'name': 'Construction Spending',
        'quarterly': False,
        'start_year': 1993,
        'end_year': 2024
    },
    {
        'code': 'm3',
        'name': 'Manufacturers Shipments Inventories Orders',
        'quarterly': False,
        'start_year': 1992,
        'end_year': 2024
    },
    {
        'code': 'advm3',
        'name': 'Advance Durable Goods',
        'quarterly': False,
        'start_year': 1992,
        'end_year': 2024
    },
    {
        'code': 'mtis',
        'name': 'Manufacturing Trade Inventories Sales',
        'quarterly': False,
        'start_year': 1992,
        'end_year': 2024
    },
    {
        'code': 'ftd',
        'name': 'International Trade Goods Services',
        'quarterly': False,
        'start_year': 1992,
        'end_year': 2024
    },
    {
        'code': 'qfr',
        'name': 'Quarterly Financial Report',
        'quarterly': True,
        'start_year': 1988,
        'end_year': 2024
    },
    {
        'code': 'qss',
        'name': 'Quarterly Services Survey',
        'quarterly': True,
        'start_year': 2003,
        'end_year': 2024
    },
    {
        'code': 'qtax',
        'name': 'Quarterly State Local Taxes',
        'quarterly': True,
        'start_year': 1994,
        'end_year': 2024
    },
    {
        'code': 'qpr',
        'name': 'Quarterly Public Pensions',
        'quarterly': True,
        'start_year': 2003,
        'end_year': 2024
    },
    {
        'code': 'bfs',
        'name': 'Business Formation Statistics',
        'quarterly': True,
        'start_year': 2004,
        'end_year': 2024
    },
    {
        'code': 'mhs2',
        'name': 'Manufactured Housing Survey',
        'quarterly': False,
        'start_year': 2014,
        'end_year': 2024
    },
]

grand_total = 0

for indicator in INDICATORS:
    code = indicator['code']
    name = indicator['name']
    is_quarterly = indicator['quarterly']
    start_year = indicator['start_year']
    end_year = indicator['end_year']
    
    print(f"\n>>> Processing {name} ({code})...")
    print(f"    Years: {start_year}-{end_year}, {'Quarterly' if is_quarterly else 'Monthly'}")
    
    indicator_total = 0
    
    # Process year by year
    for year in range(end_year, start_year - 1, -1):
        # Build URL based on documentation format
        url = f"https://api.census.gov/data/timeseries/eits/{code}?get=cell_value,data_type_code,time_slot_id,category_code,seasonally_adj&time={year}&key={API_KEY}"
        
        try:
            response = requests.get(url, timeout=120)
            
            if response.status_code == 200 and response.text:
                try:
                    data = response.json()
                    
                    if isinstance(data, list) and len(data) > 1:
                        headers = data[0]
                        rows = data[1:]
                        col_map = {col: idx for idx, col in enumerate(headers)}
                        
                        for row in rows:
                            time_val = row[col_map.get('time')] if 'time' in col_map else str(year)
                            
                            # Parse time period
                            parsed_year = year
                            parsed_month = None
                            parsed_quarter = None
                            
                            if time_val and '-' in str(time_val):
                                parts = str(time_val).split('-')
                                if len(parts) == 2:
                                    parsed_year = int(parts[0])
                                    period = int(parts[1])
                                    if is_quarterly:
                                        parsed_quarter = period
                                    else:
                                        parsed_month = period
                            
                            cur.execute("""
                                INSERT INTO econ_indicators_data 
                                (indicator_type, indicator_name, time_period, year, month, quarter,
                                 data_type_code, category_code, cell_value, seasonally_adj, time_slot_id, geo_level)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                code,
                                name,
                                time_val,
                                parsed_year,
                                parsed_month,
                                parsed_quarter,
                                row[col_map.get('data_type_code')] if 'data_type_code' in col_map else None,
                                row[col_map.get('category_code')] if 'category_code' in col_map else None,
                                safe_float(row[col_map.get('cell_value')]) if 'cell_value' in col_map else None,
                                row[col_map.get('seasonally_adj')] if 'seasonally_adj' in col_map else None,
                                row[col_map.get('time_slot_id')] if 'time_slot_id' in col_map else None,
                                'national'
                            ))
                        
                        indicator_total += len(rows)
                        
                except Exception as e:
                    pass
            
        except Exception as e:
            pass
        
        time.sleep(0.3)
        
        # Commit every 10 years
        if year % 10 == 0:
            conn.commit()
    
    conn.commit()
    
    if indicator_total > 0:
        print(f"    ✓ Ingested {indicator_total:,} rows")
        grand_total += indicator_total
    else:
        print(f"    ✗ No data retrieved")

# =============================================================================
# ALSO ADD GOVERNMENT FINANCES (GOVS) - it worked in our test
# =============================================================================
print("\n" + "=" * 60)
print("ADDING GOVERNMENT FINANCES")
print("=" * 60)

cur.execute("DROP TABLE IF EXISTS govs_data CASCADE;")
cur.execute("""
    CREATE TABLE govs_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        state_fips VARCHAR(2),
        geo_name VARCHAR(255),
        agg_desc VARCHAR(20),
        amount NUMERIC(20,2),
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_govs_vintage ON govs_data(vintage);")
cur.execute("CREATE INDEX idx_govs_state ON govs_data(state_fips);")
print("✓ Created govs_data table")

govs_total = 0

for year in range(2022, 1991, -1):
    url = f"https://api.census.gov/data/timeseries/govs?get=NAME,AGG_DESC,AMOUNT&for=state:*&YEAR={year}&key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 1:
                headers = data[0]
                rows = data[1:]
                col_map = {col: idx for idx, col in enumerate(headers)}
                
                for row in rows:
                    cur.execute("""
                        INSERT INTO govs_data (vintage, state_fips, geo_name, agg_desc, amount)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        year,
                        row[col_map.get('state')],
                        row[col_map.get('NAME')],
                        row[col_map.get('AGG_DESC')],
                        safe_float(row[col_map.get('AMOUNT')])
                    ))
                
                govs_total += len(rows)
                print(f"  {year}: ✓ {len(rows):,} rows")
                conn.commit()
    except Exception as e:
        print(f"  {year}: ✗ {e}")
    
    time.sleep(0.5)

print(f"\n✓ Government Finances total: {govs_total:,} rows")

# =============================================================================
# ALSO ADD PUBLIC SCHOOL FINANCES - it worked in our test
# =============================================================================
print("\n" + "=" * 60)
print("ADDING PUBLIC SCHOOL FINANCES")
print("=" * 60)

cur.execute("DROP TABLE IF EXISTS school_finance_data CASCADE;")
cur.execute("""
    CREATE TABLE school_finance_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        state_fips VARCHAR(2),
        geo_name VARCHAR(255),
        total_revenue BIGINT,
        federal_revenue BIGINT,
        state_revenue BIGINT,
        local_revenue BIGINT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cur.execute("CREATE INDEX idx_school_vintage ON school_finance_data(vintage);")
cur.execute("CREATE INDEX idx_school_state ON school_finance_data(state_fips);")
print("✓ Created school_finance_data table")

# 2012 is the only year that seems to be available via API
url = f"https://api.census.gov/data/2012/pubschlfin?get=NAME,TOTALREV,TFEDREV,TSTREV,TLOCREV&for=state:*&key={API_KEY}"
response = requests.get(url, timeout=120)

if response.status_code == 200:
    data = response.json()
    if len(data) > 1:
        headers = data[0]
        rows = data[1:]
        col_map = {col: idx for idx, col in enumerate(headers)}
        
        school_total = 0
        for row in rows:
            cur.execute("""
                INSERT INTO school_finance_data (vintage, state_fips, geo_name, total_revenue, federal_revenue, state_revenue, local_revenue)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                2012,
                row[col_map.get('state')],
                row[col_map.get('NAME')],
                safe_float(row[col_map.get('TOTALREV')]),
                safe_float(row[col_map.get('TFEDREV')]),
                safe_float(row[col_map.get('TSTREV')]),
                safe_float(row[col_map.get('TLOCREV')])
            ))
            school_total += 1
        
        conn.commit()
        print(f"✓ School Finance: {school_total:,} rows")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("ECONOMIC INDICATORS INGESTION COMPLETE")
print("=" * 70)

# Count by indicator type
cur.execute("""
    SELECT indicator_type, indicator_name, COUNT(*) as rows,
           MIN(year) as min_year, MAX(year) as max_year
    FROM econ_indicators_data 
    GROUP BY indicator_type, indicator_name
    ORDER BY rows DESC
""")
print("\nEconomic Indicators by type:")
for row in cur.fetchall():
    print(f"  {row[0]} ({row[1][:30]}): {row[2]:,} rows ({row[3]}-{row[4]})")

cur.execute("SELECT COUNT(*) FROM econ_indicators_data")
econ_total = cur.fetchone()[0]
print(f"\nTotal Economic Indicators: {econ_total:,} rows")

# Full database summary
print("\n" + "=" * 70)
print("COMPLETE DATABASE SUMMARY")
print("=" * 70)

tables = [
    'cbp_data', 'zbp_data', 'nes_data', 'acs_data', 'pep_data', 
    'ec_data', 'decennial_data', 'abs_data', 'saipe_data', 
    'sahie_data', 'bds_data', 'sbo_data', 'acs1_data', 'cps_data',
    'econ_indicators_data', 'govs_data', 'school_finance_data'
]

grand_total = 0
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        grand_total += count
        print(f"  {table}: {count:,} rows")
    except:
        print(f"  {table}: Not found")

print(f"  ----------------------------------------")
print(f"  TOTAL: {grand_total:,} rows")

cur.close()
conn.close()