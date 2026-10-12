# Exercise 1 - Ingest SAP Data Products from BDC

In this exercise, you will find the SAP S/4HANA manufacturing data products in SAP Business Data Cloud (BDC) and make them available to Dremio zero-copy — no extraction, no duplication.

This is the "SAP side" of your golden record: trusted production-order, operation, and work-center data, delivered with business semantics already applied.

## Exercise 1.1 Find the OTIF data products in the BDC catalog

After completing these steps you will have identified the three SAP data products that feed your golden OTIF record.

1. In the SAP Business Data Cloud launchpad, open the Data Products catalog and search for `production` (or `work center`).
<br>![BDC Data Products catalog filtered to production](/exercises/ex1/images/01_01_0010.png)

2. Open the **Production Order** data product and review its contents. Note that it exposes a governed, business-semantic view — meaningful field names, descriptions, and a defined contract — not a raw S/4HANA table.

   > These are the three data products you will use (grouped under the `otif-demo-data-products` share):
   > - **Production Order** (`productionorder.productionorder`) — order header: `ProductionOrder`, `ProductionOrderType`, `ProductionPlant`, `OrderPlannedTotalQty`, `OrderConfirmedYieldQty`, `OrderConfirmedScrapQty`, `OrderScheduledStartDate`, `OrderScheduledEndDate`, `OrderActualStartDate`, `OrderActualEndDate`.
   > - **Production Order Operation** (`productionorder.productionorderoperation`) — one row per operation: `ProductionOrder`, `ProductionOrderOperation`, `WorkCenterInternalID`, `OpPlannedTotalQuantity`, `OpTotalConfirmedYieldQty`, `OpTotalConfirmedScrapQty`, `OperationScrapPercent`, `ConfirmedWorkQuantity1`, `WorkCenterStandardWorkQty1`.
   > - **Work Center** (`workcenter.workcenter`) — machine/station master: `WorkCenterInternalID`, `WorkCenter`, `WorkCenterName`, `WorkCenterCategoryCode`, `Plant`.

3. Open the **Production Order Operation** data product and confirm it carries both the `ProductionOrder` key (to join back to the header) and the `WorkCenterInternalID` key (to join to Work Center).

## Exercise 1.2 Share the data products to Dremio (zero-copy)

After completing these steps the SAP data products will be queryable from Dremio without copying any data.

1. From each data product, choose Share (or Install / Make available, depending on your tenant) and select your Dremio target space as the consumer.
<br>![Sharing a BDC data product to the Dremio target](/exercises/ex1/images/01_02_0010.png)

2. Switch to Dremio. Under your BDC source, confirm the three shared data products now appear as queryable datasets.

3. Run a quick validation query in the Dremio SQL runner to confirm the production-order header is readable in place:
```sql
-- Confirm the SAP production-order data product is reachable zero-copy from Dremio
SELECT ProductionOrder, ProductionOrderType, ProductionPlant,
       OrderPlannedTotalQty, OrderScheduledEndDate, OrderActualEndDate
FROM BDC.productionorder.productionorder
LIMIT 20;
```

4. Confirm the operation and work-center products are readable and share their join keys:
```sql
-- Operations carry ProductionOrder (join to header) and WorkCenterInternalID (join to work center)
SELECT ProductionOrder, ProductionOrderOperation, WorkCenterInternalID,
       OpPlannedTotalQuantity, OpTotalConfirmedScrapQty,
       ConfirmedWorkQuantity1, WorkCenterStandardWorkQty1
FROM BDC.productionorder.productionorderoperation
LIMIT 20;

SELECT WorkCenterInternalID, WorkCenter, WorkCenterName, Plant
FROM BDC.workcenter.workcenter
LIMIT 20;
```

> Why this matters (showcase point): nothing was extracted. BDC governs the data product and its semantics; Dremio reads it live. The customer keeps one governed source of truth with full lineage back to SAP S/4HANA.

## Screenshots to capture (for authors)

- [ ] `01_01_0010.png` — BDC Data Products catalog filtered to "production"
- [ ] `01_01_0020.png` — Production Order data product detail (fields + contract)
- [ ] `01_02_0010.png` — Share-to-Dremio dialog
- [ ] `01_02_0020.png` — Dremio showing the three shared data products under the BDC source
- [ ] `01_02_0030.png` — Validation query result

## Summary

You've now made governed SAP manufacturing data products (production order, operation, work center) available to Dremio with zero copies. Next you will bring in the non-SAP MES side.

Continue to - [Exercise 2 - Land Non-SAP MES Data as Iceberg on S3](../ex2/README.md)
