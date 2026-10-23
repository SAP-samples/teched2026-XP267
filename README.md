# XP267 - Enrich your agents with context

## Description

This repository contains the material for the SAP TechEd 2026 session XP267 - Enrich your agents with context.

In this hands-on session you build an end-to-end modern SAP data stack scenario: you take governed SAP S/4HANA data products from SAP Business Data Cloud (BDC) — sales orders, purchase orders, and customer master, plus a manufacturing track — refine them into golden records using layered SQL views in Dremio, and finally ground a Joule agent on those golden records.

## Overview

The primary scenario resolves a non-SAP CRM to governed SAP customers and proves the churn ↔ delivery link: *"are our at-risk renewals driven by our own delivery performance?"* — built by resolving messy CRM account names to SAP customer numbers, rolling SAP sales lines up to a per-customer on-time-in-full (OTIF) truth, and joining CRM cases and renewals into one golden account record. An OTIF manufacturing production-risk record is kept as an optional advanced appendix. You unify everything with data-product-centric ELT — not classic extract-and-duplicate ETL — and put a trustworthy AI agent on top.

The stack:

| Layer | Product | Role |
| --- | --- | --- |
| SAP data | SAP Business Data Cloud (BDC) | Governed S/4HANA data products shared zero-copy |
| Lakehouse + transformation | Dremio | ELT + semantic layer: medallion as layered SQL views, accelerated by reflections |
| AI / agents | Joule | Agent grounded on the golden CRM 360 record (via the ontology) |
| Open storage | Apache Iceberg on Amazon S3 | Non-SAP MES data, queried in place |

> Terminology note: there is no new brand name for "ETL" here. The deliberate framing is data-product engineering on an open lakehouse (zero-copy ELT) — transformation as semantics (SQL views + reflections), not pipeline jobs. The movement primitives you will hear named in the tooling are replication flows and transformation flows.

## The data

All data you need is already provisioned in Dremio for the session — you query it there, you don't download or load anything. The SAP tables resolve under `"teched_labs_sandbox"."sap_dp".*` and the non-SAP CRM under `"teched_labs_sandbox"."non_sap".*`; each exercise tells you exactly which objects to use.

## Requirements

- Access to the lab tenant for SAP Business Data Cloud, Dremio, and Joule (credentials provided at the session).
- A modern browser. No local installation required — all tools are browser-based.
- Basic familiarity with SQL is helpful but not required; all queries are provided.

## Exercises

- [Exercise 1 - Build the Golden Records in Dremio](exercises/ex1/)
    - [Exercise 1.1 - Resolve a non-SAP CRM to SAP customers](exercises/ex1#exercise-11-resolve-a-non-sap-crm-to-sap-customers)
    - [Exercise 1.2 - Build & materialize the CRM 360 golden record](exercises/ex1#exercise-12-build--materialize-the-crm-360-golden-record)
    - [Optional (Advanced) - OTIF manufacturing medallion](exercises/ex1/optional/)
- [Exercise 2 - Ontologies on the Golden Record (coming soon)](exercises/ex2/)
- [Exercise 3 - Build a Joule Skill on the Golden Record](exercises/ex3/)
    - [Exercise 3.1 - Import and enable the skill](exercises/ex3#exercise-31-import-and-enable-the-skill)
    - [Exercise 3.2 - Ask the skill churn & delivery questions](exercises/ex3#exercise-32-ask-the-skill-churn--delivery-questions)

## Contributing
Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) to understand the contribution guidelines.

## Code of Conduct
Please read the [SAP Open Source Code of Conduct](https://github.com/SAP-samples/.github/blob/main/CODE_OF_CONDUCT.md).

## How to obtain support

Support for the content in this repository is available during the actual time of the online session for which this content has been designed. Otherwise, you may request support via the [Issues](../../issues) tab.

## License
Copyright (20xx-)20xx SAP SE or an SAP affiliate company and <your-project> contributors. Please see our [LICENSE](LICENSE) for copyright and license information. Detailed information including third-party components and their licensing/copyright information is available [via the REUSE tool](https://api.reuse.software/info/github.com/SAP/<your-project>).
