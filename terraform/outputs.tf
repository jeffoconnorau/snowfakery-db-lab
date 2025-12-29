output "alloydb_ip" {
  value = length(google_alloydb_instance.default) > 0 ? google_alloydb_instance.default[0].ip_address : null
}

output "postgres_ip" {
  value = length(google_sql_database_instance.postgres) > 0 ? google_sql_database_instance.postgres[0].ip_address.0.ip_address : null
}

output "mysql_ip" {
  value = length(google_sql_database_instance.mysql) > 0 ? google_sql_database_instance.mysql[0].ip_address.0.ip_address : null
}

output "mssql_ip" {
  value = length(google_sql_database_instance.mssql) > 0 ? google_sql_database_instance.mssql[0].ip_address.0.ip_address : null
}

output "hana_vm_ip" {
  value = length(google_compute_instance.hana_vm) > 0 ? google_compute_instance.hana_vm[0].network_interface.0.network_ip : null
}
