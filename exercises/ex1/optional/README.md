# Exercise 1 — Optional / Advanced: OTIF Manufacturing Medallion

A deterministic shopfloor **production-risk** golden record (silver → gold), rebuilt as Dremio views. Every score and flag is hand-authored `CASE` logic and thresholds — no ML. "Predictive" means a rule that fires early on open orders, before the due date.

This is optional secondary context the Exercise 3 agent can use for manufacturing questions. It is **not part of the main flow**, and it is the most likely live-failure point in the lab (the `ARRAY_SORT`/`SET_UNION` array functions — see the closing note).

**Prerequisite:** [Exercise 1](../README.md) completed. Views build into your own space, `"<your_space>"` (e.g. `xp267-001`) — the same space you used in Exercise 1. Replace `<your_space>` in each block with your space name.

## Steps

### Step 1 — Preview production orders and operations

Each production order (`productionorder`) has one or more operations (`productionorderoperation`). Scheduled vs actual end dates drive lateness; planned vs confirmed/scrap quantities drive the anomaly signals.

```sql
SELECT po.ProductionOrder, po.OrderScheduledEndDate, po.OrderActualEndDate,
       op.ProductionOrderOperation, op.WorkCenterInternalID,
       op.OpPlannedTotalQuantity, op.OpTotalConfirmedScrapQty
FROM "teched_labs_sandbox"."sap_dp".productionorder          AS po
JOIN "teched_labs_sandbox"."sap_dp".productionorderoperation AS op
  ON po.ProductionOrder = op.ProductionOrder
LIMIT 20;
```

> **You should see** several operation rows per order; a NULL `OrderActualEndDate` marks an open order — the ones the risk rules fire on *before* the due date.

---

### Step 2 — Preview the work-center master

The work-center master names each machine (`WorkCenterName`) by its `WorkCenterInternalID` — the label that makes the risk record human-readable.

```sql
SELECT WorkCenterInternalID, WorkCenterName
FROM "teched_labs_sandbox"."sap_dp".workcenter
LIMIT 20;
```

> **You should see** one row per work center; `WorkCenterInternalID` is the key the Silver view joins on.

---

### Step 3 — Build the Silver view `otif_production`

One harmonized, enriched row per production-order operation.

```sql
-- Silver: one harmonized, enriched row per production-order operation
CREATE VIEW "<your_space>".otif_production AS
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

---

### Step 4 — Build the Gold view `otif_risk`

One row per production order, keeping the *worst* operation signals.

```sql
-- Gold: the golden OTIF risk record (one row per production order)
CREATE VIEW "<your_space>".otif_risk AS
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
    FROM "<your_space>".otif_production
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

---

### Step 5 — Preview the Gold risk record

The at-risk open orders, worst first — the shopfloor half of what the agent answers in Exercise 3.

```sql
SELECT ProductionOrder, risk_tier, otif_risk_score,
       primary_root_cause, anomalous_work_centers
FROM "<your_space>".otif_risk
WHERE delivery_status = 'In Progress'
ORDER BY otif_risk_score DESC
LIMIT 20;
```

> **You should see** open orders ranked by `otif_risk_score`, each with a `risk_tier`, a `primary_root_cause`, and the `anomalous_work_centers` driving the risk — a deterministic, explainable verdict (no ML). Change a Silver threshold and the Gold verdict updates — no pipeline to re-run.

![otif_risk query result — at-risk open orders, worst first](images/01_0A_0010.png)

---

### Step 6 — Accelerate with a Raw Reflection

Enable a Raw Reflection on `otif_risk` (same mechanic as the main flow) so the agent gets fast responses.

---

> **Live-failure caveat:** `ARRAY_SORT` / `SET_UNION` syntax varies by engine. If your Dremio build differs, substitute the equivalent array-aggregation function — the reference Databricks logic uses `ARRAY_JOIN(COLLECT_SET(...))`.

> **Author note:** this OTIF SQL has **not** been run against a live Dremio — validate before the session, especially the `ARRAY_SORT`/`SET_UNION` array functions.

← Back to [Exercise 1](../README.md)