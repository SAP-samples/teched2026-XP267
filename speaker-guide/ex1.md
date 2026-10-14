# Speaker Guide — Exercise 1: Build the Golden Records

**~15 min — the heart of the session.** Student doc: [`exercises/ex1`](../exercises/ex1/README.md)

## Goal
Build the primary Sales/CRM golden record `v_customer_order_fulfillment` (customer demand vs purchasing supply, with customer context) and materialize it with a Raw Reflection. Then build the secondary CRM 360 record (`v_crm_account_360`): resolve a non-SAP CRM to SAP customers and prove the churn ↔ delivery link. Keep the OTIF manufacturing medallion as an optional appendix (`otif_production` → `otif_risk`) only if time permits.

## The narrative arc
1. **Sourcing**: `customer`, `salesorderitem`, `purchaseorderitem` are governed BDC data products, exported and pre-loaded into Dremio (`"teched_labs_sandbox"."sap_dp".*`). Narrate BDC; query Dremio — no live BDC connection so nothing can fail live.
2. **Fulfillment golden record**: demand (sales) vs supply (purchasing) per Material+Plant, joined to customer master → `coverage_ratio` + `coverage_status`. This is the record Exercise 2 (ontology) and Exercise 3 (agent) build on.
3. **Materialize**: Dremio has no `MATERIALIZED VIEW` — it's `CREATE VIEW` + a Raw Reflection. The reflection is the only physical thing; the view stays the single source of truth.
4. **CRM resolution (secondary)**: a non-SAP CRM export with messy names and no SAP key. Resolve names → SAP customers (regex fuzzy + golden crosswalk, `match_method` records which path won), roll SAP lines up to per-customer OTIF, join cases → `v_crm_account_360`. The payoff is the gradient: At Risk ≈ 79% OTIF / NPS −21 / ~13 open cases; Healthy ≈ 93% / +25 / ~2. This is validated-live SQL — safe to run on screen. Full deep dive: `exercises/ex-crm`.
5. **OTIF (appendix, optional)**: the manufacturing risk medallion, deterministic SQL, no ML — only if time permits; it's the most likely live-failure point.

## Must-say points
- **The `EA` gotcha**: quantity columns are strings and some rows hold a unit token (`EA`), so a plain `CAST` errors. The `REGEXP_LIKE` guard = Databricks `try_cast`. Say it — it's the most likely live failure in the fulfillment track.
- **Quoted mixed-case aliases** preserve the Databricks-style names (`"Material"`, `"Customer"`); once quoted, queries are case-sensitive.
- **View, not copy**: change the coverage threshold → every downstream consumer updates. No pipeline re-run.
- **The link is discovered, not assumed** (CRM track): the churn ↔ delivery gradient falls out of *joining* CRM churn signals to SAP OTIF — we never label it in the data.
- **`match_method` is the honest MDM boundary**: `fuzzy_auto` is what a few regex resolved on their own; `mdm_resolved` / `ambiguous_needs_mdm` are what only a real MDM (golden crosswalk) could settle.

## Gotchas (rehearse these)
- Fulfillment (1.1) and the OTIF appendix are not yet validated on live Dremio — check the cast guard, quoted identifiers, and the OTIF `ARRAY_SORT`/`SET_UNION` array funcs (Databricks ref uses `ARRAY_JOIN(COLLECT_SET(...))`). The CRM (1.3) SQL *was* validated live 2026-10-13.
- Reflection DDL / refresh-policy syntax varies by Dremio build — have the UI path ready as a fallback.

## Transition
"Two governed, materialized golden records — order fulfillment and the CRM 360 that proves our delivery drives churn. Next, another team builds an ontology on top — then we put an agent on it."
