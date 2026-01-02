import os
import argparse
import logging
import shutil
from urllib.parse import quote_plus
import sqlalchemy
import certifi
from snowfakery import generate_data
from snowfakery.output_streams import SqlDbOutputStream
from google.cloud.sql.connector import Connector, IPTypes
from google.cloud.alloydb.connector import Connector as AlloyConnector

# Configure logging to show Snowfakery progress
logging.basicConfig(level=logging.INFO)

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

DB_PASSWORD = os.getenv("DB_PASSWORD")
if not DB_PASSWORD:
    raise ValueError("❌ DB_PASSWORD environment variable is required. Please export DB_PASSWORD='your_password'")

if not DB_PASSWORD:
    raise ValueError("❌ DB_PASSWORD environment variable is required. Please export DB_PASSWORD='your_password'")

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
    env_user = os.getenv("DB_USER", "").strip()
    
    if db_type == "MSSQL":
        # Force 'sqlserver' if user is default or 'dbadmin' to avoid permission issues
        if not env_user or "dbadmin" in env_user.lower():
            print(f"   ⚠️ Forcing user 'sqlserver' for MSSQL (ignoring '{env_user}')")
            return "sqlserver"
        return env_user

    if env_user:
        return env_user
    
    return "dbadmin"

def get_db_name(db_type):
    """Returns configured database name or smart default based on DB type."""
    env_name = os.getenv("DB_NAME")
    if env_name:
        return env_name
    
    if db_type == "POSTGRES":
        return "postgres_db"
    elif db_type == "MYSQL":
        return "mysql_db"
    elif db_type == "MSSQL":
        return "mssql_db"
    elif db_type == "ALLOYDB":
        return "postgres" # AlloyDB default DB
    return "postgres_db"

def get_engine(db_type):
    """Creates a SQLAlchemy engine using appropriate connector."""
    current_user = get_db_user(db_type)
    current_db = get_db_name(db_type)
    
    if db_type == "POSTGRES":
        connector = get_sql_connector()
        def getconn():
            return connector.connect(
                POSTGRES_CONNECTION_NAME,
                "pg8000",
                user=current_user,
                password=DB_PASSWORD,
                db=current_db,
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
                db=current_db,
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
                db=current_db,
                ip_type=DB_IP_TYPE
            )
        return sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)

    elif db_type == "MSSQL":
        connector = get_sql_connector()
        def getconn():
            # DEBUG: Force sqlserver to prove code update
            print(f"   🔌 MSSQL: Connecting as 'sqlserver' to '{current_db}'...")
            return connector.connect(
                MSSQL_CONNECTION_NAME,
                "pytds",
                user="sqlserver", # HARDCODED override
                password=DB_PASSWORD,
                db=current_db,
                ip_type=DB_IP_TYPE
            )
        try:
            import pytds # explicit check
        except ImportError:
            raise ImportError("❌ Python package 'python-tds' is NOT installed. Please run: pip install python-tds")

        try:
            return sqlalchemy.create_engine("mssql+pytds://", creator=getconn)
        except sqlalchemy.exc.NoSuchModuleError:
             raise ImportError("❌ SQLAlchemy could not load 'mssql+pytds'. Ensure 'sqlalchemy-pytds' is installed: pip install sqlalchemy-pytds")

    else:
        raise ValueError(f"Unknown DB type for Connector: {db_type}")

# --- Monkeypatching Snowfakery ---
from snowfakery.data_gen_exceptions import DataGenError

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
        return cls(engine, mappings)
    return _original_from_url(db_url, mappings)

SqlDbOutputStream.from_url = patched_from_url

# We patch create_or_validate_tables to allow appending to existing tables without error
_original_create_or_validate_tables = SqlDbOutputStream.create_or_validate_tables

def patched_create_or_validate_tables(self, inferred_tables):
    try:
        _original_create_or_validate_tables(self, inferred_tables)
    except DataGenError as e:
        err_msg = str(e).lower()
        # Catch "Table already exists" (Postgres/MySQL) OR "There is already an object named" (MSSQL)
        if ("table already exists" in err_msg or "already an object named" in err_msg) and os.getenv("DB_APPEND", "false").lower() == "true":
            print(f"   ⚠️ Ignoring table existence check (DB_APPEND=true).")
            # Auto-Migrate: Check for missing PAYLOAD column and add it if missing
            try:
                insp = sqlalchemy.inspect(self.engine)
                for table_name in ["MARA", "KNA1", "VBAK"]:
                    # Note: Table names might be lower/upper case depending on DB. Snowfakery recipe uses UPPER.
                    # We try to find the actual table name match.
                    db_table_names = insp.get_table_names()
                    actual_table_name = next((t for t in db_table_names if t.upper() == table_name), None)
                    
                    if actual_table_name:
                        cols = [c['name'].upper() for c in insp.get_columns(actual_table_name)]
                        if "PAYLOAD" not in cols:
                            print(f"   🛠️ Auto-migrating: Adding PAYLOAD column to {actual_table_name}...")
                            # Determine type based on dialect
                            dialect = self.engine.dialect.name
                            col_type = "TEXT"
                            if dialect == "mysql":
                                col_type = "LONGTEXT" # standard TEXT is 64KB, might be tight for 50KB+ overhead
                            
                            quoted_table = self.engine.dialect.identifier_preparer.quote(actual_table_name)
                            quoted_col = self.engine.dialect.identifier_preparer.quote("PAYLOAD")
                            with self.engine.connect() as conn:
                                conn.execute(sqlalchemy.text(f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_col} {col_type}"))
                                conn.commit()
                            print(f"   ✅ Added PAYLOAD to {actual_table_name}")
            except Exception as migration_err:
                print(f"   ❌ Migration failed: {migration_err}")
                # We continue, assuming maybe it wasn't needed or user will fix.
        else:
            raise

    # Post-validation/creation: Ensure MySQL uses LONGTEXT for PAYLOAD to avoid "Data too long" (1406)
    if self.engine.dialect.name == "mysql":
        try:
             insp = sqlalchemy.inspect(self.engine)
             for table_name in ["MARA", "KNA1", "VBAK"]:
                # Match table name
                db_table_names = insp.get_table_names()
                actual_table_name = next((t for t in db_table_names if t.upper() == table_name), None)
                
                if actual_table_name:
                    cols = insp.get_columns(actual_table_name)
                    payload_col = next((c for c in cols if c['name'].upper() == "PAYLOAD"), None)
                    
                    # If column exists, force LONGTEXT. 
                    # Note: We do this blindly to ensure it's specifically LONGTEXT, as introspection might just say 'TEXT' for all blobs sometimes.
                    if payload_col:
                        # Optimization: only alter if we suspect it's small? 
                        # Actually, executing ALTER MODIFY is cheap enough if no data or usually safe.
                        # But wait, we might have just added it?
                        # Let's just do it.
                        print(f"   🔧 MySQL: Enforcing LONGTEXT for {actual_table_name}.PAYLOAD...")
                        with self.engine.connect() as conn:
                            # MySQL requires repeated definition for MODIFY?
                            # ALTER TABLE t MODIFY col LONGTEXT
                            # MySQL usually is case-insensitive for cols unless strict, but quoting is safe.
                            quoted_col = self.engine.dialect.identifier_preparer.quote("PAYLOAD")
                            conn.execute(sqlalchemy.text(f"ALTER TABLE {actual_table_name} MODIFY {quoted_col} LONGTEXT"))
                            conn.commit()
        except Exception as e:
            print(f"   ⚠️ Could not enforce LONGTEXT on MySQL: {e}")

def fix_mssql_schema(engine):
    """
    Pre-emptively fixes MSSQL schema issues:
    1. Ensures PSTLZ (Postal Code) is VARCHAR, not BIGINT (Snowfakery inference bug with numeric mixed data).
    2. Ensures PAYLOAD is VARCHAR(MAX).
    """
    try:
        # 1. Ensure Table Exists with Correct Schema
        # If table doesn't exist, we create it with strict types to prevent bad inference.
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("""
                IF OBJECT_ID('KNA1', 'U') IS NULL
                BEGIN
                    CREATE TABLE KNA1 (
                        id BIGINT IDENTITY(1,1) PRIMARY KEY,
                        KUNNR BIGINT,
                        NAME1 NVARCHAR(255),
                        ORT01 NVARCHAR(255),
                        PSTLZ NVARCHAR(50),      -- Critical: Force String
                        LAND1 NVARCHAR(255),
                        TELF1 NVARCHAR(255),     -- Critical: Force String
                        ERDAT DATE,
                        PAYLOAD VARCHAR(MAX)     -- Critical: Force Max
                    );
                END
                ELSE
                BEGIN
                    -- Table exists, potentially bad schema. Force fix.
                    
                    -- 1. Payload
                    IF COL_LENGTH('KNA1', 'PAYLOAD') IS NULL
                        ALTER TABLE KNA1 ADD PAYLOAD VARCHAR(MAX);
                    ELSE
                        ALTER TABLE KNA1 ALTER COLUMN PAYLOAD VARCHAR(MAX);

                    -- 2. Critical Text Fields
                    IF COL_LENGTH('KNA1', 'TELF1') IS NULL ALTER TABLE KNA1 ADD TELF1 NVARCHAR(255);
                    ELSE ALTER TABLE KNA1 ALTER COLUMN TELF1 NVARCHAR(255);

                    IF COL_LENGTH('KNA1', 'ORT01') IS NULL ALTER TABLE KNA1 ADD ORT01 NVARCHAR(255);
                    ELSE ALTER TABLE KNA1 ALTER COLUMN ORT01 NVARCHAR(255);

                    IF COL_LENGTH('KNA1', 'NAME1') IS NULL ALTER TABLE KNA1 ADD NAME1 NVARCHAR(255);
                    ELSE ALTER TABLE KNA1 ALTER COLUMN NAME1 NVARCHAR(255);

                    IF COL_LENGTH('KNA1', 'LAND1') IS NULL ALTER TABLE KNA1 ADD LAND1 NVARCHAR(255);
                    ELSE ALTER TABLE KNA1 ALTER COLUMN LAND1 NVARCHAR(255);

                    IF COL_LENGTH('KNA1', 'PSTLZ') IS NULL ALTER TABLE KNA1 ADD PSTLZ NVARCHAR(50);
                    ELSE ALTER TABLE KNA1 ALTER COLUMN PSTLZ NVARCHAR(50);
                END
            """))
            conn.commit()

    except Exception as e:
        print(f"   ❌ Failed to fix MSSQL schema: {e}")

    # Post-validation: Ensure Postgres uses TEXT for PAYLOAD (fix for VARCHAR limit issues)
    if self.engine.dialect.name == "postgresql":
        try:
             insp = sqlalchemy.inspect(self.engine)
             for table_name in ["MARA", "KNA1", "VBAK"]:
                db_table_names = insp.get_table_names()
                actual_table_name = next((t for t in db_table_names if t.upper() == table_name), None)
                
                if actual_table_name:
                    cols = insp.get_columns(actual_table_name)
                    payload_col = next((c for c in cols if c['name'].upper() == "PAYLOAD"), None)
                    
                    if payload_col:
                        print(f"   🔧 Postgres: Enforcing TEXT for {actual_table_name}.PAYLOAD...")
                        quoted_table = self.engine.dialect.identifier_preparer.quote(actual_table_name)
                        quoted_col = self.engine.dialect.identifier_preparer.quote("PAYLOAD")
                        with self.engine.connect() as conn:
                            # Postgres syntax: ALTER COLUMN col TYPE type
                            conn.execute(sqlalchemy.text(f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_col} TYPE TEXT"))
                            conn.commit()
        except Exception as e:
            print(f"   ⚠️ Could not enforce TEXT on Postgres: {e}")

    # EXPLCIT MSSQL Support for PAYLOAD
    if self.engine.dialect.name == "mssql":
        fix_mssql_schema(self.engine) # Call the new function here
        try:
             insp = sqlalchemy.inspect(self.engine)
             for table_name in ["MARA", "KNA1", "VBAK"]:
                db_table_names = insp.get_table_names()
                # MSSQL might require schema checks, usually 'dbo'. get_table_names() usually returns simple names.
                actual_table_name = next((t for t in db_table_names if t.upper() == table_name), None)
                
                if actual_table_name:
                    cols = insp.get_columns(actual_table_name)
                    payload_col = next((c for c in cols if c['name'].upper() == "PAYLOAD"), None)
                    
                    if payload_col:
                         print(f"   🔧 MSSQL: Enforcing VARCHAR(MAX) for {actual_table_name}.PAYLOAD...")
                         quoted_table = self.engine.dialect.identifier_preparer.quote(actual_table_name)
                         quoted_col = self.engine.dialect.identifier_preparer.quote("PAYLOAD")
                         with self.engine.connect() as conn:
                             # MSSQL syntax: ALTER TABLE t ALTER COLUMN c TYPE
                             conn.execute(sqlalchemy.text(f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_col} VARCHAR(MAX)"))
                             conn.commit()
        except Exception as e:
            print(f"   ⚠️ Could not enforce VARCHAR(MAX) on MSSQL: {e}")

SqlDbOutputStream.create_or_validate_tables = patched_create_or_validate_tables
# ----------------------------------

def run_generation(recipe_file, iterations=1, targets=None, drop_tables=False):
    if not targets:
        # Default Targets (MSSQL skipped by default in this mode until fixed)
        targets = ["POSTGRES", "ALLOYDB", "MYSQL", "HANA"] 
    
    print(f"Starting generation using recipe: {recipe_file}")
    print(f"Iterations: {iterations}, Targets: {targets}")
    
    for db_type in targets:
        print(f"\n--- Target: {db_type} ---")
        try:
            # Determine DB URL and get engine
            if db_type == "HANA":
                # HANA uses standard URL (SSH Tunnel)
                host = os.getenv("HANA_HOST", "localhost")
                port = os.getenv("HANA_PORT", "39015")
                db_url = f"hana://{DB_USER}:{quote_plus(DB_PASSWORD)}@{host}:{port}"
            elif db_type == "MSSQL":
                 # Use Connector with pytds
                 db_url = f"connector://{db_type}"
            else:
                # Use Connector
                db_url = f"connector://{db_type}"

            engine = get_engine(db_type)
            if not engine:
                print(f"   ⚠️ Skipping {db_type} (No Engine)")
                continue

            # 0. NUCLEAR OPTION: Drop Tables if requested (BEFORE fixing schema)
            if drop_tables:
                 print(f"   ☢️ DROP TABLES requested for {db_type}. Dropping known tables...")
                 with engine.connect() as conn:
                     for tbl in ["KNA1", "MARA", "VBAK", "VBAP", "BSEG", "BKPF"]: # List known tables
                         try:
                             conn.execute(sqlalchemy.text(f"DROP TABLE IF EXISTS {tbl}"))
                             conn.commit()
                             print(f"      Deleted {tbl}")
                         except Exception as e:
                             print(f"      Could not drop {tbl}: {e}")

            # 4. Fix MSSQL Schema (Pre-emptively)
            if "mssql" in db_type.lower():
                 fix_mssql_schema(engine)

            # Check for Append Mode
            db_append = os.getenv("DB_APPEND", "false").lower() == "true"
            continuation_file = "snowfakery_continuation.yml"
            temp_continuation_file = "snowfakery_continuation_next.yml"

            if db_append:
                print(f"🔄 DB_APPEND enabled.")

            for i in range(iterations):
                print(f"Batch {i+1}/{iterations}...")
                gen_kwargs = {}
                
                if db_append:
                    # Input: Use existing continuation file if valid (exists and not empty)
                    if os.path.exists(continuation_file) and os.path.getsize(continuation_file) > 0:
                        gen_kwargs["continuation_file"] = continuation_file
                        print(f"   Using continuation file '{continuation_file}'")
                    else:
                        print(f"   Starting fresh (no valid continuation file found).")
                    
                    # Output: Write to a temp file to avoid corruption during run
                    gen_kwargs["generate_continuation_file"] = temp_continuation_file
                
                # Removed the old drop_tables block from here

                try:
                    generate_data(
                        recipe_file,
                        dburl=db_url,
                        **gen_kwargs
                    )
                    
                    # Commit: Move temp file to main continuation file
                    if db_append and os.path.exists(temp_continuation_file):
                        shutil.move(temp_continuation_file, continuation_file)
                        print(f"   Updated continuation file '{continuation_file}'")
                        
                    print(f"Success {db_type} batch {i+1}")
                except Exception as e:
                    logging.error(f"❌ Error in {db_type} batch {i+1}: {e}", exc_info=True)
                    # If error, do not overwrite continuation file with potentially partial state
                    break
                
        except Exception as e:
            logging.error(f"❌ Error in {db_type}: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", "-t", nargs="+", help="Targets: POSTGRES ALLOYDB MYSQL MSSQL HANA")
    
    # Default iterations from environment variable, or 1 if not set
    default_iterations = int(os.getenv("DATA_ITERATIONS", "1"))
    parser.add_argument("--iterations", "-i", type=int, default=default_iterations, 
                        help=f"Number of batches (Default: {default_iterations} from DATA_ITERATIONS env var)")
    
    parser.add_argument("--recipe", "-r", default="complete_data.recipe.yml")
    parser.add_argument("--drop-tables", action="store_true", help="Drop tables before starting (Fresh Start)")
    args = parser.parse_args()
    
    run_generation(args.recipe, args.iterations, args.targets, args.drop_tables)