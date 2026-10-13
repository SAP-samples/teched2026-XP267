# Speaker Guide — Exercise 1: Build the Golden Records

**~15 min — the heart of the session.** Student doc: [`exercises/ex1`](../exercises/ex1/README.md)

## Goal
Build the **primary** Sales/CRM golden record `v_customer_order_fulfillment` (customer demand vs purchasing supply, with customer context) and materialize it with a Raw Reflection. Keep the **secondary** OTIF manufacturing medallion (`otif_production` → `otif_risk`, both created in `"teched_labs_sandbox"."hands-on-test"."ex1"`) as a second deterministic golden record.

## The narrative arc
1. **Sourcing**: `customer`, `salesorderitem`, `purchaseorderitem` are governed **BDC data products**, exported and pre-loaded into Dremio (`"teched_labs_sandbox"."sap_dp".*`). Narrate BDC; query Dremio — **no live BDC connection** so nothing can fail live.
2. **Fulfillment golden record**: demand (sales) vs supply (purchasing) per Material+Plant, joined to customer master → `coverage_ratio` + `coverage_status`. This is the record Exercise 2 (ontology) and Exercise 3 (agent) build on.
3. **Materialize**: Dremio has no `MATERIALIZED VIEW` — it's `CREATE VIEW` + a **Raw Reflection**. The reflection is the only physical thing; the view stays the single source of truth.
4. **OTIF (secondary)**: the manufacturing risk medallion, deterministic SQL, no ML.

## Must-say points
- **The `EA` gotcha**: quantity columns are strings and some rows hold a unit token (`EA`), so a plain `CAST` errors. The `REGEXP_LIKE` guard = Databricks `try_cast`. Say it — it's the most likely live failure.
- **Quoted mixed-case aliases** preserve the Databricks-style names (`"Material"`, `"Customer"`); once quoted, queries are case-sensitive.
- **View, not copy**: change the coverage threshold → every downstream consumer updates. No pipeline re-run.
- **No ML** (OTIF track): every score is hand-authored `CASE`/threshold SQL.

## Gotchas (rehearse these)
- SQL is **not yet validated on live Dremio** (author note in the exercise). Check the cast guard, quoted identifiers, and the OTIF `ARRAY_SORT`/`SET_UNION` array funcs (Databricks ref uses `ARRAY_JOIN(COLLECT_SET(...))`).
- Reflection DDL / refresh-policy syntax varies by Dremio build — have the UI path ready as a fallback.

## Transition
"One governed, materialized golden record of customer order fulfillment. Next, another team builds an ontology on top of it — then we put an agent on it."
