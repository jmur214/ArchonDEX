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
import contextlib
import json
import os
import signal
import sys
from pathlib import Path

import numpy as np
import pandas as pd


class _ArmTimeout(Exception):
    pass


@contextlib.contextmanager
def _quiet_with_timeout(seconds: int):
    """Suppress the engine's per-bar print() spam (258MB-log thrash → disk
    stall at 0% CPU) and bound each arm with a SIGALRM so one stalled arm
    can't eat the whole measurement (the T-154 re-run incident)."""
    def _handler(signum, frame):
        raise _ArmTimeout(f"arm exceeded {seconds}s")
    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    devnull = open(os.devnull, "w")
    try:
        with contextlib.redirect_stdout(devnull):
            yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
        devnull.close()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "measurements" / "pit_universe_t154"
OUT_JSON = OUT_DIR / "pit_strategy_results.json"
BASELINE_JSON = OUT_DIR / "pre_edit_baseline_canon.json"

START, END = "2014-01-01", "2025-12-31"
SMOKE_START, SMOKE_END = "2023-01-01", "2024-12-31"   # canon-proof window
SEED = 0


def build_data_map(start: str, end: str):
    """LOCAL-ONLY data_map: resolve the historical universe (pure, reads the
    membership parquet — no network) then load each ticker's OHLCV DIRECTLY
    from data/processed CSVs. Deliberately bypasses DataManager.ensure_data,
    which fetches missing history over the network with no timeout and HUNG
    the 12-yr arm three times at 0% CPU (the SIGALRM can't interrupt a C-level
    blocking socket read). Same proven path every T-117/T-129 analysis used."""
    from engines.data_manager.universe_resolver import (
        discover_cached_tickers, resolve_universe)
    cache_root = ROOT / "data"
    cached = discover_cached_tickers(cache_root, timeframe="1d")
    tickers, _ = resolve_universe(static_tickers=[], start=start, end=end,
                                  use_historical=True, cache_dir=cache_root,
                                  anchor_dates=None, available_filter=cached)
    proc = cache_root / "processed"
    dm = {}
    for t in tickers:
        f = proc / f"{t}_1d.csv"
        if not f.exists():
            continue
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
        except Exception:
            continue
        if not {"Open", "High", "Low", "Close"} <= set(df.columns):
            continue
        df = df[(df.index >= start) & (df.index <= end)]
        if len(df) >= 30:
            dm[t] = df
    return dm


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


SURVIVOR_RUN = "0dcae34c"   # canonical arm0 2014-2025 (T-117 reference)


def trade_filter_estimate() -> int:
    """ROBUST per-strategy survivor-inflation via membership-filtering the
    canonical survivor arm0 trade log (no live backtest — the 12-yr ensemble
    harness stalled 4x on environment flakiness; the built+inert hook is the
    exact full-engine follow-up).

    Method: load 0dcae34c trades (the standing 2014-2025 arm0 run). Daily
    realized-PnL stream / INITIAL_CAPITAL = the survivor return series. The
    PIT-correct series ZEROS the PnL of every fill whose ticker was NOT
    in-index on its fill date (per the T-136 membership panel). Recompute
    CAGR/Sharpe/MDD for both.

    HONEST BOUND (stated): this is a trade-FILTERING decomposition, not a true
    PIT re-backtest — the capital freed by dropping out-of-index fills is NOT
    redeployed to in-index names. So it isolates the PnL ATTRIBUTABLE to
    out-of-index holdings; it under-states full PIT inflation if that capital
    would have earned the in-index average (the usual case in a rising market).
    Direction: a LOWER bound on inflation. Determinism: pure function of the
    frozen trade log + membership parquet."""
    import glob
    from engines.data_manager.membership import load_membership
    cap = 100_000.0
    tp = glob.glob(str(ROOT / "data" / "trade_logs" / f"{SURVIVOR_RUN}*" / "trades.csv"))[0]
    tr = pd.read_csv(tp, usecols=["timestamp", "ticker", "edge_id", "pnl"])
    tr["timestamp"] = pd.to_datetime(tr["timestamp"], errors="coerce")
    tr["pnl"] = pd.to_numeric(tr["pnl"], errors="coerce")
    tr = tr.dropna(subset=["timestamp", "pnl"])
    tr["date"] = tr["timestamp"].dt.normalize()

    mem = load_membership()
    # in-index(ticker, date) via interval lookup, vectorized per ticker
    in_idx = pd.Series(False, index=tr.index)
    by_t = mem.groupby("ticker")
    for t, sub in tr.groupby("ticker"):
        if t not in by_t.groups:
            continue
        flag = pd.Series(False, index=sub.index)
        for _, r in by_t.get_group(t).iterrows():
            end = r["end"] if pd.notna(r["end"]) else pd.Timestamp("2100-01-01")
            flag |= (sub["date"] >= r["start"]) & (sub["date"] <= end)
        in_idx.loc[sub.index] = flag.values

    surv_daily = tr.groupby("date")["pnl"].sum() / cap
    pit_daily = tr[in_idx].groupby("date")["pnl"].sum() / cap
    cal = surv_daily.index
    pit_daily = pit_daily.reindex(cal).fillna(0.0)

    def met(s):
        r = s.dropna()
        if len(r) < 2:
            return {}
        sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
        yrs = (r.index.max() - r.index.min()).days / 365.25
        cum = (1 + r).cumprod()
        cagr = float(cum.iloc[-1] ** (1 / yrs) - 1) * 100 if yrs > 0 else 0.0
        mdd = float(((cum - cum.cummax()) / cum.cummax()).min()) * 100
        return {"sharpe": round(sharpe, 3), "cagr_pct": round(cagr, 2),
                "mdd_pct": round(mdd, 2), "n_days": int(len(r))}

    # T-144 market-adjusted test: subtract the in-index EW market return
    out_of_idx_pnl = tr[~in_idx]["pnl"].sum()
    sm, pm = met(surv_daily), met(pit_daily)
    res = {
        "task": "T-2026-06-11-154 (trade-filter estimate)",
        "method": "membership-filter of canonical survivor arm0 trade log "
                  f"({SURVIVOR_RUN}, 2014-2025); LOWER bound on PIT inflation",
        "survivor": sm,
        "pit_correct": pm,
        "inflation_strategy_level_lower_bound": {
            "delta_sharpe": round(sm.get("sharpe", 0) - pm.get("sharpe", 0), 3),
            "delta_cagr_pp": round(sm.get("cagr_pct", 0) - pm.get("cagr_pct", 0), 2),
            "delta_mdd_pp": round(sm.get("mdd_pct", 0) - pm.get("mdd_pct", 0), 2),
        },
        "n_fills_total": int(len(tr)),
        "n_fills_out_of_index": int((~in_idx).sum()),
        "pct_fills_out_of_index": round(100 * float((~in_idx).mean()), 2),
        "out_of_index_pnl_usd": round(float(out_of_idx_pnl), 2),
        "out_of_index_pnl_pct_of_total": round(
            100 * float(out_of_idx_pnl / tr["pnl"].sum()), 2) if tr["pnl"].sum() else None,
    }
    OUT_JSON.write_text(json.dumps(res, indent=2, default=str))
    print(f"[T154-TF] survivor: {sm}")
    print(f"[T154-TF] pit:      {pm}")
    print(f"[T154-TF] inflation (lower bound): {res['inflation_strategy_level_lower_bound']}")
    print(f"[T154-TF] out-of-index fills: {res['pct_fills_out_of_index']}% "
          f"carrying {res['out_of_index_pnl_pct_of_total']}% of total PnL")
    print(f"[T154-TF] wrote {OUT_JSON}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture-baseline", action="store_true",
                    help="pre-edit smoke canon (run BEFORE the hook edits)")
    ap.add_argument("--trade-filter-estimate", action="store_true",
                    help="robust per-strategy inflation via membership-filtering "
                         "the canonical survivor trade log (no live backtest)")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.trade_filter_estimate:
        return trade_filter_estimate()

    if args.capture_baseline:
        dm = build_data_map(SMOKE_START, SMOKE_END)
        r = run_arm(dm, SMOKE_START, SMOKE_END, mask=None)
        BASELINE_JSON.write_text(json.dumps(
            {"window": [SMOKE_START, SMOKE_END], "canon_md5": r["canon_md5"],
             "metrics": r["metrics"]}, indent=2, default=str))
        print(f"[T154] PRE-EDIT baseline canon: {r['canon_md5']} "
              f"({SMOKE_START}..{SMOKE_END})")
        return 0

    ARM_TIMEOUT = 1500  # s; one stalled arm aborts itself, not the run

    def safe_arm(label, dm_, s, e, mask):
        try:
            with _quiet_with_timeout(ARM_TIMEOUT):
                r = run_arm(dm_, s, e, mask=mask)
            print(f"[T154] arm {label}: OK canon={r['canon_md5'][:12]} "
                  f"{r['metrics']}", flush=True)
            return r
        except _ArmTimeout as ex:
            print(f"[T154] arm {label}: TIMEOUT ({ex})", flush=True)
            return None

    # ---- bitwise-OFF proof on the smoke window ----
    dm_s = build_data_map(SMOKE_START, SMOKE_END)
    off1 = safe_arm("off1(smoke)", dm_s, SMOKE_START, SMOKE_END, None)
    off2 = safe_arm("off2(smoke)", dm_s, SMOKE_START, SMOKE_END, None)
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

    # persist the OFF-proof immediately (so a later stall can't lose it)
    OUT_JSON.write_text(json.dumps({"task": "T-2026-06-11-154",
                                    "off_proof": proof, "status": "partial"},
                                   indent=2, default=str))

    # ---- the measurement: 12-yr A/B (each arm guarded + persisted) ----
    dm = build_data_map(START, END)
    mask = membership_mask(dm, START, END)
    surv = safe_arm("survivor(12yr)", dm, START, END, None)
    pit1 = safe_arm("pit(12yr)", dm, START, END, mask)
    pit2 = safe_arm("pit-det(12yr)", dm, START, END, mask)
    if surv is None or pit1 is None:
        print("[T154] PARTIAL: a 12yr arm timed out; OFF-proof persisted, "
              "inflation number not computed.", flush=True)
        return 1

    # T-144 prediction: market-adjusted stream moves less
    ew = pd.concat({t: df["Close"].astype(float).pct_change()
                    for t, df in dm.items()
                    if df is not None and not df.empty
                    and "Close" in df.columns}, axis=1, sort=True).mean(axis=1)

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
        "pit_det_x2": bool(pit2 is not None and pit1["canon_md5"] == pit2["canon_md5"]),
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
