# Exercise 3 - Build the Medallion: Bronze → Silver → Gold in Dremio

In this exercise, you will refine the raw Bronze data into a trusted golden inventory record. You will build the medallion as layered SQL views in Dremio and accelerate the final layer with a reflection — this is the "ELT" in the modern stack: transformation as semantics, not pipeline jobs.

- Bronze (done in ex2) — raw, as-landed.
- Silver — cleaned, typed, conformed to shared keys.
- Gold — the business-ready golden inventory record joining SAP + non-SAP.

## Exercise 3.1 Build the Silver layer (clean & conform)

After completing these steps you will have conformed the non-SAP data to the keys used by the SAP data products.

1. Create a Silver view that cleans shipments and aligns `material_number`/`plant` to the SAP convention, and derives whether a shipment is late:
```sql
-- Silver: cleaned, typed, conformed shipments
CREATE VIEW silver.shipments_clean AS
SELECT
    CAST(shipment_id AS VARCHAR)        AS shipment_id,
    UPPER(TRIM(material_number))        AS material_number,
    CAST(quantity AS DOUBLE)            AS quantity_in_transit,
    carrier,
    CAST(promised_eta AS TIMESTAMP)     AS promised_eta,
    CASE WHEN CAST(promised_eta AS TIMESTAMP) < CURRENT_TIMESTAMP
         THEN TRUE ELSE FALSE END       AS is_late
FROM s3lake.bronze.shipments
WHERE material_number IS NOT NULL;
```
<br>![Dremio showing the silver.shipments_clean view](/exercises/ex3/images/03_01_0010.png)

2. Create a Silver view that summarizes the latest warehouse conditions per plant:
```sql
-- Silver: latest sensor reading per plant
CREATE VIEW silver.plant_conditions AS
SELECT
    plant,
    AVG(temperature_c)   AS avg_temperature_c,
    AVG(humidity_pct)    AS avg_humidity_pct,
    MAX(reading_ts)      AS last_reading_ts
FROM s3lake.bronze.sensors
GROUP BY plant;
```

## Exercise 3.2 Build the Gold golden inventory record

After completing these steps you will have one business-ready view blending SAP data products with the conformed non-SAP data.

1. Create the Gold view. Note it joins BDC data products (SAP, zero-copy) directly to the Silver Iceberg-derived views (non-SAP) — the two worlds unified in one record:
```sql
-- Gold: the golden inventory record (SAP data products + non-SAP lakehouse)
CREATE VIEW gold.inventory_risk AS
SELECT
    mm.material_number,
    mm.material_description,
    mm.plant,
    mm.base_unit,
    soh.unrestricted_stock,
    soh.blocked_stock,
    COALESCE(sh.in_transit_qty, 0)          AS in_transit_qty,
    COALESCE(sh.late_shipments, 0)          AS late_shipments,
    pc.avg_temperature_c,
    -- simple, explainable risk flag for the showcase
    CASE
        WHEN soh.unrestricted_stock < 50 AND COALESCE(sh.in_transit_qty,0) = 0
            THEN 'HIGH'
        WHEN soh.unrestricted_stock < 50
            THEN 'MEDIUM'
        ELSE 'LOW'
    END                                     AS stockout_risk
FROM BDC.inventory.material_master           AS mm
JOIN BDC.inventory.stock_on_hand             AS soh
    ON mm.material_number = soh.material_number
   AND mm.plant           = soh.plant
LEFT JOIN (
    SELECT material_number,
           SUM(quantity_in_transit)                      AS in_transit_qty,
           SUM(CASE WHEN is_late THEN 1 ELSE 0 END)      AS late_shipments
    FROM silver.shipments_clean
    GROUP BY material_number
) AS sh ON mm.material_number = sh.material_number
LEFT JOIN silver.plant_conditions AS pc
    ON mm.plant = pc.plant;
```
<br>![Query result over gold.inventory_risk](/exercises/ex3/images/03_02_0010.png)

2. Query the golden record and sort by risk:
```sql
SELECT material_number, material_description, plant,
       unrestricted_stock, in_transit_qty, late_shipments, stockout_risk
FROM gold.inventory_risk
ORDER BY stockout_risk DESC, unrestricted_stock ASC
LIMIT 50;
```

3. Accelerate the Gold layer with a reflection so the agent (ex4) and dashboards get fast responses. In Dremio, open `gold.inventory_risk`, go to Reflections, and enable a Raw Reflection.
<br>![Enabling a raw reflection on the gold view](/exercises/ex3/images/03_02_0020.png)

   > Why this matters (showcase point): the golden record is a view, not a copy. Change a Silver rule and the Gold record updates — no pipeline to re-run. The reflection gives physical speed without giving up the single logical source of truth.

## Screenshots to capture (for authors)

- [ ] `03_01_0010.png` — `silver.shipments_clean` view defined and previewed
- [ ] `03_01_0020.png` — `silver.plant_conditions` preview
- [ ] `03_02_0010.png` — `gold.inventory_risk` query result with risk column
- [ ] `03_02_0020.png` — Raw reflection enabled on the Gold view

## Summary

You've built a golden inventory record that unifies SAP data products with open non-SAP lakehouse data, accelerated by a reflection. Next you will put an agent on top of it.

Continue to - [Exercise 4 - Build a Joule Agent on the Golden Record](../ex4/README.md)
