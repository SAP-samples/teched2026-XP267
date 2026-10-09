# Exercise 4 - Build a Joule Agent on the Golden Record

In this exercise, you will build a Joule agent grounded on the `gold.inventory_risk` golden record from Exercise 3. The agent lets a supply-chain planner ask questions in natural language and get trustworthy, explainable answers — because it is grounded on governed, lineage-tracked data, not a black box.

This is the payoff of the whole stack: context-rich AI on top of a trusted golden record.

## Exercise 4.1 Create the agent and connect its data context

After completing these steps you will have an agent that can read the golden inventory record.

1. In Joule, open the Agent Builder and create a new agent named `Inventory Risk Advisor`.
<br>![Creating a new agent in Joule Agent Builder](/exercises/ex4/images/04_01_0010.png)

2. Add a data context / tool that points at the Dremio `gold.inventory_risk` view (via the Dremio connection configured for your lab). This is the single source the agent is allowed to reason over.

3. Give the agent its grounding instructions:
```text
You are an inventory risk advisor for a supply chain team.
Answer only from the gold.inventory_risk dataset in Dremio.
Each row is one material at one plant, with current stock, in-transit quantity,
late shipment count, average warehouse temperature, and a stockout_risk flag
(HIGH / MEDIUM / LOW).
When you flag a risk, always cite the material_number, plant, and the figures
that drove the conclusion. If the data does not support an answer, say so.
```

## Exercise 4.2 Ask the agent inventory-risk questions

After completing these steps you will have validated the agent end-to-end.

1. Ask the agent a direct question and confirm it answers from the golden record:
```text
Which materials are at HIGH stockout risk right now, and why?
```
<br>![Joule agent answering a HIGH-risk question with citations](/exercises/ex4/images/04_02_0010.png)

2. Ask a question that forces it to combine the SAP and non-SAP signals it inherited through the golden record:
```text
For plant 1010, which at-risk materials have no incoming shipments
and are also sitting in a warehouse running above 25°C?
```

3. Ask a "so what should I do" question to show reasoning over the trusted data:
```text
Rank the top 5 materials I should expedite this week and explain the trade-off.
```

   > Why this matters (showcase point): the agent is only as good as its grounding. Because it sits on a governed golden record with lineage back to SAP data products, every answer is explainable and auditable — the opposite of an ungrounded chatbot. Swap in a better Silver rule in ex3 and the agent immediately reasons on better data.

## Screenshots to capture (for authors)

- [ ] `04_01_0010.png` — New agent creation in Joule Agent Builder
- [ ] `04_01_0020.png` — Agent data context pointed at `gold.inventory_risk`
- [ ] `04_02_0010.png` — Agent answering the HIGH-risk question with citations
- [ ] `04_02_0020.png` — Agent answering the combined SAP + non-SAP question

## Summary

You've built an AI agent that answers supply-chain questions from a trusted, governed golden record spanning SAP and non-SAP data. Finally, you will step back and look at the whole picture.

Continue to - [Exercise 5 - Showcase & Wrap: Lineage, Governance, Value](../ex5/README.md)
