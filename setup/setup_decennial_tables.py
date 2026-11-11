import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
conn.autocommit = True
cur = conn.cursor()

print("Creating Decennial Census tables...\n")

cur.execute("DROP TABLE IF EXISTS decennial_data CASCADE;")

cur.execute("""
    CREATE TABLE decennial_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        county_fips VARCHAR(3),
        tract VARCHAR(10),
        geo_name VARCHAR(255),
        total_population BIGINT,
        housing_units INTEGER,
        occupied_housing INTEGER,
        vacant_housing INTEGER,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
print("✓ Created decennial_data table")

cur.execute("CREATE INDEX idx_dec_vintage ON decennial_data(vintage);")
cur.execute("CREATE INDEX idx_dec_state ON decennial_data(state_fips);")
cur.execute("CREATE INDEX idx_dec_geo_level ON decennial_data(geo_level);")
print("✓ Created indexes")

cur.close()
conn.close()

print("\nDecennial Census schema created successfully!")