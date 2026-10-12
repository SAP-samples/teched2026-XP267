# Speaker Guide — XP267

Presenter material for the session. **Not student-facing** — don't link it from the exercise flow. One file per exercise with talking points, timings, demo gotchas, and the expected result of each query so you can narrate confidently even if a query is slow.

| Guide | Exercise | ~Time |
|---|---|---|
| [ex0.md](ex0.md) | Getting started / the stack | 5 min |
| [ex1.md](ex1.md) | SAP data products from BDC | 8 min |
| [ex2.md](ex2.md) | Non-SAP MES data as Iceberg (Bronze) | 10 min |
| [ex3.md](ex3.md) | Medallion Silver → Gold | 15 min |
| [ex4.md](ex4.md) | Joule agent on the golden record | 10 min |
| [ex5.md](ex5.md) | Lineage, governance, value | 7 min |

**Total:** ~55 min of hands-on + wrap.

## Before you present

- Complete the entire [`infra/README.md`](../infra/README.md) pre-flight checklist. The single biggest live-demo risk is unstaged S3 data or an unshared BDC product — both are eliminated by staging **all data once, up front**.
- The one-sentence spine for the whole session: *"Which production orders will miss OTIF — and why — so we can act before the due date?"* Repeat it at ex0, ex3 (gold), and ex4 (agent).
- The anti-ETL message is the recurring theme: **zero-copy SAP data products + open Iceberg, unified as SQL views, not copied by pipelines.**

## The data in one breath

- **SAP side** = 3 governed BDC data products (production order, operation, work center), zero-copy to Dremio.
- **Non-SAP side** = 7 Vertex MES CSVs on S3 as Iceberg (work_order, equipment, downtime_event, quality_event, production_count, oee_snapshot, ground_truth_xref).
- The two meet in **ex3** via `ground_truth_xref` (MES `equipment_id` ↔ SAP `WorkCenterInternalID`).