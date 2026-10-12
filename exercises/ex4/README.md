# Exercise 4 - Build a Joule Agent on the Golden Record

In this exercise, you will build a Joule agent grounded on the `gold.otif_risk_enriched` golden record from Exercise 3. The agent lets a production planner ask questions in natural language and get trustworthy, explainable answers — because it is grounded on governed, lineage-tracked data, not a black box.

This is the payoff of the whole stack: context-rich AI on top of a trusted golden record.

## Exercise 4.1 Create the agent and connect its data context

After completing these steps you will have an agent that can read the golden OTIF record.

1. In Joule, open the Agent Builder and create a new agent named `OTIF Risk Advisor`.
<br>![Creating a new agent in Joule Agent Builder](/exercises/ex4/images/04_01_0010.png)

2. Add a data context / tool that points at the Dremio `gold.otif_risk_enriched` view (via the Dremio connection configured for your lab). This is the primary source the agent reasons over. Optionally, add the supplementary shopfloor context (see note below) so the agent can speak to capacity and OEE in detail.

3. Give the agent its grounding instructions:
```text
You are an OTIF (on-time-in-full) risk advisor for a manufacturing operation.
Answer only from the gold.otif_risk_enriched dataset in Dremio.
Each row is one production order, with its delivery_status, otif_risk_score (0-100),
risk_tier (Breached / High Risk / Medium Risk / Low Risk / Completed / Normal),
is_at_risk flag, primary_root_cause (Work Overrun / High Scrap / Final Acceptance
Failure / Normal), the anomalous_work_centers driving it, and the non-SAP shopfloor
signals avg_oee and unplanned_downtime_minutes for the worst work center.
When you flag an order, always cite the ProductionOrder, the plant, the
primary_root_cause, the anomalous_work_centers, and the figures that drove the
conclusion. If the data does not support an answer, say so.
```

   > **Supplementary context (optional):** the `data/mes_synthetic_data` dataset holds a self-contained shopfloor OEE / capacity-recovery scenario (OEE time-series, free-capacity projection, proposed recovery lots). Point a second read-only tool at it (or its `mes_synthetic_data.json` fixture) when you want the agent to go deeper on "do we have the capacity to recover?" questions. Keep it clearly separate from the governed OTIF record — it is shopfloor planning context, not a BDC data product.

## Exercise 4.2 Ask the agent OTIF-risk questions

After completing these steps you will have validated the agent end-to-end.

1. Ask the agent a direct question and confirm it answers from the golden record:
```text
Which production orders are at HIGH risk of missing OTIF right now, and why?
```
<br>![Joule agent answering a HIGH-risk question with citations](/exercises/ex4/images/04_02_0010.png)

2. Ask a question that forces it to combine the SAP and non-SAP signals it inherited through the golden record:
```text
For the orders flagged "Final Acceptance Failure", which work centers are driving it,
and what is their OEE and unplanned downtime? Should I expect more slippage?
```

3. Ask a "so what should I do" question to show reasoning over the trusted data:
```text
Rank the top 5 production orders I should intervene on this week by otif_risk_score,
name the machine to look at for each, and explain the trade-off.
```

   > Why this matters (showcase point): the agent is only as good as its grounding. Because it sits on a governed golden record with lineage back to SAP data products — and the non-SAP MES signals conformed into it — every answer is explainable and auditable, the opposite of an ungrounded chatbot. Swap in a better Silver threshold in ex3 and the agent immediately reasons on better data.

## Screenshots to capture (for authors)

- [ ] `04_01_0010.png` — New agent creation in Joule Agent Builder
- [ ] `04_01_0020.png` — Agent data context pointed at `gold.otif_risk_enriched`
- [ ] `04_02_0010.png` — Agent answering the HIGH-risk question with citations
- [ ] `04_02_0020.png` — Agent answering the combined SAP + non-SAP (root cause / OEE) question

## Summary

You've built an AI agent that answers manufacturing delivery-risk questions from a trusted, governed golden record spanning SAP and non-SAP data. Finally, you will step back and look at the whole picture.

Continue to - [Exercise 5 - Showcase & Wrap: Lineage, Governance, Value](../ex5/README.md)
