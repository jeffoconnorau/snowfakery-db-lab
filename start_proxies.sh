#!/bin/bash
set -e

# Configuration - Connection Names
# Use 'terraform output' to verify these if they change
POSTGRES_INSTANCE="argo-svc-dbs:asia-southeast1:postgres-lab-instance"
MYSQL_INSTANCE="argo-svc-dbs:asia-southeast1:mysql-lab-instance"
MSSQL_INSTANCE="argo-svc-dbs:asia-southeast1:mssql-lab-instance"
ALLOYDB_CLUSTER="projects/argo-svc-dbs/locations/asia-southeast1/clusters/alloydb-lab-cluster"
ALLOYDB_INSTANCE="alloydb-lab-instance"

# Ports (Default mapping to avoid variable changes in generate_data.py where possible)
PORT_PG=5432
PORT_MYSQL=3306
PORT_MSSQL=1433
PORT_ALLOY=5433 # AlloyDB also uses 5432, so we map it to 5433 to avoid conflict with Postgres

# Determine AlloyDB Proxy Command
if command -v alloydb-auth-proxy &> /dev/null; then
    ALLOY_CMD="alloydb-auth-proxy"
elif [ -f "./alloydb-auth-proxy" ]; then
    ALLOY_CMD="./alloydb-auth-proxy"
else
    echo "❌ Error: alloydb-auth-proxy is not installed and local binary not found."
    echo "   Run: brew install google-cloud-tools/tap/alloydb-auth-proxy"
    echo "   OR download it to this directory."
    exit 1
fi

# Determine Cloud SQL Proxy Command
if command -v cloud-sql-proxy &> /dev/null; then
    SQL_CMD="cloud-sql-proxy"
else
    echo "❌ Error: cloud-sql-proxy is not installed."
    echo "   Run: brew install cloud-sql-proxy"
    exit 1
fi

echo "🚀 Starting Proxies..."

# Start Cloud SQL Proxy (Postgres, MySQL, MSSQL)
echo "   -> Starting Cloud SQL Proxy for Postgres ($PORT_PG), MySQL ($PORT_MYSQL), MSSQL ($PORT_MSSQL)..."
$SQL_CMD \
  "$POSTGRES_INSTANCE" --port=$PORT_PG \
  "$MYSQL_INSTANCE"    --port=$PORT_MYSQL \
  "$MSSQL_INSTANCE"    --port=$PORT_MSSQL &
PID_SQL=$!

# Start AlloyDB Proxy
echo "   -> Starting AlloyDB Proxy on port $PORT_ALLOY..."
$ALLOY_CMD \
  "$ALLOYDB_CLUSTER" \
  --port=$PORT_ALLOY &
PID_ALLOY=$!

echo "✅ Proxies running in background."
echo "   PID SQL:   $PID_SQL"
echo "   PID Alloy: $PID_ALLOY"
echo ""
echo "📝 ENVIRONMENT VARIABLES FOR generate_data.py:"
echo "   export ALLOYDB_PORT=$PORT_ALLOY"
echo ""
echo "⚠️  Press Ctrl+C to stop all proxies."

# Trap to kill background processes on exit
trap "kill $PID_SQL $PID_ALLOY" SIGINT SIGTERM

# Wait for processes
wait
