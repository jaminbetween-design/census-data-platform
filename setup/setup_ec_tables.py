import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
conn.autocommit = True
cur = conn.cursor()

print("Creating Economic Census tables...\n")

cur.execute("DROP TABLE IF EXISTS ec_data CASCADE;")

cur.execute("""
    CREATE TABLE ec_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        county_fips VARCHAR(3),
        geo_name VARCHAR(255),
        naics_code VARCHAR(10),
        establishments INTEGER,
        employees INTEGER,
        annual_payroll BIGINT,
        receipts BIGINT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
print("✓ Created ec_data table")

cur.execute("CREATE INDEX idx_ec_vintage ON ec_data(vintage);")
cur.execute("CREATE INDEX idx_ec_state ON ec_data(state_fips);")
cur.execute("CREATE INDEX idx_ec_naics ON ec_data(naics_code);")
cur.execute("CREATE INDEX idx_ec_geo_level ON ec_data(geo_level);")
print("✓ Created indexes")

cur.close()
conn.close()

print("\nEconomic Census schema created successfully!")