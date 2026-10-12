# XP267 - Enrich your agents with context

## Description

This repository contains the material for the SAP TechEd 2026 session XP267 - Enrich your agents with context.

In this hands-on session you build an end-to-end modern SAP data stack scenario: you combine governed SAP S/4HANA data products from SAP Business Data Cloud (BDC) with non-SAP manufacturing-execution (MES) data stored as Apache Iceberg tables on Amazon S3, refine everything into a golden **OTIF risk** record using the bronze → silver → gold medallion in Dremio, and finally ground a Joule agent on that golden record.

## Overview

The scenario is manufacturing delivery risk — **on-time-in-full (OTIF)**. The data that answers *"which production orders are going to miss their OTIF commitment, and why?"* is split across SAP (production orders, operations, work-center master) and a non-SAP shopfloor system (machine telemetry, downtime, quality, OEE). You will unify them with zero-copy, data-product-centric ELT — not classic extract-and-duplicate ETL — and put a trustworthy AI agent on top.

The stack:

| Layer | Product | Role |
| --- | --- | --- |
| SAP data | SAP Business Data Cloud (BDC) | Governed S/4HANA data products shared zero-copy |
| Lakehouse + transformation | Dremio | ELT + semantic layer: medallion as layered SQL views, accelerated by reflections |
| AI / agents | Joule | Agent grounded on the golden OTIF record |
| Open storage | Apache Iceberg on Amazon S3 | Non-SAP MES data, queried in place |

> Terminology note: there is no new brand name for "ETL" here. The deliberate framing is data-product engineering on an open lakehouse (zero-copy ELT) — transformation as semantics (SQL views + reflections), not pipeline jobs. The movement primitives you will hear named in the tooling are replication flows and transformation flows.

## The data

All data in this session is fully synthetic and lives under [`data/`](data/):

- **`data/otif-synth-data`** — the Vertex MES ↔ SAP S/4 scenario. The SAP S/4 side (`productionorder`, `productionorderoperation`, `workcenter`) stands in for the governed BDC data products; the Vertex MES CSVs (`work_order`, `equipment`, `downtime_event`, `quality_event`, `production_count`, `oee_snapshot`) stand in for the non-SAP data landed as Iceberg on S3.
- **`data/otif-medallion`** — a reference implementation of the same silver → gold OTIF medallion on Azure Databricks ([read its README](data/otif-medallion/README.md)). The exercises reuse its derived-column logic (`otif_risk_score`, `is_at_risk`, `risk_tier`, `primary_root_cause`, `anomalous_work_centers`), rebuilt as Dremio SQL views.
- **`data/mes_synthetic_data`** — a shopfloor capacity/OEE dataset used as supplementary grounding and visualization context for the Joule agent (see [its README](data/mes_synthetic_data/README.md)).

## Requirements

- Access to the lab tenant for SAP Business Data Cloud, Dremio, and Joule (credentials provided at the session).
- A modern browser. No local installation required — all tools are browser-based.
- Basic familiarity with SQL is helpful but not required; all queries are provided.

## Exercises

- [Exercise 0 - Getting Started: The SAP Modern Data Stack](exercises/ex0/)
- [Exercise 1 - Ingest SAP Data Products from BDC](exercises/ex1/)
    - [Exercise 1.1 - Find the OTIF data products in the BDC catalog](exercises/ex1#exercise-11-find-the-otif-data-products-in-the-bdc-catalog)
    - [Exercise 1.2 - Share the data products to Dremio (zero-copy)](exercises/ex1#exercise-12-share-the-data-products-to-dremio-zero-copy)
- [Exercise 2 - Land Non-SAP MES Data as Iceberg on S3 (Bronze)](exercises/ex2/)
    - [Exercise 2.1 - Explore the raw files on S3](exercises/ex2#exercise-21-explore-the-raw-files-on-s3)
    - [Exercise 2.2 - Register the data as Iceberg tables](exercises/ex2#exercise-22-register-the-data-as-iceberg-tables)
- [Exercise 3 - Build the Medallion: Bronze → Silver → Gold](exercises/ex3/)
    - [Exercise 3.1 - Build the Silver layer (clean & conform)](exercises/ex3#exercise-31-build-the-silver-layer-clean--conform)
    - [Exercise 3.2 - Build the Gold golden OTIF record](exercises/ex3#exercise-32-build-the-gold-golden-otif-record)
- [Exercise 4 - Build a Joule Agent on the Golden Record](exercises/ex4/)
    - [Exercise 4.1 - Create the agent and connect its data context](exercises/ex4#exercise-41-create-the-agent-and-connect-its-data-context)
    - [Exercise 4.2 - Ask the agent OTIF-risk questions](exercises/ex4#exercise-42-ask-the-agent-otif-risk-questions)
- [Exercise 5 - Showcase & Wrap: Lineage, Governance, Value](exercises/ex5/)
    - [Exercise 5.1 - Trace end-to-end lineage](exercises/ex5#exercise-51-trace-end-to-end-lineage)
    - [Exercise 5.2 - Narrate the value (the "so what")](exercises/ex5#exercise-52-narrate-the-value-the-so-what)

## Contributing
Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) to understand the contribution guidelines.

## Code of Conduct
Please read the [SAP Open Source Code of Conduct](https://github.com/SAP-samples/.github/blob/main/CODE_OF_CONDUCT.md).

## How to obtain support

Support for the content in this repository is available during the actual time of the online session for which this content has been designed. Otherwise, you may request support via the [Issues](../../issues) tab.

## License
Copyright (20xx-)20xx SAP SE or an SAP affiliate company and <your-project> contributors. Please see our [LICENSE](LICENSE) for copyright and license information. Detailed information including third-party components and their licensing/copyright information is available [via the REUSE tool](https://api.reuse.software/info/github.com/SAP/<your-project>).
