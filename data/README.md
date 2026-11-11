# data/

Local working files. Everything here except this README is gitignored.

The scripts write these files here when you run them from the repo root:

| File | Written by | Size |
| --- | --- | --- |
| `census_api_discovery.json` | `explore/explore_census_api.py` (read by `explore/analyze_census_catalog.py`) | ~5 MB |
| `acs_variables.json` | `explore/explore_acs_api.py` | ~10 MB |
| `cbp_2021_variables.json`, `cbp_2021_geography.json` | `explore/explore_dataset_details.py` | <1 MB |
| `cbp_county_progress.json` | `ingest/ingest_cbp_county_by_county.py` (resume point) | small |
| `zbp_progress.json` | `ingest/ingest_zbp_data.py` (resume point) | small |
