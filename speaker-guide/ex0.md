# Speaker Guide — Exercise 0: Getting Started

**~5 min.** Student doc: [`exercises/ex0`](../exercises/ex0/README.md)

## Goal of this segment
Set the scene and confirm everyone can see BDC, Dremio, and Joule. No building yet.

## Talking points
- Open with the spine question: *"Which production orders will miss OTIF — and why — so we can act before the due date?"*
- Name the two worlds plainly: **SAP** (production orders, operations, work-center master — governed data products) and **non-SAP** (a Vertex MES: downtime, quality, OEE, counts).
- The deliberate framing: this is **ELT / data-product engineering, not ETL**. "Data product engineering on an open lakehouse (zero-copy ELT)" is the phrase to teach.

## Do live
- Show the BDC Data Products catalog, the Dremio space with BDC + S3 sources, and the Joule Agent Builder landing. That's it.

## Gotchas
- If a student can't see a source, it's an access-grant issue from `infra/README.md` Step 3/4 — fix at the role level, don't debug per-student.

## Transition
"We have three tools and two worlds of data. Let's start with the SAP side — and prove we never copy it."
