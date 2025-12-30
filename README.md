# Snowfakery DB Lab

This project generates synthetic enterprise data (SAP schema flavor) and populates multiple database targets: PostgreSQL, AlloyDB, MySQL, MSSQL, and SAP HANA. It leverages **Snowfakery** for data generation and **Terraform** for infrastructure provisioning.

## Prerequisites
- **Python 3.8+**
- **Terraform** (for infrastructure)
- **Docker** (optional, for local DB testing)
- **ODBC Driver** (for MSSQL on macOS): `brew install unixodbc`

## 1. Infrastructure Setup (Terraform)
If you need to provision the database infrastructure on Google Cloud (AlloyDB, Cloud SQL), navigate to the `terraform/` directory.

```bash
cd terraform
# Initialize Terraform
terraform init

# Plan and Apply
terraform plan
terraform apply
```
*Note: This will output connection details (IPs, connection strings) required for the data generation step.*

### Selective/Cost-optimized Provisioning
You can choose to create only specific databases to save costs or for focused testing. New variables (`create_postgres`, `create_mysql`, `create_mssql`, `create_alloydb`) default to `true`.

**Example: Create only Postgres and AlloyDB:**
```bash
terraform apply \
  -var="create_mysql=false" \
  -var="create_mssql=false" \
  -var="create_hana_vm=false"
```bash
  -var="create_hana_vm=false"
```
*Note: If you destroy a database, remember to exclude it from `generate_data.py --targets`.*

### Database Observability
**Query Insights** are enabled by default for:
*   **PostgreSQL** (Cloud SQL)
*   **MySQL** (Cloud SQL)
*   **AlloyDB**

This allows you to see query performance and tags alongside the generated traffic. MSSQL does not currently support this configuration via the same Terraform block.

## 2. Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd snowfakery-db-lab
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare Database Schemas:**
   - For **SAP HANA**, run the DDL scripts located in `sap_hana/ddl.sql` using your HANA Cockpit or HDBSQL.
   - For other databases, Snowfakery can typically auto-create tables, but ensuring schemas match your requirements is recommended.

## 3. Data Generation

The primary script is `generate_data.py`. It generates data based on the recipe (default: `complete_data.recipe.yml`) and inserts it into the targeted databases.

### Basic Usage
```bash
# Generate data for all configured targets (default)
python generate_data.py
```

### Advanced Usage (CLI)
Target specific databases or change iteration counts:
```bash
# Only target PostgreSQL and MySQL
python generate_data.py --targets POSTGRES MYSQL

# Run 5 iterations for HANA
python generate_data.py --targets HANA --iterations 5

# Use a specific recipe
python generate_data.py --recipe erp_data.recipe.yml
```

### Configuration (Environment Variables)
You can configure database connection strings via environment variables. This is useful for CI/CD or connecting to the Terraform-provisioned infrastructure.

```bash
export POSTGRES_HOST="10.x.x.x"
# DB_PASSWORD is REQUIRED (no default for security)
export DB_PASSWORD="your_secure_password"
# See generate_data.py for all available environment variables

# For Private IP Connectivity (e.g., from a VM or VPN)
export DB_IP_TYPE="PRIVATE" # Defaults to PUBLIC

# Best Practice: Use a non-root user
# It is recommended to create specific service accounts for applications.
export DB_USER="my_app_user"

# Optional: Override Database Name (Defaults: mysql_db, postgres_db, mssql_db, postgres for AlloyDB)
# export DB_NAME="custom_db_name"

# Scaling Data: Set number of iteration batches (Default: 1)
# NOTE: This is additive! Running with 10 will append 10 *more* batches.
# export DATA_ITERATIONS=10

# Append Mode: Add to existing data instead of crashing (Uses snowfakery_continuation.yml)
# export DB_APPEND=true

python generate_data.py
```

## 4. Validation

After generation, you can validate the data integrity (e.g., Foreign Key relationships between orders and customers) using `validate_data.py`.

```bash
python validate_data.py
```
This script performs cross-database row count comparisons and referential integrity checks (e.g., ensuring every `VBAK` order has a valid `KNA1` customer).

## Project Structure
- `data/`: Contains reference CSV files.
- `sap_hana/`: Contains SAP HANA specific DDL scripts.
- `terraform/`: Infrastructure as Code for Google Cloud databases.
- `complete_data.recipe.yml`: Main Snowfakery recipe with SAP schema. Includes `PAYLOAD` fields (~2KB/row) to simulate heavy data.
- `generate_data.py`: Main execution script.
- `validate_data.py`: Data integrity validation script.
