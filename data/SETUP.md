# Infra Setup — Lab Provisioning (author / lab-admin)

Pre-session setup for XP267. Students do not perform these steps. By the time the session starts, the SAP data products are pre-loaded into Dremio and (for the OTIF secondary track) all raw non-SAP data is staged in a single shared S3 bucket. Students only *build* Dremio objects (ex1) and the Joule agent (ex3).

> Guiding principle: stage once, transform progressively. Load/upload all raw data up front (inert, zero live-demo risk); let students run the `CREATE VIEW` transformations live during the session.

## What's SAP vs. non-SAP

| Side | What | How it reaches Dremio |
|---|---|---|
| **SAP — primary (Sales/CRM)** | `customer`, `salesorderitem` | Governed **BDC data products**, exported and **pre-loaded into Dremio** as `"teched_labs_sandbox"."sap_dp".*`. Narrate the BDC origin; the SQL queries Dremio — **no live BDC connection** in the lab. |
| **SAP — secondary (OTIF)** | `productionorder`, `productionorderoperation`, `workcenter` | Same pattern: BDC data products, available in Dremio under `"teched_labs_sandbox"."sap_dp".*`. Nothing uploaded to S3. |
| **Non-SAP (OTIF track)** | 7 Vertex MES CSVs (see below) | Uploaded **once** to the shared S3 bucket in the `bronze/` layout; read by the Dremio S3 source. Only needed for the OTIF secondary track in ex1. |

> ⚠️ `data/otif-synth-data/sap_work_center.csv` is the SAP side (the workcenter master) and must not be uploaded to S3. The upload script already excludes it.

## The 7 non-SAP files (uploaded to S3)

From `data/otif-synth-data/`:

- `work_order.csv`
- `equipment.csv`
- `downtime_event.csv`
- `quality_event.csv`
- `production_count.csv`
- `oee_snapshot.csv`
- `ground_truth_xref.csv` — the MES `equipment_id` ↔ SAP `WorkCenterInternalID` bridge used in the ex1 OTIF secondary track.

## Required S3 layout

Dremio promotes a folder (not a loose file) as a dataset, and the ex1 OTIF-track SQL reads `s3lake."bronze/work_order"` etc. So each feed gets its own folder:

```
s3://<shared-bucket>/bronze/
├── work_order/work_order.csv
├── equipment/equipment.csv
├── downtime_event/downtime_event.csv
├── quality_event/quality_event.csv
├── production_count/production_count.csv
├── oee_snapshot/oee_snapshot.csv
└── ground_truth_xref/ground_truth_xref.csv
```

## Step 1 — Create / choose the shared bucket

One bucket for the whole room (students have read access via the Dremio S3 source; they do not need direct S3 credentials). Example:

```bash
aws s3 mb s3://teched2026-xp267-lab --region eu-central-1
```

## Step 2 — Stage the non-SAP CSVs

Run the provided script once from the repo root:

```bash
# dry-run first to confirm the plan
DRY_RUN=1 ./data/upload_bronze.sh s3://teched2026-xp267-lab

# then the real upload
./data/upload_bronze.sh s3://teched2026-xp267-lab
```

Optional second arg nests everything under a prefix: `./data/upload_bronze.sh s3://bucket my-lab` → `my-lab/bronze/...`.

## Step 3 — Configure the Dremio S3 source

1. In Dremio, add (or confirm) an Amazon S3 source pointing at the shared bucket. In the exercises this source is referred to as `s3lake` — name it `s3lake` (or update the ex1 OTIF-track SQL to match your source name).
2. Grant the student role read access to that source.
3. Browse to `bronze/` and format each `bronze/<table>/` folder as a CSV dataset with "Extract field names" (header on first row) enabled. (Students can also do the format-on-first-query step live; pre-formatting removes a click during the demo.)

> Note on types: the MES timestamps are epoch-millis (e.g. `1769125936076`) and will promote as `BIGINT`. That is fine for the OTIF track — the date math in the medallion lives on the SAP side.

## Step 4 — Confirm the SAP data products are in Dremio

All SAP tables are exported BDC data products pre-loaded into Dremio — there is no live BDC connection in the lab.

- **Primary (Sales/CRM)**: `customer`, `salesorderitem` — confirm they resolve as `"teched_labs_sandbox"."sap_dp".customer` / `.salesorderitem` and the ex1 `v_customer_otif` rollup returns rows.
- **Secondary (OTIF)**: `productionorder`, `productionorderoperation`, `workcenter` — confirm they resolve under `"teched_labs_sandbox"."sap_dp".*` for the ex1 manufacturing track. The reference medallion that defines the SAP-side OTIF logic is documented in [`data/otif-medallion`](./otif-medallion/README.md).

## Pre-flight checklist (do before the room arrives)

- [ ] Primary Sales/CRM products resolve in Dremio: `"teched_labs_sandbox"."sap_dp".customer` / `.salesorderitem` preview with rows.
- [ ] Secondary OTIF products resolve: `"teched_labs_sandbox"."sap_dp".productionorder` / `.productionorderoperation` / `.workcenter`.
- [ ] (OTIF track) Shared bucket exists; `./data/upload_bronze.sh` run; all 7 folders present under `bronze/`; Dremio `s3lake` source reads the bucket and each `bronze/<table>/` previews with correct headers.
- [ ] A Dremio space exists for the CRM 360 views (`v_customer_otif`, `v_crm_account_resolved`, `v_crm_account_360`) + their Raw Reflections, and for the `silver.*` / `gold.*` OTIF appendix objects students will create.
- [ ] Joule Agent Builder is available to the student role, with a Dremio connection it can query (used in ex3).
- [ ] (Optional) `data/mes_synthetic_data` staged wherever the ex3 supplementary agent tool will read it.

## Teardown

- Drop the student-created CRM 360 views (`v_customer_otif`, `v_crm_account_resolved`, `v_crm_account_360`) and their Raw Reflections, the `silver.*` / `gold.*` OTIF appendix views, and any `bronze.*` Iceberg tables in Dremio.
- `aws s3 rm s3://teched2026-xp267-lab/bronze --recursive` to clear staged data.
