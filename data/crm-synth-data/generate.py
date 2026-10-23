#!/usr/bin/env python3
"""
Synthetic non-SAP CRM generator for the Sales-Order / OTIF scenario.

The "red thread": every CRM signal is derived DETERMINISTICALLY from each account's
*real* published OTIF performance (data/crm-synth-data/_seed_customer_otif.csv, extracted
from otif-demo-bdc.otif_demo.mv_otif_sales_fulfillment). Worse OTIF -> lower NPS/health,
more Delivery-Delay / Short-Shipment cases, higher churn risk, at-risk renewals. The link
is planted so an agent can *discover* it; the ground-truth crosswalk is never a feature.

Pure stdlib (csv, random, datetime). Deterministic via SEED=42. No live DB dependency —
the two _seed_*.csv files are the frozen inputs.

Crosswalk = BOTH:
  - crm_account.csv carries a NOISED account_name (legal suffixes, abbreviations) -> the
    fuzzy entity-resolution exercise (Splink/Zingg-style) back to sap:Customer.
  - crm_account_resolution_xref.csv carries the hidden true sap_customer_id -> clean join
    and ER scoring truth.

Usage:
    python3 -I generate.py            # regenerate all CRM CSVs
    python3 -I generate.py --validate # regenerate + assert integrity + print red-thread proof
"""
import csv, sys, random
from datetime import date, timedelta

SEED = 42
rng = random.Random(SEED)
HERE = __file__.rsplit("/", 1)[0] if "/" in __file__ else "."
TODAY = date(2026, 10, 13)
MIN_LINES = 100   # accounts below this are the long tail: lightweight unmanaged SMB rows,
                  # no managed CRM activity (keeps ontology coverage without small-sample distortion)

CSM_POOL = ["Dana Whitfield", "Marco Lentz", "Priya Nair", "Tom Becker", "Sofia Alvarez", "Lars Jensen"]
ROLES = ["Procurement Lead", "Supply Chain Manager", "Operations Director", "Buyer",
         "VP Supply Chain", "Logistics Coordinator"]
FIRST = ["Alex", "Jordan", "Sam", "Riley", "Casey", "Morgan", "Jamie", "Taylor", "Chris", "Robin",
         "Lena", "Nils", "Mateo", "Ingrid", "Paulo", "Hannah"]
LAST = ["Meyer", "Novak", "Harris", "Okafor", "Bianchi", "Fischer", "Reyes", "Walsh", "Kraus", "Santos"]
LEGAL = {"US": ["Inc.", "LLC", "Co.", "Corp."], "MX": ["S.A. de C.V.", "S. de R.L."],
         "DE": ["GmbH", "AG", "KG"], "_": ["Ltd.", "Group"]}


def write_csv(name, header, rows):
    with open(f"{HERE}/{name}", "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow([r[c] for c in header])


def slug(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


# --- name noising for the fuzzy crosswalk -----------------------------------
def noise_name(name, country, difficulty):
    suffix = rng.choice(LEGAL.get(country, LEGAL["_"]))
    if difficulty == "easy":
        style = rng.choice(["suffix", "ampersand", "asis"])
        if style == "suffix":
            return f"{name} {suffix}"
        if style == "ampersand":
            return name.replace(" and ", " & ")
        return name
    if difficulty == "hard":
        toks = name.split()
        style = rng.choice(["abbrev", "drop", "initials", "typo"])
        if style == "abbrev" and len(toks) > 1:
            toks[0] = toks[0][:3].upper() + "."
            return " ".join(toks) + f" {suffix}"
        if style == "drop" and len(toks) > 2:
            return " ".join(toks[:-1]) + f" {suffix}"
        if style == "initials" and len(toks) > 1:
            return "".join(t[0] for t in toks).upper() + f" {suffix}"
        # typo
        s = list(name)
        if len(s) > 4:
            p = rng.randrange(len(s))
            s[p] = rng.choice("aeiorXZ")
        return "".join(s) + f" {suffix}"
    # opaque
    return f"{slug(name)[:6].upper()}-{rng.randrange(100,999)}"


# --- OTIF tier -> CRM signal mapping (the planted red thread) ----------------
def tier_of(otif):
    if otif >= 95: return "excellent"
    if otif >= 90: return "good"
    if otif >= 80: return "fair"
    if otif >= 70: return "poor"
    return "critical"

NPS_BAND = {"excellent": (40, 70), "good": (10, 40), "fair": (-10, 20),
            "poor": (-40, 0), "critical": (-70, -20)}
CHURN_BASE = {"excellent": "Healthy", "good": "Healthy", "fair": "Watch",
              "poor": "At Risk", "critical": "At Risk"}


def segment_of(lines):
    if lines >= 1000: return "Strategic"
    if lines >= 300:  return "Enterprise"
    if lines >= 100:  return "Mid-Market"
    return "SMB"


def main(validate=False):
    seed = list(csv.DictReader(open(f"{HERE}/_seed_customer_otif.csv")))
    late = {}
    for r in csv.DictReader(open(f"{HERE}/_seed_late_orders.csv")):
        late.setdefault(r["SoldToParty"], []).append(r["SalesOrder"])

    accounts, contacts, cases, opps, xref = [], [], [], [], []
    cid = coid = caid = oid = 0

    for i, s in enumerate(sorted(seed, key=lambda x: -int(x["lines"])), start=1):
        sap_id = s["SoldToParty"]; cname = s["customer_name"] or sap_id
        country = s["country"] or "US"; region = s["region"] or ""
        lines = int(s["lines"]); otif = float(s["otif_pct"])
        late_n = int(s["late"]); short_n = int(s["short"]); qty = int(s["total_req_qty"])
        tier = tier_of(otif); seg = segment_of(lines)
        acc_id = f"ACC-{i:05d}"

        difficulty = rng.choices(["easy", "hard", "opaque"], weights=[70, 22, 8])[0]
        disp_name = noise_name(cname, country, difficulty)
        xref.append(dict(crm_account_id=acc_id, sap_customer_id=sap_id,
                         account_name_clean=cname, account_name_crm=disp_name,
                         name_match_difficulty=difficulty))

        if lines < MIN_LINES:   # long tail: lightweight SMB row, no managed CRM activity
            accounts.append(dict(crm_account_id=acc_id, account_name=disp_name,
                                 billing_country=country, billing_region=region, segment="SMB",
                                 health_score="", nps="", churn_risk="Unmanaged",
                                 annual_contract_value=max(5000, round(qty * rng.uniform(8, 25), -3)),
                                 renewal_date="", csm_owner=""))
            continue

        # case volume is driven by the REAL late+short counts (planted link to OTIF)
        n_cases = min(25, round((late_n + short_n) / 25))
        lo, hi = NPS_BAND[tier]; nps = round(min(hi, max(lo, rng.gauss((lo + hi) / 2, 12))))
        # health is a COMPOSITE of sentiment + support load, not a copy of OTIF (avoids leakage)
        health = max(0, min(100, round(70 + nps * 0.4 - n_cases * 1.0 + rng.gauss(0, 4))))
        churn = CHURN_BASE[tier]
        if rng.random() < 0.12:  # small realistic noise flip
            churn = rng.choice(["Healthy", "Watch", "At Risk"])
        acv = max(25000, round(qty * rng.uniform(8, 25), -3))
        # renewals: at-risk accounts biased into the next 60-90 days (demo anchors)
        if churn == "At Risk" and rng.random() < 0.5:
            renewal = TODAY + timedelta(days=rng.randint(25, 90))
        else:
            renewal = TODAY + timedelta(days=rng.randint(30, 365))
        csm = CSM_POOL[(hash(sap_id) % len(CSM_POOL))]

        accounts.append(dict(crm_account_id=acc_id, account_name=disp_name,
                             billing_country=country, billing_region=region, segment=seg,
                             health_score=health, nps=nps, churn_risk=churn,
                             annual_contract_value=int(acv), renewal_date=renewal.isoformat(),
                             csm_owner=csm))

        # contacts
        ncontacts = {"Strategic": 4, "Enterprise": 3, "Mid-Market": 2, "SMB": 1}[seg]
        dom = slug(cname)[:16] or slug(sap_id)
        for _ in range(ncontacts):
            cid += 1; fn = rng.choice(FIRST); ln = rng.choice(LAST)
            contacts.append(dict(contact_id=f"CON-{cid:06d}", crm_account_id=acc_id,
                                 full_name=f"{fn} {ln}", role=rng.choice(ROLES),
                                 email=f"{fn.lower()}.{ln.lower()}@{dom}.com"))

        # cases: split by cause, linked to REAL late orders where available
        for _ in range(n_cases):
            caid += 1
            is_delay = rng.random() < (late_n / max(1, late_n + short_n))
            cat = "Delivery Delay" if is_delay else "Short Shipment"
            if rng.random() < 0.1:
                cat = rng.choice(["Billing Dispute", "Quality Complaint"])
            rel = ""
            if cat in ("Delivery Delay", "Short Shipment") and late.get(sap_id):
                rel = rng.choice(late[sap_id])
            opened = TODAY - timedelta(days=rng.randint(1, 270))
            status = "Open" if (churn == "At Risk" and rng.random() < 0.5) or rng.random() < 0.3 else "Closed"
            pri = rng.choices(["Low", "Medium", "High"],
                              weights=[2, 3, 5] if churn == "At Risk" else [5, 3, 1])[0]
            cases.append(dict(case_id=f"CASE-{caid:06d}", crm_account_id=acc_id, category=cat,
                              priority=pri, status=status, opened_date=opened.isoformat(),
                              related_sales_order=rel))

        # opportunities: a renewal for every named account; upsell for healthy larger ones
        if seg != "SMB":
            oid += 1
            stage = {"At Risk": "Negotiation", "Watch": "Proposal",
                     "Healthy": "Renewal Booked"}[churn]
            opps.append(dict(opportunity_id=f"OPP-{oid:06d}", crm_account_id=acc_id,
                             opportunity_type="Renewal", stage=stage, amount=int(acv),
                             close_date=renewal.isoformat(),
                             forecast_category="Commit" if churn == "Healthy" else "Upside"))
            if churn == "Healthy" and seg in ("Strategic", "Enterprise") and rng.random() < 0.5:
                oid += 1
                opps.append(dict(opportunity_id=f"OPP-{oid:06d}", crm_account_id=acc_id,
                                 opportunity_type="Upsell", stage="Qualification",
                                 amount=int(acv * rng.uniform(0.1, 0.4)),
                                 close_date=(TODAY + timedelta(days=rng.randint(60, 300))).isoformat(),
                                 forecast_category="Pipeline"))

    write_csv("crm_account.csv",
              ["crm_account_id", "account_name", "billing_country", "billing_region", "segment",
               "health_score", "nps", "churn_risk", "annual_contract_value", "renewal_date", "csm_owner"],
              accounts)
    write_csv("crm_contact.csv",
              ["contact_id", "crm_account_id", "full_name", "role", "email"], contacts)
    write_csv("crm_case.csv",
              ["case_id", "crm_account_id", "category", "priority", "status", "opened_date",
               "related_sales_order"], cases)
    write_csv("crm_opportunity.csv",
              ["opportunity_id", "crm_account_id", "opportunity_type", "stage", "amount",
               "close_date", "forecast_category"], opps)
    write_csv("crm_account_resolution_xref.csv",
              ["crm_account_id", "sap_customer_id", "account_name_clean", "account_name_crm",
               "name_match_difficulty"], xref)

    print(f"accounts={len(accounts)} contacts={len(contacts)} cases={len(cases)} "
          f"opportunities={len(opps)} xref={len(xref)}")
    linked = sum(1 for c in cases if c["related_sales_order"])
    print(f"cases linked to a real SalesOrder: {linked}/{len(cases)}")

    if validate:
        sap_ids = {s["SoldToParty"] for s in seed}
        assert all(x["sap_customer_id"] in sap_ids for x in xref), "xref points to unknown customer"
        assert len({a["crm_account_id"] for a in accounts}) == len(accounts), "dup account id"
        # red-thread proof: signals must worsen monotonically as OTIF tier worsens
        from statistics import mean
        by = {}
        o = {a["crm_account_id"]: a for a in accounts}
        ncases = {}
        for c in cases: ncases[c["crm_account_id"]] = ncases.get(c["crm_account_id"], 0) + 1
        for s in seed:
            if int(s["lines"]) < MIN_LINES:
                continue
            acc = next(a for a, x in zip(accounts, xref) if x["sap_customer_id"] == s["SoldToParty"])
            by.setdefault(tier_of(float(s["otif_pct"])), []).append(
                (acc["nps"], acc["health_score"], ncases.get(acc["crm_account_id"], 0),
                 1 if acc["churn_risk"] == "At Risk" else 0))
        print("\nRED-THREAD PROOF  (OTIF tier -> CRM signals)")
        print(f"  {'tier':10} {'n':>4} {'avg_nps':>8} {'avg_health':>11} {'avg_cases':>10} {'%at_risk':>9}")
        for t in ["excellent", "good", "fair", "poor", "critical"]:
            v = by.get(t)
            if not v: continue
            print(f"  {t:10} {len(v):>4} {mean(x[0] for x in v):>8.1f} {mean(x[1] for x in v):>11.1f} "
                  f"{mean(x[2] for x in v):>10.2f} {100*mean(x[3] for x in v):>8.0f}%")


if __name__ == "__main__":
    main(validate="--validate" in sys.argv)
