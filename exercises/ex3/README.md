# Exercise 3 - Build the Medallion: Bronze → Silver → Gold in Dremio

In this exercise, you will refine the raw data into a trusted golden **OTIF risk** record. You will build the medallion as layered SQL views in Dremio and accelerate the final layer with a reflection — this is the "ELT" in the modern stack: transformation as semantics, not pipeline jobs.

- Bronze (SAP data products from ex1 + MES Iceberg from ex2) — raw, as-landed.
- Silver — one clean, typed row per production-order *operation*, enriched with anomaly signals.
- Gold — one business-ready row per production *order*: the OTIF risk verdict.

The derived-column logic below mirrors the reference implementation in [`data/otif-medallion`](../../data/otif-medallion/README.md) (there it runs as Spark SQL on Databricks; here you rebuild it as Dremio views). Every score and flag is deterministic SQL — hand-authored `CASE` statements and thresholds, **no ML model**. "Predictive" means a rule that fires early on open orders, before the due date.

## Exercise 3.1 Build the Silver layer (clean & conform)

After completing these steps you will have one flat, per-operation row that harmonizes the three SAP data products and derives anomaly signals.

1. Create the Silver view. It joins the Production Order header to its operations on `ProductionOrder` (inner join), then left-joins Work Center on `WorkCenterInternalID` so operations survive even without matching machine master data:
```sql
-- Silver: one harmonized, enriched row per production-order operation
CREATE VIEW silver.otif_production AS
SELECT
    po.ProductionOrder,
    po.ProductionOrderType,
    po.ProductionPlant,
    po.OrderScheduledEndDate,
    po.OrderActualEndDate,
    op.ProductionOrderOperation,
    op.WorkCenterInternalID,
    wc.WorkCenterName,
    op.OpPlannedTotalQuantity,
    op.OpTotalConfirmedScrapQty                                   AS ActualScrapQty,

    -- delivery_status: is the order late?
    CASE
        WHEN po.OrderActualEndDate IS NULL                        THEN 'In Progress'
        WHEN po.OrderActualEndDate > po.OrderScheduledEndDate     THEN 'Late'
        WHEN po.OrderActualEndDate <= po.OrderScheduledEndDate    THEN 'On Time'
        ELSE 'Unknown'
    END                                                           AS delivery_status,

    -- schedule_delay_days: how many days late the order finished
    DATEDIFF(po.OrderActualEndDate, po.OrderScheduledEndDate)     AS schedule_delay_days,

    -- actual_scrap_pct: real scrap rate for the operation (0 when planned qty not > 0)
    CASE WHEN op.OpPlannedTotalQuantity > 0
         THEN ROUND(op.OpTotalConfirmedScrapQty / op.OpPlannedTotalQuantity * 100, 2)
         ELSE 0 END                                               AS actual_scrap_pct,

    -- work_ratio_vs_standard: actual vs. standard work (1.0 = on standard)
    CASE WHEN op.WorkCenterStandardWorkQty1 > 0
         THEN ROUND(op.ConfirmedWorkQuantity1 / op.WorkCenterStandardWorkQty1, 3)
         ELSE NULL END                                            AS work_ratio_vs_standard,

    -- root_cause_tag: why the operation is bad
    CASE
        WHEN op.WorkCenterStandardWorkQty1 > 0
             AND op.ConfirmedWorkQuantity1 / op.WorkCenterStandardWorkQty1 > 1.5
            THEN 'Work Overrun'
        WHEN op.OpPlannedTotalQuantity > 0
             AND op.OpTotalConfirmedScrapQty / op.OpPlannedTotalQuantity > 0.30
            THEN 'High Scrap'
        WHEN op.WorkCenterInternalID = '10000040'
             AND op.OpPlannedTotalQuantity > 0
             AND op.OpTotalConfirmedScrapQty / op.OpPlannedTotalQuantity > 0.10
            THEN 'Final Acceptance Failure'
        ELSE 'Normal'
    END                                                           AS root_cause_tag,

    -- operation_anomaly_score: 0-100 severity blend of overrun + scrap
    LEAST(100, CAST(
        LEAST(50, GREATEST(0,
            (COALESCE(op.ConfirmedWorkQuantity1 / NULLIF(op.WorkCenterStandardWorkQty1,0), 1.0) - 1.0) * 50))
        + LEAST(50,
            CASE WHEN op.OpPlannedTotalQuantity > 0
                 THEN op.OpTotalConfirmedScrapQty / op.OpPlannedTotalQuantity * 100
                 ELSE 0 END)
        AS INT))                                                  AS operation_anomaly_score
FROM BDC.productionorder.productionorder                 AS po
JOIN BDC.productionorder.productionorderoperation        AS op
    ON po.ProductionOrder = op.ProductionOrder
LEFT JOIN BDC.workcenter.workcenter                      AS wc
    ON op.WorkCenterInternalID = wc.WorkCenterInternalID;
```
<br>![Dremio showing the silver.otif_production view](/exercises/ex3/images/03_01_0010.png)

2. Preview the Silver view and confirm each operation now carries `delivery_status`, `actual_scrap_pct`, `work_ratio_vs_standard`, `root_cause_tag`, and `operation_anomaly_score`:
```sql
SELECT ProductionOrder, ProductionOrderOperation, WorkCenterName,
       delivery_status, actual_scrap_pct, work_ratio_vs_standard,
       root_cause_tag, operation_anomaly_score
FROM silver.otif_production
ORDER BY operation_anomaly_score DESC
LIMIT 20;
```
<br>![silver.otif_production preview sorted by anomaly](/exercises/ex3/images/03_01_0020.png)

## Exercise 3.2 Build the Gold golden OTIF record

After completing these steps you will have one business-ready view, one row per production order, that turns the worst operation signals into an OTIF risk verdict.

1. Create the Gold view. It aggregates all operations of an order and keeps the *worst* signals (an order is only as healthy as its worst operation), then derives the per-order verdict:
```sql
-- Gold: the golden OTIF risk record (one row per production order)
CREATE VIEW gold.otif_risk AS
WITH agg AS (
    SELECT
        ProductionOrder,
        MAX(ProductionPlant)                                     AS plant,
        MAX(delivery_status)                                     AS delivery_status,
        MAX(schedule_delay_days)                                 AS schedule_delay_days,
        COUNT(ProductionOrderOperation)                          AS total_operations,
        MAX(operation_anomaly_score)                             AS max_anomaly_score,
        ROUND(AVG(actual_scrap_pct), 2)                          AS avg_scrap_pct,
        ROUND(MAX(actual_scrap_pct), 2)                          AS max_scrap_pct,
        ROUND(MAX(work_ratio_vs_standard), 3)                    AS max_work_ratio,
        SUM(ActualScrapQty)                                      AS total_scrap_qty,
        -- which machines are driving the risk (score >= 30), sorted & de-duped
        ARRAY_JOIN(
            ARRAY_SORT(SET_UNION(
                CASE WHEN operation_anomaly_score >= 30
                     THEN ARRAY[WorkCenterName] ELSE ARRAY[] END)), ', ')
                                                                 AS anomalous_work_centers
    FROM silver.otif_production
    GROUP BY ProductionOrder
)
SELECT
    ProductionOrder,
    plant,
    delivery_status,
    schedule_delay_days,
    total_operations,
    max_anomaly_score,
    avg_scrap_pct,
    max_scrap_pct,
    max_work_ratio,
    total_scrap_qty,
    anomalous_work_centers,

    -- primary_root_cause: single most-severe cause on the order (severity precedence)
    CASE
        WHEN max_work_ratio IS NOT NULL AND max_anomaly_score >= 50 THEN 'Work Overrun'
        WHEN max_anomaly_score >= 40                                THEN 'High Scrap'
        WHEN max_anomaly_score >= 15                                THEN 'Final Acceptance Failure'
        ELSE 'Normal'
    END                                                             AS primary_root_cause,

    -- otif_risk_score: 0-100 order-level OTIF risk
    LEAST(100, CAST(
        LEAST(40, COALESCE(schedule_delay_days, 0) * 4)
        + max_anomaly_score * 0.6
        AS INT))                                                    AS otif_risk_score,

    -- is_at_risk: predictive flag -- open order already showing trouble
    CASE WHEN delivery_status = 'In Progress' AND max_anomaly_score >= 30
         THEN TRUE ELSE FALSE END                                   AS is_at_risk,

    -- risk_tier: human-readable bucket for reporting
    CASE
        WHEN delivery_status = 'Late'                               THEN 'Breached'
        WHEN delivery_status = 'In Progress'
             AND LEAST(100, LEAST(40, COALESCE(schedule_delay_days,0)*4) + max_anomaly_score*0.6) >= 40
            THEN 'High Risk'
        WHEN delivery_status = 'In Progress'
             AND LEAST(100, LEAST(40, COALESCE(schedule_delay_days,0)*4) + max_anomaly_score*0.6) >= 20
            THEN 'Medium Risk'
        WHEN delivery_status = 'In Progress'
             AND LEAST(100, LEAST(40, COALESCE(schedule_delay_days,0)*4) + max_anomaly_score*0.6) > 0
            THEN 'Low Risk'
        WHEN delivery_status = 'On Time'                            THEN 'Completed'
        ELSE 'Normal'
    END                                                             AS risk_tier
FROM agg;
```
<br>![Query result over gold.otif_risk](/exercises/ex3/images/03_02_0010.png)

2. Query the golden record and work the worst first:
```sql
SELECT ProductionOrder, plant, delivery_status, risk_tier,
       otif_risk_score, primary_root_cause, anomalous_work_centers
FROM gold.otif_risk
WHERE is_at_risk = TRUE OR risk_tier = 'Breached'
ORDER BY otif_risk_score DESC
LIMIT 50;
```

3. **Unify the non-SAP side.** The Gold view above is built purely from SAP data products — faithful to the [reference medallion](../../data/otif-medallion/README.md), which is SAP-only. Now add the shopfloor explanation that only the non-SAP MES has: join the Vertex downtime/OEE telemetry to the SAP work centers through the `ground_truth_xref` mapping (MES `equipment_id` ↔ SAP `WorkCenterInternalID`). First build a Silver bridge that conforms the MES machine identity to the SAP key:
```sql
-- Silver: conform non-SAP MES telemetry to the SAP work-center key
CREATE VIEW silver.workcenter_shopfloor AS
SELECT
    x.WorkCenterInternalID,
    AVG(o.oee)                              AS avg_oee,
    AVG(o.availability)                     AS avg_availability,
    SUM(CASE WHEN d.planned_flag = false
             THEN d.duration_minutes ELSE 0 END) AS unplanned_downtime_minutes
FROM s3lake.bronze.ground_truth_xref x
LEFT JOIN s3lake.bronze.oee_snapshot    o ON o.equipment_id = x.equipment_id
LEFT JOIN s3lake.bronze.downtime_event  d ON d.equipment_id = x.equipment_id
GROUP BY x.WorkCenterInternalID;
```
Then extend the Gold record so each at-risk order can point at the real machine condition behind the risk (left-join on the worst anomalous work center). This is where SAP and non-SAP meet in one row:
```sql
-- Gold+: enrich the OTIF verdict with non-SAP shopfloor condition
CREATE VIEW gold.otif_risk_enriched AS
SELECT
    g.*,
    sf.avg_oee,
    sf.unplanned_downtime_minutes
FROM gold.otif_risk g
LEFT JOIN silver.otif_production op
    ON op.ProductionOrder = g.ProductionOrder
   AND op.operation_anomaly_score = g.max_anomaly_score
LEFT JOIN silver.workcenter_shopfloor sf
    ON sf.WorkCenterInternalID = op.WorkCenterInternalID;
```

4. Accelerate the Gold layer with a reflection so the agent (ex4) and dashboards get fast responses. In Dremio, open `gold.otif_risk_enriched`, go to Reflections, and enable a Raw Reflection.
<br>![Enabling a raw reflection on the gold view](/exercises/ex3/images/03_02_0020.png)

   > Why this matters (showcase point): the golden record is a view, not a copy. Change a Silver threshold and the Gold verdict updates — no pipeline to re-run. The reflection gives physical speed without giving up the single logical source of truth. (Note: `ARRAY_SORT` / `SET_UNION` syntax varies by engine — if your Dremio build differs, substitute the equivalent array-aggregation function; the reference Databricks logic uses `ARRAY_JOIN(COLLECT_SET(...))`.)

## Screenshots to capture (for authors)

- [ ] `03_01_0010.png` — `silver.otif_production` view defined
- [ ] `03_01_0020.png` — `silver.otif_production` preview sorted by `operation_anomaly_score`
- [ ] `03_02_0010.png` — `gold.otif_risk` query result with risk columns
- [ ] `03_02_0020.png` — Raw reflection enabled on the Gold view

## Summary

You've built a golden OTIF record that unifies SAP data products with open non-SAP lakehouse data, accelerated by a reflection. Next you will put an agent on top of it.

Continue to - [Exercise 4 - Build a Joule Agent on the Golden Record](../ex4/README.md)
