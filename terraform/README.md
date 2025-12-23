Terraform Infrastructure Code (main.tf)
This configuration sets up a Private Service Access connection, an AlloyDB Cluster/Instance, and a Cloud SQL PostgreSQL instance within a single VPC.

Updated Data Generation Strategy
As you scale your dataset to be "as large as possible," keep in mind these Snowfakery and database principles:


Snowfakery Versioning: Ensure your recipe starts with snowfakery_version: 3 as required by the latest language standards.
+1


Unique Identifiers: The unique_id function is critical for SAP tables like BELNR and VBELN to ensure records remain distinct across multiple generation batches.


Data Types: Snowfakery handles data types via SQLAlchemy, but for SAP HANA, ensure you are casting values correctly if using non-integer ranges for numeric fields.
+1


Relational Integrity: Snowfakery refers between tables with IDs automatically. By nesting objects like BSEG within BKPF, you ensure that child records always point back to the correct parent document.

Table Summary for GenerationSAP TablePurposeGeneration KeySource DetailKNA1Customer Masterfake.CompanyStandard SAP Customer data6.VBAKSales Headerdate_betweenRelates orders to a specific timeframe7.BKPFAccounting Headerunique_idPrimary key for financial documents8.BSEGAccounting Segmentparent.BELNRLinks financial lines to the header9.


## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| `project_id` | Google Cloud Project ID | `string` | n/a |
| `region` | Region for resources | `string` | `us-central1` |
| `zone` | Zone for VMs | `string` | `us-central1-a` |
| `db_password` | Password for DB users | `string` | n/a |
| `network_name` | Existing VPC Name (optional) | `string` | `""` (Creating new) |
| `network_project_id` | Project ID for Shared VPC | `string` | `var.project_id` |
| `create_hana_vm` | Create SAP HANA VM | `bool` | `false` |

## Usage
```bash
# Standard usage (creating new VPC)
terraform apply -var="project_id=my-project" -var="db_password=secret"

# Shared VPC usage
terraform apply \
  -var="project_id=my-project" \
  -var="network_name=my-shared-vpc" \
  -var="network_project_id=host-project-id" \
  -var="db_password=secret"
```

## Troubleshooting

### Error: `oauth2: "invalid_grant" "reauth related error (invalid_rapt)"`
This indicates your Google Cloud credentials have expired or require re-authentication due to organization policies.

**Fix:**
Run the following command to refresh your Application Default Credentials:
```bash
gcloud auth application-default login --reauth
```
