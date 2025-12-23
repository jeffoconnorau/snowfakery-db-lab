# main.tf

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Network Setup
resource "google_compute_network" "vpc_network" {
  name = "sap-data-gen-vpc"
}

resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# 2. AlloyDB Infrastructure
resource "google_alloydb_cluster" "default" {
  cluster_id = "alloydb-sap-cluster"
  location   = var.region
  network    = google_compute_network.vpc_network.id

  initial_user {
    password = var.db_password
  }
}

resource "google_alloydb_instance" "default" {
  cluster       = google_alloydb_cluster.default.name
  instance_id   = "alloydb-sap-instance"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = 2
  }
}

# 3. Cloud SQL PostgreSQL Infrastructure
resource "google_sql_database_instance" "postgres" {
  name             = "postgres-sap-instance"
  database_version = "POSTGRES_15"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-custom-2-7680" # Tweaked for better performance
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc_network.id
    }
  }
  
  # Set root password
  root_password = var.db_password
}

# 4. Cloud SQL MySQL Infrastructure
resource "google_sql_database_instance" "mysql" {
  name             = "mysql-sap-instance"
  database_version = "MYSQL_8_0"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-custom-2-7680"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc_network.id
    }
  }
  
  root_password = var.db_password
}

# 5. Cloud SQL SQL Server Infrastructure
resource "google_sql_database_instance" "mssql" {
  name             = "mssql-sap-instance"
  database_version = "SQLSERVER_2019_STANDARD"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-custom-2-7680"
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc_network.id
    }
  }
  
  root_password = var.db_password
}

# 6. SAP HANA VM (Placeholder for HANA Express)
# Note: User must manually install HANA or use a specific image if available
resource "google_compute_instance" "hana_vm" {
  name         = "hana-express-vm"
  machine_type = "e2-highmem-4" # HANA loves memory
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11" # Base OS, manual HANA install required OR use SUSE/RHEL if available
      size  = 50
    }
  }

  network_interface {
    network = google_compute_network.vpc_network.name
    
    # Empty access_config to allow external access (if needed, else remove for private only)
    # For now, keeping it private-ish but accessible via VPC
  }

  metadata_startup_script = "echo 'Please install SAP HANA Express here'"
  
  service_account {
    scopes = ["cloud-platform"]
  }
}