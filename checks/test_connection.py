import psycopg2
import os

from dotenv import load_dotenv

load_dotenv()  # reads CENSUS_API_KEY and DATABASE_URL from the repo's .env

try:
    conn = psycopg2.connect(os.environ.get("DATABASE_URL", ""))
    print("Connection successful!")
    
    # Get PostgreSQL version
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print(cur.fetchone()[0])
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Connection failed: {e}") 