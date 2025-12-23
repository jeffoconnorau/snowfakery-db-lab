
## Getting Started

### Prerequisites
- Python 3.8+
- [Terraform](https://www.terraform.io/downloads.html)
- Docker (optional, for local DB testing)
- **macOS Users**: `brew install unixodbc` (required for MSSQL driver)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd snowfakery-db-lab
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Quick Start
To generate data across all configured databases:
```bash
python setup.py
```
*Note: Ensure your databases are running and accessible via the connection strings defined in `setup.py`.*




### Advanced Usage (CLI Arguments)
You can now target specific databases using command-line arguments:

```bash
# Run only for PostgreSQL and MySQL
python generate_data.py --targets POSTGRES MYSQL

# Run with custom iterations
python generate_data.py --targets HANA --iterations 5

# Show help
python generate_data.py --help
```

Supported targets: `POSTGRES`, `ALLOYDB`, `MYSQL`, `MSSQL`, `HANA`.

Referece environment variables (optional fallback):
```bash
export ENABLED_DBS="POSTGRES,MYSQL"
python generate_data.py
```

## Data Generation
This recipe reproduces the structure of your provided CSV files (Customers, Orders, Products, etc.) and uses formulas to ensure relational integrity.

Since Snowfakery uses SQLAlchemy, you can use the `setup.py` script to output the data to all five of your required database types.

Note: The `requirements.txt` file includes the necessary database drivers (psycopg2, pymysql, pyodbc, hdbcli).

Implementation Details

Scaling: To make the dataset "as large as possible," simply increase the count on the Customer object in the YAML file.


AlloyDB: Since AlloyDB is fully PostgreSQL-compatible, you can use the standard PostgreSQL SQLAlchemy dialect.


Relational Integrity: By nesting Order inside Customer (using the friends or child object pattern), Snowfakery automatically handles the foreign key relationships using its internal ID generation.
+1


Data Types: The recipe uses random_number and date_between to ensure the data is formatted correctly for standard SQL INT, DECIMAL, and DATE columns.

To refine your Snowfakery recipe for SAP HANA and enterprise environments, we need to shift from generic naming conventions to standard SAP table structures (like KNA1 for Customers and VBAK/VBAP for Sales) and use specific SAP-style data formats.
+2

Refined SAP-Style Snowfakery Recipe (sap_enterprise.recipe.yml)
This recipe uses Snowfakery's object templates to simulate a standard SAP schema with related header and item tables.

#SAP

Data Generation Strategy for Enterprise Scale
To generate "as large as possible" datasets across your five target databases (MySQL, MS SQL, SAP HANA, AlloyDB, PostgreSQL), follow these steps:

1. Optimization for Massive Datasets
When generating millions of rows, do not run one massive execution. Instead, use the --plugin and count features to iterate.
+1


Batching: Use Snowfakery's count at the top level to generate data in blocks of 10,000 to avoid memory overflow.
+1


Targeted Scaling: Increase the count in the KNA1 (Customer) object to scale the entire relational tree.
+1

2. SQL Schema Preparation
Before running the script, ensure your target databases have the tables ready with SAP-specific lengths (e.g., MATNR as VARCHAR(18) or KUNNR as VARCHAR(10)). AlloyDB and PostgreSQL can share the same schema.
+1

Execution Script (Refined for Performance)

```
import subprocess

# Define your connections [cite: 10]
db_targets = {
    "PostgreSQL": "postgresql://user:pass@localhost/postgres",
    "AlloyDB": "postgresql://user:pass@alloydb-ip/postgres",
    "MySQL": "mysql+pymysql://user:pass@localhost/sap_db",
    "MSSQL": "mssql+pyodbc://user:pass@localhost/sap_db?driver=ODBC+Driver+17+for+SQL+Server",
    "SAPHANA": "hana://user:pass@hana-host:30015"
}

def run_large_gen(iterations=10):
    for name, url in db_targets.items():
        print(f"--- Starting {name} Generation ---")
        for i in range(iterations):
            # Running multiple iterations to build a massive dataset [cite: 2295, 2296]
            subprocess.run([
                "snowfakery", 
                "sap_enterprise.recipe.yml", 
                "--dburl", url
            ])
            print(f"Batch {i+1}/{iterations} complete for {name}")

run_large_gen(iterations=50) # Adjust iterations for total size

Key Field Adjustments

Unique IDs: Used unique_id to ensure primary keys like VBELN (Sales Order Number) do not collide across batches.
+1


Categorical Data: Used random_choice to mimic SAP's internal codes (e.g., MTART for material types like Finished Goods/FERT).
+1


Formula Logic: You can use formulas to calculate NETWR (Total Value) as a sum of item prices if needed for higher data quality

#sap-complete_recipe

Implementation for Large Datasets
To ensure your five databases (MySQL, MS SQL, SAP HANA, AlloyDB, and PostgreSQL) handle this load efficiently, consider the following technical adjustments:


Fiscal Year Logic: The GJAHR field can be calculated using a formula like ${{now.strftime('%Y')}} to ensure it always reflects the current year.
+1


Company Code Consistency: In enterprise SAP landscapes, BUKRS (Company Code) and VKORG (Sales Org) are usually fixed within a specific business unit; keeping them static (e.g., "1000") helps with testing cross-module reporting.


Relational Hierarchies: By using the friends keyword, Snowfakery maintains the parent-child relationship, ensuring that for every Sales Order (VBAK), there is a corresponding Accounting Header (BKPF) and multiple segments (BSEG).
+1


Scale: Increasing the count for KNA1 to 100,000 or more will automatically scale the related Sales and Financial records, potentially creating millions of rows in the BSEG table.

#SAP DDL Scripts

These are tailored for enterprise standards, ensuring that the fields match the data generated by the Snowfakery recipe provided earlier.

SAP HANA DDL Scripts
You should run these commands in your SAP HANA Cockpit or HDBSQL interface before executing the data generation script.

Data Generation Configuration Notes

Object Templates: Snowfakery uses the keyword object to define instructions for creating rows in these tables.


Unique Identifiers: The unique_id function is utilized for primary keys like VBELN and BELNR to distinguish every record from others.


Field Formulas: You can combine fake data with other logic using the formula syntax ${{ ... }}.
+1


Date Ranges: The date_between function is used for ERDAT fields to pick a random date within a specified range, such as between a fixed date and today.
+1


Randomized Choices: To simulate SAP-specific codes like Posting Keys (BSCHL), the random_choice function randomly selects an option from a predefined list.

Summary of Infrastructure
This setup allows you to test:

High-Volume Ingestion: Generating millions of rows for BSEG to test HANA’s column store performance.

Referential Integrity: Ensuring that accounting documents correctly reference sales documents across disparate systems.

Cross-Cloud Architecture: Using Terraform to manage your AlloyDB and PostgreSQL instances while injecting simulated SAP data into all targets simultaneously.

#SAP validation
Data Validation Script (validate_sap_data.py)
This script performs two critical checks:

Referential Integrity: Ensures every Sales Order (VBAK) has a valid Customer (KNA1) and every Accounting Segment (BSEG) has a valid Header (BKPF).

Cross-Database Consistency: Compares row counts across your five instances.

Validation Principles for SnowfakeryBased on the Snowfakery documentation, the following concepts are critical for ensuring your validation script passes:Relational LogicObject Templates: Snowfakery creates rows in a database or CSV file based on an "object template"1111.+1Unique IDs: Every row generated is assigned a unique id2. Snowfakery uses these IDs to refer between tables, ensuring relational links are maintained3.+1Formula References: You can reference parent values in child objects (e.g., using parent.BELNR) to ensure a child row correctly links to its ancestor4.Data Integrity FeaturesConditional Values: The if and when functions allow you to make field values conditional, which helps simulate complex SAP business logic (like only creating a Financial Document if a Sales Order is in a certain state)5.Unique Constraints: For fields like Employee Numbers or SAP Document Numbers, the unique_id function ensures no duplicates are created during a single execution6.Null Handling: The NULL value can be used to represent missing data, and you can test for its presence using formulas like ${{ EndDate != 'None' }}7777.+1Comparison of Generation Functions used in SAP ScenariosFunctionPurposeExample Usagerandom_choiceSelecting specific SAP codes 8AUART: ${{random_choice("OR", "RE")}} 9random_numberGenerating quantities or prices 10NETWR: ${{random_number(min=10, max=100)}} 11date_betweenSimulating posting or creation dates 12ERDAT: ${{date_between(start_date='-1y', end_date='today')}} 13fake.CompanyGenerating customer names 14NAME1: ${{fake.Company}} 15


