variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud region"
  type        = string
  default     = "asia-southeast1"
}

variable "zone" {
  description = "The Google Cloud zone"
  type        = string
  default     = "asia-southeast1-a"
}

variable "db_password" {
  description = "Password for the databases"
  type        = string
  sensitive   = true
}

variable "create_vpc" {
  description = "Whether to create a new VPC. If false, attempts to use existing VPC named var.network_name."
  type        = bool
  default     = false
}

variable "network_name" {
  description = "Name of the VPC to create or use."
  type        = string
  default     = "sap-data-gen-vpc"
}

variable "network_project_id" {
  description = "Project ID where the existing/shared VPC resides. Defaults to var.project_id if using existing network."
  type        = string
  default     = ""
}

variable "create_hana_vm" {
  description = "Whether to create the SAP HANA VM and associated disks"
  type        = bool
  default     = false
}

variable "create_psa" {
  description = "Whether to create the Private Service Access (IP Range & Peering). Set to false if already configured in Host Project."
  type        = bool
  default     = true
}
