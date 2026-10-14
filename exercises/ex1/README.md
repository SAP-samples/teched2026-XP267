# Exercise 1 - Build the Golden Records in Dremio

In this exercise, you will refine governed SAP data into trusted golden records using layered SQL views in Dremio, and accelerate them with reflections — this is the "ELT" in the modern stack: transformation as semantics, not pipeline jobs.

> **The data-product lens (applies across these exercises).** The view you build and materialize in your space is a "current product truth" proxy. The direction of travel in the SAP Business Data Cloud Lakehouse is that curated assets like this become Primary Data Products — governed, discoverable, contract-bound — which downstream consumers, and Joule, turn into derived data products on demand, from intent. The Dremio mechanics you use here — engines for compute, reflections for acceleration — persist into that story. Today you model the product truth in SQL; tomorrow you publish it as a data product.

You will build two tracks:

- **Primary — Customer Order Fulfillment (Sales / CRM).** A golden customer order-fulfillment record that blends sales demand, purchasing supply, and customer master data into one business-ready view, materialized for downstream use. This is the record Exercise 2 builds an ontology on, and Exercise 3 grounds a Joule agent on.
- **Secondary — Non-SAP CRM resolution & the churn ↔ delivery link.** Bring a 3rd-party CRM export into the lakehouse, resolve its messy account names to governed SAP customers, and join your real per-customer OTIF so you can *prove* that at-risk renewals are driven by your own delivery performance — a second golden record (`v_crm_account_360`) the agent can also reason over.

> **Advanced / optional:** an OTIF manufacturing medallion (silver → gold production-risk record) is kept as an appendix at the end of this exercise for attendees who want a deterministic shopfloor track. It is not part of the main flow.

## Where the data comes from (and why we query it in Dremio)

The SAP tables you use here — `customer`, `salesorderitem`, `purchaseorderitem` (and the production/work-center data for the OTIF track) — originate as governed SAP S/4HANA data products in SAP Business Data Cloud (BDC): meaningful field names, business semantics, and a defined contract, not raw tables.

For this hands-on lab those data products have been exported and pre-loaded into Dremio, where you query them as tables under `"teched_labs_sandbox"."sap_dp"`:

- `"teched_labs_sandbox"."sap_dp".customer`
- `"teched_labs_sandbox"."sap_dp".salesorderitem`
- `"teched_labs_sandbox"."sap_dp".purchaseorderitem`

> **Why not read BDC live?** The sourcing story is still BDC data products — that is where this governed data is born and where lineage leads back to. We query the exported copies in Dremio so the hands-on session has no live-connection dependency on BDC during the demo. Narrate the BDC origin; run the SQL against Dremio.

## Exercise 1.1 Build the Customer Order Fulfillment golden record

> **Where your objects land:** every view you create in this exercise is written to this exercise's folder, `"teched_labs_sandbox"."hands-on-test"."ex1"`. The source tables stay in `"teched_labs_sandbox"."sap_dp"` — you only *read* those. The `hands-on-test/ex1` folder is pre-created for the lab; if it is missing, create it in the Dremio UI first (`CREATE VIEW` will not create the parent folders).
>
> In the full lab each attendee builds their own copy in their own space — the golden record is *your* product truth to own and, in the data-product future, publish. This shared `ex1` folder holds the reference build.

After completing these steps you will have one business-ready view, one row per customer + material + plant, that compares what customers ordered (demand) against what purchasing secured (supply), enriched with customer context.

Before building anything, run three quick `SELECT`s to see the raw data you're about to combine — this is where the demand, the supply, and the customer context each come from.

1. **Look at sales-order demand.**

   *Each row is one sales-order line — the customer (`SoldToParty`), what they want (`Material`, `Plant`), and how much (`RequestedQuantity`). Notice the quantity is stored as text, not a number.*

```sql
SELECT SoldToParty, Material, Plant, RequestedQuantity, OrderQuantity
FROM "teched_labs_sandbox"."sap_dp".salesorderitem
LIMIT 20;
```

   > **You should see:** one row per sales-order line. `RequestedQuantity` comes back as a string, and some rows carry a unit token like `EA` instead of a number — remember this, it's why the build below needs a guarded cast.

2. **Look at purchasing supply.**

   *Each row is one purchase-order line — the `Material`/`Plant` being procured, the `OrderQuantity`, and the `Supplier` who provides it.*

```sql
SELECT Material, Plant, OrderQuantity, Supplier
FROM "teched_labs_sandbox"."sap_dp".purchaseorderitem
LIMIT 20;
```

   > **You should see:** supply keyed by the same `Material` + `Plant` as the demand above — that pair is the join key. `OrderQuantity` is again a string with occasional unit tokens.

3. **Look at the customer master.**

   *One row per customer — the context columns (`CustomerName`, `Country`, `Industry`, `CustomerClassification`) you'll attach to every fulfillment row.*

```sql
SELECT Customer, CustomerName, Country, Industry, CustomerClassification
FROM "teched_labs_sandbox"."sap_dp".customer
LIMIT 20;
```

   > **You should see:** one row per customer. `Customer` here is the key that matches `SoldToParty` from the sales orders — that's how customer context gets joined on.

4. **Build the fulfillment view.** Now combine the three: aggregate sales-order demand and purchase-order supply per `Material` + `Plant`, join the customer master for context, and derive a coverage ratio and a fulfillment verdict.

```sql
CREATE VIEW "teched_labs_sandbox"."hands-on-test"."ex1".v_customer_order_fulfillment AS
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

5. Preview the golden record and work the gaps first — customers whose demand is not covered by supply:

```sql
SELECT "Customer", "CustomerName", "Country", "Industry",
       "Material", "Plant", "req_qty", "po_qty",
       "coverage_ratio", "coverage_status"
FROM "teched_labs_sandbox"."hands-on-test"."ex1".v_customer_order_fulfillment
WHERE "coverage_status" IN ('demand_no_supply', 'under_covered')
ORDER BY "coverage_ratio" NULLS FIRST
LIMIT 50;
```
<br>![v_customer_order_fulfillment preview sorted by coverage](/exercises/ex1/images/01_01_0020.png)

> Note: output column names are double-quoted to preserve the capitalized Databricks-style names (`Material`, `Plant`, `Customer`, …). Once quoted, later references are case-sensitive — query them as `"Material"`, not `material`.

## Exercise 1.2 Materialize the golden record for downstream use

After completing these steps the fulfillment golden record will be physically accelerated so Exercise 2's ontology and Exercise 3's agent get fast, stable responses.

Dremio has no `CREATE MATERIALIZED VIEW` statement — you create a regular view (above) and enable a Reflection on it. The reflection is the physically stored, auto-maintained copy that Dremio transparently substitutes to accelerate queries; you keep querying the view by name.

1. Enable a Raw Reflection on the view. In the Dremio UI, open `v_customer_order_fulfillment` → Reflections → toggle on Raw Reflection. Or via SQL:

```sql
ALTER DATASET "teched_labs_sandbox"."hands-on-test"."ex1".v_customer_order_fulfillment
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
ALTER DATASET "teched_labs_sandbox"."hands-on-test"."ex1".v_customer_order_fulfillment
SET REFRESH EVERY '1' HOUR;
```

> Why this matters (showcase point): the golden record is a view, not a copy. Change the coverage threshold and every downstream consumer — the ontology in Exercise 2, the agent in Exercise 3 — reflects it immediately. The reflection gives physical speed without giving up the single logical source of truth. This is the "current product truth" proxy for a Primary Data Product: the same asset that, published in the BDC Lakehouse, Joule would turn into derived products from intent. This materialized `v_customer_order_fulfillment` is the hand-off to Exercise 2, where another team builds an ontology on top of it.

## Exercise 1.3 Resolve a non-SAP CRM & prove the churn ↔ delivery link

Real businesses don't run on SAP alone. Here you bring in a non-SAP source — a 3rd-party CRM export — resolve its accounts to your SAP customers, and build a second golden record that answers one cross-domain money question:

> *"Are our at-risk renewals being driven by our own delivery performance?"*

The CRM is the system of record for the relationship: accounts, the cases they open when something goes wrong (Delivery Delay, Short Shipment), and the renewals your reps are working. SAP is the system of record for the transaction — how well you actually delivered. The link between them is *planted but not labelled*: worse SAP delivery (OTIF) shows up as more cases and higher churn risk. You'll surface that link by joining, not by assuming it.

Three gaps stand between the two systems, and the build closes each one:

1. **No shared key.** CRM has company *names* (messy — legal suffixes, abbreviations, typos); SAP has customer *numbers*. You resolve one to the other.
2. **No comparable metric.** OTIF lives at the sales-order *line*; the CRM lives at the *account*. You roll SAP lines up to a per-customer OTIF truth.
3. **The real question is cross-domain** and needs both worlds joined.

> **This is a condensed walkthrough.** The full, line-by-line build — including the "see why fuzzy matching only gets you so far" detour and the MDM narrative — lives in the **extended** companion [Exercise (CRM)](../ex-crm/README.md), with the complete validated DDL in [`crm_resolution_and_360.sql`](../ex-crm/crm_resolution_and_360.sql). Below is the short path.

You build three views (same pattern as 1.1: read-only SAP + CRM sources in, golden record out, materialized by a reflection). For consistency with 1.1/1.2 the objects land in `"teched_labs_sandbox"."hands-on-test"."ex1"`; the CRM sources are shared and read-only under `"teched_labs_sandbox"."non_sap"`.

| View | What it is |
|---|---|
| `v_customer_otif` | Per-customer OTIF truth, rolled up from SAP sales-order lines (the SAP-side metric). |
| `v_crm_account_resolved` | The **Account → Customer crosswalk** — the resolution/MDM step, with a `match_method` recording *how* each account resolved (`fuzzy_auto` vs `mdm_resolved` vs `ambiguous_needs_mdm`). |
| `v_crm_account_360` | The **ontology-ready golden account product**: CRM + resolved SAP customer + OTIF + case counts. This is the one you materialize. |

1. **Look at what you're connecting.** The CRM accounts (messy names, a `churn_risk`, a `renewal_date`, no SAP key) and the cases (the voice of the customer, dominated by delivery complaints):

```sql
SELECT crm_account_id, account_name, segment, churn_risk, nps, renewal_date
FROM "teched_labs_sandbox"."non_sap".crm_account
LIMIT 20;

SELECT category, status, COUNT(*) n
FROM "teched_labs_sandbox"."non_sap".crm_case
GROUP BY category, status ORDER BY n DESC;
```

   > **You should see** account names that are clean (`US Large Cycles 5`), suffixed (`USC1 Inc.`), or mistyped (`CA Specialty Cyales 5 Ltd.`) — and no SAP customer number. Cases are dominated by Delivery Delay and Short Shipment, each with a `related_sales_order` pointing back at a real SAP order. Every CRM value imports as text (`nps` comes back as `'-21'`), so the same guarded-cast pattern from 1.1 applies.

2. **Build the three views.** The full DDL is in [`crm_resolution_and_360.sql`](../ex-crm/crm_resolution_and_360.sql) — run it against your target folder (substitute `"teched_labs_sandbox"."hands-on-test"."ex1"` for `<your_space>`). In short:
   - `v_customer_otif` rolls `salesorderitem` up per `SoldToParty` into `otif_pct`, `pct_on_time`, `pct_in_full`, `late`/`short` counts (windowed to `RequestedDeliveryDate >= '2023-01-01'`, where committed dates are populated).
   - `v_crm_account_resolved` normalizes names with a few regex rules (upper-case, punctuation → space, strip legal suffixes) to auto-resolve the easy names, then defers the rest to the golden crosswalk `crm_account_resolution_xref` — recording the winning path in `match_method`. That split is the honest boundary between "a few regex" and "a real MDM."
   - `v_crm_account_360` joins CRM account → resolved customer → `v_customer_otif` → case counts, with the guarded cast on the text columns (`CASE WHEN REGEXP_LIKE(nps, '^-?[0-9]+$') THEN CAST(nps AS INTEGER) END`).

3. **Materialize `v_crm_account_360`** with a Raw Reflection — same mechanic as 1.2 — so the ontology (Exercise 2) and agent (Exercise 3) get fast, stable responses off a single logical source.

4. **Prove the thread.** Delivery performance by churn tier — the link, surfaced by the join:

```sql
SELECT churn_risk, COUNT(*) accounts, ROUND(AVG(otif_pct),1) avg_otif,
       ROUND(AVG(nps),1) avg_nps, ROUND(AVG(open_cases),1) avg_open_cases
FROM "teched_labs_sandbox"."hands-on-test"."ex1".v_crm_account_360
GROUP BY churn_risk ORDER BY avg_otif;
```

   > **You should see** a clean gradient — At Risk ≈ 79% OTIF / NPS −21 / ~13 open cases; Watch ≈ 82% / +11 / ~6; Healthy ≈ 93% / +25 / ~2. The CRM's churn signal tracks SAP delivery performance — the relationship was discovered by the join, not assumed.

5. **The money query** — at-risk, high-value renewals, each with how it was resolved:

```sql
SELECT account_name, sap_customer_id, otif_pct, late_lines, open_cases,
       annual_contract_value, renewal_date, match_method
FROM "teched_labs_sandbox"."hands-on-test"."ex1".v_crm_account_360
WHERE churn_risk='At Risk' ORDER BY otif_pct ASC LIMIT 10;
```

   > **You should see** at-risk renewals worth real money, each with low OTIF, many late lines and open delivery cases — some resolved by `fuzzy_auto`, others only by `mdm_resolved`. That contrast *is* the MDM narrative on screen. This materialized `v_crm_account_360` is a second hand-off to Exercises 2 and 3, alongside the fulfillment record.

## Appendix (advanced, optional) — OTIF manufacturing medallion

> **Optional / advanced.** This track is not part of the main Exercise 1 flow — it's kept for attendees who want a deterministic shopfloor production-risk record (and it's the optional secondary context the Exercise 3 agent can use for manufacturing questions). It is also the most likely live-failure point in this lab (the `ARRAY_SORT`/`SET_UNION` array functions — see the note at the end). Skip it unless you have time.

This track keeps the on-time-in-full production-risk golden record so the agent in Exercise 3 can also answer shopfloor-delivery questions, rebuilt here as Dremio views. Every score and flag is deterministic SQL — hand-authored `CASE` statements and thresholds, no ML model. "Predictive" means a rule that fires early on open orders, before the due date.

As before, look at the raw manufacturing data first, then build.

1. **Look at production orders and their operations.**

   *Each production order (`productionorder`) has one or more operations (`productionorderoperation`). Scheduled vs actual end dates drive lateness; planned vs confirmed/scrap quantities drive the anomaly signals.*

```sql
SELECT po.ProductionOrder, po.OrderScheduledEndDate, po.OrderActualEndDate,
       op.ProductionOrderOperation, op.WorkCenterInternalID,
       op.OpPlannedTotalQuantity, op.OpTotalConfirmedScrapQty
FROM "teched_labs_sandbox"."sap_dp".productionorder          AS po
JOIN "teched_labs_sandbox"."sap_dp".productionorderoperation AS op
  ON po.ProductionOrder = op.ProductionOrder
LIMIT 20;
```

   > **You should see:** several operation rows per production order. A NULL `OrderActualEndDate` means the order is still in progress — those are the open orders the risk rules fire on *before* the due date (the "predictive" part).

2. **Look at the work-center master.**

   *The work-center master names each machine (`WorkCenterName`) by its `WorkCenterInternalID` — the label that makes the risk record human-readable.*

```sql
SELECT WorkCenterInternalID, WorkCenterName
FROM "teched_labs_sandbox"."sap_dp".workcenter
LIMIT 20;
```

   > **You should see:** one row per work center. `WorkCenterInternalID` is the key the Silver view joins on to attach each machine's name.

3. **Build the Silver layer** — one harmonized, enriched row per production-order operation:

```sql
-- Silver: one harmonized, enriched row per production-order operation
CREATE VIEW "teched_labs_sandbox"."hands-on-test"."ex1".otif_production AS
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

4. Build the Gold golden OTIF record — one row per production order, keeping the *worst* operation signals:

```sql
-- Gold: the golden OTIF risk record (one row per production order)
CREATE VIEW "teched_labs_sandbox"."hands-on-test"."ex1".otif_risk AS
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
    FROM "teched_labs_sandbox"."hands-on-test"."ex1".otif_production
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

5. Preview the Gold risk record — the at-risk open orders, worst first. This is the shopfloor half of what the agent answers in Exercise 3:

```sql
SELECT ProductionOrder, risk_tier, otif_risk_score,
       primary_root_cause, anomalous_work_centers
FROM "teched_labs_sandbox"."hands-on-test"."ex1".otif_risk
WHERE delivery_status = 'In Progress'
ORDER BY otif_risk_score DESC
LIMIT 20;
```

   > **You should see:** open production orders ranked by `otif_risk_score`, each with a `risk_tier`, a `primary_root_cause`, and the `anomalous_work_centers` driving the risk — the deterministic, explainable verdict (no ML).

6. Accelerate the Gold layer with a Raw Reflection too (same pattern as 1.2), so the agent gets fast responses.

> Why this matters (showcase point): change a Silver threshold and the Gold verdict updates — no pipeline to re-run. (Note: `ARRAY_SORT` / `SET_UNION` syntax varies by engine — if your Dremio build differs, substitute the equivalent array-aggregation function; the reference Databricks logic uses `ARRAY_JOIN(COLLECT_SET(...))`.)

## Screenshots to capture (for authors)

- [ ] `01_01_0010.png` — `v_customer_order_fulfillment` view defined
- [ ] `01_01_0020.png` — `v_customer_order_fulfillment` preview sorted by `coverage_ratio`
- [ ] `01_02_0010.png` — Raw reflection enabled on the fulfillment view
- [ ] `01_03_0010.png` — CRM raw previews (`crm_account`, `crm_case`) and the name-normalization SELECT (matched vs unmatchable)
- [ ] `01_03_0020.png` — `v_crm_account_360` red-thread query (OTIF by churn tier) and the at-risk-renewals money query
- [ ] (appendix, optional) `01_0A_0010.png` — `"teched_labs_sandbox"."hands-on-test"."ex1".otif_risk` query result (OTIF manufacturing track)

> **Author note:** the fulfillment (1.1) and OTIF-appendix SQL have not been run against a live Dremio — validate before the session, especially the quantity-cast guard, the quoted mixed-case identifiers, and (OTIF appendix) the `ARRAY_SORT`/`SET_UNION` array functions. The CRM (1.3) SQL *was* built and validated live on 2026-10-13 (see the [Exercise (CRM)](../ex-crm/README.md) author note).

## Summary

You've built a golden customer order-fulfillment record (primary) and a CRM 360 golden account product (secondary) that resolves a non-SAP source to governed SAP customers and proves the churn ↔ delivery link — both as Dremio views accelerated by reflections, sourced from governed SAP BDC data products queried in Dremio. The materialized `v_customer_order_fulfillment` is the foundation Exercise 2 builds an ontology on; `v_crm_account_360` is the second hand-off. An optional OTIF manufacturing medallion appendix provides a deterministic shopfloor track for Exercise 3's secondary agent context.

Continue to - [Exercise 2 - Ontologies on the Golden Record](../ex2/README.md)
