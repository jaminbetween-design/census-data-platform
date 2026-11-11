import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
conn.autocommit = True
cur = conn.cursor()

print("Creating Annual Business Survey tables...\n")

cur.execute("DROP TABLE IF EXISTS abs_data CASCADE;")

cur.execute("""
    CREATE TABLE abs_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        geo_level VARCHAR(50) NOT NULL,
        state_fips VARCHAR(2),
        geo_name VARCHAR(255),
        naics_code VARCHAR(10),
        establishments INTEGER,
        employees INTEGER,
        annual_payroll BIGINT,
        receipts BIGINT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
print("✓ Created abs_data table")

cur.execute("CREATE INDEX idx_abs_vintage ON abs_data(vintage);")
cur.execute("CREATE INDEX idx_abs_state ON abs_data(state_fips);")
cur.execute("CREATE INDEX idx_abs_naics ON abs_data(naics_code);")
print("✓ Created indexes")

cur.close()
conn.close()

print("\nABS schema created successfully!")