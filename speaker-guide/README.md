# Speaker Guide — XP267

Presenter material for the session. Not student-facing — don't link it from the exercise flow. One file per exercise with talking points, timings, demo gotchas, and the expected result of each query so you can narrate confidently even if a query is slow.

| Guide | Exercise | ~Time |
|---|---|---|
| [ex1.md](ex1.md) | Build the golden records (fulfillment + CRM resolution; OTIF appendix) | 15 min |
| [ex2.md](ex2.md) | Ontologies on the golden record (placeholder — other team) | TBD |
| [ex3.md](ex3.md) | Joule agent on the golden record | 10 min |

**Total:** ~25 min of hands-on (+ the ontology exercise from the other team).

## Before you present

- Complete the entire [`data/SETUP.md`](../data/SETUP.md) pre-flight checklist. The SAP data products (`customer`, `salesorderitem`, `purchaseorderitem`, plus the OTIF production tables) are pre-loaded into Dremio as `"teched_labs_sandbox"."sap_dp".*` — narrate the BDC origin, but there is no live BDC connection in the demo. For the OTIF secondary track, the non-SAP MES data is pre-staged on S3.
- The one-sentence spine for the whole session: *"Which customers' orders are covered by supply — and where are the gaps?"* Repeat it at ex1 (golden record) and ex3 (agent). The secondary track is the cross-domain question *"are our at-risk renewals driven by our own delivery performance?"* (CRM 360). The OTIF manufacturing question (*"which production orders will miss OTIF, and why?"*) is the optional appendix / advanced track.
- The anti-ETL message is the recurring theme: zero-copy SAP data products + open Iceberg, unified as SQL views, not copied by pipelines.

## The data in one breath

- **Primary (Sales/CRM)** = 3 governed BDC data products — `customer`, `salesorderitem`, `purchaseorderitem` — exported and queried in Dremio as `"teched_labs_sandbox"."sap_dp".*`.
- **Secondary (OTIF manufacturing)** = production order / operation / work center (SAP) + 7 Vertex MES CSVs on S3 as Iceberg (work_order, equipment, downtime_event, quality_event, production_count, oee_snapshot, ground_truth_xref).
- Sales/CRM is the primary data: `salesorderitem` (demand) + `purchaseorderitem` (supply) + `customer` (context), queried in Dremio as `"teched_labs_sandbox"."sap_dp".*`. In the OTIF secondary track the SAP and non-SAP worlds meet via `ground_truth_xref` (MES `equipment_id` ↔ SAP `WorkCenterInternalID`).