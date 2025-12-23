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

def run_generation(recipe_file, iterations=1, batch_size=1000):
    """Runs Snowfakery generation for all configured targets."""
    
    # Detect which DBs are enabled via env vars (default to all if not specified)
    # We can use a comma-separated list in ENABLED_DBS env var
    enabled_dbs = os.getenv("ENABLED_DBS", "POSTGRES,ALLOYDB,MYSQL,MSSQL,HANA").split(",")
    enabled_dbs = [db.strip().upper() for db in enabled_dbs]

    print(f"Starting generation using recipe: {recipe_file}")
    print(f"Iterations: {iterations}, Targets: {enabled_dbs}")

    for db_type in enabled_dbs:
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
                # Snowfakery doesn't have a specific 'batch size' arg per se for the CLI to restart, 
                # but 'count' in recipe controls volume. 
                # We assume recipe handles 'count' or we pass it if needed.
                # If we want to override count from CLI: "--plugin-option", "count=..."
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"Error in {db_type} batch {i+1}:")
                    print(result.stderr)
                else:
                    print(f"Success {db_type} batch {i+1}")
                    
        except Exception as e:
            print(f"Skipping {db_type} due to configuration error: {e}")

if __name__ == "__main__":
    # Default execution
    run_generation(
        recipe_file="sap_complete.recipe.yml",
        iterations=int(os.getenv("ITERATIONS", "1"))
    )