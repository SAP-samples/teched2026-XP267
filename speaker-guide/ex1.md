# Speaker Guide — Exercise 1: Build the Golden Records

**~15 min — the heart of the session.** Student doc: [`exercises/ex1`](../exercises/ex1/README.md)

## Goal
Build the primary golden records: resolve a non-SAP CRM to governed SAP customers (`v_crm_account_resolved`), roll SAP sales lines up to a per-customer OTIF truth (`v_customer_otif`), and join them into the CRM 360 account product (`v_crm_account_360`) that proves the churn ↔ delivery link — all materialized with Raw Reflections. The OTIF manufacturing medallion (`otif_production` → `otif_risk`) is a separate optional add-on ([`exercises/ex1/optional`](../exercises/ex1/optional/README.md)), only if time permits.

## The narrative arc
1. **Sourcing**: `customer`, `salesorderitem` are governed BDC data products, pre-loaded into Dremio (`"teched_labs_sandbox"."sap_dp".*`); the CRM export is read-only under `"non_sap".*`. (Presenter-only: no live BDC connection in the lab — nothing can fail live.)
2. **CRM resolution (1.1)**: a non-SAP CRM export with messy names and no SAP key. Resolve names → SAP customers (regex fuzzy + golden crosswalk; `match_method` records which path won), and roll SAP lines up to per-customer OTIF (`v_customer_otif`). These two views are Exercise 2's required inputs.
3. **CRM 360 + materialize (1.2)**: join CRM account → resolved customer → OTIF → cases → `v_crm_account_360`. Dremio has no `MATERIALIZED VIEW` — it's `CREATE VIEW` + a Raw Reflection (the only physical thing; the view stays the single source of truth). Enable reflections on `v_customer_otif` and `v_crm_account_360`. The payoff is the gradient: At Risk ≈ 79% OTIF / NPS −21 / ~13 open cases; Healthy ≈ 93% / +25 / ~2. Validated-live SQL — safe to run on screen. The complete runnable DDL is inlined step-by-step in the ex1 student doc.
4. **OTIF (optional, advanced)**: the manufacturing risk medallion, deterministic SQL, no ML — now a separate add-on doc at [`exercises/ex1/optional`](../exercises/ex1/optional/README.md); only if time permits, and the most likely live-failure point.

## Must-say points
- **The `EA` gotcha**: metric/quantity columns are strings and some rows hold a unit token (`EA`), so a plain `CAST` errors. The `REGEXP_LIKE` guard casts only numeric-looking values. Say it — it's the most likely live failure in the OTIF rollup.
- **Quoted mixed-case aliases** preserve the mixed-case names (`"Customer"`); once quoted, queries are case-sensitive.
- **View, not copy**: change a threshold → every downstream consumer updates. No pipeline re-run.
- **The link is discovered, not assumed**: the churn ↔ delivery gradient falls out of *joining* CRM churn signals to SAP OTIF — we never label it in the data.
- **`match_method` is the honest MDM boundary**: `fuzzy_auto` is what a few regex resolved on their own; `mdm_resolved` / `ambiguous_needs_mdm` are what only a real MDM (golden crosswalk) could settle.

## Gotchas (rehearse these)
- The OTIF optional add-on ([`exercises/ex1/optional`](../exercises/ex1/optional/README.md)) is validated live — all six steps run on the lab Dremio. String-aggregation is the one build-specific spot: `SET_UNION` is 2-arg and `COLLECT_SET` is unavailable there, so the doc uses `LISTAGG(DISTINCT …) WITHIN GROUP (ORDER BY …)`. Quantity columns import as text, so the medallion casts to `DOUBLE` before arithmetic. The CRM (1.1/1.2) SQL *was* validated live 2026-10-13.
- Reflection DDL / refresh-policy syntax varies by Dremio build — have the UI path ready as a fallback.

## Transition
"A governed, materialized CRM 360 golden record that proves our delivery drives churn. Next, another team builds an ontology on top — then we put an agent on it."
