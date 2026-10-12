# Infra Setup — Lab Provisioning (author / lab-admin)

Pre-session setup for XP267. **Students do not perform these steps.** By the time the session starts, all raw non-SAP data is already staged in a **single shared S3 bucket**, the SAP data products are shared to Dremio, and students only *build* Dremio objects (ex2–ex3) and the Joule agent (ex4).

> Guiding principle: **stage once, transform progressively.** Upload all raw files up front (inert bytes, zero live-demo risk); let students run the `CREATE TABLE` / `CREATE VIEW` transformations live during the session.

## What's SAP vs. non-SAP

| Side | What | How it reaches Dremio |
|---|---|---|
| **SAP** | `productionorder.productionorder`, `productionorder.productionorderoperation`, `workcenter.workcenter` | Governed BDC data products, shared **zero-copy** to the Dremio BDC source (ex1). Nothing is uploaded to S3. |
| **Non-SAP** | 7 Vertex MES CSVs (see below) | Uploaded **once** to the shared S3 bucket in the `bronze/` layout; read by the Dremio S3 source (ex2). |

> ⚠️ `data/otif-synth-data/sap_work_center.csv` is the **SAP side** (the workcenter master) and must **not** be uploaded to S3. The upload script already excludes it.

## The 7 non-SAP files (uploaded to S3)

From `data/otif-synth-data/`:

- `work_order.csv`
- `equipment.csv`
- `downtime_event.csv`
- `quality_event.csv`
- `production_count.csv`
- `oee_snapshot.csv`
- `ground_truth_xref.csv` — the MES `equipment_id` ↔ SAP `WorkCenterInternalID` bridge used in ex3.

## Required S3 layout

Dremio promotes a **folder** (not a loose file) as a dataset, and ex2's SQL reads `s3lake."bronze/work_order"` etc. So each feed gets its own folder:

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
DRY_RUN=1 ./infra/upload_bronze.sh s3://teched2026-xp267-lab

# then the real upload
./infra/upload_bronze.sh s3://teched2026-xp267-lab
```

Optional second arg nests everything under a prefix: `./infra/upload_bronze.sh s3://bucket my-lab` → `my-lab/bronze/...`.

## Step 3 — Configure the Dremio S3 source

1. In Dremio, add (or confirm) an **Amazon S3** source pointing at the shared bucket. In the exercises this source is referred to as **`s3lake`** — name it `s3lake` (or update the ex2/ex3 SQL to match your source name).
2. Grant the student role read access to that source.
3. Browse to `bronze/` and **format each `bronze/<table>/` folder as a CSV dataset** with "Extract field names" (header on first row) enabled. (Students can also do the format-on-first-query step live; pre-formatting removes a click during the demo.)

> Note on types: the MES timestamps are **epoch-millis** (e.g. `1769125936076`) and will promote as `BIGINT`. That is fine for ex2/ex3 — the date math in the medallion lives on the SAP side.

## Step 4 — Confirm the SAP data products are shared

Confirm the three BDC data products are shared zero-copy to the Dremio **BDC** source (ex1 references them as `BDC.productionorder.productionorder`, `BDC.productionorder.productionorderoperation`, `BDC.workcenter.workcenter`). The reference medallion that defines the SAP-side logic is documented in [`data/otif-medallion`](../data/otif-medallion/README.md).

## Pre-flight checklist (do before the room arrives)

- [ ] Shared bucket exists; `./infra/upload_bronze.sh` run; all 7 folders present under `bronze/`.
- [ ] Dremio `s3lake` source reads the bucket; each `bronze/<table>/` previews with correct headers.
- [ ] BDC source shows the 3 SAP data products and the ex1 validation queries return rows.
- [ ] A Dremio space exists for `bronze`, `silver`, `gold` objects students will create.
- [ ] Joule Agent Builder is available to the student role, with a Dremio connection it can query.
- [ ] (Optional) `data/mes_synthetic_data` staged wherever the ex4 supplementary agent tool will read it.

## Teardown

- Drop the student-created `silver.*` / `gold.*` views and `bronze.*` Iceberg tables in Dremio.
- `aws s3 rm s3://teched2026-xp267-lab/bronze --recursive` to clear staged data.
