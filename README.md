# XP267 - Enrich your agents with context

## Description

This repository contains the material for the SAP TechEd 2026 session XP267 - Enrich your agents with context.

In this hands-on session you build an end-to-end modern SAP data stack scenario: you take governed SAP S/4HANA data products from SAP Business Data Cloud (BDC) — sales orders, purchase orders, and customer master, plus a manufacturing track — refine them into golden records using layered SQL views in Dremio, and finally ground a Joule agent on those golden records.

## Overview

The primary scenario is **customer order fulfillment** (Sales / CRM): *"which customers' orders are covered by supply, and where are the gaps?"* — built by blending `salesorderitem` (demand), `purchaseorderitem` (supply), and `customer` (context) into one golden record. A secondary manufacturing track keeps the **on-time-in-full (OTIF)** production-risk record. You unify everything with data-product-centric ELT — not classic extract-and-duplicate ETL — and put a trustworthy AI agent on top.

> **Sourcing note:** these SAP tables are governed **BDC data products**. For the hands-on lab they are exported and pre-loaded into Dremio (queried as `"teched_labs_sandbox"."sap_dp".*`) so the session has **no live BDC connection dependency** — the sourcing story is still BDC; the SQL runs against Dremio.

The stack:

| Layer | Product | Role |
| --- | --- | --- |
| SAP data | SAP Business Data Cloud (BDC) | Governed S/4HANA data products shared zero-copy |
| Lakehouse + transformation | Dremio | ELT + semantic layer: medallion as layered SQL views, accelerated by reflections |
| AI / agents | Joule | Agent grounded on the golden OTIF record |
| Open storage | Apache Iceberg on Amazon S3 | Non-SAP MES data, queried in place |

> Terminology note: there is no new brand name for "ETL" here. The deliberate framing is data-product engineering on an open lakehouse (zero-copy ELT) — transformation as semantics (SQL views + reflections), not pipeline jobs. The movement primitives you will hear named in the tooling are replication flows and transformation flows.

## The data

All data in this session is synthetic and lives under [`data/`](data/):

- **`data/data-products`** — the primary Sales / CRM SAP data products exported from BDC and pre-loaded into Dremio: `customer`, `salesorderitem`, `purchaseorderitem`. Exercise 1 blends these into the golden customer order-fulfillment record (`v_customer_order_fulfillment`).
- **`data/otif-synth-data`** — the Vertex MES ↔ SAP S/4 scenario. The SAP S/4 side (`productionorder`, `productionorderoperation`, `workcenter`) stands in for the governed BDC data products; the Vertex MES CSVs (`work_order`, `equipment`, `downtime_event`, `quality_event`, `production_count`, `oee_snapshot`) stand in for the non-SAP data landed as Iceberg on S3.
- **`data/otif-medallion`** — a reference implementation of the same silver → gold OTIF medallion on Azure Databricks ([read its README](data/otif-medallion/README.md)). The exercises reuse its derived-column logic (`otif_risk_score`, `is_at_risk`, `risk_tier`, `primary_root_cause`, `anomalous_work_centers`), rebuilt as Dremio SQL views.
- **`data/mes_synthetic_data`** — a shopfloor capacity/OEE dataset used as supplementary grounding and visualization context for the Joule agent (see [its README](data/mes_synthetic_data/README.md)).

## Requirements

- Access to the lab tenant for SAP Business Data Cloud, Dremio, and Joule (credentials provided at the session).
- A modern browser. No local installation required — all tools are browser-based.
- Basic familiarity with SQL is helpful but not required; all queries are provided.

## Exercises

- [Exercise 1 - Build the Golden Records in Dremio](exercises/ex1/)
    - [Exercise 1.1 - Build the Customer Order Fulfillment golden record](exercises/ex1#exercise-11-build-the-customer-order-fulfillment-golden-record)
    - [Exercise 1.2 - Materialize the golden record for downstream use](exercises/ex1#exercise-12-materialize-the-golden-record-for-downstream-use)
    - [Exercise 1.3 - (Secondary) Build the OTIF manufacturing medallion](exercises/ex1#exercise-13-secondary-build-the-otif-manufacturing-medallion)
- [Exercise 2 - Ontologies on the Golden Record (coming soon)](exercises/ex2/)
- [Exercise 3 - Build a Joule Agent on the Golden Record](exercises/ex3/)
    - [Exercise 3.1 - Create the agent and connect its data context](exercises/ex3#exercise-31-create-the-agent-and-connect-its-data-context)
    - [Exercise 3.2 - Ask the agent fulfillment questions](exercises/ex3#exercise-32-ask-the-agent-fulfillment-questions)

## Contributing
Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) to understand the contribution guidelines.

## Code of Conduct
Please read the [SAP Open Source Code of Conduct](https://github.com/SAP-samples/.github/blob/main/CODE_OF_CONDUCT.md).

## How to obtain support

Support for the content in this repository is available during the actual time of the online session for which this content has been designed. Otherwise, you may request support via the [Issues](../../issues) tab.

## License
Copyright (20xx-)20xx SAP SE or an SAP affiliate company and <your-project> contributors. Please see our [LICENSE](LICENSE) for copyright and license information. Detailed information including third-party components and their licensing/copyright information is available [via the REUSE tool](https://api.reuse.software/info/github.com/SAP/<your-project>).
