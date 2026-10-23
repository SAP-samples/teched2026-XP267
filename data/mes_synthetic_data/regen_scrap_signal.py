#!/usr/bin/env python3
"""Proposal A: inject a learnable-but-noisy scrap process into the 15-min stream.

Reads shopfloor_timeseries_15min.csv, keeps every row's states/stops/runtime
untouched, and re-draws scrap_units from a hidden latent model so TabPFN has a
real target. Recomputes good_units + the 4 OEE percentages from the new scrap.
Adds 3 partial-signal feature columns the capacity files never read, so the
Oct 1-14 coverage narrative is unaffected.

Hidden scrap drivers (none fully observable -> accuracy caps below 100%):
  - tool wear: scrap rises as tool_age_intervals grows, resets on changeover/day
  - restart defects: first 1-2 RUNNING intervals after any stop are riskier
  - late-shift fatigue: hazard rises after ~5h into the shift
  - cell baseline: ACC-02 slightly worse than ACC-01
  - ambient_temp: weak real driver + irreducible noise
"""
import numpy as np
import pandas as pd
from pathlib import Path

SRC = Path(__file__).parent / "shopfloor_timeseries_15min.csv"
OUT = Path(__file__).parent / "shopfloor_timeseries_15min_signal.csv"
SEED = 20261001

def logistic(x):
    return 1.0 / (1.0 + np.exp(-x))

def main():
    rng = np.random.default_rng(SEED)
    df = pd.read_csv(SRC, dtype={"stop_reason": str}).fillna({"stop_reason": ""})
    df["interval_start"] = pd.to_datetime(df["interval_start"], utc=True)

    # new feature columns (partial signal only)
    df["tool_age_intervals"] = 0
    df["intervals_since_stop"] = 99
    df["hours_into_shift"] = 0.0
    df["ambient_temp_c"] = np.nan

    # process each cell's timeline in order
    for line, g in df.groupby("line_id"):
        idx = g.sort_values("interval_start").index
        tool_age = 0
        since_stop = 99
        for i in idx:
            row = df.loc[i]
            running = row["state"] == "RUNNING"
            # shift clock: minutes since 08:00 local that day
            local = row["interval_start"].tz_convert("America/Los_Angeles")
            hrs = (local.hour - 8) + local.minute / 60.0
            df.at[i, "hours_into_shift"] = round(max(hrs, 0.0), 2)
            # ambient temp: diurnal + weak noise, same for both cells per interval
            temp = 20 + 4 * np.sin((local.hour - 6) / 24 * 2 * np.pi) + rng.normal(0, 0.6)
            df.at[i, "ambient_temp_c"] = round(temp, 1)

            if not running:
                # any non-RUNNING interval is a "stop": resets restart counter,
                # a full planned break / day boundary also resets tool wear
                since_stop = 0
                if row["stop_reason"] in ("MEAL_BREAK", "NO_ORDER_SCHEDULED"):
                    tool_age = 0
                df.at[i, "tool_age_intervals"] = tool_age
                df.at[i, "intervals_since_stop"] = since_stop
                df.at[i, "scrap_units"] = 0
                df.at[i, "good_units"] = row["total_units"]  # 0 anyway
                continue

            tool_age += 1
            since_stop += 1
            df.at[i, "tool_age_intervals"] = tool_age
            df.at[i, "intervals_since_stop"] = since_stop

            total = int(row["total_units"])
            if total <= 0:
                df.at[i, "scrap_units"] = 0
                continue

            # ---- hidden hazard model (per-unit defect probability) ----
            # Target is scrap_units as a COUNT (regression), not scrap>0: over ~12
            # units the binary event saturates, but the count keeps real spread.
            # Tuned for realistic mean (~1 scrap/interval) with driver signal that
            # dominates the Poisson-ish noise. Unobserved term = irreducible floor.
            z = -4.1                                    # base ~1.6% per unit
            z += 0.11 * tool_age                        # wear: strong drift
            z += 1.6 if since_stop <= 1 else 0.0        # restart: big spike
            z += 0.8 if since_stop == 2 else 0.0
            z += 0.22 * max(hrs - 5.0, 0.0)             # late-shift fatigue
            z += 0.6 if line == "SKL-ACC-02" else 0.0   # cell baseline
            z += rng.normal(0, 0.4)                     # unobserved -> noise floor
            p = logistic(z)
            scrap = int(rng.binomial(total, p))
            scrap = min(scrap, total)
            df.at[i, "scrap_units"] = scrap
            df.at[i, "good_units"] = total - scrap

    # recompute OEE family where scheduled production happened
    sched = df["scheduled_production_minutes"].astype(float)
    runt = df["runtime_minutes"].astype(float)
    total = df["total_units"].astype(float)
    good = df["good_units"].astype(float)
    ics = df["ideal_cycle_seconds"].astype(float)

    has_sched = sched > 0
    df.loc[has_sched, "availability_pct"] = (100 * runt / sched).round(4)[has_sched]
    with np.errstate(divide="ignore", invalid="ignore"):
        perf = np.where(runt > 0, 100 * total * ics / (runt * 60), np.nan)
        qual = np.where(total > 0, 100 * good / total, np.nan)
        oee = np.where(sched > 0, 100 * good * ics / (sched * 60), np.nan)
    df["performance_pct"] = np.where(has_sched, np.round(perf, 4), np.nan)
    df["quality_pct"] = np.where(total > 0, np.round(qual, 4), np.nan)
    df["oee_pct"] = np.where(has_sched, np.round(oee, 4), np.nan)

    # restore original timestamp string format (keep offset, drop pandas UTC)
    df["interval_start"] = df["interval_start"].dt.tz_convert("America/Los_Angeles").dt.strftime("%Y-%m-%dT%H:%M:%S%z").str.replace(r"(\d{2})(\d{2})$", r"\1:\2", regex=True)
    df["interval_end"] = pd.to_datetime(df["interval_end"], utc=True).dt.tz_convert("America/Los_Angeles").dt.strftime("%Y-%m-%dT%H:%M:%S%z").str.replace(r"(\d{2})(\d{2})$", r"\1:\2", regex=True)

    df.to_csv(OUT, index=False)

    # ---- self-check: scrap COUNT must be predictable above predict-the-mean ----
    # Proxy: a plain multi-feature linear regression (closed form, numpy only) on
    # a train split must beat predict-the-mean on a held-out split. Uses ALL
    # drivers jointly, like TabPFN would — a single-split rule understates signal
    # because wear is continuous and restart intervals are rare.
    run = df[df["state"] == "RUNNING"].reset_index(drop=True)
    scrap = run["scrap_units"].astype(float).values
    feats = np.column_stack([
        run["tool_age_intervals"].astype(float).values,
        (run["intervals_since_stop"] <= 1).astype(float).values,
        (run["intervals_since_stop"] == 2).astype(float).values,
        np.maximum(run["hours_into_shift"].astype(float).values - 5.0, 0.0),
        (run["line_id"] == "SKL-ACC-02").astype(float).values,
        np.ones(len(run)),
    ])
    n = len(run); k = int(n * 0.7)
    Xtr, Xte, ytr, yte = feats[:k], feats[k:], scrap[:k], scrap[k:]
    beta, *_ = np.linalg.lstsq(Xtr, ytr, rcond=None)
    pred = Xte @ beta
    mae_lin = np.abs(yte - pred).mean()
    mae_mean = np.abs(yte - ytr.mean()).mean()
    by_wear = run.groupby(run["tool_age_intervals"] > 15)["scrap_units"].mean()
    mean_scrap = scrap.mean()
    print(f"RUNNING rows: {n}   mean scrap/interval: {mean_scrap:.2f}  (orig data ~0.2)")
    print(f"scrap count dist: {sorted(run['scrap_units'].astype(int).value_counts().to_dict().items())}")
    print(f"mean scrap by high-tool-wear:\n{by_wear}")
    print(f"holdout MAE  predict-mean={mae_mean:.3f}  linear={mae_lin:.3f}  "
          f"({100*(1-mae_lin/mae_mean):.0f}% better)")
    assert 0.5 < mean_scrap < 2.0, f"mean scrap {mean_scrap:.2f} unrealistic vs original data"
    assert mae_lin < mae_mean * 0.85, "regression signal too weak (<15% MAE gain over mean)"
    assert by_wear.loc[True] > by_wear.loc[False], "tool-wear signal missing"
    print(f"OK -> {OUT.name}")

if __name__ == "__main__":
    main()
