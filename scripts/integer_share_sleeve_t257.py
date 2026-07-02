"""
scripts/integer_share_sleeve_t257.py
====================================
T-2026-07-02-257 Part 1 — INTEGER-SHARE reality check on the T-236 trend sleeve.

The gap: every sleeve gauntlet computes CONTINUOUS-weight returns, but Schwab
offers NO fractional ETF shares. One SPY share (~$680 in 2026) is ~14% of a $5K
account. This simulates the T-236 sleeve (long/flat 105-day absolute momentum on
SPY/AGG/GLD, EW) held in WHOLE shares (the `paper_trader/sleeve_constructor`
floor logic: qty = floor(equity·w / price)) at $5K / $10K / $15K, vs the
continuous backtest, and asks whether cheaper share classes (SPLG≈SPY/9,
GLDM≈GLD/5 — same index, finer granularity) materially fix the discretization.

Read-only (no production-code change). Deterministic. Windows START at fixed
capital and compound (a realistic single deployment) — recent-start × $5K is the
binding "deploy today at high prices" case.

Output: data/research/t257/integer_share.json + table.
Usage: python -m scripts.integer_share_sleeve_t257
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.trend_overlay import TrendOverlay, LOOKBACK_DAYS, sleeve_returns  # noqa: E402
from core.metrics_engine import MetricsEngine  # noqa: E402

PROC = ROOT / "data" / "processed"
OUT = ROOT / "data" / "research" / "t257" / "integer_share.json"
LOOKBACK = LOOKBACK_DAYS[5]          # 105d = the T-236 5-month sleeve
COST_BPS = 5.0
SLEEVE = ["SPY", "AGG", "GLD"]


def _load(tkr: str) -> pd.Series:
    return pd.read_csv(PROC / f"{tkr}_1d.csv", index_col=0, parse_dates=True)["Close"].astype(float)


def _positions(closes: dict) -> pd.DataFrame:
    """Per-asset long/flat target weight (1/3 if price>SMA else 0; act on
    yesterday's signal — no look-ahead). Matches `sleeve_returns`."""
    w = 1.0 / len(closes)
    cols = {}
    for t, c in closes.items():
        sig = TrendOverlay(LOOKBACK, enabled=True).exposure(c).shift(1)
        cols[t] = sig.fillna(0.0) * w
    return pd.DataFrame(cols).dropna()


def _integer_book(closes: dict, weights: pd.DataFrame, capital: float) -> pd.Series:
    """Daily equity of a WHOLE-SHARE book that rebalances to floor(equity·w/px)
    each bar (best-tracking integer book), charged COST_BPS on share turnover.
    Returns the daily return series."""
    idx = weights.index
    px = pd.DataFrame({t: closes[t].reindex(idx).ffill() for t in closes}).loc[idx]
    equity = float(capital)
    shares = {t: 0 for t in closes}
    rets = []
    prev_idx = None
    for d in idx:
        # mark-to-market at today's close using yesterday's shares
        if prev_idx is not None:
            mv = sum(shares[t] * px.at[d, t] for t in closes)
            new_equity = mv + cash
            r = new_equity / equity - 1.0 if equity > 0 else 0.0
            equity = new_equity
            rets.append((d, r))
        # rebalance to floored integer targets on today's close
        tgt_shares = {t: int(np.floor(equity * weights.at[d, t] / px.at[d, t]))
                      if px.at[d, t] > 0 else 0 for t in closes}
        turnover = sum(abs(tgt_shares[t] - shares[t]) * px.at[d, t] for t in closes)
        cost = turnover * (COST_BPS / 1e4)
        equity -= cost
        shares = tgt_shares
        cash = equity - sum(shares[t] * px.at[d, t] for t in closes)
        prev_idx = d
    return pd.Series({d: r for d, r in rets})


def _metrics(r: pd.Series) -> dict:
    eq = (1.0 + r).cumprod() * 100.0
    return {"sortino": round(float(MetricsEngine.sortino_ratio(r)), 4),
            "sharpe": round(float(MetricsEngine.sharpe_ratio(r)), 4),
            "maxdd_pct": round(float(MetricsEngine.max_drawdown(eq)) * 100.0, 2),
            "cagr_pct": round(float((1.0 + r).prod() ** (252.0 / max(len(r), 1)) - 1.0) * 100.0, 2)}


def _run_window(closes: dict, start: str, capitals: list, label: str, share_class: str) -> dict:
    sub = {t: c.loc[start:] for t, c in closes.items()}
    weights = _positions(sub)
    cont = sleeve_returns(sub, LOOKBACK).reindex(weights.index).dropna()
    common = weights.index.intersection(cont.index)
    cont = cont.reindex(common).dropna()
    out = {"window": label, "start": start, "share_class": share_class,
           "n_obs": int(len(cont)), "continuous": _metrics(cont), "by_capital": {}}
    for cap in capitals:
        ib = _integer_book(sub, weights.reindex(common), cap).reindex(common).dropna()
        j = pd.concat([cont.rename("c"), ib.rename("i")], axis=1).dropna()
        te = float((j["i"] - j["c"]).std() * np.sqrt(252)) * 100.0  # annualized TE, %
        m = _metrics(ib)
        out["by_capital"][f"${int(cap/1000)}K"] = {
            **m,
            "tracking_error_pct": round(te, 3),
            "maxdd_drift_pp": round(m["maxdd_pct"] - out["continuous"]["maxdd_pct"], 2),
            "cagr_drift_pp": round(m["cagr_pct"] - out["continuous"]["cagr_pct"], 2),
        }
    return out


def main() -> int:
    for t in SLEEVE:
        if not (PROC / f"{t}_1d.csv").exists():
            print(f"[T257] FATAL: {t} data absent"); return 2
    closes = {t: _load(t) for t in SLEEVE}
    # share-class fix: SPLG≈SPY/9, GLDM≈GLD/5 (SAME index/returns, finer granularity).
    cheap = {"SPY": closes["SPY"] / 9.0, "AGG": closes["AGG"], "GLD": closes["GLD"] / 5.0}

    caps = [5_000.0, 10_000.0, 15_000.0]
    report = {"task": "T-2026-07-02-257 Part 1 — integer-share sleeve",
              "lookback_days": LOOKBACK, "cost_bps": COST_BPS,
              "DATA_LIMITATION": ("data/processed GLD starts 2020-04-09, so the SPY∩AGG∩GLD "
                                  "sleeve window is 2020-2026 here (the full-cycle T-236 used a "
                                  "longer gold series not in data/processed). This recent HIGH-PRICE "
                                  "regime (SPY ~$710) is the CONSERVATIVE / binding granularity test "
                                  "for 'deploy $5K today' — pre-2020's lower prices would discretize FINER."),
              "note": "SPLG≈SPY/9, GLDM≈GLD/5 synthesized (same index/returns, finer share granularity)",
              "runs": []}
    for start, lbl in [("2020-01-01", "2020-2026_full_available"),
                       ("2024-01-01", "2024-2026_deploy_today")]:
        report["runs"].append(_run_window(closes, start, caps, lbl, "SPY/AGG/GLD"))
    # share-class fix on the same windows
    for start, lbl in [("2020-01-01", "2020-2026_full_available"),
                       ("2024-01-01", "2024-2026_deploy_today")]:
        report["runs"].append(_run_window(cheap, start, caps, lbl + "_CHEAP_CLASS", "SPLG/AGG/GLDM"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"\nT-257 Part 1 — integer-share T-236 sleeve (105d, {COST_BPS}bps). TE/drift vs continuous:")
    for run in report["runs"]:
        c = run["continuous"]
        print(f"\n[{run['window']}] {run['share_class']}  n={run['n_obs']}  "
              f"continuous: Sortino {c['sortino']} MaxDD {c['maxdd_pct']}% CAGR {c['cagr_pct']}%")
        for cap, m in run["by_capital"].items():
            print(f"   {cap:>5s}: TE {m['tracking_error_pct']:>6.2f}%/yr | "
                  f"Sortino {m['sortino']:>6.3f} | MaxDD {m['maxdd_pct']:>7.2f}% "
                  f"(drift {m['maxdd_drift_pp']:+.2f}pp) | CAGR drift {m['cagr_drift_pp']:+.2f}pp")
    print(f"\n[T257] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
