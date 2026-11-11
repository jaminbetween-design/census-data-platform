from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from pydantic import BaseModel
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

# Initialize FastAPI app
app = FastAPI(
    title="Census Data API",
    description="Access US Census Bureau data including business patterns, demographics, and employment statistics",
    version="1.0.0"
)

# Templates for HTML pages
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

# Database connection
def get_db():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""), cursor_factory=RealDictCursor)
    return conn

# =============================================================================
# RESPONSE MODELS
# =============================================================================

class StateBusinessData(BaseModel):
    state_fips: str
    geo_name: str
    vintage: int
    establishments: Optional[int]
    employees: Optional[int]
    annual_payroll: Optional[int]

class CountyBusinessData(BaseModel):
    state_fips: str
    county_fips: str
    geo_name: str
    vintage: int
    naics_code: str
    establishments: Optional[int]
    employees: Optional[int]
    annual_payroll: Optional[int]

class ZIPBusinessData(BaseModel):
    zipcode: str
    vintage: int
    naics_code: Optional[str]
    establishments: Optional[int]
    employees: Optional[int]
    annual_payroll: Optional[int]

class DemographicData(BaseModel):
    state_fips: str
    county_fips: Optional[str]
    geo_name: str
    vintage: int
    total_population: Optional[int]
    median_household_income: Optional[int]
    median_age: Optional[float]
    median_home_value: Optional[int]

# =============================================================================
# HTML PAGES (Demo Frontend)
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with demo interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/explorer", response_class=HTMLResponse)
async def explorer(request: Request):
    """Data explorer page"""
    return templates.TemplateResponse("explorer.html", {"request": request})

# =============================================================================
# API ENDPOINTS - DATABASE OVERVIEW
# =============================================================================

@app.get("/api/overview")
async def get_overview():
    """Get database overview statistics"""
    conn = get_db()
    cur = conn.cursor()
    
    stats = {}
    
    # Total rows by dataset
    datasets = [
        ('cbp_data', 'County Business Patterns'),
        ('zbp_data', 'ZIP Code Business Patterns'),
        ('nes_data', 'Nonemployer Statistics'),
        ('acs_data', 'American Community Survey'),
        ('pep_data', 'Population Estimates'),
        ('ec_data', 'Economic Census'),
        ('decennial_data', 'Decennial Census'),
        ('abs_data', 'Annual Business Survey')
    ]
    
    stats['datasets'] = []
    total_rows = 0
    
    for table, name in datasets:
        try:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            total_rows += count
            
            cur.execute(f"SELECT MIN(vintage) as min_year, MAX(vintage) as max_year FROM {table}")
            years = cur.fetchone()
            
            stats['datasets'].append({
                'name': name,
                'table': table,
                'rows': count,
                'min_year': years['min_year'],
                'max_year': years['max_year']
            })
        except:
            pass
    
    stats['total_rows'] = total_rows
    
    # Geographic coverage
    cur.execute("SELECT COUNT(DISTINCT state_fips) FROM cbp_data WHERE state_fips IS NOT NULL")
    stats['states'] = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(DISTINCT zipcode) FROM zbp_data")
    stats['zipcodes'] = cur.fetchone()['count']
    
    # Historical range
    cur.execute("SELECT MIN(vintage), MAX(vintage) FROM cbp_data")
    year_range = cur.fetchone()
    stats['min_year'] = year_range['min']
    stats['max_year'] = year_range['max']
    
    cur.close()
    conn.close()
    
    return stats

# =============================================================================
# API ENDPOINTS - COUNTY BUSINESS PATTERNS (CBP)
# =============================================================================

@app.get("/api/cbp/states")
async def get_cbp_states(
    year: int = Query(2023, description="Data year (2008-2023)"),
    naics: str = Query("00", description="NAICS code (00 for all industries)")
):
    """Get state-level business data"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, geo_name, vintage, establishments, employees, annual_payroll
        FROM cbp_data
        WHERE vintage = %s AND geo_level = 'state' AND naics_code = %s
        ORDER BY employees DESC
    """, (year, naics))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "naics": naics, "count": len(results), "data": results}

@app.get("/api/cbp/counties/{state_fips}")
async def get_cbp_counties(
    state_fips: str,
    year: int = Query(2023, description="Data year"),
    naics: str = Query("00", description="NAICS code")
):
    """Get county-level business data for a state"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, county_fips, geo_name, vintage, naics_code,
               establishments, employees, annual_payroll
        FROM cbp_data
        WHERE vintage = %s AND geo_level = 'county' 
          AND state_fips = %s AND naics_code = %s
        ORDER BY employees DESC
    """, (year, state_fips, naics))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"state_fips": state_fips, "year": year, "naics": naics, "count": len(results), "data": results}

@app.get("/api/cbp/trends")
async def get_cbp_trends(
    state_fips: Optional[str] = Query(None, description="State FIPS (omit for national)"),
    naics: str = Query("00", description="NAICS code")
):
    """Get employment trends over time"""
    conn = get_db()
    cur = conn.cursor()
    
    if state_fips:
        cur.execute("""
            SELECT vintage, SUM(establishments) as establishments, 
                   SUM(employees) as employees, SUM(annual_payroll) as annual_payroll
            FROM cbp_data
            WHERE geo_level = 'state' AND state_fips = %s AND naics_code = %s
            GROUP BY vintage
            ORDER BY vintage
        """, (state_fips, naics))
    else:
        cur.execute("""
            SELECT vintage, SUM(establishments) as establishments, 
                   SUM(employees) as employees, SUM(annual_payroll) as annual_payroll
            FROM cbp_data
            WHERE geo_level = 'state' AND naics_code = %s
            GROUP BY vintage
            ORDER BY vintage
        """, (naics,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"state_fips": state_fips, "naics": naics, "data": results}

@app.get("/api/cbp/industries")
async def get_industries(
    year: int = Query(2023, description="Data year"),
    state_fips: Optional[str] = Query(None, description="State FIPS (omit for national)")
):
    """Get industry breakdown"""
    conn = get_db()
    cur = conn.cursor()
    
    if state_fips:
        cur.execute("""
            SELECT naics_code, SUM(establishments) as establishments, 
                   SUM(employees) as employees, SUM(annual_payroll) as annual_payroll
            FROM cbp_data
            WHERE vintage = %s AND geo_level = 'state' AND state_fips = %s
              AND LENGTH(naics_code) = 2 AND naics_code != '00'
            GROUP BY naics_code
            ORDER BY employees DESC
        """, (year, state_fips))
    else:
        cur.execute("""
            SELECT naics_code, SUM(establishments) as establishments, 
                   SUM(employees) as employees, SUM(annual_payroll) as annual_payroll
            FROM cbp_data
            WHERE vintage = %s AND geo_level = 'state'
              AND LENGTH(naics_code) = 2 AND naics_code != '00'
            GROUP BY naics_code
            ORDER BY employees DESC
        """, (year,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    # Add industry names
    naics_labels = {
        '11': 'Agriculture, Forestry, Fishing', '21': 'Mining, Quarrying, Oil/Gas',
        '22': 'Utilities', '23': 'Construction',
        '31': 'Manufacturing', '32': 'Manufacturing', '33': 'Manufacturing',
        '42': 'Wholesale Trade', '44': 'Retail Trade', '45': 'Retail Trade',
        '48': 'Transportation', '49': 'Warehousing',
        '51': 'Information', '52': 'Finance and Insurance',
        '53': 'Real Estate', '54': 'Professional Services',
        '55': 'Management of Companies', '56': 'Administrative/Support Services',
        '61': 'Educational Services', '62': 'Health Care and Social Assistance',
        '71': 'Arts, Entertainment, Recreation', '72': 'Accommodation and Food Services',
        '81': 'Other Services', '99': 'Unclassified'
    }
    
    for row in results:
        row['industry_name'] = naics_labels.get(row['naics_code'], 'Unknown')
    
    return {"year": year, "state_fips": state_fips, "data": results}

# =============================================================================
# API ENDPOINTS - ZIP CODE BUSINESS PATTERNS (ZBP)
# =============================================================================

@app.get("/api/zbp/zipcode/{zipcode}")
async def get_zbp_zipcode(
    zipcode: str,
    year: int = Query(2023, description="Data year (2018-2023)")
):
    """Get business data for a specific ZIP code"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT zipcode, vintage, naics_code, establishments, employees, annual_payroll
        FROM zbp_data
        WHERE zipcode = %s AND vintage = %s
        ORDER BY 
            CASE WHEN naics_code = '00' THEN 0 ELSE 1 END,
            employees DESC NULLS LAST
    """, (zipcode, year))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    if not results:
        raise HTTPException(status_code=404, detail=f"No data found for ZIP code {zipcode} in {year}")
    
    return {"zipcode": zipcode, "year": year, "count": len(results), "data": results}

@app.get("/api/zbp/top")
async def get_top_zipcodes(
    year: int = Query(2023, description="Data year"),
    limit: int = Query(25, description="Number of results", le=100)
):
    """Get top ZIP codes by establishments"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT zipcode, establishments, employees, annual_payroll
        FROM zbp_data
        WHERE vintage = %s AND naics_code = '00' AND zipcode != '99999'
        ORDER BY establishments DESC
        LIMIT %s
    """, (year, limit))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "data": results}

# =============================================================================
# API ENDPOINTS - NONEMPLOYER STATISTICS (NES)
# =============================================================================

@app.get("/api/nes/states")
async def get_nes_states(
    year: int = Query(2023, description="Data year (2012-2023)"),
    naics: str = Query("00", description="NAICS code")
):
    """Get state-level self-employment data"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, geo_name, vintage, establishments, receipts
        FROM nes_data
        WHERE vintage = %s AND geo_level = 'state' AND naics_code = %s
        ORDER BY establishments DESC
    """, (year, naics))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "naics": naics, "count": len(results), "data": results}

@app.get("/api/nes/trends")
async def get_nes_trends(
    state_fips: Optional[str] = Query(None, description="State FIPS (omit for national)")
):
    """Get self-employment trends over time"""
    conn = get_db()
    cur = conn.cursor()
    
    if state_fips:
        cur.execute("""
            SELECT vintage, SUM(establishments) as establishments, SUM(receipts) as receipts
            FROM nes_data
            WHERE geo_level = 'state' AND state_fips = %s AND naics_code = '00'
            GROUP BY vintage
            ORDER BY vintage
        """, (state_fips,))
    else:
        cur.execute("""
            SELECT vintage, SUM(establishments) as establishments, SUM(receipts) as receipts
            FROM nes_data
            WHERE geo_level = 'state' AND naics_code = '00'
            GROUP BY vintage
            ORDER BY vintage
        """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"state_fips": state_fips, "data": results}

# =============================================================================
# API ENDPOINTS - DEMOGRAPHICS (ACS)
# =============================================================================

@app.get("/api/acs/states")
async def get_acs_states(
    year: int = Query(2023, description="Data year (2012-2023)")
):
    """Get state-level demographic data"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, geo_name, vintage, total_population, 
               median_household_income, per_capita_income, median_age,
               median_home_value, median_gross_rent,
               labor_force, unemployed
        FROM acs_data
        WHERE vintage = %s AND geo_level = 'state'
        ORDER BY total_population DESC
    """, (year,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "count": len(results), "data": results}

@app.get("/api/acs/counties/{state_fips}")
async def get_acs_counties(
    state_fips: str,
    year: int = Query(2023, description="Data year")
):
    """Get county-level demographic data for a state"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, county_fips, geo_name, vintage, total_population,
               median_household_income, per_capita_income, median_age,
               median_home_value, median_gross_rent
        FROM acs_data
        WHERE vintage = %s AND geo_level = 'county' AND state_fips = %s
        ORDER BY total_population DESC
    """, (year, state_fips))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"state_fips": state_fips, "year": year, "count": len(results), "data": results}

# =============================================================================
# API ENDPOINTS - COMBINED ANALYSES
# =============================================================================

@app.get("/api/combined/state-profile/{state_fips}")
async def get_state_profile(
    state_fips: str,
    year: int = Query(2022, description="Data year")
):
    """Get comprehensive state profile combining all datasets"""
    conn = get_db()
    cur = conn.cursor()
    
    # Demographics
    cur.execute("""
        SELECT * FROM acs_data
        WHERE vintage = %s AND geo_level = 'state' AND state_fips = %s
    """, (year, state_fips))
    demographics = cur.fetchone()
    
    # Business (employers)
    cur.execute("""
        SELECT establishments, employees, annual_payroll
        FROM cbp_data
        WHERE vintage = %s AND geo_level = 'state' AND state_fips = %s AND naics_code = '00'
    """, (year, state_fips))
    business = cur.fetchone()
    
    # Self-employment
    cur.execute("""
        SELECT establishments, receipts
        FROM nes_data
        WHERE vintage = %s AND geo_level = 'state' AND state_fips = %s AND naics_code = '00'
    """, (year, state_fips))
    self_employment = cur.fetchone()
    
    # Top industries
    cur.execute("""
        SELECT naics_code, establishments, employees, annual_payroll
        FROM cbp_data
        WHERE vintage = %s AND geo_level = 'state' AND state_fips = %s
          AND LENGTH(naics_code) = 2 AND naics_code != '00'
        ORDER BY employees DESC
        LIMIT 5
    """, (year, state_fips))
    top_industries = cur.fetchall()
    
    cur.close()
    conn.close()
    
    if not demographics:
        raise HTTPException(status_code=404, detail=f"No data found for state {state_fips}")
    
    return {
        "state_fips": state_fips,
        "year": year,
        "demographics": demographics,
        "business": business,
        "self_employment": self_employment,
        "top_industries": top_industries
    }

@app.get("/api/combined/economic-density")
async def get_economic_density(
    year: int = Query(2022, description="Data year")
):
    """Get economic density (jobs per capita) by state"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            a.state_fips,
            a.geo_name,
            a.total_population,
            c.employees,
            n.establishments as self_employed,
            ROUND(100.0 * (c.employees + n.establishments) / NULLIF(a.total_population, 0), 1) as density
        FROM acs_data a
        JOIN cbp_data c ON a.state_fips = c.state_fips AND a.vintage = c.vintage
        JOIN nes_data n ON a.state_fips = n.state_fips AND a.vintage = n.vintage
        WHERE a.vintage = %s
          AND a.geo_level = 'state'
          AND c.geo_level = 'state'
          AND n.geo_level = 'state'
          AND c.naics_code = '00'
          AND n.naics_code = '00'
        ORDER BY density DESC
    """, (year,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "data": results}

# =============================================================================
# API ENDPOINTS - POPULATION ESTIMATES (PEP)
# =============================================================================

@app.get("/api/pep/states")
async def get_pep_states(
    year: int = Query(2021, description="Data year (2019-2021)")
):
    """Get state-level population estimates"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, geo_name, vintage, population, density
        FROM pep_data
        WHERE vintage = %s AND geo_level = 'state'
        ORDER BY population DESC
    """, (year,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "count": len(results), "data": results}

@app.get("/api/pep/trends")
async def get_pep_trends():
    """Get population trends over time"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT vintage, SUM(population) as total_population
        FROM pep_data
        WHERE geo_level = 'state'
        GROUP BY vintage
        ORDER BY vintage
    """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"data": results}

# =============================================================================
# API ENDPOINTS - ECONOMIC CENSUS (EC)
# =============================================================================

@app.get("/api/ec/states")
async def get_ec_states(
    year: int = Query(2022, description="Census year (2012, 2017, 2022)"),
    naics: Optional[str] = Query(None, description="NAICS code filter")
):
    """Get state-level Economic Census data"""
    conn = get_db()
    cur = conn.cursor()
    
    if naics:
        cur.execute("""
            SELECT state_fips, geo_name, naics_code, establishments, employees, annual_payroll, receipts
            FROM ec_data
            WHERE vintage = %s AND geo_level = 'state' AND naics_code = %s
            ORDER BY employees DESC NULLS LAST
        """, (year, naics))
    else:
        cur.execute("""
            SELECT state_fips, geo_name, naics_code, establishments, employees, annual_payroll, receipts
            FROM ec_data
            WHERE vintage = %s AND geo_level = 'state' AND LENGTH(naics_code) = 2
            ORDER BY employees DESC NULLS LAST
            LIMIT 1000
        """, (year,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "naics": naics, "count": len(results), "data": results}

@app.get("/api/ec/industries")
async def get_ec_industries(
    year: int = Query(2022, description="Census year"),
    state_fips: Optional[str] = Query(None, description="State FIPS code")
):
    """Get industry summary from Economic Census"""
    conn = get_db()
    cur = conn.cursor()
    
    if state_fips:
        cur.execute("""
            SELECT naics_code, SUM(establishments) as establishments, 
                   SUM(employees) as employees, SUM(receipts) as receipts
            FROM ec_data
            WHERE vintage = %s AND geo_level = 'state' AND state_fips = %s
              AND LENGTH(naics_code) = 2
            GROUP BY naics_code
            ORDER BY employees DESC NULLS LAST
        """, (year, state_fips))
    else:
        cur.execute("""
            SELECT naics_code, SUM(establishments) as establishments, 
                   SUM(employees) as employees, SUM(receipts) as receipts
            FROM ec_data
            WHERE vintage = %s AND geo_level = 'state' AND LENGTH(naics_code) = 2
            GROUP BY naics_code
            ORDER BY employees DESC NULLS LAST
        """, (year,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    # Add industry names
    naics_labels = {
        '11': 'Agriculture, Forestry, Fishing', '21': 'Mining, Quarrying, Oil/Gas',
        '22': 'Utilities', '23': 'Construction',
        '31': 'Manufacturing', '32': 'Manufacturing', '33': 'Manufacturing',
        '42': 'Wholesale Trade', '44': 'Retail Trade', '45': 'Retail Trade',
        '48': 'Transportation', '49': 'Warehousing',
        '51': 'Information', '52': 'Finance and Insurance',
        '53': 'Real Estate', '54': 'Professional Services',
        '55': 'Management of Companies', '56': 'Administrative/Support Services',
        '61': 'Educational Services', '62': 'Health Care and Social Assistance',
        '71': 'Arts, Entertainment, Recreation', '72': 'Accommodation and Food Services',
        '81': 'Other Services', '99': 'Unclassified'
    }
    
    for row in results:
        row['industry_name'] = naics_labels.get(row['naics_code'], 'Unknown')
    
    return {"year": year, "state_fips": state_fips, "data": results}

@app.get("/api/ec/compare")
async def get_ec_compare(
    naics: str = Query(..., description="NAICS code to compare"),
    state_fips: Optional[str] = Query(None, description="State FIPS (omit for national)")
):
    """Compare Economic Census data across census years"""
    conn = get_db()
    cur = conn.cursor()
    
    if state_fips:
        cur.execute("""
            SELECT vintage, SUM(establishments) as establishments, 
                   SUM(employees) as employees, SUM(receipts) as receipts
            FROM ec_data
            WHERE naics_code = %s AND geo_level = 'state' AND state_fips = %s
            GROUP BY vintage
            ORDER BY vintage
        """, (naics, state_fips))
    else:
        cur.execute("""
            SELECT vintage, SUM(establishments) as establishments, 
                   SUM(employees) as employees, SUM(receipts) as receipts
            FROM ec_data
            WHERE naics_code = %s AND geo_level = 'state'
            GROUP BY vintage
            ORDER BY vintage
        """, (naics,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"naics": naics, "state_fips": state_fips, "data": results}


# =============================================================================
# API ENDPOINTS - DECENNIAL CENSUS
# =============================================================================

@app.get("/api/decennial/states")
async def get_decennial_states(
    year: int = Query(2020, description="Census year (2010, 2020)")
):
    """Get state-level Decennial Census data"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, geo_name, total_population, housing_units, occupied_housing, vacant_housing
        FROM decennial_data
        WHERE vintage = %s AND geo_level = 'state'
        ORDER BY total_population DESC
    """, (year,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "count": len(results), "data": results}

@app.get("/api/decennial/counties/{state_fips}")
async def get_decennial_counties(
    state_fips: str,
    year: int = Query(2020, description="Census year")
):
    """Get county-level Decennial Census data for a state"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, county_fips, geo_name, total_population, housing_units
        FROM decennial_data
        WHERE vintage = %s AND geo_level = 'county' AND state_fips = %s
        ORDER BY total_population DESC
    """, (year, state_fips))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "state_fips": state_fips, "count": len(results), "data": results}

# =============================================================================
# API ENDPOINTS - ANNUAL BUSINESS SURVEY (ABS)
# =============================================================================

@app.get("/api/abs/states")
async def get_abs_states(
    year: int = Query(2021, description="Data year (2017-2021)")
):
    """Get state-level Annual Business Survey data"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state_fips, geo_name, naics_code, employees, annual_payroll
        FROM abs_data
        WHERE vintage = %s AND LENGTH(naics_code) = 2
        ORDER BY employees DESC NULLS LAST
    """, (year,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"year": year, "count": len(results), "data": results}

# =============================================================================
# API ENDPOINTS - HISTORICAL DATA
# =============================================================================

@app.get("/api/historical/employment")
async def get_historical_employment():
    """Get national employment trends from 1986-2023"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT vintage, 
               SUM(employees) as total_employees,
               SUM(establishments) as total_establishments,
               SUM(annual_payroll) as total_payroll
        FROM cbp_data
        WHERE geo_level = 'state' 
          AND (naics_code = '00' OR naics_code = '------' OR naics_code = '0')
        GROUP BY vintage
        ORDER BY vintage
    """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"data": results}

@app.get("/api/historical/state/{state_fips}")
async def get_historical_state(state_fips: str):
    """Get historical employment data for a specific state"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT vintage, 
               SUM(employees) as employees,
               SUM(establishments) as establishments,
               SUM(annual_payroll) as payroll
        FROM cbp_data
        WHERE geo_level = 'state' AND state_fips = %s
          AND (naics_code = '00' OR naics_code = '------' OR naics_code = '0')
        GROUP BY vintage
        ORDER BY vintage
    """, (state_fips,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"state_fips": state_fips, "data": results}


# =============================================================================
# REFERENCE DATA
# =============================================================================

@app.get("/api/reference/states")
async def get_state_list():
    """Get list of all states with FIPS codes"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT state_fips, geo_name
        FROM cbp_data
        WHERE geo_level = 'state' AND vintage = 2023 AND naics_code = '00'
        ORDER BY geo_name
    """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"data": results}

@app.get("/api/reference/naics")
async def get_naics_codes():
    """Get list of NAICS codes with descriptions"""
    naics_labels = {
        '00': 'All Industries',
        '11': 'Agriculture, Forestry, Fishing and Hunting',
        '21': 'Mining, Quarrying, and Oil and Gas Extraction',
        '22': 'Utilities',
        '23': 'Construction',
        '31': 'Manufacturing',
        '32': 'Manufacturing',
        '33': 'Manufacturing',
        '42': 'Wholesale Trade',
        '44': 'Retail Trade',
        '45': 'Retail Trade',
        '48': 'Transportation and Warehousing',
        '49': 'Transportation and Warehousing',
        '51': 'Information',
        '52': 'Finance and Insurance',
        '53': 'Real Estate and Rental and Leasing',
        '54': 'Professional, Scientific, and Technical Services',
        '55': 'Management of Companies and Enterprises',
        '56': 'Administrative and Support Services',
        '61': 'Educational Services',
        '62': 'Health Care and Social Assistance',
        '71': 'Arts, Entertainment, and Recreation',
        '72': 'Accommodation and Food Services',
        '81': 'Other Services (except Public Administration)',
        '99': 'Unclassified'
    }
    
    return {"data": [{"code": k, "description": v} for k, v in naics_labels.items()]}

@app.get("/api/reference/years")
async def get_available_years():
    """Get available years for each dataset"""
    conn = get_db()
    cur = conn.cursor()
    
    datasets = {}
    
    for table in ['cbp_data', 'zbp_data', 'nes_data', 'acs_data']:
        cur.execute(f"SELECT DISTINCT vintage FROM {table} ORDER BY vintage DESC")
        datasets[table] = [row['vintage'] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return datasets

# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)