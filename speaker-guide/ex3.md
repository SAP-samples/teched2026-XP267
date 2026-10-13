# Speaker Guide — Exercise 3: Joule Agent on the Golden Record

**~10 min.** Student doc: [`exercises/ex3`](../exercises/ex3/README.md)

## Goal
Create the `Order Fulfillment Advisor` Joule agent grounded on `v_customer_order_fulfillment` (primary) and ask it Sales/CRM fulfillment questions. OTIF (`"teched_labs_sandbox"."hands-on-test"."ex1".otif_risk`) is optional secondary grounding.

## Talking points
- The agent is **only as good as its grounding**. It answers *only* from the governed golden record — explainable and auditable, the opposite of an ungrounded chatbot.
- Every answer cites `Customer` / `CustomerName`, `Material`, `Plant`, `coverage_status`, and the figures (`req_qty` vs `po_qty`, `coverage_ratio`) — because the golden record carries them.
- The closing loop: change the coverage threshold in Exercise 1 → the agent immediately reasons on better data. Grounding + lineage back to BDC data products, not retraining.

## The demo questions and what to expect
1. *"Which customers have orders under-covered or with no supply, and why?"* → lists rows where `coverage_status` is `under_covered` / `demand_no_supply`, with the figures.
2. *"Rank the top 5 customers by fulfillment risk (lowest coverage_ratio), with Country, Industry, materials at risk."* → prioritized list using the inherited customer context. **The money shot for Sales/CRM.**
3. *(Secondary / OTIF)* *"Which production orders are at HIGH risk of missing OTIF, and why?"* → only if the OTIF tool was attached; shows the agent spans both golden records.

## Gotchas
- If the agent answers from general knowledge instead of the data, the grounding instruction or the Dremio tool binding is wrong. Re-paste the system prompt verbatim.
- Keep questions scoped to columns that exist in `v_customer_order_fulfillment` — out-of-scope asks invite hallucination; use them to demo the "if the data doesn't support it, say so" behavior.

## Transition
"Trustworthy, cited answers on a governed golden record sourced from BDC data products. That's the session."
