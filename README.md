# U.S. Census Data Platform

A local data platform that pulls 18 public datasets from the U.S. Census Bureau API into one PostgreSQL database (more than 120 million rows) and serves them through a documented FastAPI service.

The Census Bureau publishes each survey through its own API endpoint, with its own variable names, geography codes, and quirks that change between vintages. This project collects them in one place with consistent keys (state and county FIPS codes, ZIP codes, NAICS industry codes, and year). That makes questions that span surveys, such as business density against household income by county, a single SQL query.

## At a glance

- **18 Census Bureau datasets**, from business statistics (County Business Patterns, Economic Census, Nonemployer Statistics) to household surveys (American Community Survey, Current Population Survey, Household Pulse) and monthly international trade.
- **120M+ rows in 23 tables, about 30 GB**, covering 1956 to 2025 depending on the dataset.
- **FastAPI service with 26 JSON endpoints**, interactive docs at `/docs`, and a small demo page.
- **Python ingestion scripts** with resumable, rate-limited downloads for the largest sources.

## Datasets

Row counts are exact, taken from the database on 2026-11-10.

| Table | Dataset | Census API endpoint | Coverage | Rows |
| --- | --- | --- | --- | ---: |
| `intltrade_exports_hs` | International Trade: exports by Harmonized System code | `timeseries/intltrade/exports/hs` | 2013-01 to 2025-09, monthly | 62,400,861 |
| `cbp_data` | County Business Patterns (state and county, by NAICS) | `{year}/cbp` | 1986–2023 | 24,164,559 |
| `zbp_data` | ZIP Code Business Patterns | `{year}/cbp` (ZIP level) | 2018–2023 | 17,508,335 |
| `nes_data` | Nonemployer Statistics | `{year}/nonemp` | 2012–2023 | 10,321,283 |
| `ec_data` | Economic Census | `{year}/ecnbasic` | 2012, 2017, 2022 | 3,399,516 |
| `econ_indicators_data` | Economic Indicators (17 monthly and quarterly series, e.g. retail sales, construction, housing vacancies) | `timeseries/eits/{series}` | 1956 Q1 to 2024 Q4 | 1,953,854 |
| `bds_data` | Business Dynamics Statistics | `timeseries/bds` | 1978–2023 | 147,015 |
| `cps_data` | Current Population Survey, basic monthly | `{year}/cps/basic/{month}` | 1994–2023 | 146,592 |
| `abs_data` | Annual Business Survey | `{year}/abscs` | 2017–2021 | 132,380 |
| `sbo_data` | Survey of Business Owners | `2012/sbo` | 2012 | 90,248 |
| `saipe_data` | Small Area Income and Poverty Estimates | `timeseries/poverty/saipe` | 2000–2022 | 73,439 |
| `sahie_data` | Small Area Health Insurance Estimates | `timeseries/healthins/sahie` | 2006–2022 | 54,288 |
| `acs_data` | American Community Survey, 5-year estimates | `{year}/acs/acs5` | 2012–2023 | 39,272 |
| `hps_data` | Household Pulse Survey | `timeseries/hps` | 2020–2023 (weeks 1–63) | 38,495 |
| `hhpulse_data` | Household Pulse Survey, 2024 cycles | `timeseries/hhpulse` | 2024 | 7,839 |
| `decennial_data` | Decennial Census | `{year}/dec/pl`, `2010/dec/sf1` | 2010, 2020 | 6,546 |
| `pep_data` | Population Estimates Program | `{year}/pep/population` | 2019–2021 | 3,376 |
| `acs1_data` | American Community Survey, 1-year estimates | `{year}/acs/acs1` | 2005–2023 | 936 |

Support tables: `dataset_metadata` (one row per dataset and vintage loaded, with its endpoint and row count), `intltrade_ingestion_log` (progress log for the trade ingest), `intltrade_country_ref` (country codes), and two tables that exist in the schema but are empty: `intltrade_imports_hs` (import ingestion not run yet) and `geography_ref`.

All endpoints are relative to `https://api.census.gov/data/`.

## Repository layout

```
app/            FastAPI service (app.py) and its demo page (templates/index.html)
setup/          Scripts that create tables, one per dataset family
ingest/         Scripts that download from the Census API and load PostgreSQL
ingest/fixes/   Follow-up scripts that corrected or resumed earlier loads
explore/        API exploration: catalog discovery, variable and geography lookups, test queries
checks/         Read-only verification and summary reports on the loaded database
sql/schema.sql  Full database schema (structure only, no data), dumped with pg_dump
data/           Local working files (gitignored): API catalogs and resume points
```

The scripts were written iteratively while learning each API, and they are kept as they were written so the process stays visible. Most are self-contained: each has its own connection helper and can run on its own.

## Setup

Requires Python 3.11 and PostgreSQL (built and tested on version 16).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env    # then add your Census API key and database URL
```

Get a free API key at <https://api.census.gov/data/key_signup.html>. Every script reads `CENSUS_API_KEY` and `DATABASE_URL` from `.env`. If `DATABASE_URL` is not set, the standard PostgreSQL variables (`PGHOST`, `PGUSER`, `PGDATABASE`, and so on) are used instead.

Create the database and load the schema:

```bash
createdb census_data
psql "$DATABASE_URL" -f sql/schema.sql
```

Run all scripts from the repository root, for example `python ingest/ingest_cbp_data.py`.

## Ingesting data

> **Warning:** many `setup/` and `ingest/` scripts start with `DROP TABLE` and recreate their tables. Running one again replaces that table's data. Back up first if you have a loaded database.

Each dataset family follows the same pattern: explore the endpoint, create the table, then ingest one vintage at a time with retries and a pause between requests to respect the API's rate limits. A typical order:

1. **Tables:** load `sql/schema.sql` (above), or run the `setup/` scripts.
2. **Business statistics:** `ingest_cbp_data.py`, `ingest_cbp_expanded.py`, `ingest_cbp_older.py` and `ingest_cbp_earlier_fixed.py` (County Business Patterns by era, because industry codes move from SIC to successive NAICS editions and field names change across vintages), `ingest_zbp_data.py`, `ingest_nes_data.py` and `ingest_nes_missing.py`, `ingest_ec_data.py`, `ingest_abs_data.py`.
3. **Population and households:** `ingest_acs_with_key.py` and `ingest_acs_missing_years.py`, `ingest_pep_data.py` and `ingest_pep_county_2021.py`, `ingest_decennial_data.py` (then `fixes/fix_2010_decennial.py` for 2010), `ingest_household_pulse.py`.
4. **Additional series:** `ingest_new_datasets.py` (SAIPE, SAHIE, SBO), `add_more_datasets.py` (ACS 1-year), `add_cps_fix_bds.py` (CPS), `fixes/fix_bds_comprehensive.py` (the final Business Dynamics Statistics load), `ingest_econ_indicators_complete.py`.
5. **International trade:** `setup/setup_intltrade_tables.py`, then `ingest/ingest_intltrade_robust.py`. This is the largest load (tens of millions of rows). It logs each month to `intltrade_ingestion_log` and resumes where it stopped. Run it in the background:

   ```bash
   nohup python -u ingest/ingest_intltrade_robust.py > intltrade_ingestion.log 2>&1 &
   python checks/intltrade_status.py      # progress report
   python ingest/update_intltrade.py      # later: pull newly released months
   ```

A few scripts tried sources that did not make it into the final database (for example building permits, QWI, and the Commodity Flow Survey). Their tables are not in `sql/schema.sql`.

`explore/explore_census_api.py` downloads the full Census API catalog to `data/census_api_discovery.json`, and `explore/analyze_census_catalog.py` summarizes it. Those catalog files are regenerated on demand and are not committed.

## Running the API

```bash
uvicorn app.app:app --reload
```

Then open:

- <http://127.0.0.1:8000/docs> for the interactive API documentation
- <http://127.0.0.1:8000/> for the demo page
- <http://127.0.0.1:8000/api/overview> for row counts and year ranges for the main datasets

Endpoint groups:

| Group | Examples |
| --- | --- |
| Overview and reference | `/api/overview`, `/api/reference/states`, `/api/reference/naics`, `/api/reference/years` |
| Business patterns | `/api/cbp/states`, `/api/cbp/counties/{state_fips}`, `/api/cbp/trends`, `/api/cbp/industries`, `/api/zbp/zipcode/{zipcode}`, `/api/zbp/top` |
| Nonemployers and Economic Census | `/api/nes/states`, `/api/nes/trends`, `/api/ec/states`, `/api/ec/industries`, `/api/ec/compare` |
| Population and demographics | `/api/acs/states`, `/api/acs/counties/{state_fips}`, `/api/pep/states`, `/api/pep/trends`, `/api/decennial/states`, `/api/decennial/counties/{state_fips}` |
| Cross-dataset | `/api/combined/state-profile/{state_fips}`, `/api/combined/economic-density`, `/api/historical/employment`, `/api/historical/state/{state_fips}`, `/api/abs/states` |

The API currently covers the business, population, and demographic tables. The newer tables (trade, economic indicators, CPS, Household Pulse, SAIPE, SAHIE) are in the database and can be queried with SQL, but they have no endpoints yet.

## Checking the database

```bash
python checks/test_connection.py             # can we connect?
python checks/verify_complete_database.py    # row counts, coverage, and spot checks per table
python checks/final_summary.py               # one-page summary of every table
```

## Known gaps and next steps

- The `/explorer` route expects a `templates/explorer.html` page that was never written.
- Import trade data (`intltrade_imports_hs`) is not loaded yet.
- Connection and request code is repeated in each script. A shared module and a single command-line entry point per dataset would make the pipeline easier to rerun.
- No automated tests yet.

## Data source

This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau. All data comes from public U.S. Census Bureau releases.

## License

No license has been chosen yet.
