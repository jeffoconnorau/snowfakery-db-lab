import subprocess

# List of connection strings for your target databases
databases = {
    "PostgreSQL": "postgresql://user:pass@localhost/postgres",
    "AlloyDB": "postgresql://user:pass@alloydb-ip/postgres", # Uses Postgres driver
    "MySQL": "mysql+pymysql://user:pass@localhost/dbname",
    "MSSQL": "mssql+pyodbc://user:pass@localhost/dbname?driver=ODBC+Driver+17+for+SQL+Server",
    "SAPHANA": "hana://user:pass@localhost:30015"
}

def generate_data():
    recipe_path = "enterprise_data.recipe.yml"
    
    for db_name, conn_string in databases.items():
        print(f"Generating data for {db_name}...")
        try:
            # Snowfakery command to write directly to a database
            subprocess.run([
                "snowfakery", 
                recipe_path, 
                "--dburl", conn_string
            ], check=True)
            print(f"Successfully populated {db_name}")
        except Exception as e:
            print(f"Failed to populate {db_name}: {e}")

if __name__ == "__main__":
    generate_data()