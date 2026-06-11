"""
scripts/analyze_13f_crowding_t145.py
====================================
T-2026-06-10-145 Phase 1 — 13F crowding (Antón-Polk class): the event lane's
LAST structured-data item, dual-universe.

PRE-REGISTERED (fixed before measuring):
  - Panel: data/edgar/13f/ownership_panel.parquet (SEC structured 13F sets,
    2013q2-2026q1, 13F-HR originals only). Crowding measure shipped:
    OWNERSHIP CONCENTRATION (holder-share HHI) — the pre-registered fallback;
    Antón-Polk pairwise connectedness not computed (cost), stated plainly.
  - PRIMARY construction: quarterly cross-sectional sort on hhi_holders
    within the price-panel universe; LONG the LOW-crowding tercile, SHORT the
    HIGH-crowding tercile (literature direction: crowded names are fragile /
    underperform at medium horizon), inverse-vol legs, dollar-neutral.
  - PIT ANCHOR (the classic 13F trap, handled): positions as-of quarter-end
    PERIODOFREPORT become tradeable only after the 45-day filing window. We
    rebalance at the first close AFTER (period_end + 60 calendar days) —
    conservative vs the per-filer max_filing_date, uniform across quarters.
  - FAMILY (2 members, StepM): holding period {1 quarter, 2 quarters}.
    Two-sided. N_trials += 4 (2 members × 2 universes; membership-correct is
    the verdict universe per the T-144 standard).
  - Gate: FF5+Mom HAC α + 1000-iter block-bootstrap CI on the daily long-short
    stream, NET of 5 bps/side on rebalance turnover; sub-periods 2013-2019 /
    2020-2026; standalone Sharpe ci_low; book correlation.
  - Stress-conditional read (descriptive ONLY, not verdict-bearing, per
    brief): the long-short's mean return on the worst-decile market days.
  - Determinism: seed 0, no wall-clock in artifact, ×2 bit-identical.

VERDICT (pre-registered): clears → first live event-lane candidate. Misses →
the structured-event lane closes AS A CLASS (8-K, Form-4, 13F all clean).

Usage: PYTHONHASHSEED=0 python -m scripts.analyze_13f_crowding_t145
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
from core.metrics_engine import MetricsEngine  # noqa: E402
from scripts.factor_decomp_substrate_honest import regress_with_hac  # noqa: E402
from engines.engine_f_governance.factor_alpha_gate import (  # noqa: E402
    compute_alpha_tstat_with_bootstrap_ci,
)
from scripts.analyze_8k_events_t137 import romano_wolf_stepm  # noqa: E402
from engines.data_manager.membership import load_membership  # noqa: E402

PANEL_13F = ROOT / "data" / "edgar" / "13f" / "ownership_panel.parquet"
OUT_DIR = ROOT / "data" / "measurements" / "crowding_13f_t145"
OUT_JSON = OUT_DIR / "crowding_analysis.json"

LAG_DAYS = 60
TERCILE = 1.0 / 3.0
VOL_WINDOW = 60
COST_BPS = 5.0
HOLD_QUARTERS = [1, 2]
SUB_PERIODS = {"2013_2019": ("2013-06-01", "2019-12-31"),
               "2020_2026": ("2020-01-01", "2025-12-31")}


def load_prices() -> pd.DataFrame:
    cols = []
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        if "Close" not in df.columns or len(df) < 100:
            continue
        df = df[(df.index >= "2012-01-01") & (df.index <= "2025-12-31")]
        if len(df) < 100:
            continue
        cols.append(df["Close"].astype(float).pct_change().rename(
            f.split("/")[-1].replace("_1d.csv", "")))
    return pd.concat(cols, axis=1).sort_index()


def build_strategy(own: pd.DataFrame, rets: pd.DataFrame,
                   member_mask: pd.DataFrame | None, hold_q: int):
    """Quarterly-rebalanced low-minus-high-crowding long-short.
    With hold_q=2 each rebalance carries half the book (staggered sleeves)."""
    idx = rets.index
    periods = sorted(own["period"].unique())
    sleeves = []   # list of (start_pos, end_pos, weights)
    for p in periods:
        snap = own[own["period"] == p]
        trade_d = pd.Timestamp(p) + pd.Timedelta(days=LAG_DAYS)
        pos = idx.searchsorted(trade_d, side="right")
        if pos >= len(idx):
            continue
        d = idx[pos]
        names = [t for t in snap["ticker"] if t in rets.columns]
        if member_mask is not None:
            names = [t for t in names
                     if t in member_mask.columns and member_mask.loc[d, t]]
        snap = snap[snap["ticker"].isin(names)].set_index("ticker")
        if len(snap) < 30:
            continue
        hhi = snap["hhi_holders"]
        ranks = hhi.rank(pct=True)
        low = hhi.index[ranks <= TERCILE]      # LONG low-crowding
        high = hhi.index[ranks >= 1 - TERCILE]  # SHORT high-crowding
        vol = rets[list(low) + list(high)].loc[:d].tail(VOL_WINDOW).std() * np.sqrt(252)
        ivol = (1.0 / vol).replace([np.inf, -np.inf], np.nan).dropna()

        def _legw(ns):
            w = ivol.reindex(ns).fillna(0.0)
            return w / w.sum() if w.sum() > 0 else w

        w = pd.Series(0.0, index=hhi.index, dtype=float)
        w.loc[low] += _legw(low)
        w.loc[high] -= _legw(high)
        # find the end: hold_q quarters later
        p_i = periods.index(p)
        if p_i + hold_q < len(periods):
            end_d = pd.Timestamp(periods[p_i + hold_q]) + pd.Timedelta(days=LAG_DAYS)
            end_pos = idx.searchsorted(end_d, side="right")
        else:
            end_pos = len(idx)
        sleeves.append((pos, min(end_pos, len(idx)), w / hold_q))

    daily = pd.Series(0.0, index=idx)
    turn = pd.Series(0.0, index=idx)
    for (a, b, w) in sleeves:
        seg = rets.iloc[a + 1:b]
        if seg.empty:
            continue
        contrib = seg.reindex(columns=w.index).fillna(0.0).mul(w, axis=1).sum(axis=1)
        daily.loc[contrib.index] += contrib
        turn.iloc[a] += float(w.abs().sum()) * 2  # in + (eventual) out
    live = daily.ne(0).cumsum() > 0
    net = (daily - turn * (COST_BPS / 1e4)).loc[live]
    return net.dropna()


def factor_report(stream: pd.Series, factors: pd.DataFrame, label: str) -> Dict:
    r = stream.dropna()
    if len(r) < 120:
        return {"n_obs": int(len(r)), "skipped": "too few obs"}
    full = r + factors["RF"].reindex(r.index).fillna(0.0)
    hac = regress_with_hac(full, factors, label)
    ci = compute_alpha_tstat_with_bootstrap_ci(full, factors, min_obs=30,
                                               n_iter=1000, seed=0)
    bd = MetricsEngine.bootstrap_distribution(r, MetricsEngine.sharpe_ratio,
                                              n_iterations=1000, seed=0)
    return {
        "n_obs": hac.get("n_obs"),
        "alpha_annual_pct": hac.get("alpha_annualized", 0.0) * 100.0 if hac.get("ok") else None,
        "alpha_tstat_point": ci.alpha_tstat_point,
        "alpha_tstat_ci_low": ci.alpha_tstat_ci_low,
        "alpha_tstat_ci_high": ci.alpha_tstat_ci_high,
        "clears_t2_point": ci.alpha_tstat_point > 2.0,
        "betas": {k: round(v["beta"], 4) for k, v in hac.get("betas", {}).items()} if hac.get("ok") else None,
        "sharpe_point": bd["point_estimate"], "sharpe_ci_low": bd["ci_low"],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    factors = load_factor_data(auto_download=False)
    own = pd.read_parquet(PANEL_13F)
    own["period"] = pd.to_datetime(own["period"])
    rets = load_prices()
    own = own[own["ticker"].isin(set(rets.columns))]
    print(f"[T145] ownership panel: {len(own)} rows, {own.ticker.nunique()} panel "
          f"tickers, {own.period.min().date()}..{own.period.max().date()}")

    membership = load_membership()
    member_mask = pd.DataFrame(False, index=rets.index, columns=rets.columns)
    for _, r in membership.iterrows():
        t = r["ticker"]
        if t not in member_mask.columns:
            continue
        end = r["end"] if pd.notna(r["end"]) else rets.index[-1]
        member_mask.loc[(member_mask.index >= r["start"]) &
                        (member_mask.index <= end), t] = True

    mkt = rets.mean(axis=1)
    stress_days = mkt[mkt <= mkt.quantile(0.10)].index

    results: Dict = {
        "task": "T-2026-06-10-145",
        "preregistration": {
            "measure": "hhi_holders (concentration fallback; connectedness not "
                       "computed — stated)",
            "construction": "quarterly L/S: long low-crowding / short "
                            "high-crowding terciles, inverse-vol, "
                            f"PIT = period_end + {LAG_DAYS}d",
            "family": [f"hold_{q}q" for q in HOLD_QUARTERS],
            "verdict_universe": "membership_correct",
            "n_trials_consumed": 4,
        },
        "universes": {},
    }
    for uni, mask in [("membership_correct", member_mask), ("survivor", None)]:
        family = {}
        for q in HOLD_QUARTERS:
            family[f"hold_{q}q"] = build_strategy(own, rets, mask, q)
        rw = romano_wolf_stepm(family)
        block = {"romano_wolf": rw, "factor_gate": {}, "sub_periods": {},
                 "stress_read_descriptive": {}}
        for name, s in family.items():
            block["factor_gate"][name] = factor_report(s, factors, f"{uni}_{name}")
            for sp, (a, z) in SUB_PERIODS.items():
                seg = s.loc[a:z]
                rep = factor_report(seg, factors, f"{uni}_{name}_{sp}")
                if not rep.get("skipped"):
                    block["sub_periods"][f"{name}_{sp}"] = rep
            sd = s.reindex(stress_days).dropna()
            block["stress_read_descriptive"][name] = {
                "mean_bps_on_worst_decile_days": round(float(sd.mean()) * 1e4, 2)
                if len(sd) else None}
        results["universes"][uni] = block
        print(f"[T145] {uni}: StepM survivors {rw['survivors_fwer05'] or 'NONE'} "
              f"| t_obs {rw['t_observed']}")
        for name, g in block["factor_gate"].items():
            if g.get("skipped"):
                continue
            print(f"[T145]   {name}: α={g['alpha_annual_pct']:+.2f}% "
                  f"t={g['alpha_tstat_point']:+.2f} "
                  f"ci[{g['alpha_tstat_ci_low']:+.2f},{g['alpha_tstat_ci_high']:+.2f}] "
                  f"Sharpe={g['sharpe_point']:+.2f}({g['sharpe_ci_low']:+.2f})")

    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"[T145] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
