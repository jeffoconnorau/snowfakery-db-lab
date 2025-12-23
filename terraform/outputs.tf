output "alloydb_ip" {
  value = google_alloydb_instance.default.ip_address
}

output "postgres_ip" {
  value = google_sql_database_instance.postgres.ip_address.0.ip_address
}

output "mysql_ip" {
  value = google_sql_database_instance.mysql.ip_address.0.ip_address
}

output "mssql_ip" {
  value = google_sql_database_instance.mssql.ip_address.0.ip_address
}

output "hana_vm_ip" {
  value = length(google_compute_instance.hana_vm) > 0 ? google_compute_instance.hana_vm[0].network_interface.0.network_ip : null
}
