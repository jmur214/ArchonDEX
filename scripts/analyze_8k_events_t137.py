"""
scripts/analyze_8k_events_t137.py
=================================
T-2026-06-10-137 — 8-K post-filing drift by ITEM TYPE, with family-wise
multiplicity control (Romano-Wolf StepM) and a factor gate on survivors.

PRE-REGISTERED (fixed BEFORE any return is examined; no post-hoc item shopping):
  - Event panel: data/edgar/8k/panel_8k_items.parquet (form 8-K only, 8-K/A
    excluded), window 2004-08-23 (item-code regime start) → 2025-12-31.
  - ITEM FAMILY (8 types, chosen for economic distinctness + literature
    coverage, fixed a priori):
      1.01 material agreement      2.01 acquisition/disposition completed
      2.02 results of operations   2.05 exit/disposal costs
      4.02 non-reliance (restatement)  5.02 officer/director departure
      7.01 Reg FD                  8.01 other events
    An event counts for item X if X is in the filing's item list (filings can
    count for several items — they are different hypotheses about different
    information).
  - HORIZONS: {1, 5, 20} trading days → FAMILY SIZE = 24, tested TWO-SIDED
    (structured codes carry no direction; agnostic by construction).
    N_trials += 24 (the family, honestly counted).
  - Event anchor (closes only — no opens, per the T-135 corrupt-opens flag):
    acceptance before 16:00 US/Eastern on trading day t → anchor = close(t);
    otherwise anchor = close(next trading day). Forward abnormal return =
    name's close-to-close log return MINUS the panel equal-weight log return
    over the same horizon (market-adjusted).
  - STATISTIC: calendar-time portfolio per family member — each trading day's
    value is the mean 1-day abnormal return over all events inside their
    horizon window (Jegadeesh-Karceski overlap handling). Test = mean of the
    daily series ≠ 0.
  - MULTIPLICITY: Romano-Wolf StepM, HAND-ROLLED (arch is not installed; the
    no-new-deps rule + T-132 precedent apply). Algorithm: Romano & Wolf
    (2005) stepwise — studentized statistics, joint circular-block-bootstrap
    null (B=1000, block=21 days, seed=0, recentred), max-statistic ladder,
    two-sided, FWER α=0.05.
  - SURVIVORS (if any): full factor gate — FF5+Mom HAC α t-stat + 1000-iter
    residual block-bootstrap CI on a tradeable long(-only or signed) version,
    NET of 5 bps/side on event-driven turnover, with breakeven cost reported.
  - Determinism: all seeds 0; NO wall-clock inside the result JSON.

Usage: PYTHONHASHSEED=0 python -m scripts.analyze_8k_events_t137
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path
from typing import Dict, List

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

PANEL_8K = ROOT / "data" / "edgar" / "8k" / "panel_8k_items.parquet"
OUT_DIR = ROOT / "data" / "measurements" / "event_8k_t137"
OUT_JSON = OUT_DIR / "event_8k_analysis.json"

START, END = "2004-08-23", "2025-12-31"
ITEM_FAMILY = ["1.01", "2.01", "2.02", "2.05", "4.02", "5.02", "7.01", "8.01"]
HORIZONS = [1, 5, 20]
B_BOOT = 1000
BLOCK = 21
FWER_ALPHA = 0.05
COST_PER_SIDE_BPS = 5.0
SEED = 0


# --------------------------------------------------------------------------- #
# Price panel (closes only)
# --------------------------------------------------------------------------- #

def build_close_returns() -> pd.DataFrame:
    cols = []
    for f in glob.glob(str(ROOT / "data" / "processed" / "*_1d.csv")):
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        if "Close" not in df.columns or len(df) < 100:
            continue
        df = df[(df.index >= "2004-01-01") & (df.index <= END)]
        if len(df) < 100:
            continue
        cols.append(np.log(df["Close"].astype(float)).diff().rename(
            f.split("/")[-1].replace("_1d.csv", "")))
    return pd.concat(cols, axis=1).sort_index()


# --------------------------------------------------------------------------- #
# Event anchoring
# --------------------------------------------------------------------------- #

def anchor_events(ev: pd.DataFrame, trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    """Map acceptance datetime (UTC) -> anchor trading-day close index pos."""
    accept_et = ev["acceptance_dt"].dt.tz_convert("US/Eastern")
    accept_date = accept_et.dt.normalize().dt.tz_localize(None)
    before_close = accept_et.dt.hour * 60 + accept_et.dt.minute < 16 * 60

    td = pd.Series(np.arange(len(trading_days)), index=trading_days)
    # position of the first trading day >= acceptance date
    pos_same_or_next = np.searchsorted(trading_days.values, accept_date.values)
    is_trading_day = pd.Index(accept_date).isin(trading_days)

    # before 16:00 on a trading day -> that day's close; else next trading day's
    anchor_pos = np.where(is_trading_day & before_close.values,
                          pos_same_or_next, pos_same_or_next +
                          np.where(is_trading_day, 1, 0))
    ok = anchor_pos < len(trading_days)
    out = ev.loc[ok].copy()
    out["anchor_pos"] = anchor_pos[ok].astype(int)
    out["anchor_day"] = trading_days[out["anchor_pos"]]
    return out


# --------------------------------------------------------------------------- #
# Calendar-time portfolios per (item, horizon)
# --------------------------------------------------------------------------- #

def calendar_time_series(events: pd.DataFrame, abn: pd.DataFrame,
                         horizon: int) -> pd.Series:
    """Daily mean abnormal return over events within (anchor, anchor+horizon]."""
    n_days, _ = abn.shape
    weight_counts = {}
    for _, e in events.iterrows():
        t = e["ticker"]
        if t not in abn.columns:
            continue
        a = int(e["anchor_pos"])
        for p in range(a + 1, min(a + 1 + horizon, n_days)):
            weight_counts.setdefault(p, []).append(t)
    vals, idx = [], []
    for p in sorted(weight_counts):
        names = weight_counts[p]
        v = abn.iloc[p][names].dropna()
        if len(v):
            vals.append(float(v.mean()))
            idx.append(abn.index[p])
    return pd.Series(vals, index=pd.DatetimeIndex(idx)).sort_index()


# --------------------------------------------------------------------------- #
# Romano-Wolf StepM — PROMOTED to core/multiple_testing.py (T-149 Part A;
# three consumers: T-137/T-144/T-145). Re-exported here so downstream
# imports (`from scripts.analyze_8k_events_t137 import romano_wolf_stepm`)
# keep working.
# --------------------------------------------------------------------------- #
from core.multiple_testing import romano_wolf_stepm  # noqa: E402,F401


# --------------------------------------------------------------------------- #
# Factor gate for survivors
# --------------------------------------------------------------------------- #

def factor_gate(stream: pd.Series, factors: pd.DataFrame, label: str,
                daily_turnover: float) -> Dict:
    cost = daily_turnover * (COST_PER_SIDE_BPS / 1e4)
    net = stream - cost
    full = net + factors["RF"].reindex(net.index).fillna(0.0)
    hac = regress_with_hac(full, factors, label)
    ci = compute_alpha_tstat_with_bootstrap_ci(full, factors, min_obs=30,
                                               n_iter=1000, seed=SEED)
    bd = MetricsEngine.bootstrap_distribution(net.dropna(), MetricsEngine.sharpe_ratio,
                                              n_iterations=1000, seed=SEED)
    gross_daily = float(stream.mean())
    breakeven_bps = (gross_daily / max(daily_turnover, 1e-9)) * 1e4
    return {
        "n_obs": hac.get("n_obs"),
        "alpha_annual_pct": hac.get("alpha_annualized", 0.0) * 100.0 if hac.get("ok") else None,
        "alpha_tstat_point": ci.alpha_tstat_point,
        "alpha_tstat_ci_low": ci.alpha_tstat_ci_low,
        "alpha_tstat_ci_high": ci.alpha_tstat_ci_high,
        "clears_t2_point": ci.alpha_tstat_point > 2.0,
        "betas": {k: round(v["beta"], 4) for k, v in hac.get("betas", {}).items()} if hac.get("ok") else None,
        "sharpe_point": bd["point_estimate"],
        "sharpe_ci_low": bd["ci_low"],
        "assumed_daily_turnover": daily_turnover,
        "breakeven_cost_bps_per_side": breakeven_bps,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    factors = load_factor_data(auto_download=False)

    ev = pd.read_parquet(PANEL_8K)
    ev = ev.dropna(subset=["acceptance_dt"])
    ev = ev[(ev["filing_date"] >= START) & (ev["filing_date"] <= END)]
    ev = ev[ev["items"].str.len() > 0]
    print(f"[T137] events: {len(ev)} 8-Ks, {ev.ticker.nunique()} tickers, "
          f"{ev.filing_date.min().date()}..{ev.filing_date.max().date()}")

    rets = build_close_returns()
    abn = rets.sub(rets.mean(axis=1), axis=0)        # market-adjusted
    trading_days = rets.index
    ev = anchor_events(ev, trading_days)

    # family construction
    family: Dict[str, pd.Series] = {}
    counts = {}
    for item in ITEM_FAMILY:
        sub = ev[ev["items"].str.contains(item, regex=False)]
        counts[item] = int(len(sub))
        for h in HORIZONS:
            family[f"{item}_{h}d"] = calendar_time_series(sub, abn, h)
    print(f"[T137] event counts/item: {counts}")

    rw = romano_wolf_stepm(family)
    print(f"[T137] RW-StepM survivors (FWER 5%): {rw['survivors_fwer05'] or 'NONE'}")
    print(f"[T137] observed |t| top5: "
          f"{sorted(rw['t_observed'].items(), key=lambda kv: -abs(kv[1]))[:5]}")

    survivors_gate = {}
    for name in rw["survivors_fwer05"]:
        item, hd = name.rsplit("_", 1)
        h = int(hd[:-1])
        sub = ev[ev["items"].str.contains(item, regex=False)]
        stream = family[name]
        # event-driven turnover: each event = enter + exit over h days, gross 1
        events_per_day = len(sub) / max(len(stream), 1)
        daily_turnover = 2.0 / h  # full position cycled every h days
        survivors_gate[name] = factor_gate(stream, factors, name, daily_turnover)
        g = survivors_gate[name]
        print(f"[T137] GATE {name}: α={g['alpha_annual_pct']:+.2f}% "
              f"t={g['alpha_tstat_point']:+.2f} ci[{g['alpha_tstat_ci_low']:+.2f},"
              f"{g['alpha_tstat_ci_high']:+.2f}] breakeven={g['breakeven_cost_bps_per_side']:.1f}bps")

    results = {
        "task": "T-2026-06-10-137",
        "preregistration": {
            "window": [START, END],
            "item_family": ITEM_FAMILY,
            "horizons_days": HORIZONS,
            "family_size": len(family),
            "two_sided": True,
            "fwer_alpha": FWER_ALPHA,
            "stepm": f"hand-rolled Romano-Wolf 2005 (arch not installed; "
                     f"no-new-deps rule), CBB B={B_BOOT} block={BLOCK} seed={SEED}",
        },
        "n_trials_consumed": len(family),
        "event_counts_per_item": counts,
        "n_events_total": int(len(ev)),
        "romano_wolf": rw,
        "survivors_factor_gate": survivors_gate,
        "mean_daily_abnormal_bps": {k: round(float(s.mean()) * 1e4, 3)
                                    for k, s in family.items()},
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"[T137] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
