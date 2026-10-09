# Exercise 5 - Showcase & Wrap: Lineage, Governance, Value

In this exercise, you will step back from building and look at the whole picture you created. This is the exec-showcase close: trace the end-to-end lineage, see the governance story, and articulate the business value.

No new objects are created here — you will inspect and narrate what you already built.

## Exercise 5.1 Trace end-to-end lineage

After completing these steps you will be able to prove where every answer the agent gives comes from.

1. In Dremio, open the `gold.inventory_risk` view and open its Lineage / Graph view. Walk the graph backward:
<br>![Dremio lineage graph for the gold inventory record](/exercises/ex5/images/05_01_0010.png)

   > The lineage should show, in one picture:
   > - `gold.inventory_risk` ← `silver.shipments_clean` + `silver.plant_conditions` ← `bronze.shipments` / `bronze.sensors` (Iceberg on S3), and
   > - `gold.inventory_risk` ← the BDC data products (Material Master, Stock on Hand) with lineage continuing back into SAP.

2. Point out that the Joule agent's answer in ex4 traces all the way back through this graph to governed SAP data products — nothing is a black box.

## Exercise 5.2 Narrate the value (the "so what")

After completing these steps you will have the talking points to close the session.

1. One source of truth, zero copies. SAP data stayed in BDC as governed data products; non-SAP data stayed in open Iceberg on S3. Dremio unified them logically. There was no extract-and-duplicate ETL.

2. ELT / data-product engineering, not pipelines. The medallion is layered SQL views; the only physical acceleration is a reflection. Change a rule and everything downstream — including the agent — reflects it immediately.

3. Open and portable. The non-SAP data is in Apache Iceberg on your own S3. No lock-in; any Iceberg engine can read it.

4. Trustworthy AI. The Joule agent is grounded on a governed golden record with full lineage, so every answer is explainable and auditable.

5. Recap the flow for the audience:
<br>![End-to-end architecture recap diagram](/exercises/ex5/images/05_02_0010.png)
```text
SAP (S/4) ──► BDC Data Products ──┐
                                  ├──► Dremio: Bronze ─► Silver ─► Gold ──► Joule Agent
Non-SAP ──► Iceberg on S3 ────────┘        (ELT: layered SQL views + reflections)
```

## Discussion prompts (optional, for the room)

- Where in *your* landscape is data copied today that could instead be a zero-copy data product?
- Which non-SAP source would you land as Iceberg first?
- What is the first agent you would ground on a golden record?

## Screenshots to capture (for authors)

- [ ] `05_01_0010.png` — Dremio lineage graph of `gold.inventory_risk`
- [ ] `05_02_0010.png` — End-to-end architecture recap diagram

## Summary

You've built and then narrated a complete modern-data-stack story: governed SAP data products from BDC, open non-SAP Iceberg data on S3, a golden record refined through the medallion in Dremio, and a Joule agent delivering trustworthy answers on top — all with end-to-end lineage and no ETL copies.

That's the session. Thank you for participating!

Return to - [Overview](../../README.md)
