-- =============================================================================
-- Exercise (CRM): Bring a non-SAP CRM into the lakehouse + resolve it to SAP.
--
-- The data-product lens: each object below is a SQL view (materialized with a
-- reflection) that stands in as a "current product truth" proxy. In the SAP
-- Business Data Cloud Lakehouse these become Primary Data Products -- governed,
-- discoverable -- that Joule turns into derived data products from intent. The
-- engines + reflections you use here persist into that story.
--
-- HOW TO RUN: replace <your_space> with your personal Dremio space (students each
-- build their own copy). Leave the SHARED, read-only sources as-is:
--   "teched_labs_sandbox"."sap_dp".{salesorderitem, customer}
--   "teched_labs_sandbox"."non_sap".{crm_account, crm_case, crm_account_resolution_xref}
--
-- VALIDATED live 2026-10-13 against Dremio Cloud project 7448000a-... in the
-- reference space "teched_labs_sandbox"."hands-on-test"."ex-crm".
--
-- Note: CRM CSV columns import as VARCHAR -> guarded casts below (same pattern as
-- Exercise 1's quantity cast).
-- =============================================================================

-- 1) Per-customer OTIF truth (recent window; committed-line on-time + SD-status in-full)
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

-- 2) Hybrid Account -> Customer resolution.
--    "Fuzzy" here is a few regex normalizations in Dremio SQL -- enough to auto-resolve the
--    easy names and SEE the problem, but a proxy. A real deployment uses an MDM solution
--    (ER in Zingg/Splink, PLUS survivorship, stewardship, confidence, a maintained golden
--    crosswalk). Here crm_account_resolution_xref stands in for that MDM output; match_method
--    records which path resolved each account (fuzzy_auto vs mdm_resolved vs ambiguous_needs_mdm).
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

-- 3) Ontology-ready golden account product (CRM + resolved customer + OTIF + cases).
--    This is the asset you materialize and that becomes a Primary Data Product.
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

-- 4) Materialize the product: a Raw Reflection makes v_crm_account_360 fast + stable for the
--    ontology and the agent -- the "product truth" acceleration that persists into BDC.
ALTER DATASET "<your_space>".v_crm_account_360
CREATE RAW REFLECTION crm360_raw
USING DISPLAY (
  crm_account_id, account_name, segment, churn_risk, annual_contract_value, renewal_date,
  sap_customer_id, match_method, CustomerName, Country, Industry,
  otif_pct, pct_on_time, pct_in_full, late_lines, open_cases, delivery_delay_cases
);
