import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
conn.autocommit = True
cur = conn.cursor()

# Drop tables if they exist (for clean setup)
cur.execute("DROP TABLE IF EXISTS cbp_data CASCADE;")
cur.execute("DROP TABLE IF EXISTS dataset_metadata CASCADE;")
cur.execute("DROP TABLE IF EXISTS geography_ref CASCADE;")

print("Creating tables...\n")

# 1. Metadata table to track ingested datasets
cur.execute("""
    CREATE TABLE dataset_metadata (
        id SERIAL PRIMARY KEY,
        dataset_name VARCHAR(100) NOT NULL,
        vintage INTEGER NOT NULL,
        api_endpoint VARCHAR(255) NOT NULL,
        description TEXT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        row_count INTEGER,
        UNIQUE(dataset_name, vintage)
    );
""")
print("✓ Created dataset_metadata table")

# 2. Geography reference table
cur.execute("""
    CREATE TABLE geography_ref (
        geo_id VARCHAR(20) PRIMARY KEY,
        geo_level VARCHAR(50) NOT NULL,
        name VARCHAR(255),
        state_fips VARCHAR(2),
        county_fips VARCHAR(3),
        full_fips VARCHAR(11)
    );
""")
print("✓ Created geography_ref table")

# 3. County Business Patterns data table
cur.execute("""
    CREATE TABLE cbp_data (
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
        quarterly_payroll_q1 BIGINT,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
print("✓ Created cbp_data table")

# Create indexes for common queries
cur.execute("CREATE INDEX idx_cbp_vintage ON cbp_data(vintage);")
cur.execute("CREATE INDEX idx_cbp_state ON cbp_data(state_fips);")
cur.execute("CREATE INDEX idx_cbp_naics ON cbp_data(naics_code);")
cur.execute("CREATE INDEX idx_cbp_geo_level ON cbp_data(geo_level);")
print("✓ Created indexes")

cur.close()
conn.close()

print("\nDatabase schema created successfully!")