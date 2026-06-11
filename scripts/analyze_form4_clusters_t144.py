"""
scripts/analyze_form4_clusters_t144.py
======================================
T-2026-06-10-144 — Form-4 insider-cluster gauntlet on the SEC structured feed
(the DIRECTIONAL event-data test), dual-universe (survivor + membership-correct).

PRE-REGISTERED (fixed before measuring; no post-hoc variant shopping):
  - Feed: data/insider_sec/ (T-136 canonical SEC structured panel, 2006-2026)
    via an explicit FEED-SOURCE PARAMETER — the production edge default is
    NOT touched (the repoint is director-gated on this verdict).
  - Events: cluster-buy trigger on ticker T at day D (FILING date — the PIT
    timestamp; transaction_date precedes public knowledge) when, in the
    trailing 30 calendar days, >= K DISTINCT insiders filed open-market
    purchases (TRANS_CODE 'P', subtype 'A') totaling >= $50,000. One event
    per ticker per 30d (cool-off). Entry anchor = first trading day AFTER the
    filing date, at the close (closes only — no opens, corrupt-opens moot).
  - FAMILY (4 members, Romano-Wolf StepM per the T-137 discipline):
      K in {2, 3}  x  horizons {20d, 60d}
    Two-sided tests (sign reported; literature predicts positive).
  - VERDICT UNIVERSE: membership-correct (event counted only if the ticker is
    in the S&P at the event date, in_index 2006+; abnormal return vs the
    MEMBER-mean). Survivor universe reported alongside — the first
    dual-universe edge test in the project; a verdict flip is itself a finding.
  - Factor gate on StepM survivors + on the primary member (K=2, 20d)
    regardless (reporting): FF5+Mom HAC alpha + 1000-iter block-bootstrap CI,
    NET of 5 bps/side event turnover (daily turnover = 2/horizon), breakeven
    reported. Sub-periods: 2006-2013 vs 2014-2026 (the decay question).
  - N_trials += 8 (4-member family x 2 universes, counted honestly).
  - Determinism: seed 0, no wall-clock in artifact, x2 bit-identical.

Reuses T-137 machinery (calendar-time portfolios, hand-rolled Romano-Wolf
StepM w/ joint CBB, factor gate) by import — one implementation, two tasks.

Usage: PYTHONHASHSEED=0 python -m scripts.analyze_form4_clusters_t144
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.factor_decomposition import load_factor_data  # noqa: E402
from scripts.analyze_8k_events_t137 import (  # noqa: E402
    build_close_returns, calendar_time_series, romano_wolf_stepm, factor_gate,
)
from engines.data_manager.membership import load_membership  # noqa: E402

FEED_DIR = ROOT / "data" / "insider_sec"      # feed-source parameter (NOT prod default)
OUT_DIR = ROOT / "data" / "measurements" / "form4_gauntlet_t144"
OUT_JSON = OUT_DIR / "form4_cluster_analysis.json"

START, END = "2006-01-01", "2025-12-31"
CLUSTER_WINDOW_D = 30
MIN_VALUE = 50_000.0
KS = [2, 3]
HORIZONS = [20, 60]
SUB_PERIODS = {"2006_2013": ("2006-01-01", "2013-12-31"),
               "2014_2026": ("2014-01-01", "2025-12-31")}


def load_buys(tickers: set[str]) -> pd.DataFrame:
    rows = []
    for t in sorted(tickers):
        f = FEED_DIR / f"{t}.parquet"
        if not f.exists():
            continue
        df = pd.read_parquet(f)
        df = df[(df["transaction_type"] == "P") &
                (df["transaction_subtype"].astype(str) == "A")]
        if df.empty:
            continue
        df = df.reset_index()
        df = df[(df["filing_date"] >= START) & (df["filing_date"] <= END)]
        if df.empty:
            continue
        rows.append(df[["filing_date", "ticker", "insider_name", "value"]]
                    .assign(ticker=t))
    out = pd.concat(rows, ignore_index=True)
    out["filing_date"] = pd.to_datetime(out["filing_date"]).dt.normalize()
    return out.dropna(subset=["filing_date"])


def cluster_events(buys: pd.DataFrame, k: int) -> pd.DataFrame:
    """Cluster-buy events: >=k distinct insiders, >=MIN_VALUE total, within a
    trailing 30-calendar-day window; 30d per-ticker cool-off."""
    events = []
    for t, sub in buys.groupby("ticker"):
        sub = sub.sort_values("filing_date")
        last_event = None
        days = sub["filing_date"].unique()
        for d in days:
            if last_event is not None and (d - last_event).days < CLUSTER_WINDOW_D:
                continue
            win = sub[(sub["filing_date"] > d - pd.Timedelta(days=CLUSTER_WINDOW_D)) &
                      (sub["filing_date"] <= d)]
            if win["insider_name"].nunique() >= k and \
                    win["value"].fillna(0).sum() >= MIN_VALUE:
                events.append({"ticker": t, "event_date": d})
                last_event = d
    return pd.DataFrame(events)


def anchor(events: pd.DataFrame, trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    pos = np.searchsorted(trading_days.values, events["event_date"].values,
                          side="right")           # first trading day AFTER filing
    ok = pos < len(trading_days)
    out = events.loc[ok].copy()
    out["anchor_pos"] = pos[ok].astype(int)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    factors = load_factor_data(auto_download=False)
    rets = build_close_returns()
    universe = set(rets.columns)
    print(f"[T144] price panel: {rets.shape[1]} names, "
          f"{rets.index.min().date()}..{rets.index.max().date()}")

    buys = load_buys(universe)
    print(f"[T144] open-market P/A buys on panel names: {len(buys)} filings, "
          f"{buys.ticker.nunique()} tickers")

    # membership mask on the price calendar
    membership = load_membership()
    member_mask = pd.DataFrame(False, index=rets.index, columns=rets.columns)
    for _, r in membership.iterrows():
        t = r["ticker"]
        if t not in member_mask.columns:
            continue
        end = r["end"] if pd.notna(r["end"]) else rets.index[-1]
        member_mask.loc[(member_mask.index >= r["start"]) &
                        (member_mask.index <= end), t] = True

    abn_survivor = rets.sub(rets.mean(axis=1), axis=0)
    member_mean = rets.where(member_mask).mean(axis=1)
    abn_member = rets.sub(member_mean, axis=0)

    results: Dict = {
        "task": "T-2026-06-10-144",
        "preregistration": {
            "feed": str(FEED_DIR), "window": [START, END],
            "cluster": f">= K distinct insiders, P/A open-market buys, "
                       f"{CLUSTER_WINDOW_D}d window, >= ${MIN_VALUE:,.0f}, 30d cool-off, "
                       f"anchor = first close AFTER filing date",
            "family": [f"K{k}_{h}d" for k in KS for h in HORIZONS],
            "verdict_universe": "membership_correct",
            "n_trials_consumed": 8,
        },
        "universes": {},
    }

    for uni_name, abn, member_gate in [
        ("membership_correct", abn_member, True),
        ("survivor", abn_survivor, False),
    ]:
        family, counts = {}, {}
        for k in KS:
            ev = cluster_events(buys, k)
            ev = anchor(ev, rets.index)
            if member_gate:
                keep = []
                for _, e in ev.iterrows():
                    t = e["ticker"]
                    d = rets.index[e["anchor_pos"]]
                    keep.append(bool(t in member_mask.columns and
                                     member_mask.loc[d, t]))
                ev = ev.loc[keep]
            counts[f"K{k}"] = int(len(ev))
            for h in HORIZONS:
                family[f"K{k}_{h}d"] = calendar_time_series(ev, abn, h)
        rw = romano_wolf_stepm(family)
        block = {
            "event_counts": counts,
            "romano_wolf": rw,
            "mean_daily_abnormal_bps": {k: round(float(s.mean()) * 1e4, 3)
                                        for k, s in family.items() if len(s)},
            "factor_gate": {},
            "sub_periods": {},
        }
        gate_members = sorted(set(rw["survivors_fwer05"] + ["K2_20d"]))
        for name in gate_members:
            h = int(name.split("_")[1][:-1])
            stream = family[name]
            if len(stream) < 60:
                block["factor_gate"][name] = {"skipped": "too few obs"}
                continue
            block["factor_gate"][name] = factor_gate(stream, factors, f"{uni_name}_{name}",
                                                     daily_turnover=2.0 / h)
            for sp, (a, z) in SUB_PERIODS.items():
                seg = stream.loc[a:z]
                if len(seg) < 60:
                    continue
                block["sub_periods"][f"{name}_{sp}"] = factor_gate(
                    seg, factors, f"{uni_name}_{name}_{sp}", daily_turnover=2.0 / h)
        results["universes"][uni_name] = block
        print(f"[T144] {uni_name}: events {counts} | StepM survivors: "
              f"{rw['survivors_fwer05'] or 'NONE'} | t_obs "
              f"{sorted(rw['t_observed'].items(), key=lambda kv: -abs(kv[1]))}")
        for name, g in block["factor_gate"].items():
            if g.get("skipped"):
                continue
            print(f"[T144]   gate {name}: α={g['alpha_annual_pct']:+.2f}% "
                  f"t={g['alpha_tstat_point']:+.2f} "
                  f"ci[{g['alpha_tstat_ci_low']:+.2f},{g['alpha_tstat_ci_high']:+.2f}] "
                  f"Sharpe={g['sharpe_point']:+.2f}({g['sharpe_ci_low']:+.2f}) "
                  f"breakeven={g['breakeven_cost_bps_per_side']:.1f}bps")

    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"[T144] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
