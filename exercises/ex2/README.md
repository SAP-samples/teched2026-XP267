# Exercise 2 - Land Non-SAP MES Data as Iceberg on S3 (Bronze)

In this exercise, you will bring the non-SAP side of the story into the lakehouse: shopfloor telemetry from the "Vertex" manufacturing-execution system (MES), stored as Apache Iceberg tables on Amazon S3 and queried in place by Dremio. This is the Bronze (raw) layer of your medallion.

The raw CSVs live in [`data/otif-synth-data`](../../data/otif-synth-data); in the lab they are already staged under your S3 `bronze/` prefix.

## Exercise 2.1 Explore the raw files on S3

After completing these steps you will have located the raw non-SAP data in object storage.

1. In Dremio, open your S3 source and browse to the `bronze/` prefix. You will see the incoming MES feeds:
<br>![Dremio browsing the S3 bronze prefix](/exercises/ex2/images/02_01_0010.png)

   > The non-SAP MES feeds (one Iceberg table each):
   > - `work_order/` — MES work orders: `work_order_id`, `equipment_id`, `material_number`, `sap_material_xref`, `planned_qty`, `completed_qty`, `scrap_qty`, `planned_start`, `planned_end`, `actual_start`, `actual_end`, `status`.
   > - `equipment/` — machine master: `equipment_id`, `equipment_name`, `equipment_type`, `plant_code`, `status`, `work_center_id`, `work_center_name`.
   > - `downtime_event/` — stoppages: `downtime_id`, `equipment_id`, `work_order_id`, `reason_category`, `reason_code`, `duration_minutes`, `planned_flag`, `start_ts`, `end_ts`, `shift`.
   > - `quality_event/` — inspections: `quality_event_id`, `equipment_id`, `work_order_id`, `inspection_type`, `result`, `defect_code`, `defect_qty`, `sample_size`, `inspection_ts`.
   > - `production_count/` — per-shift counts: `count_id`, `equipment_id`, `work_order_id`, `good_qty`, `scrap_qty`, `rework_qty`, `cycle_time_avg_sec`, `shift`, `report_ts`.
   > - `oee_snapshot/` — OEE windows: `snapshot_id`, `equipment_id`, `availability`, `performance`, `quality`, `oee`, `good_count`, `total_count`, `window_start`, `window_end`.
   > - `ground_truth_xref/` — the MES-equipment ↔ SAP work-center mapping (`WorkCenterInternalID`, `equipment_id`). This is the scoring truth for entity resolution — keep it out of any feature logic.

2. Preview a sample file and note that the data is raw — epoch-millis timestamps, mixed types, MES-local IDs not yet aligned to SAP work centers. That is expected for Bronze.

## Exercise 2.2 Register the data as Iceberg tables

After completing these steps the raw feeds will be queryable as managed Iceberg tables.

1. Create the Bronze Iceberg tables from the landed data. Running this in the Dremio SQL runner registers the data as open Iceberg tables that Dremio can query and that any Iceberg-compatible engine can read:
```sql
-- Bronze: non-SAP MES work orders as an Iceberg table on S3
CREATE TABLE s3lake.bronze.work_order AS
SELECT * FROM s3lake."bronze/work_order";

-- Bronze: machine master
CREATE TABLE s3lake.bronze.equipment AS
SELECT * FROM s3lake."bronze/equipment";

-- Bronze: downtime, quality and production-count telemetry
CREATE TABLE s3lake.bronze.downtime_event AS
SELECT * FROM s3lake."bronze/downtime_event";

CREATE TABLE s3lake.bronze.quality_event AS
SELECT * FROM s3lake."bronze/quality_event";

CREATE TABLE s3lake.bronze.production_count AS
SELECT * FROM s3lake."bronze/production_count";

-- Bronze: OEE snapshots
CREATE TABLE s3lake.bronze.oee_snapshot AS
SELECT * FROM s3lake."bronze/oee_snapshot";
```

2. Confirm the work-order and equipment tables exist and are readable:
```sql
SELECT work_order_id, equipment_id, material_number, sap_material_xref,
       planned_qty, completed_qty, scrap_qty, status
FROM s3lake.bronze.work_order
LIMIT 20;
```
<br>![Query result over the bronze work_order Iceberg table](/exercises/ex2/images/02_02_0010.png)

3. Confirm the quality and OEE feeds as well:
```sql
SELECT quality_event_id, equipment_id, work_order_id, inspection_type,
       result, defect_code, defect_qty
FROM s3lake.bronze.quality_event
LIMIT 20;

SELECT snapshot_id, equipment_id, availability, performance, quality, oee
FROM s3lake.bronze.oee_snapshot
LIMIT 20;
```

> Why this matters (showcase point): the non-SAP MES data stays in open Iceberg format on your own S3 — no proprietary lock-in. Dremio queries SAP data products *and* this open data through one engine, so the two worlds are already side-by-side, ready to be conformed in Silver.

## Screenshots to capture (for authors)

- [ ] `02_01_0010.png` — Dremio browsing the S3 `bronze/` prefix with the MES feeds
- [ ] `02_01_0020.png` — Preview of a raw work_order file
- [ ] `02_02_0010.png` — Query result over `bronze.work_order`
- [ ] `02_02_0020.png` — Query result over `bronze.oee_snapshot`

## Summary

You've now landed the non-SAP MES data as open Iceberg tables in the Bronze layer, queryable alongside your SAP data products. Next you will refine everything into a golden OTIF record.

Continue to - [Exercise 3 - Build the Medallion: Bronze → Silver → Gold](../ex3/README.md)
