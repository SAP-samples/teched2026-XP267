# Synthetic non-SAP CRM — Sales-Order / OTIF scenario

A synthetic **3rd-party CRM** source for the published Sales-Order OTIF demo. It exists to be
turned into an **ontology** and used as **agentic context** alongside the governed SAP data
products (`customer`, `salesorderitem`) that were taken into the target environment.

## The red thread (why this is relevant, not just adjacent)

Every CRM signal is derived **deterministically from each account's real published OTIF**
(`_seed_customer_otif.csv`, extracted from `otif-demo-bdc.otif_demo.mv_otif_sales_fulfillment`,
recent window 2023+). Worse OTIF → lower NPS/health, more Delivery-Delay / Short-Shipment cases,
higher churn risk, at-risk renewals. The relationship is **planted** so an agent can *discover*
it; the ground-truth crosswalk is never exposed as a feature. Validated gradient (managed book,
52 accounts ≥100 order lines):

| OTIF tier | accounts | avg NPS | avg health | avg open+closed cases | % At Risk |
|---|---|---|---|---|---|
| excellent (95%+) | 3 | 51 | 96 | 1 | 0% |
| good (90–95) | 12 | 30 | 91 | 8 | 0% |
| fair (80–90) | 15 | 5 | 82 | 20 | 0% |
| poor (70–80) | 22 | −22 | 79 | 20 | 100% |

The long tail (177 low-volume customers) is kept as lightweight **unmanaged SMB** account rows
(`churn_risk=Unmanaged`, no cases/opps) — ontology coverage without small-sample distortion.

## Files

| File | Rows | Role |
|---|---|---|
| `crm_account.csv` | 229 | Account (52 managed + 177 SMB). Health, NPS, churn_risk, ACV, renewal_date, CSM |
| `crm_contact.csv` | 208 | Contacts per managed account |
| `crm_case.csv` | 843 | Support cases; `category` ∈ Delivery Delay / Short Shipment / Billing / Quality; `related_sales_order` links **669** to real SAP sales orders |
| `crm_opportunity.csv` | 56 | Renewal / Upsell opportunities; stage reflects churn risk |
| `crm_account_resolution_xref.csv` | 229 | **Ground truth** (never a feature): `crm_account_id → sap_customer_id`, clean name, noised name, match difficulty |

## Crosswalk = BOTH (clean + fuzzy)

- **Fuzzy (MDM moment):** `crm_account.account_name` is **noised** (legal suffixes `Inc./GmbH/S.A. de C.V.`,
  abbreviations, initials, typos; ~70% easy / 22% hard / 8% opaque). Resolve it back to
  `sap:Customer` by name + `billing_region` — the MDM-style entity-resolution exercise.
- **Clean:** `crm_account_resolution_xref.csv` gives the true `sap_customer_id` for a trivial join
  and for scoring the fuzzy match.

## Ontology (classes + relationships)

```
crm:Account ──has──▶ crm:Contact
crm:Account ──has──▶ crm:Case          (category, priority, status)
crm:Account ──has──▶ crm:Opportunity   (type: Renewal | Upsell)
crm:Case  ──references──▶ sap:SalesOrder            (via related_sales_order — real join)
crm:Account ──resolvesTo──▶ sap:Customer            (via xref / fuzzy name match)
        sap:Customer ──placesOrder──▶ sap:SalesOrderItem ──hasOutcome──▶ OTIF (on-time / in-full)
```

Join keys back to the published SAP side:
- `crm_account_resolution_xref.sap_customer_id` = `salesorderitem.SoldToParty` = `customer.Customer`
- `crm_case.related_sales_order` = `salesorderitem.SalesOrder`

## Agentic money questions this unlocks

- *"Which renewals are at risk, and is our own delivery performance the cause?"*
  (Opportunity[Renewal, At Risk] → Account → OTIF from SAP + open Delivery-Delay cases)
- *"US Large Cycles 5 renews soon — build the account brief."* → OTIF %, late-order count, open
  cases (with the actual SAP sales-order numbers), NPS, ACV, recommended recovery actions.
- *"Rank my book of business by churn risk driven by OTIF."*

## Regenerate

```
python3 -I generate.py            # rewrite all CRM CSVs (deterministic, SEED=42)
python3 -I generate.py --validate # + integrity asserts + the red-thread proof table above
```

Pure stdlib. The two `_seed_*.csv` files are the frozen inputs (no live DB dependency at
generation time); re-extract them only if the underlying sales OTIF MV changes.
