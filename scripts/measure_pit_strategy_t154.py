"""
scripts/measure_pit_strategy_t154.py
====================================
T-2026-06-11-154 — the PER-STRATEGY survivor-inflation number (T-136's
missing translation), via the pit_membership hook in the pure-backtest path.

PRE-REGISTERED (before any measurement run):
  - Engine path: run_backtest_pure (the production-equivalent ensemble runner
    the gauntlet uses — Engine A/C/E/F parity, governor reset, no side
    effects), arm0 = the FULL production edge set
    (DiscoveryEngine._build_production_edges, exclude=∅: active at weight +
    soft-paused at 0.25x — the deployed-set semantics).
  - Window: 2014-01-01 → 2025-12-31 (the deepest local arm0-equivalent window
    with a standing reference run, 0dcae34c). Universe: historical S&P union
    via resolve_universe(use_historical=True) — survivor-tilted by data, the
    status quo every standing number rode.
  - ARMS:
      survivor:   pit mask OFF (status quo; also the bitwise-OFF canon proof
                  arm vs the pre-edit baseline)
      pit:        pit mask ON — per-bar, names NOT in-index at t are excluded
                  from SIGNAL GENERATION only (held positions keep full data
                  for risk management and exit via normal engine logic — real
                  index-tracking semantics; avoids the bagholder trap).
  - HEADLINE: ΔCAGR / ΔSharpe / ΔMDD (survivor − pit) = the per-strategy
    survivor-inflation number, next to T-136's universe-level band.
  - Shumway translation: held-position TRUNCATION events (position open when
    the name's price path ends) counted per arm; worst-case bound reported
    (each truncated position's remaining value → -100%) — the strategy-level
    analogue of T-136 variant (c). (The engine cannot trade missing paths, so
    imputation enters as a BOUND, not a backtest input.)
  - T-144 prediction test: the MARKET-ADJUSTED stream (strategy minus
    universe EW) compared across arms — predicted to move much less than the
    absolute numbers.
  - N accounting: survivor arm = re-measurement of the standing config
    (N += 0); pit arm = one new configuration (N += 1). Policy stated.
  - Determinism: seed 0; canon md5 of the sorted trade log; det x2 per arm;
    bitwise-OFF proof = post-edit survivor canon == pre-edit baseline canon
    (captured by --capture-baseline before the hook edits landed).

Usage:
  python -m scripts.measure_pit_strategy_t154 --capture-baseline   (pre-edit)
  PYTHONHASHSEED=0 python -m scripts.measure_pit_strategy_t154     (full A/B)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "measurements" / "pit_universe_t154"
OUT_JSON = OUT_DIR / "pit_strategy_results.json"
BASELINE_JSON = OUT_DIR / "pre_edit_baseline_canon.json"

START, END = "2014-01-01", "2025-12-31"
SMOKE_START, SMOKE_END = "2023-01-01", "2024-12-31"   # canon-proof window
SEED = 0


def build_data_map(start: str, end: str):
    from engines.data_manager.data_manager import DataManager
    from engines.data_manager.universe_resolver import (
        discover_cached_tickers, resolve_universe)
    cache_root = ROOT / "data"
    cached = discover_cached_tickers(cache_root, timeframe="1d")
    tickers, _ = resolve_universe(static_tickers=[], start=start, end=end,
                                  use_historical=True, cache_dir=cache_root,
                                  anchor_dates=None, available_filter=cached)
    dm = DataManager(cache_dir=str(cache_root / "processed"))
    return dm.ensure_data(tickers, start, end, timeframe="1d")


def arm0_edges():
    from engines.engine_d_discovery.discovery import DiscoveryEngine
    disc = DiscoveryEngine()
    return disc._build_production_edges(registry_path=disc.registry_path,
                                        alpha_config={}, exclude_edge_ids=set())


def membership_mask(data_map, start: str, end: str) -> pd.DataFrame:
    from engines.data_manager.membership import load_membership
    cal = pd.date_range(start, end, freq="B")
    m = load_membership()
    out = pd.DataFrame(False, index=cal, columns=sorted(data_map.keys()))
    for _, r in m.iterrows():
        t = r["ticker"]
        if t not in out.columns:
            continue
        e = r["end"] if pd.notna(r["end"]) else cal[-1]
        out.loc[(out.index >= r["start"]) & (out.index <= e), t] = True
    return out


def canon_md5(trade_log: pd.DataFrame) -> str:
    if trade_log is None or trade_log.empty:
        return "(empty)"
    cols = [c for c in ("timestamp", "ticker", "side", "qty", "fill_price")
            if c in trade_log.columns]
    s = trade_log[cols].sort_values(cols).to_csv(index=False)
    return hashlib.md5(s.encode()).hexdigest()


def run_arm(data_map, start, end, mask=None) -> dict:
    from orchestration.run_backtest_pure import run_backtest_pure
    edges, weights = arm0_edges()
    kwargs = dict(data_map=data_map, edges=edges, edge_weights=weights,
                  start_date=start, end_date=end,
                  exec_params={"slippage_bps": 5, "commission": 0.0},
                  seed=SEED)
    if mask is not None:
        kwargs["pit_membership_mask"] = mask
    res = run_backtest_pure(**kwargs)
    eq = res.equity_curve
    dr = res.daily_returns
    years = len(dr) / 252.0 if dr is not None and len(dr) else 0
    cagr = (float(eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) * 100 \
        if years > 0 and eq is not None and len(eq) > 1 else None
    # truncation events: open position at a name's last data bar before END
    trunc = 0
    if res.trade_log is not None and not res.trade_log.empty:
        tl = res.trade_log
        open_qty = tl.groupby("ticker").apply(
            lambda g: float(pd.to_numeric(
                g.apply(lambda r: r["qty"] if str(r["side"]).lower() in ("buy", "long") else -r["qty"], axis=1)
            ).sum()), include_groups=False)
        for t, q in open_qty.items():
            if abs(q) > 1e-9 and t in data_map:
                last = data_map[t].index.max()
                if last < pd.Timestamp(end) - pd.Timedelta(days=7):
                    trunc += 1
    return {
        "metrics": {k: res.metrics.get(k) for k in
                    ("Sharpe Ratio", "CAGR (%)", "Max Drawdown (%)",
                     "Total Trades", "Sortino")},
        "cagr_recomputed": cagr,
        "canon_md5": canon_md5(res.trade_log),
        "n_truncated_open_positions": trunc,
        "daily_returns": res.daily_returns,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture-baseline", action="store_true",
                    help="pre-edit smoke canon (run BEFORE the hook edits)")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.capture_baseline:
        dm = build_data_map(SMOKE_START, SMOKE_END)
        r = run_arm(dm, SMOKE_START, SMOKE_END, mask=None)
        BASELINE_JSON.write_text(json.dumps(
            {"window": [SMOKE_START, SMOKE_END], "canon_md5": r["canon_md5"],
             "metrics": r["metrics"]}, indent=2, default=str))
        print(f"[T154] PRE-EDIT baseline canon: {r['canon_md5']} "
              f"({SMOKE_START}..{SMOKE_END})")
        return 0

    # ---- bitwise-OFF proof on the smoke window ----
    dm_s = build_data_map(SMOKE_START, SMOKE_END)
    off1 = run_arm(dm_s, SMOKE_START, SMOKE_END, mask=None)
    off2 = run_arm(dm_s, SMOKE_START, SMOKE_END, mask=None)
    pre = json.loads(BASELINE_JSON.read_text()) if BASELINE_JSON.exists() else {}
    proof = {
        "pre_edit_canon": pre.get("canon_md5"),
        "post_edit_off_canon_run1": off1["canon_md5"],
        "post_edit_off_canon_run2": off2["canon_md5"],
        "bitwise_off_vs_pre_edit": bool(pre.get("canon_md5") == off1["canon_md5"]),
        "det_x2_off": bool(off1["canon_md5"] == off2["canon_md5"]),
    }
    print(f"[T154] OFF-proof: pre==post {proof['bitwise_off_vs_pre_edit']} | "
          f"det x2 {proof['det_x2_off']}")

    # ---- the measurement: 12-yr A/B ----
    dm = build_data_map(START, END)
    mask = membership_mask(dm, START, END)
    surv = run_arm(dm, START, END, mask=None)
    pit1 = run_arm(dm, START, END, mask=mask)
    pit2 = run_arm(dm, START, END, mask=mask)

    # T-144 prediction: market-adjusted stream moves less
    ew = pd.concat({t: df["Close"].astype(float).pct_change()
                    for t, df in dm.items()}, axis=1).mean(axis=1)

    def madj_sharpe(dr):
        if dr is None or len(dr) < 50:
            return None
        x = (pd.Series(dr) - ew.reindex(pd.Series(dr).index)).dropna()
        return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else None

    results = {
        "task": "T-2026-06-11-154",
        "preregistration_window": [START, END],
        "n_trials_policy": "survivor arm = standing-config re-measurement (N+=0); "
                           "pit arm = new config (N+=1)",
        "off_proof": proof,
        "survivor": {k: v for k, v in surv.items() if k != "daily_returns"},
        "pit": {k: v for k, v in pit1.items() if k != "daily_returns"},
        "pit_det_x2": bool(pit1["canon_md5"] == pit2["canon_md5"]),
        "inflation_strategy_level": {
            "delta_sharpe": (surv["metrics"]["Sharpe Ratio"] or 0)
                            - (pit1["metrics"]["Sharpe Ratio"] or 0),
            "delta_cagr_pp": (surv["metrics"]["CAGR (%)"] or 0)
                             - (pit1["metrics"]["CAGR (%)"] or 0),
            "delta_mdd_pp": (surv["metrics"]["Max Drawdown (%)"] or 0)
                            - (pit1["metrics"]["Max Drawdown (%)"] or 0),
        },
        "t144_prediction_market_adjusted_sharpe": {
            "survivor": madj_sharpe(surv["daily_returns"]),
            "pit": madj_sharpe(pit1["daily_returns"]),
        },
    }
    OUT_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"[T154] survivor: {surv['metrics']}")
    print(f"[T154] pit:      {pit1['metrics']}")
    print(f"[T154] Δ (surv−pit): {results['inflation_strategy_level']}")
    print(f"[T154] market-adj Sharpe: {results['t144_prediction_market_adjusted_sharpe']}")
    print(f"[T154] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
