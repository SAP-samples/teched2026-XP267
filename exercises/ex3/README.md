# Exercise 3 - Build a Joule Agent on the Golden Record

In this exercise, you will build a Joule agent grounded on the golden records from Exercise 1 — primarily the materialized customer order-fulfillment record. The agent lets a sales or supply-chain planner ask questions in natural language and get trustworthy, explainable answers — because it is grounded on governed, lineage-tracked data, not a black box.

This is the payoff of the whole stack: context-rich AI on top of a trusted golden record.

## Exercise 3.1 Create the agent and connect its data context

After completing these steps you will have an agent that can read the golden fulfillment record.

1. In Joule, open the Agent Builder and create a new agent named `Order Fulfillment Advisor`.
<br>![Creating a new agent in Joule Agent Builder](/exercises/ex3/images/03_01_0010.png)

2. Add a data context / tool that points at the Dremio `"teched_labs_sandbox"."hands-on-test"."ex1".v_customer_order_fulfillment` view (via the Dremio connection configured for your lab). This is the primary source the agent reasons over. Optionally, add a secondary context so the agent can also answer a cross-domain question:
   - **CRM 360 (recommended):** `"teched_labs_sandbox"."hands-on-test"."ex1".v_crm_account_360` (from Exercise 1.3) — lets the agent answer *"which at-risk renewals are driven by our own delivery performance?"* with churn risk, OTIF, open cases and renewal value in one place.
   - **OTIF manufacturing (advanced):** `"teched_labs_sandbox"."hands-on-test"."ex1".otif_risk` — the shopfloor production-risk record from the Exercise 1 appendix, for manufacturing OTIF questions.

3. Give the agent its grounding instructions:
```text
You are an order-fulfillment advisor for a sales and supply-chain operation.
Answer only from the v_customer_order_fulfillment dataset in Dremio.
Each row is one customer + material + plant, with the customer's demand (req_qty,
so_lines), the matched purchasing supply (po_qty, po_lines, suppliers), the
coverage_ratio (po_qty / req_qty) and a coverage_status
(covered / under_covered / demand_no_supply / supply_only), plus customer context
(CustomerName, Country, Industry, CustomerClassification).
When you flag a fulfillment gap, always cite the Customer (and CustomerName), the
Material and Plant, the coverage_status, and the figures that drove the conclusion
(req_qty vs po_qty, coverage_ratio). If the data does not support an answer, say so.
```

   > **Secondary context (optional):** point a second read-only tool at `v_crm_account_360` (CRM renewals-at-risk, recommended) and/or `otif_risk` (manufacturing OTIF — production orders, risk_tier, primary_root_cause, anomalous_work_centers; from the Exercise 1 appendix). Keep each clearly separate from the fulfillment record.

## Exercise 3.2 Ask the agent fulfillment questions

After completing these steps you will have validated the agent end-to-end.

1. Ask the agent a direct question and confirm it answers from the golden record:
```text
Which customers have orders that are under-covered or have no supply at all, and why?
```
<br>![Joule agent answering an under-coverage question with citations](/exercises/ex3/images/03_02_0010.png)

2. Ask a question that forces it to use the customer context it inherited through the golden record:
```text
Rank the top 5 customers by fulfillment risk (lowest coverage_ratio first). For each,
name the Country and Industry, the materials at risk, and whether the gap is
'under_covered' or 'demand_no_supply'.
```

3. (Secondary) Ask a cross-domain question so the agent reasons over the secondary context you added:
   - **CRM 360:** `Which at-risk renewals have the worst delivery performance, and what's it costing us?`
   - **OTIF manufacturing (advanced):** `Which production orders are at HIGH risk of missing OTIF right now, and why?`

   > Why this matters (showcase point): the agent is only as good as its grounding. Because it sits on a governed golden record with lineage back to SAP BDC data products, every answer is explainable and auditable, the opposite of an ungrounded chatbot. Change a coverage threshold in Exercise 1 and the agent immediately reasons on better data.

## Screenshots to capture (for authors)

- [ ] `03_01_0010.png` — New agent creation in Joule Agent Builder
- [ ] `03_01_0020.png` — Agent data context pointed at `v_customer_order_fulfillment`
- [ ] `03_02_0010.png` — Agent answering the under-coverage question with citations
- [ ] `03_02_0020.png` — Agent answering the ranked fulfillment-risk question with customer context

## Summary

You've built an AI agent that answers order-fulfillment questions from a trusted, governed golden record sourced from SAP BDC data products — with the CRM 360 record (renewals-at-risk) and, optionally, the OTIF manufacturing record available as secondary context. Every answer traces back through the Dremio golden record to governed SAP data.

That's the session. Thank you for participating!

Return to - [Overview](../../README.md)
