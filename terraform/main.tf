# main.tf

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "api_compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "api_servicenetworking" {
  service            = "servicenetworking.googleapis.com"
  disable_on_destroy = false
  depends_on         = [google_project_service.api_compute]
}

resource "google_project_service" "api_sqladmin" {
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "api_alloydb" {
  service            = "alloydb.googleapis.com"
  disable_on_destroy = false
}

locals {
  # Determine if we are creating a new network or using an existing one
  create_network = var.create_vpc

  # Resolve the Network ID (Self Link)
  # If creating: google_compute_network.vpc_network[0].id
  # If existing: data.google_compute_network.existing_vpc[0].id
  network_id = local.create_network ? google_compute_network.vpc_network[0].id : data.google_compute_network.existing_vpc[0].id
  

  # Resolve Network Name for compute instances
  network_name = var.network_name
  
  # Determine Project ID for Networking Resources (Host Project if Shared VPC, else Service Project)
  # Determine Project ID for Networking Resources (Host Project if Shared VPC, else Service Project)
  network_project_id = var.network_project_id != "" ? var.network_project_id : var.project_id

  # Password Logic: Use provided var.db_password or generated one
  db_password = var.db_password != null ? var.db_password : random_password.generated_password.result
}

# Generate a random password if one isn't provided
resource "random_password" "generated_password" {
  length  = 16
  special = false # simpler for DB compatibility
}

# 1. Network Setup
# ----------------
# 1a. Create new VPC if none provided
resource "google_compute_network" "vpc_network" {
  count = local.create_network ? 1 : 0
  name  = var.network_name
  auto_create_subnetworks = true
}

# 1b. Reference existing VPC if provided
data "google_compute_network" "existing_vpc" {
  count   = local.create_network ? 0 : 1
  name    = var.network_name
  project = local.network_project_id
}

# 1c. Private Service Access (Private IP for Cloud SQL / AlloyDB)
# Note: This must be created in the PROJECT where the Network exists.
# If using Shared VPC, this requires permissions in the Host Project.
resource "google_compute_global_address" "private_ip_address" {
  count         = var.create_psa ? 1 : 0
  name          = "sap-lab-private-ip"
  project       = local.network_project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = local.network_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  count                   = var.create_psa ? 1 : 0
  network                 = local.network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address[0].name]
}

# 2. AlloyDB Infrastructure
# -------------------------
resource "google_alloydb_cluster" "default" {
  count            = var.create_alloydb ? 1 : 0
  provider         = google-beta
  cluster_id       = "alloydb-lab-cluster"
  location         = var.region
  database_version    = "POSTGRES_17"
  deletion_protection = false
  
  network_config {
    network = local.network_id
  }

  initial_user {
    password = local.db_password
  }

  automated_backup_policy {
    enabled = false
  }
  
  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.api_alloydb,
    google_project_service.api_servicenetworking
  ]
}

resource "google_alloydb_instance" "default" {
  count         = var.create_alloydb ? 1 : 0
  provider      = google-beta
  cluster       = google_alloydb_cluster.default[0].name
  instance_id   = "alloydb-lab-instance"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = 2
  }

  query_insights_config {
    record_application_tags = true
    record_client_address   = true
    query_plans_per_minute  = 5
  }
}

resource "google_alloydb_user" "dbadmin" {
  count          = var.create_alloydb ? 1 : 0
  cluster        = google_alloydb_cluster.default[0].name
  user_id        = "dbadmin"
  user_type      = "ALLOYDB_BUILT_IN"
  password       = local.db_password
  database_roles = ["alloydbsuperuser"]
  provider       = google-beta
  depends_on     = [google_alloydb_instance.default]
}



# 3. Cloud SQL PostgreSQL Infrastructure
# --------------------------------------
resource "google_sql_database_instance" "postgres" {
  count            = var.create_postgres ? 1 : 0
  name             = "postgres-lab-instance"
  database_version = "POSTGRES_17"
  region           = var.region

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.api_sqladmin,
    google_project_service.api_servicenetworking
  ]

  deletion_protection = false

  settings {
    tier              = "db-f1-micro" # Smallest available (Shared Core)
    availability_type = "ZONAL"       # No HA
    edition           = "ENTERPRISE"
    ip_configuration {
      ipv4_enabled    = false
      private_network = local.network_id
    }
    backup_configuration {
      enabled = false
    }
    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = true
    }
  }
  
  root_password = local.db_password

  timeouts {
    create = "90m"
  }
}

resource "google_sql_database" "postgres_db" {
  count    = var.create_postgres ? 1 : 0
  name     = "postgres_db"
  instance = google_sql_database_instance.postgres[0].name
}

resource "google_sql_user" "postgres_dbadmin" {
  count    = var.create_postgres ? 1 : 0
  name     = "dbadmin"
  instance = google_sql_database_instance.postgres[0].name
  password = local.db_password
}

# 4. Cloud SQL MySQL Infrastructure
# ---------------------------------
resource "google_sql_database_instance" "mysql" {
  count            = var.create_mysql ? 1 : 0
  name             = "mysql-lab-instance"
  database_version = "MYSQL_8_4"
  region           = var.region

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.api_sqladmin,
    google_project_service.api_servicenetworking
  ]

  deletion_protection = false

  settings {
    tier              = "db-custom-1-3840" # Smallest viable for MySQL 8 (1 vCPU)
    availability_type = "ZONAL"            # No HA
    edition           = "ENTERPRISE"
    ip_configuration {
      ipv4_enabled    = false
      private_network = local.network_id
    }
    backup_configuration {
      enabled = false
    }
    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = true
    }
  }
  
  root_password = local.db_password

  timeouts {
    create = "90m"
  }
}

resource "google_sql_database" "mysql_db" {
  count    = var.create_mysql ? 1 : 0
  name     = "mysql_db"
  instance = google_sql_database_instance.mysql[0].name
}

resource "google_sql_user" "mysql_dbadmin" {
  count    = var.create_mysql ? 1 : 0
  name     = "dbadmin"
  instance = google_sql_database_instance.mysql[0].name
  password = local.db_password
  host     = "%" # Allow from any host (Cloud SQL Proxy / Private IP safe-ish in VPC)
}

# 5. Cloud SQL SQL Server Infrastructure
# --------------------------------------
resource "google_sql_database_instance" "mssql" {
  count            = var.create_mssql ? 1 : 0
  name             = "mssql-lab-instance"
  database_version = "SQLSERVER_2022_EXPRESS"
  region           = var.region

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.api_sqladmin,
    google_project_service.api_servicenetworking
  ]

  deletion_protection = false

  settings {
    tier              = "db-custom-2-3840" # Express usage often lower, trying 3840MB RAM. If fails, revert to 7680.
    availability_type = "ZONAL"            # No HA
    ip_configuration {
      ipv4_enabled    = false
      private_network = local.network_id
    }
    backup_configuration {
      enabled = false
    }
  }
  
  root_password = local.db_password

  timeouts {
    create = "90m"
  }
}

resource "google_sql_database" "mssql_db" {
  count    = var.create_mssql ? 1 : 0
  name     = "mssql_db"
  instance = google_sql_database_instance.mssql[0].name
}

resource "google_sql_user" "mssql_dbadmin" {
  count    = var.create_mssql ? 1 : 0
  name     = "dbadmin"
  instance = google_sql_database_instance.mssql[0].name
  password = local.db_password
}

# 6. SAP HANA VM (Placeholder)
# ----------------------------
resource "google_compute_disk" "hana_backup" {
  count = var.create_hana_vm ? 1 : 0
  name  = "hana-backup"
  type  = "pd-balanced"
  size  = 25
  zone  = var.zone
}

resource "google_compute_disk" "hana_data" {
  count = var.create_hana_vm ? 1 : 0
  name  = "hana-data"
  type  = "pd-standard"
  size  = 50
  zone  = var.zone
}

resource "google_compute_disk" "hana_log" {
  count = var.create_hana_vm ? 1 : 0
  name  = "hana-log"
  type  = "pd-standard"
  size  = 50
  zone  = var.zone
}

resource "google_compute_disk" "hana_shared" {
  count = var.create_hana_vm ? 1 : 0
  name  = "hana-shared"
  type  = "pd-balanced"
  size  = 80
  zone  = var.zone
}

resource "google_compute_instance" "hana_vm" {
  count        = var.create_hana_vm ? 1 : 0
  name         = "hana-express-vm"
  # SAP HANA requires decent resources, e2-standard-8 is a good baseline
  machine_type = "e2-standard-8" 
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 50
    }
  }

  attached_disk {
    source      = google_compute_disk.hana_backup[0].id
    device_name = "hana-backup"
  }

  attached_disk {
    source      = google_compute_disk.hana_data[0].id
    device_name = "hana-data"
  }

  attached_disk {
    source      = google_compute_disk.hana_log[0].id
    device_name = "hana-log"
  }

  attached_disk {
    source      = google_compute_disk.hana_shared[0].id
    device_name = "hana-shared"
  }

  network_interface {
    network = local.network_name
    # Consider subnetwork if using Shared VPC in future
  }

  metadata_startup_script = "echo 'Please install SAP HANA Express here'"
  
  service_account {
    scopes = ["cloud-platform"]
  }
}
