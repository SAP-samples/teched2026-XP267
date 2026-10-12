# Speaker Guide — Exercise 5: Lineage, Governance, Value

**~7 min — the exec close.** Student doc: [`exercises/ex5`](../exercises/ex5/README.md)

## Goal
Trace the lineage graph backward from the agent's answer to governed SAP data products, then narrate the value. No new objects.

## Do live
- Open the Dremio lineage/graph for `gold.otif_risk_enriched`. Walk it backward and point out the two branches in one picture:
  - `gold.otif_risk_enriched` ← `gold.otif_risk` ← `silver.otif_production` ← the 3 BDC data products ← **SAP S/4HANA**.
  - `gold.otif_risk_enriched` ← `silver.workcenter_shopfloor` ← `bronze.oee_snapshot` / `downtime_event` / `ground_truth_xref` ← **Vertex MES, Iceberg on S3**.

## The 4 value beats (say each once)
1. **One source of truth, zero copies** — SAP stayed in BDC, non-SAP stayed in open Iceberg; Dremio unified them logically.
2. **ELT, not pipelines** — layered SQL views + one reflection; deterministic, explainable scoring (no black-box model).
3. **Open & portable** — non-SAP data is Iceberg on the customer's own S3; any Iceberg engine can read it.
4. **Trustworthy AI** — the agent sits on a governed record with full lineage; every answer is auditable.

## Discussion prompts for the room
- Where is data copied today that could be a zero-copy product?
- Which non-SAP shopfloor source would you land as Iceberg first?
- What's the first agent you'd ground on a golden record?

## Close
Restate the spine one last time: *"We can now tell which orders will miss OTIF, and why, before the due date — from one governed record spanning SAP and non-SAP, with no ETL copies."* Thank the room.