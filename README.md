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
export POSTGRES_PASSWORD="secure_password"
# See generate_data.py for all available environment variables (MySQL, MSSQL, HANA, etc.)

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
- `complete_data.recipe.yml`: Main Snowfakery recipe with SAP schema.
- `generate_data.py`: Main execution script.
- `validate_data.py`: Data integrity validation script.
