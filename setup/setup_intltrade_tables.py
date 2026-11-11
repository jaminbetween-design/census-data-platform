#!/usr/bin/env python3
"""
US CENSUS INTERNATIONAL TRADE DATA - DATABASE SCHEMA SETUP
Creates tables for Monthly International Trade Datasets (MITD)
"""

import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL", ""))

conn = connect_db()
conn.autocommit = True
cur = conn.cursor()

print("=" * 70)
print("SETTING UP INTERNATIONAL TRADE DATA TABLES")
print("=" * 70)

# =============================================================================
# 1. EXPORTS HS (Harmonized System) - National Level
# =============================================================================
cur.execute("DROP TABLE IF EXISTS intltrade_exports_hs CASCADE;")
cur.execute("""
    CREATE TABLE intltrade_exports_hs (
        id SERIAL PRIMARY KEY,
        time_period VARCHAR(7) NOT NULL,          -- YYYY-MM format
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        
        -- Commodity classification
        hs_code VARCHAR(10) NOT NULL,             -- 2,4,6,10 digit HS code
        comm_lvl VARCHAR(4),                      -- HS2, HS4, HS6, HS10
        hs_desc_short VARCHAR(100),
        hs_desc_long VARCHAR(255),
        
        -- Geography
        cty_code VARCHAR(4),                      -- Country code
        cty_name VARCHAR(100),
        district VARCHAR(2),                      -- Customs district
        district_name VARCHAR(100),
        
        -- Classification flags
        df VARCHAR(1),                            -- Domestic(1) or Foreign(2)
        summary_lvl VARCHAR(10),                  -- CGP or DET
        summary_lvl2 VARCHAR(20),                 -- Variable combination
        
        -- Trade values (in USD)
        all_val_mo BIGINT,                        -- Monthly total value
        all_val_yr BIGINT,                        -- Year-to-date total value
        
        -- Transportation mode values
        air_val_mo BIGINT,
        air_val_yr BIGINT,
        ves_val_mo BIGINT,                        -- Vessel
        ves_val_yr BIGINT,
        cnt_val_mo BIGINT,                        -- Containerized vessel
        cnt_val_yr BIGINT,
        
        -- Shipping weights
        air_wgt_mo BIGINT,
        air_wgt_yr BIGINT,
        ves_wgt_mo BIGINT,
        ves_wgt_yr BIGINT,
        cnt_wgt_mo BIGINT,
        cnt_wgt_yr BIGINT,
        
        -- Quantities
        unit_qy1 VARCHAR(5),
        unit_qy2 VARCHAR(5),
        qty_1_mo BIGINT,
        qty_1_yr BIGINT,
        qty_2_mo BIGINT,
        qty_2_yr BIGINT,
        qty_1_mo_flag VARCHAR(1),                 -- M = Missing
        qty_2_mo_flag VARCHAR(1),
        qty_1_yr_flag VARCHAR(1),
        qty_2_yr_flag VARCHAR(1),
        
        -- Metadata
        cc_mo INTEGER,                            -- Card count
        cc_yr INTEGER,
        last_update DATE,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        UNIQUE(time_period, hs_code, cty_code, district, df, summary_lvl2)
    );
""")
print("✓ Created intltrade_exports_hs table")

# Create indexes
cur.execute("CREATE INDEX idx_exp_hs_time ON intltrade_exports_hs(time_period);")
cur.execute("CREATE INDEX idx_exp_hs_year ON intltrade_exports_hs(year);")
cur.execute("CREATE INDEX idx_exp_hs_hs_code ON intltrade_exports_hs(hs_code);")
cur.execute("CREATE INDEX idx_exp_hs_comm_lvl ON intltrade_exports_hs(comm_lvl);")
cur.execute("CREATE INDEX idx_exp_hs_cty ON intltrade_exports_hs(cty_code);")
cur.execute("CREATE INDEX idx_exp_hs_district ON intltrade_exports_hs(district);")
print("✓ Created indexes for exports_hs")

# =============================================================================
# 2. IMPORTS HS (Harmonized System) - National Level
# =============================================================================
cur.execute("DROP TABLE IF EXISTS intltrade_imports_hs CASCADE;")
cur.execute("""
    CREATE TABLE intltrade_imports_hs (
        id SERIAL PRIMARY KEY,
        time_period VARCHAR(7) NOT NULL,          -- YYYY-MM format
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        
        -- Commodity classification
        hs_code VARCHAR(10) NOT NULL,             -- 2,4,6,10 digit HS code
        comm_lvl VARCHAR(4),                      -- HS2, HS4, HS6, HS10
        hs_desc_short VARCHAR(100),
        hs_desc_long VARCHAR(255),
        
        -- Geography
        cty_code VARCHAR(4),                      -- Country code
        cty_name VARCHAR(100),
        cty_subcode VARCHAR(2),                   -- Country subcode
        district VARCHAR(2),                      -- Customs district
        district_name VARCHAR(100),
        
        -- Classification flags
        rp VARCHAR(2),                            -- Rate provision code
        summary_lvl VARCHAR(10),                  -- CGP or DET
        summary_lvl2 VARCHAR(20),                 -- Variable combination
        
        -- General import values (in USD)
        gen_val_mo BIGINT,                        -- Monthly general imports
        gen_val_yr BIGINT,                        -- Year-to-date general imports
        
        -- Consumption import values
        con_val_mo BIGINT,                        -- Monthly consumption imports
        con_val_yr BIGINT,
        
        -- CIF values (Cost, Insurance, Freight)
        gen_cif_mo BIGINT,
        gen_cif_yr BIGINT,
        con_cif_mo BIGINT,
        con_cif_yr BIGINT,
        
        -- Charges
        gen_cha_mo BIGINT,
        gen_cha_yr BIGINT,
        con_cha_mo BIGINT,
        con_cha_yr BIGINT,
        
        -- Duties
        cal_dut_mo BIGINT,                        -- Calculated duty
        cal_dut_yr BIGINT,
        dut_val_mo BIGINT,                        -- Dutiable value
        dut_val_yr BIGINT,
        
        -- Transportation mode values
        air_val_mo BIGINT,
        air_val_yr BIGINT,
        ves_val_mo BIGINT,
        ves_val_yr BIGINT,
        cnt_val_mo BIGINT,
        cnt_val_yr BIGINT,
        
        -- Shipping weights
        air_wgt_mo BIGINT,
        air_wgt_yr BIGINT,
        ves_wgt_mo BIGINT,
        ves_wgt_yr BIGINT,
        cnt_wgt_mo BIGINT,
        cnt_wgt_yr BIGINT,
        
        -- Charges by transportation
        air_cha_mo BIGINT,
        air_cha_yr BIGINT,
        ves_cha_mo BIGINT,
        ves_cha_yr BIGINT,
        cnt_cha_mo BIGINT,
        cnt_cha_yr BIGINT,
        
        -- Quantities (General)
        unit_qy1 VARCHAR(5),
        unit_qy2 VARCHAR(5),
        gen_qy1_mo BIGINT,
        gen_qy1_yr BIGINT,
        gen_qy2_mo BIGINT,
        gen_qy2_yr BIGINT,
        gen_qy1_mo_flag VARCHAR(1),
        gen_qy2_mo_flag VARCHAR(1),
        gen_qy1_yr_flag VARCHAR(1),
        gen_qy2_yr_flag VARCHAR(1),
        
        -- Quantities (Consumption)
        con_qy1_mo BIGINT,
        con_qy1_yr BIGINT,
        con_qy2_mo BIGINT,
        con_qy2_yr BIGINT,
        con_qy1_mo_flag VARCHAR(1),
        con_qy2_mo_flag VARCHAR(1),
        con_qy1_yr_flag VARCHAR(1),
        con_qy2_yr_flag VARCHAR(1),
        
        -- Metadata
        cc_mo INTEGER,
        cc_yr INTEGER,
        last_update DATE,
        ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        UNIQUE(time_period, hs_code, cty_code, cty_subcode, district, rp, summary_lvl2)
    );
""")
print("✓ Created intltrade_imports_hs table")

cur.execute("CREATE INDEX idx_imp_hs_time ON intltrade_imports_hs(time_period);")
cur.execute("CREATE INDEX idx_imp_hs_year ON intltrade_imports_hs(year);")
cur.execute("CREATE INDEX idx_imp_hs_hs_code ON intltrade_imports_hs(hs_code);")
cur.execute("CREATE INDEX idx_imp_hs_comm_lvl ON intltrade_imports_hs(comm_lvl);")
cur.execute("CREATE INDEX idx_imp_hs_cty ON intltrade_imports_hs(cty_code);")
cur.execute("CREATE INDEX idx_imp_hs_district ON intltrade_imports_hs(district);")
print("✓ Created indexes for imports_hs")

# =============================================================================
# 3. TRADE DATA INGESTION TRACKING TABLE
# =============================================================================
cur.execute("DROP TABLE IF EXISTS intltrade_ingestion_log CASCADE;")
cur.execute("""
    CREATE TABLE intltrade_ingestion_log (
        id SERIAL PRIMARY KEY,
        dataset VARCHAR(50) NOT NULL,             -- e.g., 'exports_hs', 'imports_hs'
        time_period VARCHAR(7) NOT NULL,          -- YYYY-MM
        comm_lvl VARCHAR(4),                      -- HS2, HS4, HS6, HS10
        rows_ingested INTEGER,
        status VARCHAR(20),                       -- 'success', 'partial', 'failed'
        error_message TEXT,
        started_at TIMESTAMP,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(dataset, time_period, comm_lvl)
    );
""")
print("✓ Created intltrade_ingestion_log table")

# =============================================================================
# 4. COUNTRY REFERENCE TABLE
# =============================================================================
cur.execute("DROP TABLE IF EXISTS intltrade_country_ref CASCADE;")
cur.execute("""
    CREATE TABLE intltrade_country_ref (
        cty_code VARCHAR(4) PRIMARY KEY,
        cty_name VARCHAR(100),
        is_country_group BOOLEAN DEFAULT FALSE,
        region VARCHAR(50)
    );
""")

# Insert known country groupings from the API guide
country_groups = [
    ('0001', 'OPEC', True, 'Trade Organization'),
    ('0003', 'EUROPEAN UNION', True, 'Trade Organization'),
    ('0014', 'PACIFIC RIM COUNTRIES', True, 'Trade Organization'),
    ('0017', 'CAFTA-DR', True, 'Trade Organization'),
    ('0020', 'NAFTA', True, 'Trade Organization'),
    ('0021', 'TWENTY LATIN AMERICAN REPUBLICS', True, 'Trade Organization'),
    ('0022', 'OECD', True, 'Trade Organization'),
    ('0023', 'NATO', True, 'Trade Organization'),
    ('0024', 'LAFTA', True, 'Trade Organization'),
    ('0025', 'EURO AREA', True, 'Trade Organization'),
    ('0026', 'APEC', True, 'Trade Organization'),
    ('0027', 'ASEAN', True, 'Trade Organization'),
    ('0028', 'CACM', True, 'Trade Organization'),
    ('1XXX', 'NORTH AMERICA', True, 'Geographic Region'),
    ('2XXX', 'CENTRAL AMERICA', True, 'Geographic Region'),
    ('3XXX', 'SOUTH AMERICA', True, 'Geographic Region'),
    ('4XXX', 'EUROPE', True, 'Geographic Region'),
    ('5XXX', 'ASIA', True, 'Geographic Region'),
    ('6XXX', 'AUSTRALIA AND OCEANIA', True, 'Geographic Region'),
    ('7XXX', 'AFRICA', True, 'Geographic Region'),
]

for cty_code, cty_name, is_group, region in country_groups:
    cur.execute("""
        INSERT INTO intltrade_country_ref (cty_code, cty_name, is_country_group, region)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (cty_code) DO NOTHING
    """, (cty_code, cty_name, is_group, region))

print("✓ Created intltrade_country_ref table with groupings")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("INTERNATIONAL TRADE SCHEMA CREATED")
print("=" * 70)
print("""
Tables created:
  1. intltrade_exports_hs    - Export data by HS code (national level)
  2. intltrade_imports_hs    - Import data by HS code (national level)
  3. intltrade_ingestion_log - Track ingestion progress
  4. intltrade_country_ref   - Country and grouping reference

Next step: Run the ingestion script to load data
""")

cur.close()
conn.close()

print("✓ Schema setup complete!")