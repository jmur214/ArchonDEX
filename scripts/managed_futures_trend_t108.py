"""T-108 Phase 0 — managed-futures / diversified-ETF trend sleeve on
extended Stooq substrate (2007-02-20 → 2025-12-31, UUP-bound).

Per inbox + scope doc:
  - 8-ETF basket: SPY, TLT, GLD, USO, UUP, EEM, IEF, DBC
  - The TrendFollowingSleeve here runs over an ARBITRARY ticker basket
    (not Engine A equity tickers) — that's why the inbox's warning
    ("the built sleeve is the WRONG tool when applied to equities")
    doesn't bind here; we PRE-SUPPLY the futures basket.
  - Make-or-break: is realized skewness POSITIVE? (equity-trend was
    -0.133; this is THE structural-property test).
  - Crisis returns: 2008 GFC (window starts at UUP 2007-02-20 →
    covers 2008-09 onward), COVID 2020, 2022 bear.
  - Block-bootstrap CI on Sharpe + Sortino + skew per CLAUDE.md `[NN-SHARPE-CI]`.
  - Base correlation: vs 6-edge equity book proxy (use SPY daily
    returns over same window as a first-order base proxy; the FULL
    arm0_off equity-book returns require a multi-yr backtest run).

Phase 0 only — NO Engine C/B integration; standalone phantom run.

Usage: python -m scripts.managed_futures_trend_t108
"""
from __future__ import annotations

import argparse
import json
import math
import random
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]


# 8-ETF diversified-futures basket (R2's recommendation; matches
# scripts/run_diversified_futures_trend.py).
UNIVERSE = ["SPY", "TLT", "GLD", "USO", "UUP", "EEM", "IEF", "DBC"]

# Stooq mirror paths per ticker (manually located — Stooq's tree
# splits ETFs across nyse etfs/1 + 2 + nasdaq etfs).
STOOQ_PATHS = {
    "SPY": "data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt",
    "TLT": "data/raw/stooq/daily/us/nasdaq etfs/tlt.us.txt",
    "GLD": "data/raw/stooq/daily/us/nyse etfs/1/gld.us.txt",
    "USO": "data/raw/stooq/daily/us/nyse etfs/2/uso.us.txt",
    "UUP": "data/raw/stooq/daily/us/nyse etfs/2/uup.us.txt",
    "EEM": "data/raw/stooq/daily/us/nyse etfs/1/eem.us.txt",
    "IEF": "data/raw/stooq/daily/us/nasdaq etfs/ief.us.txt",
    "DBC": "data/raw/stooq/daily/us/nyse etfs/1/dbc.us.txt",
}

# Asset-class taxonomy.
ASSET_CLASS: Dict[str, str] = {
    "SPY": "equities", "EEM": "equities",
    "TLT": "bonds",    "IEF": "bonds",
    "GLD": "commodities", "USO": "commodities", "DBC": "commodities",
    "UUP": "currencies",
}

# Crisis windows (inclusive). Defined for per-period return attribution.
CRISIS_WINDOWS = [
    {"label": "2008 GFC",       "start": "2008-09-01", "end": "2009-03-31"},
    {"label": "2010 Flash crash", "start": "2010-04-23", "end": "2010-07-02"},
    {"label": "2011 EU debt",   "start": "2011-07-01", "end": "2011-10-31"},
    {"label": "2015-08 China",  "start": "2015-07-15", "end": "2015-09-30"},
    {"label": "2018-Q4",        "start": "2018-10-01", "end": "2018-12-31"},
    {"label": "COVID 2020",     "start": "2020-02-19", "end": "2020-04-30"},
    {"label": "2022 bear",      "start": "2022-01-03", "end": "2022-10-12"},
    {"label": "2025 vol-shock", "start": "2025-02-01", "end": "2025-04-30"},
]


# ----------------------------------------------------------------------
# Data loading from Stooq mirror
# ----------------------------------------------------------------------
def load_stooq_etf(rel_path: str) -> pd.DataFrame:
    df = pd.read_csv(REPO / rel_path)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date").sort_index()
    out = pd.DataFrame(index=df.index, dtype=float)
    out["Open"] = df["open"]
    out["High"] = df["high"]
    out["Low"] = df["low"]
    out["Close"] = df["close"]
    out["Volume"] = df["vol"]
    return out


def build_data_map(start: pd.Timestamp, end: pd.Timestamp) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    for t in UNIVERSE:
        df = load_stooq_etf(STOOQ_PATHS[t])
        df = df.loc[(df.index >= start) & (df.index <= end)]
        out[t] = df
    return out


# ----------------------------------------------------------------------
# Metrics + block-bootstrap CI
# ----------------------------------------------------------------------
def sharpe_ratio(rets: np.ndarray, periods: int = 252) -> float:
    if len(rets) < 2:
        return 0.0
    mu = rets.mean()
    sd = rets.std(ddof=1)
    if sd <= 1e-12:
        return 0.0
    return float(mu / sd * math.sqrt(periods))


def sortino_ratio(rets: np.ndarray, periods: int = 252) -> float:
    if len(rets) < 2:
        return 0.0
    mu = rets.mean()
    downside = rets[rets < 0]
    if len(downside) == 0:
        return float("inf")
    dd = math.sqrt((downside ** 2).mean())
    if dd <= 1e-12:
        return 0.0
    return float(mu / dd * math.sqrt(periods))


def max_drawdown(equity: pd.Series) -> float:
    running_peak = equity.cummax()
    dd = (equity / running_peak) - 1.0
    return float(dd.min())


def equity_curve(rets: pd.Series) -> pd.Series:
    return (1.0 + rets).cumprod()


def politis_white_block(n: int) -> int:
    return max(4, int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))))


def block_bootstrap_ci(
    rets: np.ndarray, metric_fn, n_iter: int = 1000, seed: int = 42,
) -> Tuple[float, float, float]:
    n = len(rets)
    if n < 30:
        return float("nan"), float("nan"), float("nan")
    point = metric_fn(rets)
    block = politis_white_block(n)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_iter):
        idx: List[int] = []
        while len(idx) < n:
            start = rng.randint(0, max(1, n - block))
            idx.extend(range(start, min(start + block, n)))
        idx_arr = np.array(idx[:n])
        boots.append(metric_fn(rets[idx_arr]))
    boots = [b for b in boots if not math.isnan(b) and not math.isinf(b)]
    if not boots:
        return point, float("nan"), float("nan")
    boots.sort()
    return point, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]


# ----------------------------------------------------------------------
# Sleeve harness — uses TrendFollowingSleeve on the ETF basket
# ----------------------------------------------------------------------
def run_phase0(start: str, end: str, lookback: int = 252, vol_window: int = 63,
               top_n: int = 4, max_pos_weight: float = 0.30,
               cadence: str = "monthly") -> Dict:
    from engines.engine_c_portfolio.sleeves.sleeve_base import SleeveSpec
    from engines.engine_c_portfolio.sleeves.trend_following_sleeve import (
        TrendFollowingSleeve,
    )
    from scripts.sleeve_phase0_verdict import _build_rebalance_dates, run_sleeve

    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    print(f"[T-108] window: {start} → {end}")
    data_map = build_data_map(start_ts - pd.Timedelta(days=400), end_ts)
    for t in UNIVERSE:
        df = data_map[t]
        print(f"   {t}: start={df.index.min().date()} end={df.index.max().date()} n={len(df)}")

    spec = SleeveSpec(
        name="trend_diversified_futures_t108",
        capital_pct=1.0,
        rebalance_cadence=cadence,
        universe_id="diversified_futures_8",
        edge_set=["momentum_252_63"],
        sizing_rule="weighted_sum",
        objective_function="sortino_skew_upside",
        enabled=True,
        max_position_weight=max_pos_weight,
    )
    sleeve = TrendFollowingSleeve(spec, lookback_days=lookback,
                                  vol_window_days=vol_window, top_n=top_n)

    rebal_dates = _build_rebalance_dates(start_ts, end_ts, cadence)
    print(f"[T-108] {len(rebal_dates)} {cadence} rebalances")

    rets, diags = run_sleeve(sleeve, UNIVERSE, rebal_dates, data_map)
    print(f"[T-108] sleeve produced {len(rets)} daily-return obs from {len(diags)} rebalances")

    if rets.empty:
        return {"verdict": "INDETERMINATE — no return data"}

    rets = rets.sort_index()
    # Headline metrics
    arr = rets.values
    sharpe_pt, sharpe_lo, sharpe_hi = block_bootstrap_ci(arr, sharpe_ratio)
    sortino_pt, sortino_lo, sortino_hi = block_bootstrap_ci(arr, sortino_ratio)
    skew = float(pd.Series(arr).skew())  # bias-corrected (Fisher-Pearson)
    skew_pt, skew_lo, skew_hi = block_bootstrap_ci(arr, lambda r: float(pd.Series(r).skew()))
    eq = equity_curve(rets)
    mdd = max_drawdown(eq)

    print(f"\n[T-108] HEADLINE METRICS (sleeve standalone):")
    print(f"   Sharpe:    {sharpe_pt:+.4f}  ci=[{sharpe_lo:+.4f}, {sharpe_hi:+.4f}]")
    print(f"   Sortino:   {sortino_pt:+.4f}  ci=[{sortino_lo:+.4f}, {sortino_hi:+.4f}]")
    print(f"   Skewness:  {skew:+.4f}  ci=[{skew_lo:+.4f}, {skew_hi:+.4f}]   (vs equity-trend -0.133 = make-or-break)")
    print(f"   MaxDD:     {mdd*100:+.2f}%")
    print(f"   Final equity: {eq.iloc[-1]:.4f} (1.0 = start)")
    print(f"   Annualized return:  {(eq.iloc[-1] ** (252 / len(rets)) - 1.0) * 100:+.2f}%/yr")

    # Crisis-window returns
    print(f"\n[T-108] CRISIS WINDOW RETURNS (sleeve, total-return in window):")
    crisis_rows = []
    for cw in CRISIS_WINDOWS:
        cw_rets = rets.loc[(rets.index >= pd.Timestamp(cw["start"])) & (rets.index <= pd.Timestamp(cw["end"]))]
        if len(cw_rets) < 5:
            print(f"   {cw['label']:20s}  no coverage")
            crisis_rows.append({**cw, "n_days": int(len(cw_rets)), "total_return": None, "max_drawdown": None})
            continue
        total = float((1.0 + cw_rets).prod() - 1.0)
        # SPY benchmark over same window
        spy_df = data_map["SPY"]
        spy_window = spy_df.loc[(spy_df.index >= pd.Timestamp(cw["start"])) & (spy_df.index <= pd.Timestamp(cw["end"]))]
        if len(spy_window) >= 2:
            spy_total = float(spy_window["Close"].iloc[-1] / spy_window["Close"].iloc[0] - 1.0)
        else:
            spy_total = float("nan")
        cw_eq = equity_curve(cw_rets)
        cw_mdd = max_drawdown(cw_eq)
        print(f"   {cw['label']:20s}  n={len(cw_rets):3d}d  sleeve={total*100:+7.2f}%  SPY={spy_total*100:+7.2f}%  Δ={total*100 - spy_total*100:+7.2f}pp  mdd={cw_mdd*100:+6.2f}%")
        crisis_rows.append({
            **cw, "n_days": int(len(cw_rets)),
            "total_return": total, "spy_total_return": spy_total,
            "outperform_spy_pp": total - spy_total, "max_drawdown": cw_mdd,
        })

    # Correlation to SPY (proxy for the base equity book; the full base
    # correlation requires a multi-yr backtest run separately)
    spy_close = data_map["SPY"]["Close"]
    spy_daily = (spy_close / spy_close.shift(1) - 1.0).dropna()
    aligned = pd.concat([rets.rename("sleeve"), spy_daily.rename("spy")],
                        axis=1, join="inner").dropna()
    corr_to_spy = float(aligned["sleeve"].corr(aligned["spy"]))
    cov_arr = aligned.cov().values  # for beta
    beta_vs_spy = float(cov_arr[0, 1] / cov_arr[1, 1]) if cov_arr[1, 1] > 0 else float("nan")

    print(f"\n[T-108] DIVERSIFICATION CHECK:")
    print(f"   Correlation sleeve vs SPY: {corr_to_spy:+.4f}  (lower is better diversification)")
    print(f"   Beta sleeve vs SPY:        {beta_vs_spy:+.4f}")

    # Verdict
    skew_positive = skew > 0
    skew_ci_clear_zero = skew_lo > 0
    sharpe_positive_ci = sharpe_lo > 0
    crisis_protective = sum(1 for c in crisis_rows
                             if c.get("total_return") is not None
                             and c.get("outperform_spy_pp") is not None
                             and c["outperform_spy_pp"] > 0) >= 4
    low_corr = corr_to_spy < 0.5

    if skew_positive and crisis_protective and low_corr and sharpe_positive_ci:
        verdict = "PROCEED"
    elif (skew_positive or skew_lo > -0.1) and low_corr:
        verdict = "RECONSIDER (DBMF/KMLM ETF route)"
    else:
        verdict = "DEAD"

    print(f"\n[T-108] === PHASE 0 VERDICT: {verdict} ===")
    print(f"   skew positive?       {skew_positive} (point {skew:+.4f}, ci_low {skew_lo:+.4f})")
    print(f"   skew ci_low > 0?     {skew_ci_clear_zero}")
    print(f"   Sharpe ci_low > 0?   {sharpe_positive_ci}")
    print(f"   crisis-protective?   {crisis_protective}  (≥4 of 8 windows beat SPY)")
    print(f"   low base correlation? {low_corr}  (vs SPY < 0.5)")

    summary = {
        "task": "T-2026-06-05-108",
        "window": [start, end],
        "universe": UNIVERSE,
        "binding_data_floor": "UUP 2007-02-20",
        "n_daily_returns": int(len(rets)),
        "n_rebalances": int(len(diags)),
        "metrics": {
            "sharpe": {"point": sharpe_pt, "ci_low": sharpe_lo, "ci_high": sharpe_hi},
            "sortino": {"point": sortino_pt, "ci_low": sortino_lo, "ci_high": sortino_hi},
            "skewness": {"point": skew, "ci_low": skew_lo, "ci_high": skew_hi,
                         "equity_trend_reference": -0.133},
            "max_drawdown": mdd,
            "final_equity_multiple": float(eq.iloc[-1]),
            "annualized_return": float(eq.iloc[-1] ** (252 / len(rets)) - 1.0),
        },
        "crisis_windows": crisis_rows,
        "diversification": {
            "correlation_to_spy": corr_to_spy,
            "beta_to_spy": beta_vs_spy,
        },
        "verdict": {
            "label": verdict,
            "skew_positive": skew_positive,
            "skew_ci_low_gt_zero": skew_ci_clear_zero,
            "sharpe_ci_low_gt_zero": sharpe_positive_ci,
            "crisis_protective": crisis_protective,
            "low_base_correlation": low_corr,
        },
    }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2008-02-20")  # UUP+12mo lookback so first rebalance has signal
    ap.add_argument("--end",   default="2025-12-31")
    ap.add_argument("--out-json",
                    default=str(REPO / "docs/Measurements/2026-06/t108_phase0_diversified_trend.json"))
    args = ap.parse_args()

    summary = run_phase0(args.start, args.end)
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n[T-108] wrote {out_path}")


if __name__ == "__main__":
    main()
