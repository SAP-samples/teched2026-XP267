# Speaker Guide — Exercise 2: Ontologies on the Golden Record

**Timing TBD — placeholder.** Student doc: [`exercises/ex2`](../exercises/ex2/README.md)

## Status
**Authored by a separate team.** This guide is a placeholder until that content lands.

## What it covers
Building an ontology on top of the materialized CRM-track views from Exercise 1 (`v_customer_otif` and `v_crm_account_resolved`), alongside the raw SAP and non-SAP CRM source tables — the semantic bridge between the golden records (Exercise 1) and the Joule agent (Exercise 3).

## Hand-off facts for the ontology team
- Inputs: `"teched_labs_sandbox"."hands-on-test"."ex1".v_customer_otif` and `...v_crm_account_resolved`, each materialized via a Raw Reflection in Exercise 1, plus the shared read-only source tables under `sap_dp.*` and `non_sap.*`.
- Grain: `v_customer_otif` is one row per `Customer` (per-customer OTIF: `otif_pct`, `pct_on_time`, `pct_in_full`, `late`/`short`); `v_crm_account_resolved` is the Account → Customer crosswalk with `match_method`.
- Downstream: Exercise 3's agent grounds on the ontology built here (whose `v_crm_account_360` golden account product unifies these).

## Transition
"With the CRM 360 golden record modeled as an ontology — the churn ↔ delivery link made semantic — we can ground an agent that speaks the business's language."
