# Exercise 1 - Build the Golden Records in Dremio

In this exercise, you will refine governed SAP data into trusted **golden records** using layered SQL views in Dremio, and accelerate them with reflections — this is the "ELT" in the modern stack: transformation as semantics, not pipeline jobs.

You will build two tracks:

- **Primary — Customer Order Fulfillment (Sales / CRM).** A golden **customer order-fulfillment** record that blends sales demand, purchasing supply, and customer master data into one business-ready view, materialized for downstream use. This is the record Exercise 2 builds an ontology on, and Exercise 3 grounds a Joule agent on.
- **Secondary — OTIF manufacturing medallion.** The on-time-in-full production-risk medallion (silver → gold), kept as a second, deterministic golden record so the agent can also reason over the shopfloor.

## Where the data comes from (and why we query it in Dremio)

The SAP tables you use here — `customer`, `salesorderitem`, `purchaseorderitem` (and the production/work-center data for the OTIF track) — originate as **governed SAP S/4HANA data products in SAP Business Data Cloud (BDC)**: meaningful field names, business semantics, and a defined contract, not raw tables.

For this hands-on lab those data products have been **exported and pre-loaded into Dremio**, where you query them as tables under `"teched_labs_sandbox"."sap_dp"`:

- `"teched_labs_sandbox"."sap_dp".customer`
- `"teched_labs_sandbox"."sap_dp".salesorderitem`
- `"teched_labs_sandbox"."sap_dp".purchaseorderitem`

> **Why not read BDC live?** The sourcing story is still BDC data products — that is where this governed data is born and where lineage leads back to. We query the exported copies in Dremio so the hands-on session has **no live-connection dependency** on BDC during the demo. Narrate the BDC origin; run the SQL against Dremio.

## Exercise 1.1 Build the Customer Order Fulfillment golden record

After completing these steps you will have one business-ready view, one row per customer + material + plant, that compares what customers ordered (demand) against what purchasing secured (supply), enriched with customer context.

1. Build the fulfillment view. It aggregates sales-order demand and purchase-order supply per `Material` + `Plant`, joins customer master for context, and derives a coverage ratio and a fulfillment verdict:

```sql
CREATE VIEW "teched_labs_sandbox"."sap_dp".v_customer_order_fulfillment AS
WITH demand AS (
  SELECT SoldToParty AS "Customer", Material AS "Material", Plant AS "Plant",
         SUM(CASE WHEN REGEXP_LIKE(RequestedQuantity, '^-?[0-9]+(\.[0-9]+)?$')
                  THEN CAST(RequestedQuantity AS DOUBLE) END) AS "req_qty",
         COUNT(*)                                             AS "so_lines"
  FROM "teched_labs_sandbox"."sap_dp".salesorderitem
  WHERE Material IS NOT NULL AND Material <> ''
  GROUP BY SoldToParty, Material, Plant
),
supply AS (
  SELECT Material AS "Material", Plant AS "Plant",
         SUM(CASE WHEN REGEXP_LIKE(OrderQuantity, '^-?[0-9]+(\.[0-9]+)?$')
                  THEN CAST(OrderQuantity AS DOUBLE) END) AS "po_qty",
         COUNT(*)                                         AS "po_lines",
         COUNT(DISTINCT Supplier)                         AS "suppliers"
  FROM "teched_labs_sandbox"."sap_dp".purchaseorderitem
  WHERE Material IS NOT NULL AND Material <> ''
  GROUP BY Material, Plant
)
SELECT
  d."Customer",
  c.CustomerName                 AS "CustomerName",
  c.Country                      AS "Country",
  c.Industry                     AS "Industry",
  c.CustomerClassification       AS "CustomerClassification",
  d."Material",
  d."Plant",
  d."req_qty", d."so_lines",
  s."po_qty",  s."po_lines", s."suppliers",
  ROUND(s."po_qty" / NULLIF(d."req_qty", 0), 3) AS "coverage_ratio",
  CASE WHEN d."req_qty" IS NOT NULL AND (s."po_qty" IS NULL OR s."po_qty" = 0) THEN 'demand_no_supply'
       WHEN s."po_qty" <  d."req_qty"  THEN 'under_covered'
       WHEN s."po_qty" >= d."req_qty"  THEN 'covered'
       ELSE 'supply_only' END                   AS "coverage_status"
FROM demand d
LEFT JOIN supply   s ON d."Material" = s."Material" AND d."Plant" = s."Plant"
LEFT JOIN "teched_labs_sandbox"."sap_dp".customer c ON c.Customer = d."Customer";
```

> **Why the guarded cast?** The quantity columns are stored as strings and some rows carry a unit token (e.g. `EA`) instead of a number. A plain `CAST(... AS DOUBLE)` errors ("Failed to cast the string EA to double"). The `REGEXP_LIKE(..., '^-?[0-9]+(\.[0-9]+)?$')` guard casts only numeric-looking values and lets `SUM` ignore the rest — the same behavior as Databricks `try_cast`. If quantities can appear in scientific notation or with thousands separators, widen the pattern.
<br>![Dremio showing the v_customer_order_fulfillment view](/exercises/ex1/images/01_01_0010.png)

2. Preview the golden record and work the gaps first — customers whose demand is not covered by supply:

```sql
SELECT "Customer", "CustomerName", "Country", "Industry",
       "Material", "Plant", "req_qty", "po_qty",
       "coverage_ratio", "coverage_status"
FROM "teched_labs_sandbox"."sap_dp".v_customer_order_fulfillment
WHERE "coverage_status" IN ('demand_no_supply', 'under_covered')
ORDER BY "coverage_ratio" NULLS FIRST
LIMIT 50;
```
<br>![v_customer_order_fulfillment preview sorted by coverage](/exercises/ex1/images/01_01_0020.png)

> Note: output column names are double-quoted to preserve the capitalized Databricks-style names (`Material`, `Plant`, `Customer`, …). Once quoted, later references are case-sensitive — query them as `"Material"`, not `material`.

## Exercise 1.2 Materialize the golden record for downstream use

After completing these steps the fulfillment golden record will be physically accelerated so Exercise 2's ontology and Exercise 3's agent get fast, stable responses.

Dremio has no `CREATE MATERIALIZED VIEW` statement — you create a regular view (above) and enable a **Reflection** on it. The reflection is the physically stored, auto-maintained copy that Dremio transparently substitutes to accelerate queries; you keep querying the view by name.

1. Enable a **Raw Reflection** on the view. In the Dremio UI, open `v_customer_order_fulfillment` → **Reflections** → toggle on **Raw Reflection**. Or via SQL:

```sql
ALTER DATASET "teched_labs_sandbox"."sap_dp".v_customer_order_fulfillment
CREATE RAW REFLECTION cof_raw
USING DISPLAY (
  "Customer", "CustomerName", "Country", "Industry", "CustomerClassification",
  "Material", "Plant", "req_qty", "so_lines", "po_qty", "po_lines", "suppliers",
  "coverage_ratio", "coverage_status"
);
```
<br>![Enabling a raw reflection on the fulfillment view](/exercises/ex1/images/01_02_0010.png)

2. (Optional) Set a refresh policy so the materialization stays current:

```sql
ALTER DATASET "teched_labs_sandbox"."sap_dp".v_customer_order_fulfillment
SET REFRESH EVERY '1' HOUR;
```

> Why this matters (showcase point): the golden record is a **view, not a copy**. Change the coverage threshold and every downstream consumer — the ontology in Exercise 2, the agent in Exercise 3 — reflects it immediately. The reflection gives physical speed without giving up the single logical source of truth. **This materialized `v_customer_order_fulfillment` is the hand-off to Exercise 2**, where another team builds an ontology on top of it.

## Exercise 1.3 (Secondary) Build the OTIF manufacturing medallion

This track keeps the on-time-in-full production-risk golden record so the agent in Exercise 3 can also answer shopfloor-delivery questions. The derived-column logic mirrors the reference implementation in [`data/otif-medallion`](../../data/otif-medallion/README.md) (there it runs as Spark SQL on Databricks; here you rebuild it as Dremio views). Every score and flag is deterministic SQL — hand-authored `CASE` statements and thresholds, **no ML model**. "Predictive" means a rule that fires early on open orders, before the due date.

1. Build the Silver layer — one harmonized, enriched row per production-order operation:

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
FROM "teched_labs_sandbox"."sap_dp".productionorder                 AS po
JOIN "teched_labs_sandbox"."sap_dp".productionorderoperation        AS op
    ON po.ProductionOrder = op.ProductionOrder
LEFT JOIN "teched_labs_sandbox"."sap_dp".workcenter                 AS wc
    ON op.WorkCenterInternalID = wc.WorkCenterInternalID;
```

2. Build the Gold golden OTIF record — one row per production order, keeping the *worst* operation signals:

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

3. Accelerate the Gold layer with a Raw Reflection too (same pattern as 1.2), so the agent gets fast responses.

> Why this matters (showcase point): change a Silver threshold and the Gold verdict updates — no pipeline to re-run. (Note: `ARRAY_SORT` / `SET_UNION` syntax varies by engine — if your Dremio build differs, substitute the equivalent array-aggregation function; the reference Databricks logic uses `ARRAY_JOIN(COLLECT_SET(...))`.)

## Screenshots to capture (for authors)

- [ ] `01_01_0010.png` — `v_customer_order_fulfillment` view defined
- [ ] `01_01_0020.png` — `v_customer_order_fulfillment` preview sorted by `coverage_ratio`
- [ ] `01_02_0010.png` — Raw reflection enabled on the fulfillment view
- [ ] `01_03_0010.png` — `gold.otif_risk` query result (secondary OTIF track)

> **Author note:** the SQL above has not been run against a live Dremio. Validate before the session — especially the quantity-cast guard, the quoted mixed-case identifiers, and (OTIF track) the `ARRAY_SORT`/`SET_UNION` array functions.

## Summary

You've built a golden **customer order-fulfillment** record (primary) and the OTIF manufacturing medallion (secondary), both as Dremio views accelerated by reflections, sourced from governed SAP BDC data products queried in Dremio. The materialized `v_customer_order_fulfillment` is the foundation the next exercise builds an ontology on.

Continue to - [Exercise 2 - Ontologies on the Golden Record](../ex2/README.md)
