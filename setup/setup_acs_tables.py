import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
conn.autocommit = True
cur = conn.cursor()

print("Creating ACS tables...\n")

# Drop if exists for clean setup
cur.execute("DROP TABLE IF EXISTS acs_data CASCADE;")

# ACS demographic data table
cur.execute("""
    CREATE TABLE acs_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        county_fips VARCHAR(3),
        geo_name VARCHAR(255),
        
        -- Population
        total_population INTEGER,
        median_age NUMERIC(5,2),
        
        -- Income
        median_household_income INTEGER,
        per_capita_income INTEGER,
        
        -- Housing
        median_home_value INTEGER,
        median_gross_rent INTEGER,
        total_housing_units INTEGER,
        occupied_housing_units INTEGER,
        owner_occupied INTEGER,
        renter_occupied INTEGER,
        
        -- Employment
        labor_force INTEGER,
        unemployed INTEGER,
        
        -- Education (population 25+ with degree)
        bachelors_degree INTEGER,
        masters_degree INTEGER,
        doctorate_degree INTEGER,
        
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
print("✓ Created acs_data table")

# Create indexes
cur.execute("CREATE INDEX idx_acs_vintage ON acs_data(vintage);")
cur.execute("CREATE INDEX idx_acs_state ON acs_data(state_fips);")
cur.execute("CREATE INDEX idx_acs_geo_level ON acs_data(geo_level);")
cur.execute("CREATE INDEX idx_acs_state_county ON acs_data(state_fips, county_fips);")
print("✓ Created indexes")

cur.close()
conn.close()

print("\nACS schema created successfully!")