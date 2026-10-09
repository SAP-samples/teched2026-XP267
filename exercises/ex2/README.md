# Exercise 2 - Land Non-SAP Data as Iceberg on S3 (Bronze)

In this exercise, you will bring the non-SAP side of the story into the lakehouse: logistics and IoT telemetry stored as Apache Iceberg tables on Amazon S3, queried in place by Dremio. This is the Bronze (raw) layer of your medallion.

## Exercise 2.1 Explore the raw files on S3

After completing these steps you will have located the raw non-SAP data in object storage.

1. In Dremio, open your S3 source and browse to the `bronze/` prefix. You will see two incoming feeds:
<br>![Dremio browsing the S3 bronze prefix](/exercises/ex2/images/02_01_0010.png)

   > The two non-SAP feeds:
   > - `shipments/` — inbound shipment events (shipment id, material number, quantity, origin, promised ETA, carrier). Partner/3PL export.
   > - `sensors/` — warehouse IoT readings (plant, sensor id, temperature, humidity, reading timestamp).

2. Preview a sample file and note that the data is raw — mixed types, no business keys aligned to SAP yet. That is expected for Bronze.

## Exercise 2.2 Register the data as Iceberg tables

After completing these steps the raw feeds will be queryable as managed Iceberg tables.

1. Create the Bronze Iceberg tables from the landed data. Running this in the Dremio SQL runner registers the data as open Iceberg tables that Dremio can query and that any Iceberg-compatible engine can read:
```sql
-- Bronze: non-SAP shipment events as an Iceberg table on S3
CREATE TABLE s3lake.bronze.shipments AS
SELECT * FROM s3lake."bronze/shipments";

-- Bronze: non-SAP warehouse IoT readings as an Iceberg table on S3
CREATE TABLE s3lake.bronze.sensors AS
SELECT * FROM s3lake."bronze/sensors";
```

2. Confirm the tables exist and are readable:
```sql
SELECT shipment_id, material_number, quantity, origin, promised_eta, carrier
FROM s3lake.bronze.shipments
LIMIT 20;
```
<br>![Query result over the bronze shipments Iceberg table](/exercises/ex2/images/02_02_0010.png)

3. Confirm the sensor feed as well:
```sql
SELECT plant, sensor_id, temperature_c, humidity_pct, reading_ts
FROM s3lake.bronze.sensors
LIMIT 20;
```

> Why this matters (showcase point): the non-SAP data stays in open Iceberg format on your own S3 — no proprietary lock-in. Dremio queries SAP data products *and* this open data through one engine, so the two worlds are already side-by-side.

## Screenshots to capture (for authors)

- [ ] `02_01_0010.png` — Dremio browsing the S3 `bronze/` prefix with both feeds
- [ ] `02_01_0020.png` — Preview of a raw shipments file
- [ ] `02_02_0010.png` — Query result over `bronze.shipments`
- [ ] `02_02_0020.png` — Query result over `bronze.sensors`

## Summary

You've now landed the non-SAP data as open Iceberg tables in the Bronze layer, queryable alongside your SAP data products. Next you will refine everything into a golden record.

Continue to - [Exercise 3 - Build the Medallion: Bronze → Silver → Gold](../ex3/README.md)
