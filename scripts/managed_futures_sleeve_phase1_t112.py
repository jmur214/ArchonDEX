"""T-112 Phase 1 — managed-futures crisis-diversifier sleeve A/B.

Per inbox T-2026-06-05-112:
- KPI is **portfolio MaxDD reduction at non-worse Sharpe**, NOT skewness.
  (T-108 + T-110 closed out the positive-skew thesis NEGATIVE across all
  3 product types. The thesis under test here is crisis-alpha /
  drawdown-reduction.)
- Analytical capital-partition: portfolio_ret = (1-w) * base_ret + w * sleeve_ret
  at w ∈ {0%, 10%, 15%, 20%}. No engine integration this dispatch.
- 3 sleeves × deepest window each supports:
    * T-108 spot 8-ETF basket (2008-2025, 17.4yr — covers GFC; PRIORITY per inbox)
    * DBMF (2019-2026, 7yr — covers COVID + 2022 + 2025)
    * KMLM (2020-2026, 5.4yr — covers 2022 + 2025 only)
- Base equity = T-092 arm0_off canonical rep1
    * 16-yr arm0_off (2010-2025) for DBMF + KMLM window matching
    * 26-yr arm0_off (2000-2025) for the spot-basket 2008-inclusive run
- Block-bootstrap CI on Sharpe + MDD + Calmar.
- Calm-year sub-period Sharpe to quantify the fee + negative-skew drag in
  non-crisis stretches.
- Pre-registered decision gate:
    MDD reduction ≥ 15% AND Sharpe ci_low not down AND calm-year drag bounded
    → recommend best (sleeve, allocation) pair; else NONE.

NO integration, NO engine touches. Phase 1 measurement only.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.dbmf_kmlm_phase0_t110 import load_stooq_etf, STOOQ_PATHS as DBMF_KMLM_PATHS  # noqa: E402

T092_SNAP_16YR = REPO / "_unused"  # set below at runtime
T092_BASE_16YR = Path("/tmp/t092_snap/2010-2025/rep1/portfolio_snapshots.csv")
T092_BASE_26YR = Path("/tmp/t092_snap/2000-2025/rep1/portfolio_snapshots.csv")


# Crisis windows (mirror T-108 + T-110 for direct comparability).
CRISIS_WINDOWS = [
    {"label": "2008 GFC",        "start": "2008-09-01", "end": "2009-03-31"},
    {"label": "2010 Flash crash", "start": "2010-04-23", "end": "2010-07-02"},
    {"label": "2011 EU debt",    "start": "2011-07-01", "end": "2011-10-31"},
    {"label": "2015-08 China",   "start": "2015-07-15", "end": "2015-09-30"},
    {"label": "2018-Q4",         "start": "2018-10-01", "end": "2018-12-31"},
    {"label": "COVID 2020",      "start": "2020-02-19", "end": "2020-04-30"},
    {"label": "2022 bear",       "start": "2022-01-03", "end": "2022-10-12"},
    {"label": "2025 vol-shock",  "start": "2025-02-01", "end": "2025-04-30"},
]


def crisis_mask(idx: pd.DatetimeIndex) -> pd.Series:
    """True where index falls inside ANY crisis window."""
    m = pd.Series(False, index=idx)
    for cw in CRISIS_WINDOWS:
        m = m | ((idx >= pd.Timestamp(cw["start"])) & (idx <= pd.Timestamp(cw["end"])))
    return pd.Series(m, index=idx)


# ----------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------
def load_base_returns(window: str) -> pd.Series:
    """Load T-092 arm0_off equity curve, return daily returns."""
    if window == "16yr":
        path = T092_BASE_16YR
    elif window == "26yr":
        path = T092_BASE_26YR
    else:
        raise ValueError(f"unknown window {window}")
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    eq = df.set_index("timestamp")["equity"].astype(float)
    rets = (eq.shift(-1) / eq - 1.0).iloc[:-1].dropna()
    return rets


def load_etf_returns(ticker: str) -> pd.Series:
    """DBMF / KMLM daily returns from Stooq mirror."""
    close = load_stooq_etf(DBMF_KMLM_PATHS[ticker])
    return (close / close.shift(1) - 1.0).dropna()


def load_spot_basket_returns() -> pd.Series:
    """Reuse T-108's exact harness to compute spot 8-ETF basket daily returns.

    Reruns the sleeve to get the daily-return time series (the T-108 JSON
    only persisted summary metrics, not the per-day series).
    """
    from engines.engine_c_portfolio.sleeves.sleeve_base import SleeveSpec
    from engines.engine_c_portfolio.sleeves.trend_following_sleeve import (
        TrendFollowingSleeve,
    )
    from scripts.sleeve_phase0_verdict import _build_rebalance_dates, run_sleeve
    from scripts.managed_futures_trend_t108 import build_data_map, UNIVERSE

    start_ts = pd.Timestamp("2008-02-20")
    end_ts = pd.Timestamp("2025-12-31")
    data_map = build_data_map(start_ts - pd.Timedelta(days=400), end_ts)

    spec = SleeveSpec(
        name="trend_diversified_futures_t108",
        capital_pct=1.0,
        rebalance_cadence="monthly",
        universe_id="diversified_futures_8",
        edge_set=["momentum_252_63"],
        sizing_rule="weighted_sum",
        objective_function="sortino_skew_upside",
        enabled=True,
        max_position_weight=0.30,
    )
    sleeve = TrendFollowingSleeve(spec, lookback_days=252, vol_window_days=63, top_n=4)
    rebal_dates = _build_rebalance_dates(start_ts, end_ts, "monthly")
    rets, _ = run_sleeve(sleeve, UNIVERSE, rebal_dates, data_map)
    return rets.sort_index()


# ----------------------------------------------------------------------
# Metrics + block-bootstrap CI
# ----------------------------------------------------------------------
def sharpe_ratio(rets: np.ndarray, periods: int = 252) -> float:
    if len(rets) < 2:
        return 0.0
    sd = rets.std(ddof=1)
    if sd <= 1e-12:
        return 0.0
    return float(rets.mean() / sd * math.sqrt(periods))


def max_drawdown_from_returns(rets: np.ndarray) -> float:
    """Block-bootstrap-friendly MDD: works on a daily-returns array directly."""
    eq = (1.0 + rets).cumprod()
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    return float(dd.min())


def calmar_from_returns(rets: np.ndarray, periods: int = 252) -> float:
    if len(rets) < 30:
        return 0.0
    eq = (1.0 + rets).cumprod()
    n_years = len(rets) / periods
    cagr = float(eq[-1] ** (1.0 / n_years) - 1.0)
    mdd = abs(max_drawdown_from_returns(rets))
    if mdd < 1e-9:
        return 0.0
    return cagr / mdd


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
# Portfolio-level analysis
# ----------------------------------------------------------------------
def crisis_period_return(rets: pd.Series, cw: Dict) -> Tuple[float, int]:
    w = rets.loc[(rets.index >= pd.Timestamp(cw["start"])) & (rets.index <= pd.Timestamp(cw["end"]))]
    if len(w) < 5:
        return float("nan"), int(len(w))
    return float((1.0 + w).prod() - 1.0), int(len(w))


def analyze_sleeve(
    name: str, base_rets: pd.Series, sleeve_rets: pd.Series,
    allocations: List[float], label_base: str,
) -> Dict:
    aligned = pd.concat(
        [base_rets.rename("base"), sleeve_rets.rename("sleeve")],
        axis=1, join="inner",
    ).dropna()
    print(f"\n{'='*72}")
    print(f"[T-112] SLEEVE = {name}  vs  BASE = {label_base}")
    print(f"   aligned rows: {len(aligned)}  "
          f"first={aligned.index.min().date()}  last={aligned.index.max().date()}  "
          f"~{(aligned.index.max()-aligned.index.min()).days/365.25:.1f}yr")

    cmask = crisis_mask(aligned.index)
    n_crisis = int(cmask.sum())
    n_calm = int((~cmask).sum())
    print(f"   crisis days: {n_crisis}  calm days: {n_calm}")

    out_arms: List[Dict] = []
    for w in allocations:
        port = (1.0 - w) * aligned["base"] + w * aligned["sleeve"]
        arr = port.values
        sharpe_pt, sharpe_lo, sharpe_hi = block_bootstrap_ci(arr, sharpe_ratio)
        mdd_pt, mdd_lo, mdd_hi = block_bootstrap_ci(arr, max_drawdown_from_returns)
        calmar_pt, calmar_lo, calmar_hi = block_bootstrap_ci(arr, calmar_from_returns)
        eq = (1.0 + port).cumprod()
        n_years = len(port) / 252.0
        cagr = float(eq.iloc[-1] ** (1.0 / n_years) - 1.0) if n_years > 0 else 0.0

        # Calm-year Sharpe
        calm = port[~cmask.values]
        if len(calm) >= 30:
            calm_sharpe = sharpe_ratio(calm.values)
        else:
            calm_sharpe = float("nan")
        # Crisis-period Sharpe
        crisis = port[cmask.values]
        if len(crisis) >= 30:
            crisis_sharpe = sharpe_ratio(crisis.values)
        else:
            crisis_sharpe = float("nan")

        # Per-crisis-window return
        crisis_rows = []
        for cw in CRISIS_WINDOWS:
            ret, n_d = crisis_period_return(port, cw)
            crisis_rows.append({**cw, "n_days": n_d, "total_return": ret})

        out_arms.append({
            "allocation": w,
            "sharpe": {"point": sharpe_pt, "ci_low": sharpe_lo, "ci_high": sharpe_hi},
            "max_drawdown": {"point": mdd_pt, "ci_low": mdd_lo, "ci_high": mdd_hi},
            "calmar": {"point": calmar_pt, "ci_low": calmar_lo, "ci_high": calmar_hi},
            "cagr": cagr,
            "final_equity_multiple": float(eq.iloc[-1]),
            "calm_year_sharpe": calm_sharpe,
            "crisis_period_sharpe": crisis_sharpe,
            "crisis_windows": crisis_rows,
        })

    # Per-allocation summary
    print(f"\n   {'alloc':>6s}  {'Sharpe':>22s}  {'MDD':>22s}  {'Calmar':>20s}  {'CAGR':>7s}  {'CalmSharpe':>11s}  {'CrisisSharpe':>13s}")
    base_mdd = out_arms[0]["max_drawdown"]["point"]
    base_sharpe_lo = out_arms[0]["sharpe"]["ci_low"]
    for r in out_arms:
        s = r["sharpe"]; m = r["max_drawdown"]; c = r["calmar"]
        print(f"   {r['allocation']*100:>5.0f}%  "
              f"{s['point']:+.4f} [{s['ci_low']:+.3f},{s['ci_high']:+.3f}]  "
              f"{m['point']*100:+7.2f}% [{m['ci_low']*100:+5.1f},{m['ci_high']*100:+5.1f}]  "
              f"{c['point']:+.3f} [{c['ci_low']:+.2f},{c['ci_high']:+.2f}]  "
              f"{r['cagr']*100:+6.2f}%  {r['calm_year_sharpe']:+8.4f}  {r['crisis_period_sharpe']:+9.4f}")

    return {
        "sleeve_name": name,
        "base_label": label_base,
        "window": [str(aligned.index.min().date()), str(aligned.index.max().date())],
        "n_aligned_rows": int(len(aligned)),
        "years": float((aligned.index.max() - aligned.index.min()).days / 365.25),
        "n_crisis_days": n_crisis,
        "n_calm_days": n_calm,
        "arms": out_arms,
    }


# ----------------------------------------------------------------------
# Decision gate
# ----------------------------------------------------------------------
def evaluate_arm(arm: Dict, base_arm: Dict, mdd_reduction_threshold: float = 0.15) -> Dict:
    base_mdd_abs = abs(base_arm["max_drawdown"]["point"])
    arm_mdd_abs = abs(arm["max_drawdown"]["point"])
    mdd_reduction = (base_mdd_abs - arm_mdd_abs) / base_mdd_abs if base_mdd_abs > 0 else float("nan")
    sharpe_ci_low_not_down = arm["sharpe"]["ci_low"] >= base_arm["sharpe"]["ci_low"] - 0.02
    calm_drag = arm["calm_year_sharpe"] - base_arm["calm_year_sharpe"]
    drag_bounded = (calm_drag > -0.20) if not math.isnan(calm_drag) else False
    pass_gate = (mdd_reduction >= mdd_reduction_threshold) and sharpe_ci_low_not_down and drag_bounded
    return {
        "mdd_reduction_pct": mdd_reduction,
        "mdd_reduction_passes_15pct": mdd_reduction >= mdd_reduction_threshold,
        "sharpe_ci_low_not_down": sharpe_ci_low_not_down,
        "calm_sharpe_delta": calm_drag,
        "calm_drag_bounded": drag_bounded,
        "passes_decision_gate": bool(pass_gate),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json",
                    default=str(REPO / "docs/Measurements/2026-06/t112_phase1_capital_partition.json"))
    args = ap.parse_args()

    allocations = [0.00, 0.10, 0.15, 0.20]

    # Load base equity curves
    print(f"[T-112] Loading T-092 arm0_off base equity curves...")
    base_16yr = load_base_returns("16yr")
    base_26yr = load_base_returns("26yr")
    print(f"   base 16yr: {base_16yr.index.min().date()} → {base_16yr.index.max().date()}  n={len(base_16yr)}")
    print(f"   base 26yr: {base_26yr.index.min().date()} → {base_26yr.index.max().date()}  n={len(base_26yr)}")

    # Load sleeve return series
    print(f"\n[T-112] Loading sleeve return series...")
    dbmf_rets = load_etf_returns("DBMF")
    kmlm_rets = load_etf_returns("KMLM")
    print(f"   DBMF: {dbmf_rets.index.min().date()} → {dbmf_rets.index.max().date()}  n={len(dbmf_rets)}")
    print(f"   KMLM: {kmlm_rets.index.min().date()} → {kmlm_rets.index.max().date()}  n={len(kmlm_rets)}")
    print(f"   Spot 8-ETF basket: re-running T-108 harness (this takes ~30-60s)...")
    spot_rets = load_spot_basket_returns()
    print(f"   Spot basket: {spot_rets.index.min().date()} → {spot_rets.index.max().date()}  n={len(spot_rets)}")

    # Run analytical capital-partition for each sleeve × deepest window
    # Spot basket → 26yr base (covers 2008)
    spot_analysis = analyze_sleeve("Spot 8-ETF basket", base_26yr, spot_rets,
                                    allocations, "T-092 arm0_off 26yr (2000-2025)")
    # DBMF → 16yr base (DBMF inception 2019 within 16yr)
    dbmf_analysis = analyze_sleeve("DBMF", base_16yr, dbmf_rets,
                                    allocations, "T-092 arm0_off 16yr (2010-2025)")
    # KMLM → 16yr base
    kmlm_analysis = analyze_sleeve("KMLM", base_16yr, kmlm_rets,
                                    allocations, "T-092 arm0_off 16yr (2010-2025)")

    # Decision gate
    print(f"\n{'='*72}")
    print(f"[T-112] DECISION GATE: MDD reduction ≥ 15% AND Sharpe ci_low not down AND calm-drag bounded")
    print(f"{'='*72}")

    all_results = {
        "spot_basket": spot_analysis,
        "dbmf": dbmf_analysis,
        "kmlm": kmlm_analysis,
    }

    gate_summary: List[Dict] = []
    for sleeve_name, a in all_results.items():
        base_arm = a["arms"][0]
        for arm in a["arms"][1:]:
            ev = evaluate_arm(arm, base_arm)
            gate_summary.append({
                "sleeve": sleeve_name, "allocation": arm["allocation"],
                **ev,
                "arm_sharpe_ci_low": arm["sharpe"]["ci_low"],
                "arm_mdd": arm["max_drawdown"]["point"],
                "base_mdd": base_arm["max_drawdown"]["point"],
                "arm_calmar": arm["calmar"]["point"],
                "calm_year_sharpe": arm["calm_year_sharpe"],
            })

    # Pick best by MDD-reduction among those that pass the gate; else NONE
    passing = [g for g in gate_summary if g["passes_decision_gate"]]
    if passing:
        best = max(passing, key=lambda g: g["mdd_reduction_pct"])
        verdict = f"RECOMMEND {best['sleeve']} @ {best['allocation']*100:.0f}% (MDD reduction {best['mdd_reduction_pct']*100:+.1f}%, calmar {best['arm_calmar']:+.3f})"
    else:
        # Find the closest miss: highest MDD reduction even if other gates failed
        if gate_summary:
            closest = max(gate_summary, key=lambda g: g["mdd_reduction_pct"])
            verdict = (f"NONE — no arm clears decision gate. Closest: {closest['sleeve']} @ "
                       f"{closest['allocation']*100:.0f}% (MDD reduction {closest['mdd_reduction_pct']*100:+.1f}%; "
                       f"gate pass: {closest['passes_decision_gate']})")
        else:
            verdict = "NONE — no arms evaluated"

    print(f"\n[T-112] VERDICT: {verdict}")
    print(f"\n[T-112] FULL GATE TABLE (sleeve | alloc | MDD reduce | Sharpe ci_low arm | calm Δ | pass gate?):")
    for g in gate_summary:
        print(f"   {g['sleeve']:18s} {g['allocation']*100:>4.0f}%  "
              f"MDDΔ={g['mdd_reduction_pct']*100:+6.1f}%  "
              f"arm Sharpe ci_low={g['arm_sharpe_ci_low']:+6.3f}  "
              f"calm-Δ={g['calm_sharpe_delta']:+6.3f}  "
              f"PASS={g['passes_decision_gate']}")

    out = {
        "task": "T-2026-06-05-112",
        "allocations": allocations,
        "sleeves": all_results,
        "decision_gate_table": gate_summary,
        "verdict": verdict,
    }
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n[T-112] wrote {out_path}")


if __name__ == "__main__":
    main()
