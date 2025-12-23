import subprocess
import os
import sys
from urllib.parse import quote_plus

def get_db_url(db_type):
    """Constructs DB URL from environment variables or defaults."""
    
    # Common defaults
    user = os.getenv(f"{db_type}_USER", "user")
    password = quote_plus(os.getenv(f"{db_type}_PASSWORD", "password"))
    host = os.getenv(f"{db_type}_HOST", "localhost")
    port = os.getenv(f"{db_type}_PORT", "")
    dbname = os.getenv(f"{db_type}_NAME", "sap_db")

    if db_type == "POSTGRES":
        port = port or "5432"
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    elif db_type == "ALLOYDB":
        port = port or "5432"
        # AlloyDB uses Postgres driver
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    elif db_type == "MYSQL":
        port = port or "3306"
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"
    elif db_type == "MSSQL":
        port = port or "1433"
        driver = quote_plus("ODBC Driver 17 for SQL Server")
        return f"mssql+pyodbc://{user}:{password}@{host}:{port}/{dbname}?driver={driver}"
    elif db_type == "HANA":
        port = port or "39015" # Default for first instance 00
        return f"hana://{user}:{password}@{host}:{port}"
    else:
        raise ValueError(f"Unknown DB type: {db_type}")

import argparse

def run_generation(recipe_file, iterations=1, targets=None):
    """Runs Snowfakery generation for all configured targets."""
    
    # Default to all if not specified
    if not targets:
        # Check env var fallback
        env_dbs = os.getenv("ENABLED_DBS", "")
        if env_dbs:
            targets = [db.strip().upper() for db in env_dbs.split(",")]
        else:
            targets = ["POSTGRES", "ALLOYDB", "MYSQL", "MSSQL", "HANA"]
    else:
        targets = [t.upper() for t in targets]

    print(f"Starting generation using recipe: {recipe_file}")
    print(f"Iterations: {iterations}, Targets: {targets}")

    for db_type in targets:
        try:
            db_url = get_db_url(db_type)
            print(f"\n--- Target: {db_type} ---")
            
            for i in range(iterations):
                print(f"Batch {i+1}/{iterations}...")
                cmd = [
                    "snowfakery",
                    recipe_file,
                    "--dburl", db_url
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"Error in {db_type} batch {i+1}:")
                    print(result.stderr)
                else:
                    print(f"Success {db_type} batch {i+1}")
                    
        except Exception as e:
            print(f"Skipping {db_type} due to configuration error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Snowfakery generation for specific databases.")
    parser.add_argument("--targets", "-t", nargs="+", help="List of databases to target (e.g. POSTGRES MYSQL)")
    parser.add_argument("--iterations", "-i", type=int, default=int(os.getenv("ITERATIONS", "1")), help="Number of iterations per database")
    parser.add_argument("--recipe", "-r", default="complete_data.recipe.yml", help="Path to recipe file")
    
    args = parser.parse_args()
    
    run_generation(
        recipe_file=args.recipe,
        iterations=args.iterations,
        targets=args.targets
    )