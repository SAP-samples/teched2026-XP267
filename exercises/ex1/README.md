# Exercise 1 - Ingest SAP Data Products from BDC

In this exercise, you will find the SAP inventory data products in SAP Business Data Cloud (BDC) and make them available to Dremio zero-copy — no extraction, no duplication.

This is the "SAP side" of your golden record: trusted material master and stock data, delivered with business semantics already applied.

## Exercise 1.1 Find the inventory data products in the BDC catalog

After completing these steps you will have identified the two SAP data products that feed your golden inventory record.

1. In the SAP Business Data Cloud launchpad, open the Data Products catalog and search for `inventory`.
<br>![BDC Data Products catalog filtered to inventory](/exercises/ex1/images/01_01_0010.png)

2. Open the Material Master data product and review its contents. Note that it exposes a governed, business-semantic view — meaningful field names, descriptions, and a defined contract — not a raw S/4HANA table.

   > These are the two data products you will use:
   > - Material Master — material number, description, plant, material type, base unit.
   > - Stock on Hand — material number, plant, unclassified / quality / blocked stock quantities, last-updated timestamp.

3. Open the Stock on Hand data product and confirm it carries the material number key that will let you join it to Material Master.

## Exercise 1.2 Share the data products to Dremio (zero-copy)

After completing these steps the SAP data products will be queryable from Dremio without copying any data.

1. From each data product, choose Share (or Install / Make available, depending on your tenant) and select your Dremio target space as the consumer.
<br>![Sharing a BDC data product to the Dremio target](/exercises/ex1/images/01_02_0010.png)

2. Switch to Dremio. Under your BDC source, confirm the two shared data products now appear as queryable datasets.

3. Run a quick validation query in the Dremio SQL runner to confirm the data is readable in place:
```sql
-- Confirm the SAP data products are reachable zero-copy from Dremio
SELECT material_number, material_description, plant, base_unit
FROM BDC.inventory.material_master
LIMIT 20;
```

4. Confirm Stock on Hand is also readable and shares the join key:
```sql
SELECT material_number, plant, unrestricted_stock, quality_stock, blocked_stock, last_updated
FROM BDC.inventory.stock_on_hand
LIMIT 20;
```

> Why this matters (showcase point): nothing was extracted. BDC governs the data product and its semantics; Dremio reads it live. The customer keeps one governed source of truth with full lineage back to SAP.

## Screenshots to capture (for authors)

- [ ] `01_01_0010.png` — BDC Data Products catalog filtered to "inventory"
- [ ] `01_01_0020.png` — Material Master data product detail (fields + contract)
- [ ] `01_02_0010.png` — Share-to-Dremio dialog
- [ ] `01_02_0020.png` — Dremio showing the shared data products under the BDC source
- [ ] `01_02_0030.png` — Validation query result

## Summary

You've now made governed SAP inventory data products available to Dremio with zero copies. Next you will bring in the non-SAP side.

Continue to - [Exercise 2 - Land Non-SAP Data as Iceberg on S3](../ex2/README.md)
