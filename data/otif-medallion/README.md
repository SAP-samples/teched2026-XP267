# OTIF Golden Records — Medallion Layer

Built by [`azure_silver_golden_dps.ipynb`](./azure_silver_golden_dps.ipynb) on Azure Databricks. It reads the SAP S/4HANA supply-chain data products from the read-only Delta-share catalog `` `otif-demo-data-products` `` and writes the golden records into the existing managed catalog `` `otif-demo-bdc` ``, schema `otif_demo`.

> **No ML model — this is pure SQL.** Every score, risk value, root cause, and "predictive" flag is produced by deterministic Spark SQL: `CASE` statements, arithmetic formulas, and hand-authored thresholds. The weights and cutoffs are all written by hand — nothing is learned. "Predictive" here just means a rule that fires early on open orders (before the due date), not a trained model forecasting an outcome. (Actual ML for OTIF risk — TabPFN / XGBoost — lives elsewhere in this repo, not in the medallion layer.)

## The main question

**Which production orders are going to miss their on-time-in-full (OTIF) delivery commitment — and why — so we can act before the due date?**

That's the one question the golden records exist to answer. Everything below serves it.

## What the golden records serve

- **Will it miss?** — `is_at_risk` / `risk_tier` flag open orders heading for a breach *before* they're actually late (the predictive part).
- **How badly?** — `otif_risk_score` (0–100) ranks them so you work the worst first.
- **Why?** — `primary_root_cause` (Work Overrun / High Scrap / Final Acceptance Failure) explains the driver.
- **Where?** — `anomalous_work_centers` points to the specific machines/stations to intervene on.

## The three objects

| Object | Grain | Type | Role |
|---|---|---|---|
| `silver_otif_production` | one row per operation | view | live harmonized silver layer, recomputed from the share |
| `silver_otif_production_tbl` | one row per operation | table | materialized snapshot of the view (shareable / stable) |
| `gold_otif_risk` | one row per production order | table | order-level OTIF risk verdict |

---

## Silver — `silver_otif_production`

**Question it answers:** *What happened on each production-order operation, and how anomalous was it?*

Silver harmonizes three source tables into one flat, per-operation row, then enriches each row with derived anomaly signals:

- header ⟕ operation on `ProductionOrder` (inner join)
- operation ⟕ work center on `WorkCenterInternalID + Plant` (left join, so operations survive without matching machine master data)

### Derived columns

**delivery_status** — Is the order late?
CASE: actual end IS NULL → 'In Progress'; actual > scheduled → 'Late'; actual <= scheduled → 'On Time'; else 'Unknown'

**schedule_delay_days** — How many days late the order finished
DATEDIFF(OrderActualEndDate, OrderScheduledEndDate)

**actual_scrap_pct** — Real scrap rate for the operation
OpTotalConfirmedScrapQty / OpPlannedTotalQuantity * 100 (0 when planned qty not > 0), rounded 2dp

**work_ratio_vs_standard** — How actual work compares to the standard (1.0 = on standard)
ConfirmedWorkQuantity1 / WorkCenterStandardWorkQty1 (NULL when standard not > 0), rounded 3dp

**scrap_deviation_pct** — Actual scrap vs. what was planned
(actual scrap %) − OperationScrapPercent (NULL when planned qty not > 0), rounded 2dp

**root_cause_tag** — Why the operation is bad
CASE: work ratio > 1.5 → 'Work Overrun'; scrap fraction > 0.30 → 'High Scrap'; WorkCenter '10000040' AND scrap fraction > 0.10 → 'Final Acceptance Failure'; else 'Normal'

**operation_anomaly_score** — 0–100 severity blend of overrun + scrap
LEAST(100, work-overrun component capped at 50 [(work_ratio − 1.0) * 50] + scrap component capped at 50 [scrap %]), rounded to INT

---

## Gold — `gold_otif_risk`

**Question it answers:** *Which orders will miss OTIF, how badly, and which machines to look at?*

Gold aggregates all operations of an order and keeps the *worst* signals (an order is only as healthy as its worst operation), then turns those into a per-order risk verdict.

### Aggregated columns (per production order)

**total_operations** — How many operations on the order
COUNT(ProductionOrderOperation)

**max_anomaly_score** — Severity of the worst operation on the order
MAX(operation_anomaly_score)

**avg_scrap_pct** — Typical scrap across operations
ROUND(AVG(actual_scrap_pct), 2)

**max_scrap_pct** — Worst scrap across operations
ROUND(MAX(actual_scrap_pct), 2)

**max_work_ratio** — Worst overrun on the order
ROUND(MAX(work_ratio_vs_standard), 3)

**total_scrap_qty** — Total scrapped quantity on the order
SUM(ActualScrapQty)

**anomalous_work_centers** — Which machines are driving the risk
Sorted, de-duped list of WorkCenterName where operation_anomaly_score ≥ 30 (ARRAY_JOIN + COLLECT_SET)

**primary_root_cause** — The single most-severe cause on the order
CASE by severity precedence: Work Overrun (score ≥ 50) → High Scrap (≥ 40) → Final Acceptance Failure (≥ 15) → 'Normal'

### Intelligence columns (the per-order verdict)

**otif_risk_score** — 0–100 order-level OTIF risk
LEAST(100, schedule component [delay_days * 4, capped at 40] + anomaly component [max_anomaly_score * 0.6]), rounded to INT

**is_at_risk** — Predictive flag: open order already showing trouble
CASE: delivery_status = 'In Progress' AND max_anomaly_score ≥ 30 → true; else false

**risk_tier** — Human-readable bucket for reporting
CASE: 'Late' → 'Breached'; In Progress & score ≥ 40 → 'High Risk'; ≥ 20 → 'Medium Risk'; > 0 → 'Low Risk'; 'On Time' → 'Completed'; else 'Normal'
