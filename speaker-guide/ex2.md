# Speaker Guide — Exercise 2: Ontologies on the Golden Record

**Timing TBD — placeholder.** Student doc: [`exercises/ex2`](../exercises/ex2/README.md)

## Status
**Authored by a separate team.** This guide is a placeholder until that content lands.

## What it covers
Building an ontology on top of the materialized `v_customer_order_fulfillment` view from Exercise 1 — the semantic bridge between the golden record (Exercise 1) and the Joule agent (Exercise 3).

## Hand-off facts for the ontology team
- Input: `"teched_labs_sandbox"."sap_dp".v_customer_order_fulfillment`, materialized via a Raw Reflection in Exercise 1.
- Grain: one row per `Customer` + `Material` + `Plant`, with demand/supply figures, `coverage_ratio`, `coverage_status`, and customer context (`CustomerName`, `Country`, `Industry`, `CustomerClassification`).
- Downstream: Exercise 3's agent grounds on the same view.

## Transition
"With the fulfillment concepts modeled as an ontology, we can ground an agent that speaks the business's language."
