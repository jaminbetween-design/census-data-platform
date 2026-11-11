import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
conn.autocommit = True
cur = conn.cursor()

print("Creating NES tables...\n")

cur.execute("DROP TABLE IF EXISTS nes_data CASCADE;")

cur.execute("""
    CREATE TABLE nes_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        county_fips VARCHAR(3),
        geo_name VARCHAR(255),
        naics_code VARCHAR(10),
        establishments INTEGER,
        receipts BIGINT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
print("✓ Created nes_data table")

cur.execute("CREATE INDEX idx_nes_vintage ON nes_data(vintage);")
cur.execute("CREATE INDEX idx_nes_state ON nes_data(state_fips);")
cur.execute("CREATE INDEX idx_nes_naics ON nes_data(naics_code);")
cur.execute("CREATE INDEX idx_nes_geo_level ON nes_data(geo_level);")
print("✓ Created indexes")

cur.close()
conn.close()

print("\nNES schema created successfully!")