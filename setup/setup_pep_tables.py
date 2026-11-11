import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
conn.autocommit = True
cur = conn.cursor()

print("Creating PEP tables...\n")

cur.execute("DROP TABLE IF EXISTS pep_data CASCADE;")

cur.execute("""
    CREATE TABLE pep_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        county_fips VARCHAR(3),
        geo_name VARCHAR(255),
        population INTEGER,
        population_change INTEGER,
        percent_change NUMERIC(6,2),
        density NUMERIC(10,2),
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
print("✓ Created pep_data table")

cur.execute("CREATE INDEX idx_pep_vintage ON pep_data(vintage);")
cur.execute("CREATE INDEX idx_pep_state ON pep_data(state_fips);")
cur.execute("CREATE INDEX idx_pep_geo_level ON pep_data(geo_level);")
print("✓ Created indexes")

cur.close()
conn.close()

print("\nPEP schema created successfully!")