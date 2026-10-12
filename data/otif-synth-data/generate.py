#!/usr/bin/env python3
"""
Coherent synthetic-data generator for the Vertex MES <-> SAP S/4 MDM lab (lab-03).

Pure stdlib (csv, random, datetime) — no faker/pandas/numpy. Deterministic via SEED.

One machine-identity catalog is the single source of truth. Both systems derive from it:
  - Vertex MES  : rich human machine names   (equipment_id=VTX-CNC-###, "Haas VF-4 #14")
  - SAP S/4     : 8-digit numeric IDs + SAP mnemonic names, name-noised
The overlap (with ~15% non-matches per side) is the MDM / entity-resolution problem
Splink resolves in lab-03. ground_truth_xref.csv is the scoring truth (never a feature).

Usage:
    python generate.py            # regenerate all CSVs
    python generate.py --validate # regenerate + assert integrity + print noise spot-check

NOTE ON TEMPORAL CORRELATION: a handful of downtime/quality events are placed shortly
before their linked work order's actual-end slip as an *internal, illustrative* signal.
Genuine cross-system correlation runs against the live SAP productionorderconfirmation
data on Databricks (Delta Share) — that table is NOT in this repo.
"""
import csv
import random
import sys
from datetime import datetime, timezone

SEED = 42
rng = random.Random(SEED)

HERE = __file__.rsplit("/", 1)[0] if "/" in __file__ else "."

# --- time window: ~6 months of 2026, epoch-millis (matches existing convention) ---
WIN_START = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
WIN_END = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000)
DAY_MS = 86_400_000
HOUR_MS = 3_600_000


def ts():
    return rng.randint(WIN_START, WIN_END)


# --- row-count targets (preserved so labs 01/02 numbers hold) ---
N_EQUIP = 100
N_WO = 200
N_DOWN = 150
N_QUAL = 150
N_COUNT = 150
N_OEE = 120

# --- SAP coverage tuning ---
N_SAP_ONLY = 10          # SAP work centers with no Vertex counterpart
FRAC_VERTEX_ONLY = 0.15  # Vertex machines with no SAP counterpart

# ---------------------------------------------------------------------------
# Machine-identity catalog: (make, model) grouped by equipment_type.
# SAP mnemonic base per type is what a real SAP work-center name tends to look like.
# ---------------------------------------------------------------------------
CATALOG = {
    "CNC_MILL": {
        "mnemonic": "MILL",
        "models": [("Haas", "VF-2"), ("Haas", "VF-4"), ("Haas", "VF-6"),
                   ("DMG Mori", "DMU 50"), ("Mazak", "VCN-530"), ("Okuma", "Genos M560")],
    },
    "CNC_LATHE": {
        "mnemonic": "LATHE",
        "models": [("DMG Mori", "NLX 2500"), ("Mazak", "QTN-350"),
                   ("Okuma", "Genos L3000"), ("Haas", "ST-20"), ("Doosan", "Lynx 2100")],
    },
    "CMM": {
        "mnemonic": "INSP",
        "models": [("Zeiss", "Contura"), ("Hexagon", "Global S"),
                   ("Mitutoyo", "Crysta-Apex"), ("Zeiss", "Prismo")],
    },
    "ASSEMBLY_CELL": {
        "mnemonic": "ASM",
        "models": [("FANUC", "R-2000"), ("KUKA", "KR-16"),
                   ("Bosch Rexroth", "Line-A"), ("ABB", "IRB-6700")],
    },
}
TYPES = list(CATALOG.keys())

VENDOR_ABBREV = {
    "Haas": "HAAS", "DMG Mori": "DMG", "Mazak": "MZK", "Okuma": "OKM",
    "Doosan": "DSN", "Zeiss": "ZSS", "Hexagon": "HEX", "Mitutoyo": "MIT",
    "FANUC": "FAN", "KUKA": "KUKA", "Bosch Rexroth": "BR", "ABB": "ABB",
}
PLANTS_SAP = ["R300", "R301", "R302"]
LOCATIONS = ["BAY-1", "BAY-2", "BAY-3", "CELL-N", "CELL-S", "QC-LAB"]
RESPONSIBLES = ["SUP-014", "SUP-021", "SUP-033", "SUP-045", "SUP-052"]
STATUSES = ["ACTIVE", "MAINTENANCE", "DECOMMISSIONED"]
VTX_WC_LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]


def write_csv(name, header, rows):
    """Alphabetically-ordered columns, minimal quoting (matches existing files)."""
    assert header == sorted(header), f"{name}: header not alphabetical: {header}"
    with open(f"{HERE}/{name}", "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow([r[c] for c in header])


# ---------------------------------------------------------------------------
# 1. Build the 100 physical machines (the backbone).
# ---------------------------------------------------------------------------
def build_machines():
    machines = []
    for i in range(1, N_EQUIP + 1):
        etype = rng.choice(TYPES)
        make, model = rng.choice(CATALOG[etype]["models"])
        machines.append({
            "idx": i,
            "equipment_id": f"VTX-CNC-{i:03d}",
            "make": make,
            "model": model,
            "unit_no": i,                     # unit number == machine index (recoverable token)
            "equipment_type": etype,
            "equipment_name": f"{make} {model} #{i}",
            "status": rng.choice(STATUSES),
            "commissioned_date": ts(),
        })
    return machines


# ---------------------------------------------------------------------------
# 2. Name-noise transforms (SAP-side). Graded difficulty; ~90% keep a recoverable
#    unit-number token so the match is solvable.
# ---------------------------------------------------------------------------
def sap_name(m, difficulty):
    """difficulty in {'easy','hard','opaque'}."""
    make, model, unit = m["make"], m["model"], m["unit_no"]
    mnem = CATALOG[m["equipment_type"]]["mnemonic"]

    if difficulty == "opaque":
        # Fully opaque SAP mnemonic — no recoverable make/model token.
        return f"Z_{mnem}_{rng.choice(VTX_WC_LETTERS)}"

    # model core token, e.g. "VF-4" -> "VF4"; "NLX 2500" -> "NLX2500"
    core = model.replace("-", "").replace(" ", "").upper()
    vend = VENDOR_ABBREV[make]

    if difficulty == "easy":
        style = rng.choice(["mnemonic", "delimiter", "abbrev"])
        if style == "mnemonic":                       # MILL_VF4_14
            return f"{mnem}_{core}_{unit}"
        if style == "delimiter":                      # HAAS VF4 14 / HAAS-VF4-14
            d = rng.choice([" ", "-", "_"])
            return f"{vend}{d}{core}{d}{unit}"
        return f"{vend}{core}{unit}"                   # HAASVF414

    # hard: heavier corruption (typo / suffix-drop / reorder / odd unit format)
    style = rng.choice(["typo", "suffixdrop", "reorder", "unitfmt"])
    if style == "typo":
        s = f"{vend} {core} {unit}"
        if len(s) > 3:
            p = rng.randrange(len(s))
            s = s[:p] + rng.choice("XZQO") + s[p + 1:]
        return s
    if style == "suffixdrop":                         # drop discriminating model digits: NLX2500 -> NLX
        stripped = "".join(ch for ch in core if not ch.isdigit()) or core
        return f"{mnem}_{stripped}_{unit}"
    if style == "reorder":                            # VF4 HAAS 14
        return f"{core} {vend} {unit}"
    # unitfmt: unusual unit token
    ufmt = rng.choice([f"-{unit}", f"U{unit}", f" {unit:03d}"])
    return f"{mnem}_{core}{ufmt}"


# ---------------------------------------------------------------------------
# 3. Build the two masters + ground truth.
# ---------------------------------------------------------------------------
def build_masters(machines):
    # Which Vertex machines get a SAP counterpart?
    shuffled = machines[:]
    rng.shuffle(shuffled)
    n_vertex_only = int(round(N_EQUIP * FRAC_VERTEX_ONLY))
    matched = shuffled[n_vertex_only:]                # ~85 machines are shared

    sap_rows, xref_rows = [], []
    next_sap_id = 10_000_600                          # distinct band from real IDs (10000040 etc.)

    # difficulty mix over matched machines: ~70 easy / ~20 hard / ~10 opaque
    diffs = (["easy"] * int(len(matched) * 0.70)
             + ["hard"] * int(len(matched) * 0.20))
    diffs += ["opaque"] * (len(matched) - len(diffs))
    rng.shuffle(diffs)

    for m, diff in zip(matched, diffs):
        wcid = str(next_sap_id); next_sap_id += 1
        cat = "0007" if m["equipment_type"] == "ASSEMBLY_CELL" else "0001"
        sap_rows.append({
            "Plant": rng.choice(PLANTS_SAP),
            "WorkCenter": sap_name(m, diff),
            "WorkCenterCategoryCode": cat,
            "WorkCenterInternalID": wcid,
            "WorkCenterLocation": rng.choice(LOCATIONS),
            "WorkCenterResponsible": rng.choice(RESPONSIBLES),
            "WorkCenterTypeCode": m["equipment_type"],
        })
        xref_rows.append({"WorkCenterInternalID": wcid, "equipment_id": m["equipment_id"]})

    # SAP-only work centers (no Vertex counterpart) — non-Vertex plant machines
    for _ in range(N_SAP_ONLY):
        wcid = str(next_sap_id); next_sap_id += 1
        etype = rng.choice(TYPES)
        make, model = rng.choice(CATALOG[etype]["models"])
        ghost = {"make": make, "model": model, "unit_no": rng.randint(200, 299),
                 "equipment_type": etype}
        cat = "0007" if etype == "ASSEMBLY_CELL" else "0001"
        sap_rows.append({
            "Plant": rng.choice(PLANTS_SAP),
            "WorkCenter": sap_name(ghost, rng.choice(["easy", "hard"])),
            "WorkCenterCategoryCode": cat,
            "WorkCenterInternalID": wcid,
            "WorkCenterLocation": rng.choice(LOCATIONS),
            "WorkCenterResponsible": rng.choice(RESPONSIBLES),
            "WorkCenterTypeCode": etype,
        })

    rng.shuffle(sap_rows)
    return sap_rows, xref_rows


# ---------------------------------------------------------------------------
# 4. Vertex equipment.csv (schema unchanged).
# ---------------------------------------------------------------------------
def build_equipment(machines):
    rows = []
    for m in machines:
        letter = VTX_WC_LETTERS[(m["idx"] - 1) % len(VTX_WC_LETTERS)]
        rows.append({
            "commissioned_date": m["commissioned_date"],
            "equipment_id": m["equipment_id"],
            "equipment_name": m["equipment_name"],
            "equipment_type": m["equipment_type"],
            "plant_code": "VTX-PLT-01",
            "status": m["status"],
            "work_center_id": f"VTX-WC-MILL-{letter}",
            "work_center_name": f"Milling Center {letter}",
        })
    return rows


# ---------------------------------------------------------------------------
# 5. Transactional tables (all reference valid equipment_id / work_order_id).
# ---------------------------------------------------------------------------
def build_work_orders(machines):
    rows = []
    for i in range(1, N_WO + 1):
        m = rng.choice(machines)
        p_start = ts()
        p_end = p_start + rng.randint(1, 20) * DAY_MS
        a_start = p_start + rng.randint(-2, 3) * DAY_MS
        a_end = a_start + rng.randint(1, 25) * DAY_MS
        planned = rng.randint(100, 1000)
        completed = rng.randint(int(planned * 0.4), planned)
        rows.append({
            "actual_end": a_end,
            "actual_start": a_start,
            "completed_qty": completed,
            "customer_po_ref": rng.choice(["", str(rng.randint(700000, 999999))]),
            "equipment_id": m["equipment_id"],
            "material_number": f"VTX-MAT-{rng.choice(VTX_WC_LETTERS)}-{rng.randint(100, 999)}",
            "planned_end": p_end,
            "planned_qty": planned,
            "planned_start": p_start,
            "sap_material_xref": str(rng.randint(30000000, 99999999)),
            "scrap_qty": rng.randint(0, 50),
            "status": rng.choice(["RELEASED", "IN_PROGRESS", "COMPLETED"]),
            "work_order_id": f"VTX-WO-2026-{i:06d}",
        })
    return rows


def build_downtime(machines, wo_rows):
    rows, corr = [], 0
    reasons = {"MECHANICAL": ["SPINDLE_FAULT", "TOOL_WEAR", "BEARING"],
               "ELECTRICAL": ["DRIVE_FAULT", "SENSOR_ERR"],
               "MATERIAL": ["MATERIAL_WAIT"], "OPERATOR": ["SETUP"],
               "PLANNED": ["PM"]}
    late_wos = [w for w in wo_rows if w["actual_end"] > w["planned_end"]]
    for i in range(1, N_DOWN + 1):
        cat = rng.choice(list(reasons))
        m = rng.choice(machines)
        wo_id = ""
        start = ts()
        # place ~5 events 6-24h before a late order's actual_end (illustrative correlation)
        if corr < 5 and late_wos and rng.random() < 0.15:
            w = rng.choice(late_wos)
            start = max(WIN_START, w["actual_end"] - rng.randint(6, 24) * HOUR_MS)
            wo_id = w["work_order_id"]
            m_id = w["equipment_id"]
            corr += 1
        else:
            m_id = m["equipment_id"]
            if rng.random() < 0.7:
                wo_id = rng.choice(wo_rows)["work_order_id"]
        dur = round(rng.uniform(15, 300), 2)
        rows.append({
            "downtime_id": f"DWN-{i:06d}",
            "duration_minutes": dur,
            "end_ts": start + int(dur * 60_000),
            "equipment_id": m_id,
            "operator_id": f"OPR-{rng.randint(1, 40):04d}",
            "planned_flag": str(cat == "PLANNED").lower(),
            "reason_category": cat,
            "reason_code": rng.choice(reasons[cat]),
            "shift": rng.choice(["A", "B", "C"]),
            "start_ts": start,
            "work_order_id": wo_id,
        })
    return rows


def build_quality(machines, wo_rows):
    rows, corr = [], 0
    late_wos = [w for w in wo_rows if w["actual_end"] > w["planned_end"]]
    for i in range(1, N_QUAL + 1):
        result = rng.choices(["PASS", "FAIL", "CONDITIONAL"], weights=[80, 12, 8])[0]
        w = rng.choice(wo_rows)
        insp = ts()
        if result == "FAIL" and corr < 3 and late_wos and rng.random() < 0.3:
            w = rng.choice(late_wos)
            insp = max(WIN_START, w["actual_end"] - rng.randint(6, 24) * HOUR_MS)
            corr += 1
        rows.append({
            "defect_code": rng.choice(["DIM_OUT_OF_SPEC", "SURFACE_FINISH", "BURR", "POROSITY"]),
            "defect_qty": rng.randint(0, 10),
            "equipment_id": w["equipment_id"],
            "inspection_ts": insp,
            "inspection_type": rng.choice(["IN_PROCESS", "FINAL", "INCOMING"]),
            "lot_number": f"LOT-{i:06d}",
            "quality_event_id": f"QL-{i:06d}",
            "result": result,
            "sample_size": rng.randint(20, 80),
            "work_order_id": w["work_order_id"],
        })
    return rows


def build_counts(wo_rows):
    rows = []
    for i in range(1, N_COUNT + 1):
        w = rng.choice(wo_rows)
        rows.append({
            "count_id": f"PC-{i:06d}",
            "cycle_time_avg_sec": round(rng.uniform(80, 200), 2),
            "equipment_id": w["equipment_id"],
            "good_qty": rng.randint(100, 1000),
            "report_ts": ts(),
            "rework_qty": rng.randint(0, 20),
            "scrap_qty": rng.randint(0, 50),
            "shift": rng.choice(["A", "B", "C"]),
            "work_order_id": w["work_order_id"],
        })
    return rows


def build_oee(machines):
    rows = []
    for i in range(1, N_OEE + 1):
        m = rng.choice(machines)
        avail = round(rng.uniform(0.72, 0.99), 2)
        perf = round(rng.uniform(0.70, 0.99), 2)
        qual = round(rng.uniform(0.80, 0.99), 2)
        ws = ts()
        rows.append({
            "actual_run_minutes": round(rng.uniform(35, 55), 2),
            "availability": avail,
            "equipment_id": m["equipment_id"],
            "good_count": rng.randint(100, 500),
            "ideal_cycle_time_sec": round(rng.uniform(50, 250), 2),
            "oee": round(avail * perf * qual, 2),
            "performance": perf,
            "planned_run_minutes": round(rng.uniform(50, 60), 2),
            "quality": qual,
            "snapshot_id": f"SNP-{i:06d}",
            "total_count": rng.randint(200, 500),
            "window_end": ws + rng.randint(1, 30) * DAY_MS,
            "window_start": ws,
        })
    return rows


def main():
    machines = build_machines()
    equip = build_equipment(machines)
    sap, xref = build_masters(machines)
    wos = build_work_orders(machines)
    down = build_downtime(machines, wos)
    qual = build_quality(machines, wos)
    counts = build_counts(wos)
    oee = build_oee(machines)

    write_csv("equipment.csv",
              ["commissioned_date", "equipment_id", "equipment_name", "equipment_type",
               "plant_code", "status", "work_center_id", "work_center_name"], equip)
    write_csv("sap_work_center.csv",
              ["Plant", "WorkCenter", "WorkCenterCategoryCode", "WorkCenterInternalID",
               "WorkCenterLocation", "WorkCenterResponsible", "WorkCenterTypeCode"], sap)
    write_csv("ground_truth_xref.csv", ["WorkCenterInternalID", "equipment_id"], xref)
    write_csv("work_order.csv",
              ["actual_end", "actual_start", "completed_qty", "customer_po_ref", "equipment_id",
               "material_number", "planned_end", "planned_qty", "planned_start",
               "sap_material_xref", "scrap_qty", "status", "work_order_id"], wos)
    write_csv("downtime_event.csv",
              ["downtime_id", "duration_minutes", "end_ts", "equipment_id", "operator_id",
               "planned_flag", "reason_category", "reason_code", "shift", "start_ts",
               "work_order_id"], down)
    write_csv("quality_event.csv",
              ["defect_code", "defect_qty", "equipment_id", "inspection_ts", "inspection_type",
               "lot_number", "quality_event_id", "result", "sample_size", "work_order_id"], qual)
    write_csv("production_count.csv",
              ["count_id", "cycle_time_avg_sec", "equipment_id", "good_qty", "report_ts",
               "rework_qty", "scrap_qty", "shift", "work_order_id"], counts)
    write_csv("oee_snapshot.csv",
              ["actual_run_minutes", "availability", "equipment_id", "good_count",
               "ideal_cycle_time_sec", "oee", "performance", "planned_run_minutes", "quality",
               "snapshot_id", "total_count", "window_end", "window_start"], oee)

    print(f"Wrote 8 CSVs: equipment={len(equip)} sap_work_center={len(sap)} "
          f"xref={len(xref)} work_order={len(wos)} downtime={len(down)} "
          f"quality={len(qual)} count={len(counts)} oee={len(oee)}")

    if "--validate" in sys.argv:
        validate(machines, equip, sap, xref, wos, down, qual, counts, oee)


def validate(machines, equip, sap, xref, wos, down, qual, counts, oee):
    eq_ids = {m["equipment_id"] for m in equip}
    wo_ids = {w["work_order_id"] for w in wos}
    sap_ids = {s["WorkCenterInternalID"] for s in sap}

    assert (len(equip), len(wos), len(down), len(qual), len(counts), len(oee)) == \
        (N_EQUIP, N_WO, N_DOWN, N_QUAL, N_COUNT, N_OEE), "row counts drifted"

    for tbl, rows in [("downtime", down), ("quality", qual), ("count", counts), ("oee", oee)]:
        bad = [r for r in rows if r["equipment_id"] not in eq_ids]
        assert not bad, f"{tbl}: {len(bad)} rows reference unknown equipment_id"
    for tbl, rows in [("downtime", down), ("quality", qual), ("count", counts)]:
        bad = [r for r in rows if r["work_order_id"] and r["work_order_id"] not in wo_ids]
        assert not bad, f"{tbl}: {len(bad)} rows reference unknown work_order_id"
    assert all(w["equipment_id"] in eq_ids for w in wos), "work_order bad equipment_id"

    for x in xref:
        assert x["equipment_id"] in eq_ids, f"xref bad equipment_id {x['equipment_id']}"
        assert x["WorkCenterInternalID"] in sap_ids, f"xref bad WCID {x['WorkCenterInternalID']}"

    matched_eq = {x["equipment_id"] for x in xref}
    print(f"\nVALIDATE OK — referential integrity holds.")
    print(f"  matches (ground truth) : {len(xref)}")
    print(f"  vertex-only (no SAP)   : {N_EQUIP - len(matched_eq)}")
    print(f"  sap-only (no vertex)   : {len(sap) - len(xref)}")

    print("\nNoise spot-check (Vertex equipment_name  ->  SAP WorkCenter):")
    xmap = {x["equipment_id"]: x["WorkCenterInternalID"] for x in xref}
    sapmap = {s["WorkCenterInternalID"]: s["WorkCenter"] for s in sap}
    ename = {e["equipment_id"]: e["equipment_name"] for e in equip}
    shown = 0
    for eid, wcid in xmap.items():
        print(f"    {ename[eid]:<26} ->  {sapmap[wcid]}")
        shown += 1
        if shown >= 10:
            break


if __name__ == "__main__":
    main()
