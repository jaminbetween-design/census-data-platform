# This script outputs the new endpoints to add to your app.py

new_endpoints = '''
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
'''

# Update the overview endpoint
updated_overview = '''
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
'''

print("=" * 60)
print("NEW ENDPOINTS TO ADD TO app.py")
print("=" * 60)
print(new_endpoints)
print("\n" + "=" * 60)
print("UPDATED OVERVIEW ENDPOINT")
print("=" * 60)
print(updated_overview)

print("\n" + "=" * 60)
print("INSTRUCTIONS")
print("=" * 60)
print("""
1. Open app/app.py
2. Add the new endpoints before the 'if __name__ == "__main__":' line
3. Replace the existing @app.get("/api/overview") function with the updated version
4. Restart the app: python app/app.py
5. Test at http://localhost:8000/docs
""")