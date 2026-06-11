"""T-2026-06-10-138 Part A — golden-master regression on the numeric pipeline.

The #1 control against agent-introduced numeric drift ("a single sign error
introduced by an agent into a live signal is a faster path to ruin than any
market event" — blind-spots research §AREA 1).

What it does
------------
Replays the production-equivalent signal→risk→portfolio pipeline
(`orchestration.run_backtest_pure`) on a FROZEN fixture:

  * input: a fixed 12-ticker, 1-year window of the PINNED substrate
    (content-addressed by config/substrate_manifest.sha256 since T-127;
    this test additionally hashes the exact sliced inputs it consumes —
    input drift fails loudly BEFORE any behavioral comparison),
  * a fixed, registry-independent edge set with pinned params/weights
    (the live registry is mutable state; the golden master detects CODE
    drift, so its edge set must not move with governor lifecycle),
  * frozen expected outputs committed under tests/golden/: the P&L vector
    (equity curve), the trade log (positions), and a signal snapshot at
    three sampled dates.

Any numeric difference (rtol=1e-9) FAILS with a human-readable diff report
(which dates, which symbols, what magnitude) plus the shadow-diff summary
(ΔSharpe / Δturnover / Δmax-position) that PR reviewers must justify.

Snapshot-update procedure (DELIBERATE, like the anchor procedure)
-----------------------------------------------------------------
1. ARCHONDEX_REGEN_GOLDEN=1 python -m pytest tests/test_golden_master.py
2. Commit the regenerated tests/golden/ files in a SEPARATE commit whose
   message justifies WHY the pipeline's numbers legitimately changed.
3. Director merges. An unexplained golden diff in a feature PR = the gate
   doing its job; never regen to silence one.

Skips (not fails) when the pinned substrate isn't present (CI without data).
"""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
PROCESSED = REPO / "data" / "processed"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# ---- frozen fixture spec ---------------------------------------------------
TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "JNJ", "XOM",
    "JPM", "PG", "NVDA", "UNH", "HD", "SPY",
]
WARMUP_START = "2019-06-01"   # history the edges may look back into
RUN_START = "2021-01-04"
RUN_END = "2021-12-31"
INITIAL_CAPITAL = 100_000.0
RTOL = 1e-9

EQUITY_FILE = GOLDEN_DIR / "golden_equity.csv"
TRADES_FILE = GOLDEN_DIR / "golden_trades.csv"
SIGNALS_FILE = GOLDEN_DIR / "golden_signals.csv"
INPUT_HASH_FILE = GOLDEN_DIR / "golden_input.sha256"
SUMMARY_FILE = GOLDEN_DIR / "golden_summary.txt"

REGEN = os.environ.get("ARCHONDEX_REGEN_GOLDEN") == "1"

pytestmark = pytest.mark.skipif(
    not (PROCESSED / "SPY_1d.csv").exists(),
    reason="Pinned substrate not present (CI without data)",
)


# --------------------------------------------------------------------------
# Fixture construction (deterministic)
# --------------------------------------------------------------------------

def _load_data_map():
    out = {}
    for t in TICKERS:
        p = PROCESSED / f"{t}_1d.csv"
        if not p.exists():
            pytest.skip(f"fixture ticker {t} missing from pinned substrate")
        df = pd.read_csv(p, index_col=0, parse_dates=True).loc[WARMUP_START:RUN_END]
        out[t] = df
    return out


def _input_hash(data_map) -> str:
    h = hashlib.sha256()
    for t in sorted(data_map):
        buf = io.BytesIO()
        data_map[t].to_csv(buf)
        h.update(t.encode())
        h.update(buf.getvalue())
    return h.hexdigest()


def _fixed_edges():
    """Registry-independent edge set with pinned params.

    Sign conventions here are the kill-surface the golden master guards:
    flip any one of these scores' sign (or any sizing sign downstream)
    and the equity/trade comparison goes RED — demonstrated in the T-138
    audit (sign-flip kill demo).
    """
    from engines.engine_a_alpha.edges.momentum_12_1_v1 import Momentum12_1Edge
    from engines.engine_a_alpha.edges.rsi_bounce import RSIBounceEdge
    from engines.engine_a_alpha.edges.short_term_reversal_v1 import ShortTermReversalEdge

    mom = Momentum12_1Edge()
    mom.params = {
        "lookback_days": 252, "skip_days": 21, "long_quantile": 0.80,
        "min_universe_size": 8, "long_score": 1.0,
    }
    rsi = RSIBounceEdge()
    rsi.params = dict(getattr(rsi, "params", {}) or {})
    rsi.params.update({"window": 14, "trend_filter": False})
    rev = ShortTermReversalEdge()
    rev.params = dict(getattr(rev, "params", {}) or {})

    edges = {"momentum_12_1_v1": mom, "rsi_bounce_v1": rsi, "short_term_reversal_v1": rev}
    weights = {"momentum_12_1_v1": 1.0, "rsi_bounce_v1": 0.8, "short_term_reversal_v1": 0.6}
    return edges, weights


def _run_pipeline(data_map):
    from orchestration.run_backtest_pure import run_backtest_pure

    edges, weights = _fixed_edges()
    res = run_backtest_pure(
        data_map=data_map,
        edges=edges,
        edge_weights=weights,
        start_date=RUN_START,
        end_date=RUN_END,
        exec_params={"slippage_bps": 5.0, "commission": 0.0},
        initial_capital=INITIAL_CAPITAL,
        use_regime_detector=True,
        use_governor=True,
        project_root=REPO,
        seed=0,
    )
    return res


def _signal_snapshot(data_map) -> pd.DataFrame:
    """Direct edge signals at 3 fixed dates through the production slicer."""
    edges, _ = _fixed_edges()
    sample_dates = ["2021-03-15", "2021-07-15", "2021-11-15"]
    rows = []
    for d in sample_dates:
        ts = pd.Timestamp(d)
        view = {}
        for t, df in data_map.items():
            if ts in df.index:
                view[t] = df.iloc[: df.index.get_loc(ts) + 1]
            else:
                view[t] = df.loc[:ts]
        for eid, edge in edges.items():
            for tk, score in sorted(edge.compute_signals(view, ts).items()):
                rows.append({"date": d, "edge": eid, "ticker": tk, "score": float(score)})
    return pd.DataFrame(rows, columns=["date", "edge", "ticker", "score"])


def _shadow_summary(res) -> dict:
    eq = res.equity_curve
    ret = eq.pct_change().dropna()
    sharpe = float(ret.mean() / ret.std(ddof=1) * np.sqrt(252)) if ret.std(ddof=1) > 0 else 0.0
    tl = res.trade_log
    turnover = float((tl["qty"].abs() * tl["fill_price"]).sum()) if len(tl) else 0.0
    max_pos = float((tl["qty"].abs() * tl["fill_price"]).max()) if len(tl) else 0.0
    return {"sharpe": sharpe, "n_trades": int(len(tl)),
            "turnover_notional": turnover, "max_position_notional": max_pos}


def _print_shadow_diff(curr: dict, stored: dict):
    print("\n[golden:shadow-diff] PR reviewers: any nonzero delta below must be "
          "justified in the PR description.")
    for k in curr:
        c, s = curr[k], stored.get(k)
        delta = (c - s) if isinstance(s, (int, float)) else None
        print(f"  {k}: stored={s} current={c}"
              + (f"  Δ={delta:+.6g}" if delta is not None else ""))


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

def test_golden_master_pipeline_replay():
    data_map = _load_data_map()

    # ---- input-drift guard (before any behavior comparison) -------------
    ih = _input_hash(data_map)
    if REGEN:
        GOLDEN_DIR.mkdir(exist_ok=True)
        INPUT_HASH_FILE.write_text(ih + "\n")
    else:
        if not INPUT_HASH_FILE.exists():
            pytest.fail("Golden fixtures missing — run with ARCHONDEX_REGEN_GOLDEN=1 "
                        "and commit tests/golden/ (separate, justified commit).")
        stored_ih = INPUT_HASH_FILE.read_text().strip()
        assert ih == stored_ih, (
            "INPUT DRIFT: the pinned-substrate slice this test consumes has "
            f"changed (sha256 {ih[:12]}… != stored {stored_ih[:12]}…). The "
            "substrate manifest should have caught this — investigate before "
            "touching the golden snapshots."
        )

    # ---- replay ----------------------------------------------------------
    res = _run_pipeline(data_map)
    eq = res.equity_curve.rename("equity").to_frame()
    eq.index.name = "timestamp"
    trades = res.trade_log.copy()
    keep_cols = [c for c in ["timestamp", "ticker", "side", "qty", "fill_price",
                             "pnl", "edge", "trigger"] if c in trades.columns]
    trades = trades[keep_cols].reset_index(drop=True)
    sigs = _signal_snapshot(data_map)
    summary = _shadow_summary(res)

    if REGEN:
        # %.17g round-trips IEEE-754 doubles exactly through CSV.
        eq.to_csv(EQUITY_FILE, float_format="%.17g")
        trades.to_csv(TRADES_FILE, index=False, float_format="%.17g")
        sigs.to_csv(SIGNALS_FILE, index=False, float_format="%.17g")
        SUMMARY_FILE.write_text(
            "\n".join(f"{k}={v}" for k, v in summary.items()) + "\n")
        print(f"\n[golden] snapshots REGENERATED at {GOLDEN_DIR} — commit "
              "separately with justification (T-138 procedure).")
        return

    # ---- compare ----------------------------------------------------------
    stored_eq = pd.read_csv(EQUITY_FILE, index_col=0, parse_dates=True)
    stored_trades = pd.read_csv(TRADES_FILE)
    stored_sigs = pd.read_csv(SIGNALS_FILE)
    stored_summary = {}
    for line in SUMMARY_FILE.read_text().splitlines():
        k, v = line.split("=", 1)
        stored_summary[k] = float(v) if "." in v or "e" in v else int(v)

    _print_shadow_diff(summary, stored_summary)

    # Signals tier (most localized diff first). Value-based comparison —
    # CSV round-trips legitimately change dtypes (int-vs-float scores), so
    # assert_frame_equal's dtype check would false-positive; what the gate
    # protects is VALUES at rtol + the exact (date, edge, ticker) key set.
    merged = sigs.merge(stored_sigs, on=["date", "edge", "ticker"],
                        how="outer", suffixes=("_curr", "_stored"))
    bad = merged[~np.isclose(merged["score_curr"].astype(float).fillna(np.nan),
                             merged["score_stored"].astype(float).fillna(np.nan),
                             rtol=RTOL, equal_nan=True)]
    if len(bad):
        pytest.fail(
            "GOLDEN DIFF — SIGNALS changed:\n"
            + bad.to_string(index=False, max_rows=20)
            + f"\n({len(bad)} differing signal rows)"
        )

    # Trades tier (positions): categorical columns compare EXACT (a changed
    # ticker/side/qty/date is a behavioral diff); numeric columns compare at
    # rtol (CSV round-trip may perturb the last ULP, ~1e-16 — far below the
    # 1e-9 gate).
    cat_cols = [c for c in ["timestamp", "ticker", "side", "qty", "edge", "trigger"]
                if c in trades.columns]
    num_cols = [c for c in ["fill_price", "pnl"] if c in trades.columns]

    def _norm_cat(df):
        out = df[cat_cols].copy()
        if "timestamp" in out:
            out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.strftime("%Y-%m-%d")
        return out.astype(str).reset_index(drop=True)

    bad_msg = None
    if len(trades) != len(stored_trades):
        bad_msg = f"{len(trades)} current vs {len(stored_trades)} stored trade rows"
    else:
        cur_cat, sto_cat = _norm_cat(trades), _norm_cat(stored_trades)
        neq = (cur_cat.values != sto_cat.values).any(axis=1)
        for c in num_cols:
            neq |= ~np.isclose(trades[c].to_numpy(dtype=float),
                               stored_trades[c].to_numpy(dtype=float),
                               rtol=RTOL, equal_nan=True)
        if neq.any():
            first_bad = int(np.argmax(neq))
            bad_msg = (
                f"first divergence at row {first_bad}:\n"
                f"  current: {trades.iloc[first_bad].to_dict()}\n"
                f"  stored : {stored_trades.iloc[first_bad].to_dict()}\n"
                f"  ({int(neq.sum())} differing rows total)"
            )
    if bad_msg:
        pytest.fail("GOLDEN DIFF — TRADES changed: " + bad_msg)

    # P&L vector tier
    try:
        pd.testing.assert_frame_equal(eq, stored_eq, rtol=RTOL)
    except AssertionError as e:
        joined = eq.join(stored_eq, rsuffix="_stored", how="outer")
        bad = joined[~np.isclose(joined["equity"], joined["equity_stored"], rtol=RTOL)]
        pytest.fail(
            "GOLDEN DIFF — P&L VECTOR changed on "
            f"{len(bad)} bars; first 10:\n{bad.head(10).to_string()}\n{e}"
        )
