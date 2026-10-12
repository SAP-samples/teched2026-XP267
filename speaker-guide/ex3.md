# Speaker Guide — Exercise 3: Medallion Silver → Gold

**~15 min — the heart of the session.** Student doc: [`exercises/ex3`](../exercises/ex3/README.md)

## Goal
Build `silver.otif_production` (per-operation, enriched) → `gold.otif_risk` (per-order verdict) → `gold.otif_risk_enriched` (adds the non-SAP shopfloor signal). Accelerate with a reflection.

## The narrative arc
1. **Silver** harmonizes the 3 SAP products into one per-operation row and derives anomaly signals (`delivery_status`, `actual_scrap_pct`, `work_ratio_vs_standard`, `root_cause_tag`, `operation_anomaly_score`).
2. **Gold** keeps the **worst** operation per order ("an order is only as healthy as its worst operation") → `otif_risk_score`, `is_at_risk`, `risk_tier`, `primary_root_cause`, `anomalous_work_centers`.
3. **Gold-enriched** joins the non-SAP MES (`oee_snapshot` + `downtime_event`) to the SAP work center via `ground_truth_xref`. **This is the SAP+non-SAP payoff.**

## Must-say points
- **No ML.** Every score is deterministic hand-authored SQL — `CASE` statements and thresholds. "Predictive" = a rule firing early on open orders, not a trained model. This is the single most important clarification; say it twice.
- The medallion mirrors the reference in `data/otif-medallion` (there it's Spark SQL on Databricks; here Dremio views). The reference is **SAP-only** — we *add* the non-SAP join to unify the worlds, which is the exercise's extra value.
- **View, not copy**: change a Silver threshold → Gold + agent update instantly. The reflection is the only physical thing.

## Gotchas (rehearse these)
- **Array functions**: the Gold `anomalous_work_centers` uses `ARRAY_SORT`/`SET_UNION`; the Databricks reference uses `ARRAY_JOIN(COLLECT_SET(...))`. Syntax varies by Dremio build — have the engine-correct form ready. This is the most likely live failure.
- The silver→gold join on `operation_anomaly_score = max_anomaly_score` picks the worst operation; if ties exist, more than one work center may surface — fine, narrate it.

## Transition
"One governed record that answers 'will it miss OTIF, and why', spanning both worlds. Now let an agent reason over it."
