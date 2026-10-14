# Exercise 2 - Ontologies on the Golden Record (coming soon)

In this exercise, you will build a semantic ontology on top of the golden record produced in Exercise 1 — turning the materialized `v_customer_order_fulfillment` view into business concepts and relationships that the Joule agent in Exercise 3 can reason over.

This connects the two halves of the session: Exercise 1 produces the trusted, materialized golden record; Exercise 3 grounds an agent on it. The ontology built here is the bridge between them — the shared vocabulary (customers, orders, materials, suppliers, coverage/fulfillment status) that makes the agent's answers precise and explainable.

> **Placeholder — content to be provided by the ontology team.**
>
> This exercise is authored by a separate team and will be added before the session. It will cover building an ontology on top of the materialized view `"teched_labs_sandbox"."hands-on-test"."ex1".v_customer_order_fulfillment` from Exercise 1.

## What this exercise will cover (outline)

- Modeling the fulfillment golden record as an ontology (entities, attributes, relationships).
- Mapping the materialized view's columns to ontology concepts.
- Exposing the ontology so the Exercise 3 agent can ground on it.

## Prerequisites

- Exercise 1 completed: `v_customer_order_fulfillment` exists in Dremio and its Raw Reflection is enabled.

Continue to - [Exercise 3 - Build a Joule Agent on the Golden Record](../ex3/README.md)
