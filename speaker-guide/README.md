# Speaker Guide — XP267

Presenter material for the session. Not student-facing — don't link it from the exercise flow. One file per exercise with talking points, timings, demo gotchas, and the expected result of each query so you can narrate confidently even if a query is slow.

| Guide | Exercise | ~Time |
|---|---|---|
| [ex1.md](ex1.md) | Build the CRM 360 golden record (resolve non-SAP CRM → SAP customers; OTIF appendix) | 15 min |
| [ex2.md](ex2.md) | Ontologies on the golden record (placeholder — other team) | TBD |
| [ex3.md](ex3.md) | Joule agent on the golden record | 10 min |

**Total:** ~25 min of hands-on (+ the ontology exercise from the other team).

## Before you present

- Complete the entire [`data/SETUP.md`](../data/SETUP.md) pre-flight checklist. The SAP data products (`customer`, `salesorderitem`, plus the OTIF production tables) are pre-loaded into Dremio as `"teched_labs_sandbox"."sap_dp".*`, and the non-SAP CRM export as `"teched_labs_sandbox"."non_sap".*` — narrate the BDC origin, but there is no live BDC connection in the demo. For the OTIF appendix, the non-SAP MES data is pre-staged on S3.
- The one-sentence spine for the whole session: *"Are our at-risk renewals driven by our own delivery performance?"* Repeat it at ex1 (golden record), ex2 (ontology), and ex3 (agent) — the churn ↔ delivery link. The OTIF manufacturing question (*"which production orders will miss OTIF, and why?"*) is the optional appendix / advanced track.
- The anti-ETL message is the recurring theme: zero-copy SAP data products + open Iceberg, unified as SQL views, not copied by pipelines.

## The data in one breath

- **Primary (CRM 360)** = governed SAP BDC data products `customer` + `salesorderitem` (queried as `"teched_labs_sandbox"."sap_dp".*`) rolled up into the per-customer OTIF truth (`v_customer_otif`), resolved against a non-SAP CRM export (`crm_account`, `crm_case`, …, as `"teched_labs_sandbox"."non_sap".*`) into the `v_crm_account_360` golden account record.
- **Appendix (OTIF manufacturing)** = production order / operation / work center (SAP) + 7 Vertex MES CSVs on S3 as Iceberg (work_order, equipment, downtime_event, quality_event, production_count, oee_snapshot, ground_truth_xref).
- The churn ↔ delivery link is the spine: each account's real published OTIF drives its CRM signals (worse delivery → more Delivery-Delay / Short-Shipment cases → higher churn risk). In the OTIF appendix the SAP and non-SAP worlds meet via `ground_truth_xref` (MES `equipment_id` ↔ SAP `WorkCenterInternalID`).