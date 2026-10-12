# Speaker Guide — Exercise 1: SAP Data Products from BDC

**~8 min.** Student doc: [`exercises/ex1`](../exercises/ex1/README.md)

## Goal
Find the 3 SAP data products in BDC and make them queryable in Dremio **zero-copy**.

## The 3 data products (the SAP side)
- `productionorder.productionorder` — order header (plan/actual qty, scheduled/actual dates).
- `productionorder.productionorderoperation` — one row per operation; carries `ProductionOrder` (→ header) and `WorkCenterInternalID` (→ work center).
- `workcenter.workcenter` — machine/station master.

## Talking points
- These are **governed, business-semantic** products — meaningful field names and a contract — not raw S/4 tables.
- "Share" (or Install / Make available) is a **zero-copy** act: Dremio reads them live. Nothing is extracted.
- Lineage runs back into S/4HANA — hold that thought for ex5.

## Do live — expected results
- `SELECT ... FROM BDC.productionorder.productionorder LIMIT 20` → ~200 orders exist in the dataset; expect a healthy mix of statuses.
- Operation query returns the two join keys (`ProductionOrder`, `WorkCenterInternalID`) — point at them explicitly; they are the backbone of ex3's silver join.

## Gotchas
- If the catalog name differs in your tenant, the exercise uses `BDC` as the Dremio source alias — adjust SQL or source name to match.
- Empty result = product shared but not refreshed, or wrong source. Covered in `infra/README.md` Step 4.

## Transition
"That's the trusted SAP side. Now the messy non-SAP shopfloor data — and we'll keep it open."
