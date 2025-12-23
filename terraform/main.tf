# main.tf

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

locals {
  # Determine if we are creating a new network or using an existing one
  create_network = var.network_name == ""

  # Resolve the Network ID (Self Link)
  # If creating: google_compute_network.vpc_network[0].id
  # If existing: data.google_compute_network.existing_vpc[0].id
  network_id = local.create_network ? google_compute_network.vpc_network[0].id : data.google_compute_network.existing_vpc[0].id
  
  # Resolve Network Name for compute instances
  network_name = local.create_network ? google_compute_network.vpc_network[0].name : var.network_name
}

# 1. Network Setup
# ----------------
# 1a. Create new VPC if none provided
resource "google_compute_network" "vpc_network" {
  count = local.create_network ? 1 : 0
  name  = "sap-data-gen-vpc"
  auto_create_subnetworks = true
}

# 1b. Reference existing VPC if provided
data "google_compute_network" "existing_vpc" {
  count   = local.create_network ? 0 : 1
  name    = var.network_name
  project = var.network_project_id != "" ? var.network_project_id : var.project_id
}

# 1c. Private Service Access (Private IP for Cloud SQL / AlloyDB)
resource "google_compute_global_address" "private_ip_address" {
  name          = "sap-lab-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = local.network_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = local.network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# 2. AlloyDB Infrastructure
# -------------------------
resource "google_alloydb_cluster" "default" {
  provider   = google-beta
  cluster_id = "alloydb-sap-cluster"
  location   = var.region
  
  network_config {
    network = local.network_id
  }

  initial_user {
    password = var.db_password
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_alloydb_instance" "default" {
  provider      = google-beta
  cluster       = google_alloydb_cluster.default.name
  instance_id   = "alloydb-sap-instance"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = 2
  }
}

# 3. Cloud SQL PostgreSQL Infrastructure
# --------------------------------------
resource "google_sql_database_instance" "postgres" {
  name             = "postgres-sap-instance"
  database_version = "POSTGRES_15"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-custom-2-7680"
    ip_configuration {
      ipv4_enabled    = false
      private_network = local.network_id
    }
  }
  
  root_password = var.db_password
}

# 4. Cloud SQL MySQL Infrastructure
# ---------------------------------
resource "google_sql_database_instance" "mysql" {
  name             = "mysql-sap-instance"
  database_version = "MYSQL_8_0"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-custom-2-7680"
    ip_configuration {
      ipv4_enabled    = false
      private_network = local.network_id
    }
  }
  
  root_password = var.db_password
}

# 5. Cloud SQL SQL Server Infrastructure
# --------------------------------------
resource "google_sql_database_instance" "mssql" {
  name             = "mssql-sap-instance"
  database_version = "SQLSERVER_2019_STANDARD"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-custom-2-7680"
    ip_configuration {
      ipv4_enabled    = false
      private_network = local.network_id
    }
  }
  
  root_password = var.db_password
}

# 6. SAP HANA VM (Placeholder)
# ----------------------------
resource "google_compute_instance" "hana_vm" {
  name         = "hana-express-vm"
  machine_type = "e2-highmem-4"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 50
    }
  }

  network_interface {
    network = local.network_name
    # Use subnetwork if it's a shared VPC! 
    # For Shared VPC, specifying just the network often works if auto-subnets, 
    # but strictly we should probably ask for a subne.
    # For now, simplistic approach:
  }

  metadata_startup_script = "echo 'Please install SAP HANA Express here'"
  
  service_account {
    scopes = ["cloud-platform"]
  }
}