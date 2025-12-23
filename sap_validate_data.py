import pandas as pd
from sqlalchemy import create_engine, text

# Define your target database connections
db_targets = {
    "PostgreSQL": "postgresql://user:pass@localhost/postgres",
    "AlloyDB": "postgresql://user:pass@alloydb-ip/postgres",
    "MySQL": "mysql+pymysql://user:pass@localhost/sap_db",
    "MSSQL": "mssql+pyodbc://user:pass@localhost/sap_db?driver=ODBC+Driver+17+for+SQL+Server",
    "SAPHANA": "hana://user:pass@hana-host:30015"
}

def validate_integrity(engine, db_name):
    print(f"\n--- Integrity Report: {db_name} ---")
    
    queries = {
        "Orphaned Sales Orders": "SELECT COUNT(*) FROM VBAK WHERE KUNNR NOT IN (SELECT KUNNR FROM KNA1)",
        "Orphaned Accounting Segments": "SELECT COUNT(*) FROM BSEG WHERE BELNR NOT IN (SELECT BELNR FROM BKPF)",
        "Empty Documents": "SELECT COUNT(*) FROM BKPF WHERE BELNR NOT IN (SELECT BELNR FROM BSEG)"
    }
    
    with engine.connect() as conn:
        for check_name, query in queries.items():
            result = conn.execute(text(query)).scalar()
            status = "PASS" if result == 0 else "FAIL"
            print(f"[{status}] {check_name}: {result} inconsistencies found.")

def get_row_counts(engine):
    tables = ["KNA1", "VBAK", "BKPF", "BSEG"]
    counts = {}
    with engine.connect() as conn:
        for table in tables:
            counts[table] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    return counts

if __name__ == "__main__":
    summary_data = []
    for name, url in db_targets.items():
        try:
            engine = create_engine(url)
            validate_integrity(engine, name)
            counts = get_row_counts(engine)
            counts['Database'] = name
            summary_data.append(counts)
        except Exception as e:
            print(f"Could not connect to {name}: {e}")

    # Display Cross-Database Comparison
    df = pd.DataFrame(summary_data)
    print("\n--- Cross-Database Row Count Comparison ---")
    print(df.to_string(index=False))