# Speaker Guide — Exercise 2: Non-SAP MES Data as Iceberg (Bronze)

**~10 min.** Student doc: [`exercises/ex2`](../exercises/ex2/README.md)

## Goal
Turn the 7 raw Vertex MES CSVs (already staged on S3) into managed **Iceberg** bronze tables in Dremio.

## The 7 non-SAP feeds
work_order, equipment, downtime_event, quality_event, production_count, oee_snapshot, ground_truth_xref.
Each lives in its own `bronze/<table>/` folder — Dremio promotes a folder, not a loose file.

## Talking points
- The data is **raw**: epoch-millis timestamps (`BIGINT`), MES-local IDs not yet aligned to SAP work centers. That's what Bronze means.
- Students upload nothing — the files were **staged once** pre-session (anti-fragile demo). The learning is the `CREATE TABLE ... AS SELECT` that converts CSV → open Iceberg.
- Message: SAP data products **and** open Iceberg, queried by **one engine**. The two worlds are already side-by-side.

## Do live — expected results
- `CREATE TABLE s3lake.bronze.work_order AS SELECT * FROM s3lake."bronze/work_order"` → ~200 rows.
- `oee_snapshot` → 120 rows; `downtime_event`/`quality_event`/`production_count` → 150 each; `equipment` → 100; `ground_truth_xref` → 85.

## Gotchas
- **Folder vs file**: if a student points at the `.csv` instead of the folder, promotion/format differs. Steer them to the folder.
- **Header row**: ensure "Extract field names" is on, or columns come back as `A, B, C...`.
- Call out `ground_truth_xref` now — "remember this one, it's the bridge that joins non-SAP to SAP in the next exercise."

## Transition
"Two worlds, side by side but not yet talking. The medallion makes them one record."
