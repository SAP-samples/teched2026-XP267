# Data — source material (author / lab-admin only)

**Students never touch this folder.** By session time, everything here is already provisioned in Dremio; students only query it there (`"teched_labs_sandbox"."sap_dp".*` and `"teched_labs_sandbox"."non_sap".*`) and build their own views. This folder is the raw synthetic source we use to prepare the lab.

For provisioning steps (S3 staging, Dremio sources, pre-flight checklist, teardown) see [`SETUP.md`](./SETUP.md); the one-time upload is [`upload_bronze.sh`](./upload_bronze.sh).

## Datasets

- **`data-products`** — the Sales / CRM SAP data products exported from BDC and pre-loaded into Dremio: `customer`, `salesorderitem`. Exercise 1 rolls these up into the per-customer OTIF truth (`v_customer_otif`) that feeds the CRM 360 golden record.
- **`crm-synth-data`** — a synthetic non-SAP CRM export (`crm_account`, `crm_case`, `crm_opportunity`, `crm_contact`, plus a ground-truth resolution crosswalk). Every CRM signal is derived from each account's real published OTIF, so worse delivery → more Delivery-Delay / Short-Shipment cases → higher churn risk. Exercise 1 resolves it to SAP customers (`"teched_labs_sandbox"."non_sap".*`) and builds the `v_crm_account_360` golden account product ([details](./crm-synth-data/README.md)).
- **`otif-synth-data`** — the Vertex MES ↔ SAP S/4 scenario. The SAP S/4 side (`productionorder`, `productionorderoperation`, `workcenter`) stands in for the governed BDC data products; the Vertex MES CSVs (`work_order`, `equipment`, `downtime_event`, `quality_event`, `production_count`, `oee_snapshot`) stand in for the non-SAP data landed as Iceberg on S3 (staged via `upload_bronze.sh`).
- **`otif-medallion`** — a reference implementation of the same silver → gold OTIF medallion on Azure Databricks ([details](./otif-medallion/README.md)). The Exercise 1 OTIF appendix reuses its derived-column logic (`otif_risk_score`, `is_at_risk`, `risk_tier`, `primary_root_cause`, `anomalous_work_centers`), rebuilt as Dremio SQL views.
- **`mes_synthetic_data`** — a shopfloor capacity/OEE dataset used as supplementary grounding and visualization context for the Joule agent ([details](./mes_synthetic_data/README.md)).
