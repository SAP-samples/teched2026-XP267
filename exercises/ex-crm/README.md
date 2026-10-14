# Exercise (CRM, Extended) - Bring a Non-SAP Source into the Lakehouse and Resolve It to SAP

> **Extended deep dive — the full build behind Exercise 1.3.** Exercise 1.3 is the condensed, run-it-on-screen path; this is the line-by-line version where you write the views yourself and see why fuzzy matching needs MDM. Start here if you want the complete walkthrough.

In Exercise 1 you refined *governed SAP* data into a golden record. Real businesses don't run on SAP alone. In this exercise you bring in a **non-SAP source** — a 3rd-party CRM — resolve its accounts to your SAP customers, and shape the result into an **ontology-ready product** that an agent can reason over alongside the SAP sales data.

## You already know this data

You've seen this system, even if we don't name the vendor. Every B2B company runs a CRM: **accounts** (the companies you sell to), the **contacts** inside them, the **cases** they open when something goes wrong, and the **opportunities** your reps are working — above all the **renewals**. It's the system of record for the *relationship*, not the transaction.

And it arrives the way 3rd-party data usually lands in a lakehouse: a **flat export** (CSV), with the source system's own spelling of company names and **no SAP keys** — no `Customer` number, no shared identifier. Making it speak to governed SAP data is the whole job.

## The data-product lens (read this once; it applies to Exercise 1 too)

Everything you build here is a SQL view, materialized with a reflection, in **your own Dremio space**. Treat that as a **"current product truth" proxy**. The direction of travel in the **SAP Business Data Cloud Lakehouse** is that these curated assets become **Primary Data Products** — governed, discoverable, contract-bound — which downstream consumers, and **Joule**, turn into **derived data products** on demand, from intent. The Dremio mechanics you use now — **engines** for compute, **reflections** for acceleration — don't go away; they're how the lakehouse keeps those products fast and fresh. So: today you model the product truth in SQL; tomorrow you publish it as a data product. Same asset, more governance.

> **Your space:** build the objects below in `"<your_space>"` (your personal Dremio space) — substitute it everywhere you see `<your_space>`. Leave the **sources** (`"teched_labs_sandbox"."sap_dp"`, `"teched_labs_sandbox"."non_sap"`) as-is; those are shared, read-only. A validated reference build lives in `"teched_labs_sandbox"."hands-on-test"."ex-crm"` if you get stuck — but build your own, because you'll *own* the product.

---

## Part A - Explore the data and frame the challenge

Run these to understand what you have before you build anything.

**1. The CRM accounts.**
```sql
SELECT crm_account_id, account_name, segment, churn_risk, nps, renewal_date
FROM "teched_labs_sandbox"."non_sap".crm_account
LIMIT 20;
```
> **You should see** one row per account, with a `churn_risk` (At Risk / Watch / Healthy / Unmanaged) and a `renewal_date`. Look at `account_name`: some are clean (`US Large Cycles 5`), some carry legal suffixes (`USC1 Inc.`), some are abbreviated or mistyped (`CA Specialty Cyales 5 Ltd.`). **There is no SAP customer number here.** Also note every value is text — CSV import types everything as `VARCHAR` (`nps` comes back as `'-21'`).

**2. The CRM cases — the voice of the customer.**
```sql
SELECT category, status, COUNT(*) n
FROM "teched_labs_sandbox"."non_sap".crm_case
GROUP BY category, status ORDER BY n DESC;
```
> **You should see** cases dominated by **Delivery Delay** and **Short Shipment**. That's the relationship system complaining about something the *transaction* system (SAP sales orders) actually records. Each case also has a `related_sales_order` pointing back at a real SAP order.

**3. The SAP side you'll connect to.** Customer master (context) and sales-order lines (the delivery facts):
```sql
SELECT Customer, CustomerName, Country, Industry
FROM "teched_labs_sandbox"."sap_dp".customer LIMIT 10;

SELECT SoldToParty, RequestedDeliveryDate, CommittedDeliveryDate, TotalDeliveryStatus
FROM "teched_labs_sandbox"."sap_dp".salesorderitem LIMIT 10;
```
> **You should see** that `customer.Customer` is the SAP key, `salesorderitem.SoldToParty` is that same key on the demand side, and the delivery columns (`RequestedDeliveryDate`, `CommittedDeliveryDate`, `TotalDeliveryStatus`) are what tell you whether an order was **on time** and **in full**.

### The challenge

You have a relationship system (CRM) that *thinks* some accounts are churning, and a transaction system (SAP) that knows how well you actually delivered to them. Three gaps stand between you and a single answer:

1. **No shared key.** CRM has company *names*, SAP has customer *numbers*. You must **resolve** one to the other — and the names are messy.
2. **No comparable metric.** "OTIF" lives at the sales-order *line*; the CRM lives at the *account*. You need a per-customer OTIF truth to compare against.
3. **The real question is cross-domain.** *"Are our at-risk renewals being driven by our own delivery performance?"* needs both worlds joined. You'll prove the link, not assume it.

---

## Part B - What you need to accomplish

Build three product-truth assets in your space, each a building block toward a publishable data product:

| # | Asset (view in `<your_space>`) | What it is |
|---|---|---|
| 1 | `v_customer_otif` | Per-customer OTIF truth, rolled up from SAP sales-order lines. The SAP-side metric. |
| 2 | `v_crm_account_resolved` | The **Account → Customer crosswalk** — the resolution/MDM step, with a `match_method` recording *how* each account was resolved. |
| 3 | `v_crm_account_360` | The **ontology-ready golden account product**: CRM + resolved SAP customer + OTIF + case counts. This is the one you materialize and that becomes a Primary Data Product. |

By the end you'll answer, from one view: *"Which at-risk renewals have the worst delivery performance, and what's it costing us?"* — the question the Joule agent in Exercise 3 grounds on, and the `resolvesTo` relationship Exercise 2 models in the ontology.

---

## Part C - Starter SQL (try it yourself first)

### C.1 Per-customer OTIF truth

Roll the sales-order lines up to one row per customer. The delivery dates are ISO strings, so you can compare them directly; "in full" uses the SD delivery-completion status (`C` = complete). Start from this skeleton and fill in `pct_in_full` and the `late` count:

```sql
SELECT
  SoldToParty AS "Customer",
  COUNT(*) AS lines,
  ROUND(100.0*AVG(CASE WHEN CommittedDeliveryDate IS NULL OR CommittedDeliveryDate='' THEN NULL
                       WHEN CommittedDeliveryDate <= RequestedDeliveryDate THEN 1.0 ELSE 0.0 END),1) AS pct_on_time,
  -- TODO: pct_in_full  = share of lines where TotalDeliveryStatus = 'C'
  -- TODO: otif_pct     = on-time AND in-full, over committed lines
  -- TODO: late         = committed lines where CommittedDeliveryDate > RequestedDeliveryDate
FROM "teched_labs_sandbox"."sap_dp".salesorderitem
WHERE RequestedDeliveryDate >= '2023-01-01'
GROUP BY SoldToParty;
```
> We window to `>= '2023-01-01'` because that's where the committed-delivery dates are populated — older rows would read as a false "100% on time."

### C.2 Resolve the names — and see why "fuzzy" only gets you so far

First, *look* at the matching problem. "Fuzzy matching" in this exercise is nothing exotic — it's **a handful of regex normalizations** you can run directly in Dremio SQL: upper-case, turn punctuation into spaces, strip trailing legal suffixes (`Inc.`, `GmbH`, `S.A. de C.V.`), remove spaces, compare.

```sql
SELECT account_name,
  REGEXP_REPLACE(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(UPPER(account_name),'[^A-Z0-9]+',' ')),
    ' (INC|LLC|CO|CORP|GMBH|AG|KG|LTD|GROUP|SA DE CV|S DE RL)$',''),' ','') AS normalized
FROM "teched_labs_sandbox"."non_sap".crm_account
LIMIT 20;
```
> **You should see** `US Large Cycles 5` and `U.S. Large Cycles 5 Inc.` both normalize to `USLARGECYCLES5` — matched. But `USC1 Inc.` and `CA Specialty Cyales 5 Ltd.` (a typo) do **not** normalize to anything in the customer master. Regex can't recover those.

Now try the fuzzy join on its own and count how far it gets:
```sql
WITH acc AS (
  SELECT crm_account_id,
    REGEXP_REPLACE(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(UPPER(account_name),'[^A-Z0-9]+',' ')),
      ' (INC|LLC|CO|CORP|GMBH|AG|KG|LTD|GROUP|SA DE CV|S DE RL)$',''),' ','') AS an
  FROM "teched_labs_sandbox"."non_sap".crm_account
),
cust AS (
  SELECT Customer,
    REGEXP_REPLACE(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(UPPER(CustomerName),'[^A-Z0-9]+',' ')),
      ' (INC|LLC|CO|CORP|GMBH|AG|KG|LTD|GROUP|SA DE CV|S DE RL)$',''),' ','') AS cn
  FROM "teched_labs_sandbox"."sap_dp".customer
)
SELECT COUNT(*) accounts,
       SUM(CASE WHEN cust.Customer IS NOT NULL THEN 1 ELSE 0 END) auto_matched
FROM acc LEFT JOIN cust ON acc.an = cust.cn;
```
> **You should see** roughly **60%** auto-matched — and if you dig in, some names collide (one normalized name maps to **more than one** `Customer`). That's the lesson: **regex fuzzy matching is a great way to *see* the resolution problem and clear the easy cases, but it is a proxy.** A production deployment reaches for a real **MDM** solution. You can run entity resolution in an engine like **Zingg** or **Splink** — but matching is only half the problem. MDM also gives you **survivorship** (which source wins, attribute by attribute, when records merge), **stewardship and governance**, **match-confidence** scoring, and a **golden crosswalk that's maintained over time**. In BDC, that golden crosswalk is exactly what the ontology's `resolvesTo` relationship points at.

For this lab we approximate the MDM output with `crm_account_resolution_xref` — a ground-truth crosswalk standing in for what Reltio (or equivalent) would publish. The **hybrid** you build next is honest about both halves: let SQL auto-resolve the easy names, defer the rest to the golden crosswalk, and **record which path won** so the hand-off to MDM is visible.

### C.3 The 360 product

Join CRM account → resolved customer → the OTIF truth from C.1 → case counts. Remember the guarded cast for the string columns:
```sql
-- numeric CRM columns are text; cast only clean integers (same idea as Exercise 1's quantity guard)
CASE WHEN REGEXP_LIKE(nps, '^-?[0-9]+$') THEN CAST(nps AS INTEGER) END AS nps
```
Build the skeleton, then check it against the reference in Part D.

---

## Part D - Reference DDL (if you fell behind, or just want the answer)

The complete, validated set is in [`crm_resolution_and_360.sql`](./crm_resolution_and_360.sql). Substitute `<your_space>` for the target space; the three views are reproduced here.

**D.1 — Per-customer OTIF truth**
```sql
CREATE OR REPLACE VIEW "<your_space>".v_customer_otif AS
SELECT
  SoldToParty AS "Customer",
  COUNT(*) AS lines,
  SUM(CASE WHEN CommittedDeliveryDate IS NOT NULL AND CommittedDeliveryDate<>'' THEN 1 ELSE 0 END) AS committed_lines,
  ROUND(100.0*AVG(CASE WHEN CommittedDeliveryDate IS NULL OR CommittedDeliveryDate='' THEN NULL
                       WHEN CommittedDeliveryDate <= RequestedDeliveryDate THEN 1.0 ELSE 0.0 END),1) AS pct_on_time,
  ROUND(100.0*AVG(CASE WHEN TotalDeliveryStatus='C' THEN 1.0 ELSE 0.0 END),1) AS pct_in_full,
  ROUND(100.0*AVG(CASE WHEN CommittedDeliveryDate IS NULL OR CommittedDeliveryDate='' THEN NULL
                       WHEN CommittedDeliveryDate <= RequestedDeliveryDate AND TotalDeliveryStatus='C' THEN 1.0 ELSE 0.0 END),1) AS otif_pct,
  SUM(CASE WHEN CommittedDeliveryDate IS NOT NULL AND CommittedDeliveryDate<>'' AND CommittedDeliveryDate > RequestedDeliveryDate THEN 1 ELSE 0 END) AS late,
  SUM(CASE WHEN TotalDeliveryStatus IN ('A','B') THEN 1 ELSE 0 END) AS short
FROM "teched_labs_sandbox"."sap_dp".salesorderitem
WHERE RequestedDeliveryDate >= '2023-01-01'
GROUP BY SoldToParty;
```

**D.2 — Hybrid resolution (SQL fuzzy + golden crosswalk)**
```sql
CREATE OR REPLACE VIEW "<your_space>".v_crm_account_resolved AS
WITH cust_norm AS (
  SELECT
    REGEXP_REPLACE(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(UPPER(CustomerName),'[^A-Z0-9]+',' ')),
      ' (INC|LLC|CO|CORP|GMBH|AG|KG|LTD|GROUP|SA DE CV|S DE RL)$',''),' ','') AS cn,
    MIN(Customer) AS one_customer,
    COUNT(DISTINCT Customer) AS ncust
  FROM "teched_labs_sandbox"."sap_dp".customer
  GROUP BY REGEXP_REPLACE(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(UPPER(CustomerName),'[^A-Z0-9]+',' ')),
      ' (INC|LLC|CO|CORP|GMBH|AG|KG|LTD|GROUP|SA DE CV|S DE RL)$',''),' ','')
),
fuzzy AS (
  SELECT a.crm_account_id, cn2.one_customer AS fuzzy_sap_id, cn2.ncust
  FROM "teched_labs_sandbox"."non_sap".crm_account a
  LEFT JOIN cust_norm cn2
    ON REGEXP_REPLACE(REGEXP_REPLACE(TRIM(REGEXP_REPLACE(UPPER(a.account_name),'[^A-Z0-9]+',' ')),
         ' (INC|LLC|CO|CORP|GMBH|AG|KG|LTD|GROUP|SA DE CV|S DE RL)$',''),' ','') = cn2.cn
)
SELECT
  x.crm_account_id,
  x.sap_customer_id,                       -- authoritative golden crosswalk (MDM / xref)
  x.name_match_difficulty,
  f.fuzzy_sap_id,
  CASE
    WHEN f.fuzzy_sap_id IS NOT NULL AND f.ncust = 1 AND f.fuzzy_sap_id = x.sap_customer_id THEN 'fuzzy_auto'
    WHEN f.ncust > 1 THEN 'ambiguous_needs_mdm'
    ELSE 'mdm_resolved'
  END AS match_method
FROM "teched_labs_sandbox"."non_sap".crm_account_resolution_xref x
LEFT JOIN fuzzy f ON f.crm_account_id = x.crm_account_id;
```
> `match_method` is the point of the hybrid: `fuzzy_auto` is what SQL resolved on its own; `mdm_resolved` and `ambiguous_needs_mdm` are what only the golden crosswalk could settle — the honest boundary between "a few regex" and "a real MDM."

**D.3 — The 360 golden account product**
```sql
CREATE OR REPLACE VIEW "<your_space>".v_crm_account_360 AS
WITH cases AS (
  SELECT crm_account_id,
         SUM(CASE WHEN status='Open' THEN 1 ELSE 0 END) AS open_cases,
         SUM(CASE WHEN category='Delivery Delay' THEN 1 ELSE 0 END) AS delivery_delay_cases,
         SUM(CASE WHEN category='Short Shipment' THEN 1 ELSE 0 END) AS short_shipment_cases
  FROM "teched_labs_sandbox"."non_sap".crm_case GROUP BY crm_account_id
)
SELECT
  a.crm_account_id, a.account_name, a.segment, a.billing_country, a.billing_region,
  CASE WHEN REGEXP_LIKE(a.health_score, '^-?[0-9]+$')          THEN CAST(a.health_score AS INTEGER) END AS health_score,
  CASE WHEN REGEXP_LIKE(a.nps, '^-?[0-9]+$')                    THEN CAST(a.nps AS INTEGER) END          AS nps,
  a.churn_risk,
  CASE WHEN REGEXP_LIKE(a.annual_contract_value, '^-?[0-9]+$')  THEN CAST(a.annual_contract_value AS INTEGER) END AS annual_contract_value,
  a.renewal_date, a.csm_owner,
  r.sap_customer_id, r.match_method, r.name_match_difficulty,
  cu.CustomerName, cu.Country, cu.Industry,
  o.otif_pct, o.pct_on_time, o.pct_in_full, o.late AS late_lines, o.short AS short_lines, o.committed_lines,
  COALESCE(ca.open_cases,0) AS open_cases,
  COALESCE(ca.delivery_delay_cases,0) AS delivery_delay_cases,
  COALESCE(ca.short_shipment_cases,0) AS short_shipment_cases
FROM "teched_labs_sandbox"."non_sap".crm_account a
JOIN "<your_space>".v_crm_account_resolved r ON r.crm_account_id = a.crm_account_id
LEFT JOIN "teched_labs_sandbox"."sap_dp".customer cu ON cu.Customer = r.sap_customer_id
LEFT JOIN "<your_space>".v_customer_otif o ON o."Customer" = r.sap_customer_id
LEFT JOIN cases ca ON ca.crm_account_id = a.crm_account_id
WHERE a.churn_risk <> 'Unmanaged';
```

---

## Make it a product (materialize + the payoff)

`v_crm_account_360` is your deliverable — the asset that becomes a **Primary Data Product**. Materialize it the Exercise 1 way: enable a **Raw Reflection** so downstream consumers (the ontology, the agent) get fast, stable responses off a single logical source.

```sql
ALTER DATASET "<your_space>".v_crm_account_360
CREATE RAW REFLECTION crm360_raw
USING DISPLAY (
  crm_account_id, account_name, segment, churn_risk, annual_contract_value, renewal_date,
  sap_customer_id, match_method, CustomerName, Country, Industry,
  otif_pct, pct_on_time, pct_in_full, late_lines, open_cases, delivery_delay_cases
);
```

Now prove the thread you set out to find:
```sql
-- delivery performance by churn tier
SELECT churn_risk, COUNT(*) accounts, ROUND(AVG(otif_pct),1) avg_otif,
       ROUND(AVG(nps),1) avg_nps, ROUND(AVG(open_cases),1) avg_open_cases
FROM "<your_space>".v_crm_account_360
GROUP BY churn_risk ORDER BY avg_otif;
```
> **You should see** a clean gradient — At Risk ≈ **79%** OTIF / NPS **-21** / **~13** open cases; Watch ≈ 82% / +11 / ~6; Healthy ≈ **93%** / +25 / ~2. The CRM's churn signal tracks SAP delivery performance — surfaced by the join, not assumed.

```sql
-- the money query: at-risk, high-value renewals, with how each was resolved
SELECT account_name, sap_customer_id, otif_pct, late_lines, open_cases,
       annual_contract_value, renewal_date, match_method
FROM "<your_space>".v_crm_account_360
WHERE churn_risk='At Risk' ORDER BY otif_pct ASC LIMIT 10;
```
> **You should see** at-risk renewals worth real money, each with low OTIF, many late lines and open delivery cases — some resolved by `fuzzy_auto`, others only by `mdm_resolved`. That contrast *is* the MDM narrative on screen.

## Ontology mapping (hand-off to Exercise 2)

The product truth you built maps 1:1 to ontology concepts for the BDC Ontology editor:

| Ontology concept | Dremio object | Key relationships |
|---|---|---|
| `crm:Account` | `v_crm_account_360` | `resolvesTo → sap:Customer` (via `sap_customer_id`; provenance in `match_method`) |
| `crm:Case` | `non_sap.crm_case` | `about → crm:Account`; `references → sap:SalesOrder` (`related_sales_order`) |
| `crm:Opportunity` | `non_sap.crm_opportunity` | `for → crm:Account` (renewals / upsells) |
| `crm:Contact` | `non_sap.crm_contact` | `at → crm:Account` |
| `sap:Customer` | `sap_dp.customer` | `placesOrder → sap:SalesOrderItem → hasOutcome → OTIF` (via `v_customer_otif`) |

That `resolvesTo` edge is where the hybrid MDM lives. Today it's a crosswalk column; as a published data product in BDC, it's a governed relationship — and the thing Joule traverses to answer *"which renewals are at risk because of our delivery performance?"*

## Screenshots to capture (for authors)

- [ ] CRM raw data (`crm_account`, `crm_case`) previews
- [ ] The normalization `SELECT` showing matched vs. unmatchable names
- [ ] `v_crm_account_resolved` `match_method` split
- [ ] `v_crm_account_360` red-thread query (OTIF by churn tier) and the at-risk-renewals money query

> **Author note:** all three views and every query here were **built and validated live** against the lab Dremio (project `7448000a-…`) on 2026-10-13, in `"teched_labs_sandbox"."hands-on-test"."ex-crm"`. The student instructions target `<your_space>`; the reference build is in that shared folder. Full DDL: [`crm_resolution_and_360.sql`](./crm_resolution_and_360.sql).

## Summary

You brought a non-SAP CRM source into the Dremio semantic layer, resolved its accounts to governed SAP customers with a hybrid SQL + golden-crosswalk approach (honest about where a real MDM takes over), and built a materialized, ontology-ready **golden account product** that unifies churn, cases, and renewals with real SAP OTIF. Modeled as SQL today; a **Primary Data Product** tomorrow. Exercise 2 turns it into an ontology; Exercise 3's agent uses it to explain which renewals are at risk — and why.

Continue to - [Exercise 2 - Ontologies on the Golden Record](../ex2/README.md)
