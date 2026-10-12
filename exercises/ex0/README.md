# Exercise 0 - Getting Started: The SAP Modern Data Stack

In this exercise, you will get oriented to the modern SAP data stack you will use throughout this session, confirm access to your lab landscape, and understand the end-to-end story you are about to build.

By the end of the full set of exercises you will have built a golden **OTIF risk** record that blends SAP and non-SAP data, and a Joule agent that answers delivery-risk questions on top of it.

## The scenario

You work for a discrete manufacturer that needs to understand **on-time-in-full (OTIF)** delivery risk across the shopfloor. The data that answers *"which production orders are going to miss their OTIF commitment — and why — so we can act before the due date?"* is scattered:

- SAP data — production orders, their operations, and work-center master data, exposed as governed data products from SAP Business Data Cloud (BDC).
- Non-SAP data — a "Vertex" manufacturing-execution system (MES): machine/equipment master, work orders, downtime events, quality events, production counts, and OEE snapshots that land as Apache Iceberg tables on Amazon S3.

You will bring these together, refine them into a trusted golden record, and ground an AI agent on the result.

## The stack — and what each piece does

| Layer | Product | Role in this session |
| --- | --- | --- |
| Source of SAP data | SAP Business Data Cloud (BDC) | Provides governed, business-semantic S/4HANA data products (not raw tables) via zero-copy sharing. |
| Lakehouse & transformation | Dremio | ELT engine + semantic layer. Builds the bronze → silver → gold medallion as layered SQL views, accelerated by reflections. Reads Iceberg on S3 and BDC data products together. |
| AI / agents | Joule | Builds the agent that reasons over the golden OTIF record. |
| Open storage | Apache Iceberg on Amazon S3 | Open table format for the non-SAP MES data, queried in place (no lock-in). |

## The data you will use

All data is fully synthetic. Two datasets back this session:

- **`data/otif-synth-data`** — the main scenario. Its SAP S/4 side (`productionorder`, `productionorderoperation`, `workcenter`) is the governed-data-product side; its Vertex MES CSVs (`work_order`, `equipment`, `downtime_event`, `quality_event`, `production_count`, `oee_snapshot`, `ground_truth_xref`) are the non-SAP side landed as Iceberg on S3.
- **`data/otif-medallion`** — a worked reference of the same silver → gold OTIF logic on Azure Databricks. Exercise 3 rebuilds that logic as Dremio SQL views; its [README](../../data/otif-medallion/README.md) is the authoritative description of every derived column.
- **`data/mes_synthetic_data`** — a shopfloor OEE / capacity dataset used in Exercise 4 as supplementary context the agent can draw on.

## A note on terminology — it is not called "ETL"

A common question: *what is the new ETL called?*

In this stack, the deliberate framing is ELT and data-product engineering, not ETL:

- You do not copy SAP data out — BDC shares governed data products zero-copy, and Dremio queries them in place.
- Transformation is layered SQL views in Dremio (the medallion), physically accelerated by reflections — not row-by-row pipeline jobs.
- Non-SAP data is lakehouse ingestion into open Iceberg tables, queried where it sits.

> If you need one phrase to teach customers, use "data product engineering on an open lakehouse (zero-copy ELT)" rather than "ETL". The movement/orchestration primitives you will hear named in the SAP tooling are replication flows and transformation flows.

## Confirm your landscape

After completing these steps you will have confirmed access to all three tools.

1. Open the SAP Business Data Cloud launchpad using the credentials provided for your lab tenant and confirm you can see the Data Products catalog.
<br>![BDC launchpad with Data Products catalog](/exercises/ex0/images/00_00_0010.png)

2. Open Dremio and confirm you can see your lab space and the sources that are already connected (your BDC source and your S3 source).

3. Open Joule and confirm the Agent Builder (or Studio) is available to your user.

## Screenshots to capture (for authors)

- [ ] `00_00_0010.png` — BDC launchpad showing the Data Products catalog
- [ ] `00_00_0020.png` — Dremio home showing the lab space + BDC and S3 sources
- [ ] `00_00_0030.png` — Joule Agent Builder landing screen

## Summary

You now understand the scenario, the three tools, and why this is ELT / data-product engineering rather than ETL.

Continue to - [Exercise 1 - Ingest SAP Data Products from BDC](../ex1/README.md)
