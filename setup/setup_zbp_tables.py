import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
conn.autocommit = True
cur = conn.cursor()

print("Creating ZBP tables...\n")

cur.execute("DROP TABLE IF EXISTS zbp_data CASCADE;")

cur.execute("""
    CREATE TABLE zbp_data (
        id SERIAL PRIMARY KEY,
        vintage INTEGER NOT NULL,
        zipcode VARCHAR(5) NOT NULL,
        naics_code VARCHAR(10),
        establishments INTEGER,
        employees INTEGER,
        annual_payroll BIGINT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
print("✓ Created zbp_data table")

# Create indexes for common queries
cur.execute("CREATE INDEX idx_zbp_vintage ON zbp_data(vintage);")
cur.execute("CREATE INDEX idx_zbp_zipcode ON zbp_data(zipcode);")
cur.execute("CREATE INDEX idx_zbp_naics ON zbp_data(naics_code);")
cur.execute("CREATE INDEX idx_zbp_zip_naics ON zbp_data(zipcode, naics_code);")
print("✓ Created indexes")

cur.close()
conn.close()

print("\nZBP schema created successfully!")