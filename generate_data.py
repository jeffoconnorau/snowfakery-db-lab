import os
import argparse
from urllib.parse import quote_plus
import sqlalchemy
import certifi
from snowfakery import generate_data
from snowfakery.output_streams import SqlDbOutputStream
from google.cloud.sql.connector import Connector, IPTypes
from google.cloud.alloydb.connector import Connector as AlloyConnector

# --- Fix SSL Issues (Zscaler/Corporate Proxy context) ---
# Force Python/OpenSSL to use certifi's bundle if no other bundle is set
if "SSL_CERT_FILE" not in os.environ:
    os.environ["SSL_CERT_FILE"] = certifi.where()
    print(f"🔒 Set SSL_CERT_FILE to {os.environ['SSL_CERT_FILE']}")
# --------------------------------------------------------

# --- Configuration ---
POSTGRES_CONNECTION_NAME = os.getenv("POSTGRES_CONNECTION_NAME", "argo-svc-dbs:asia-southeast1:postgres-lab-instance")
MYSQL_CONNECTION_NAME = os.getenv("MYSQL_CONNECTION_NAME", "argo-svc-dbs:asia-southeast1:mysql-lab-instance")
MSSQL_CONNECTION_NAME = os.getenv("MSSQL_CONNECTION_NAME", "argo-svc-dbs:asia-southeast1:mssql-lab-instance")
ALLOYDB_CLUSTER = os.getenv("ALLOYDB_CLUSTER", "projects/argo-svc-dbs/locations/asia-southeast1/clusters/alloydb-lab-cluster")
ALLOYDB_INSTANCE = os.getenv("ALLOYDB_INSTANCE", "alloydb-lab-instance")

DB_PASSWORD = os.getenv("DB_PASSWORD", "VMware123456") 
DB_NAME = os.getenv("DB_NAME", "sap_db")
DB_IP_TYPE = os.getenv("DB_IP_TYPE", "PUBLIC").upper() # PUBLIC, PRIVATE, PSC

# Global Connectors
_sql_connector = None
_alloy_connector = None

def get_sql_connector():
    global _sql_connector
    if _sql_connector is None:
        _sql_connector = Connector()
    return _sql_connector

def get_alloy_connector():
    global _alloy_connector
    if _alloy_connector is None:
        _alloy_connector = AlloyConnector()
    return _alloy_connector

def get_db_user(db_type):
    """Returns configured user or smart default based on DB type."""
    env_user = os.getenv("DB_USER")
    if env_user:
        return env_user
    
    if db_type == "MYSQL":
        return "root"
    elif db_type in ["POSTGRES", "ALLOYDB"]:
        return "postgres"
    return "user" # Fallback for others

def get_engine(db_type):
    """Creates a SQLAlchemy engine using appropriate connector."""
    current_user = get_db_user(db_type)
    
    if db_type == "POSTGRES":
        connector = get_sql_connector()
        def getconn():
            return connector.connect(
                POSTGRES_CONNECTION_NAME,
                "pg8000",
                user=current_user,
                password=DB_PASSWORD,
                db=DB_NAME,
                ip_type=DB_IP_TYPE
            )
        return sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)

    elif db_type == "ALLOYDB":
        connector = get_alloy_connector()
        # Full Instance URI: projects/config/locations/region/clusters/cluster/instances/instance
        alloydb_full_uri = f"{ALLOYDB_CLUSTER}/instances/{ALLOYDB_INSTANCE}"
        
        def getconn():
            return connector.connect(
                alloydb_full_uri,
                "pg8000",
                user=current_user,
                password=DB_PASSWORD,
                db=DB_NAME,
                ip_type=DB_IP_TYPE
            )
        return sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)

    elif db_type == "MYSQL":
        connector = get_sql_connector()
        def getconn():
            return connector.connect(
                MYSQL_CONNECTION_NAME,
                "pymysql",
                user=current_user,
                password=DB_PASSWORD,
                db=DB_NAME,
                ip_type=DB_IP_TYPE
            )
        return sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)

    elif db_type == "MSSQL":
        # For MSSQL, we currently lack a clean Connector solution without ODBC driver
        # We will skip or fail if requested.
        # If user has ODBC driver, we could try standard connection?
        # Leaving as NotImplemented for connector approach for now.
        return None

    else:
        raise ValueError(f"Unknown DB type for Connector: {db_type}")

# --- Monkeypatching Snowfakery ---
# We patch SqlDbOutputStream.from_url to intercept "connector://" URLs
_original_from_url = SqlDbOutputStream.from_url

@classmethod
def patched_from_url(cls, db_url: str, mappings=None):
    if db_url.startswith("connector://"):
        db_type = db_url.replace("connector://", "")
        print(f"🔌 Intercepting Connector request for: {db_type}")
        engine = get_engine(db_type)
        if not engine:
            raise ValueError(f"Could not create engine for {db_type}")
        return cls(engine)
    return _original_from_url(db_url, mappings)

SqlDbOutputStream.from_url = patched_from_url
# ----------------------------------

def run_generation(recipe_file, iterations=1, targets=None):
    if not targets:
        # Default Targets (MSSQL skipped by default in this mode until fixed)
        targets = ["POSTGRES", "ALLOYDB", "MYSQL", "HANA"] 
    
    print(f"Starting generation using recipe: {recipe_file}")
    print(f"Iterations: {iterations}, Targets: {targets}")
    
    for db_type in targets:
        try:
            print(f"\n--- Target: {db_type} ---")
            
            if db_type == "HANA":
                # HANA uses standard URL (SSH Tunnel)
                host = os.getenv("HANA_HOST", "localhost")
                port = os.getenv("HANA_PORT", "39015")
                db_url = f"hana://{DB_USER}:{quote_plus(DB_PASSWORD)}@{host}:{port}"
            elif db_type == "MSSQL":
                 # Skip for now
                 print("Skipping MSSQL (requires ODBC driver + Proxy or Connector setup)")
                 continue
            else:
                # Use Connector
                db_url = f"connector://{db_type}"

            for i in range(iterations):
                print(f"Batch {i+1}/{iterations}...")
                generate_data(
                    recipe_file,
                    dburl=db_url
                )
                print(f"Success {db_type} batch {i+1}")
                
        except Exception as e:
            print(f"❌ Error in {db_type}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", "-t", nargs="+", help="Targets: POSTGRES ALLOYDB MYSQL MSSQL HANA")
    parser.add_argument("--iterations", "-i", type=int, default=1)
    parser.add_argument("--recipe", "-r", default="complete_data.recipe.yml")
    args = parser.parse_args()
    
    run_generation(args.recipe, args.iterations, args.targets)