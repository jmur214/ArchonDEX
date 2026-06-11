#!/usr/bin/env python
# scripts/demo_auction_execution_t146.py
"""T-146 demonstration — what auction execution is WORTH at our turnover.

Execution-cost ACCOUNTING on a frozen, already-run book (default: the
flat data/trade_logs 2024 6-edge baseline). NOT a backtest, NOT an
N_trials claim — per-fill cost re-pricing under two conventions:

  CURRENT (prod): RealisticSlippageModel — ADV-bucketed half-spread
      (mega 1bp / mid 5bp / small 15bp per side, thresholds from
      backtest_settings.json slippage_extra) + Almgren-Chriss impact
      0.5·σ20·sqrt(qty/ADV). Recomputed per fill from the same daily
      bars the backtest used.
  AUCTION (moo_moc): the official auction print + auction_safety_bps
      (default 1.0bp) adverse per side. No spread, no impact.

Regulatory fees (SEC §31 + FINRA TAF) are identical in both conventions
and excluded from the Δ. Auction re-pricing applies ONLY to
signal-driven fills (trigger ∈ {entry, exit}); intrabar stop/take-profit
fills are not auction orders and keep slippage pricing in BOTH worlds.

Honest framing: on mega-cap names the realistic model already prices
~1bp half-spread ≈ the auction safety margin — the Δ there is ≈0 by
construction. The Δ concentrates in (a) mid/small-bucket fills,
(b) the impact term, and (c) any cell still on the legacy fixed-10bp
model (reported as a scenario line). The primary value of the auction
convention is the live-vs-backtest divergence kill (blind-spots Q8.5);
this accounting prices the cost side of that switch.

Run:  python -m scripts.demo_auction_execution_t146 [run_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TRADING_DAYS = 252.0


def _load_bars(ticker: str) -> pd.DataFrame | None:
    p = ROOT / "data" / "processed" / f"{ticker}_1d.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=[0], index_col=0)
    need = {"Close", "Volume"}
    if not need.issubset(df.columns):
        return None
    return df


def main() -> None:
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "trade_logs"
    trades = pd.read_csv(run_dir / "trades.csv",
                         engine="python", on_bad_lines="skip")
    snaps = pd.read_csv(run_dir / "portfolio_snapshots.csv")
    trades["timestamp"] = pd.to_datetime(trades["timestamp"])
    avg_equity = float(pd.to_numeric(snaps["equity"], errors="coerce").dropna().mean())
    n_years = max(
        (trades["timestamp"].max() - trades["timestamp"].min()).days / 365.25, 1e-9
    )

    cfg = json.load(open(ROOT / "config" / "backtest_settings.json"))
    sx = cfg.get("slippage_extra", {})
    mega_thr = float(sx.get("mega_cap_threshold_usd", 5e8))
    mid_thr = float(sx.get("mid_cap_threshold_usd", 1e8))
    bps_mega = float(sx.get("mega_cap_half_spread_bps", 1.0))
    bps_mid = float(sx.get("mid_cap_half_spread_bps", 5.0))
    bps_small = float(sx.get("small_cap_half_spread_bps", 15.0))
    k_impact = float(sx.get("impact_coefficient", 0.5))
    adv_lb = int(sx.get("adv_lookback", 20))
    legacy_flat_bps = float(cfg.get("slippage_bps", 10.0))
    safety_bps = float(cfg.get("auction_safety_bps", 1.0))

    bars_cache: dict[str, pd.DataFrame | None] = {}
    rows = []
    skipped = 0
    for _, t in trades.iterrows():
        trigger = str(t.get("trigger", ""))
        notional = float(t["qty"]) * float(t["fill_price"])
        eligible = trigger in ("entry", "exit")
        if not eligible:
            rows.append({"eligible": False, "notional": notional,
                         "bucket": "n/a", "cur_bps": np.nan})
            continue
        tkr = str(t["ticker"])
        if tkr not in bars_cache:
            bars_cache[tkr] = _load_bars(tkr)
        bars = bars_cache[tkr]
        if bars is None:
            skipped += 1
            continue
        upto = bars.loc[bars.index <= t["timestamp"]]
        if len(upto) < adv_lb + 2:
            skipped += 1
            continue
        win = upto.tail(adv_lb)
        adv_usd = float((win["Close"] * win["Volume"]).mean())
        adv_sh = float(win["Volume"].mean())
        sigma = float(win["Close"].pct_change().dropna().std())
        if adv_usd >= mega_thr:
            half_spread, bucket = bps_mega, "mega"
        elif adv_usd >= mid_thr:
            half_spread, bucket = bps_mid, "mid"
        else:
            half_spread, bucket = bps_small, "small"
        impact_bps = 0.0
        if adv_sh > 0 and np.isfinite(sigma):
            impact_bps = k_impact * sigma * np.sqrt(float(t["qty"]) / adv_sh) * 1e4
        rows.append({
            "eligible": True, "notional": notional, "bucket": bucket,
            "cur_bps": half_spread + impact_bps,
        })

    df = pd.DataFrame(rows)
    elig = df[df["eligible"]]
    cur_cost = float((elig["notional"] * elig["cur_bps"] / 1e4).sum())
    auc_cost = float((elig["notional"] * safety_bps / 1e4).sum())
    legacy_cost = float((elig["notional"] * legacy_flat_bps / 1e4).sum())
    delta = cur_cost - auc_cost
    delta_legacy = legacy_cost - auc_cost
    elig_notional = float(elig["notional"].sum())

    print(f"T-146 auction-execution cost accounting — {run_dir}")
    print(f"  window: {trades['timestamp'].min().date()} → "
          f"{trades['timestamp'].max().date()}  ({n_years:.2f}y), "
          f"avg equity ${avg_equity:,.0f}")
    print(f"  fills: {len(df)} total | auction-eligible (entry/exit): "
          f"{len(elig)} | stop/tp (unaffected): {int((~df['eligible']).sum())} "
          f"| skipped (no bars): {skipped}")
    print(f"  eligible turnover: ${elig_notional:,.0f} "
          f"({elig_notional / avg_equity / n_years:.1f}x equity/yr)")
    print(f"  bucket mix (eligible notional): "
          + ", ".join(f"{b}={elig[elig.bucket==b]['notional'].sum()/elig_notional:.0%}"
                      for b in ("mega", "mid", "small")))
    print()
    print(f"  {'convention':34} {'cost $':>12} {'bps of turnover':>16}")
    print(f"  {'current (realistic model)':34} {cur_cost:>12,.0f} "
          f"{cur_cost/elig_notional*1e4:>16.2f}")
    print(f"  {'auction moo_moc (+{:.1f}bp safety)'.format(safety_bps):34} "
          f"{auc_cost:>12,.0f} {auc_cost/elig_notional*1e4:>16.2f}")
    print(f"  {'legacy fixed {:.0f}bp (scenario)'.format(legacy_flat_bps):34} "
          f"{legacy_cost:>12,.0f} {legacy_cost/elig_notional*1e4:>16.2f}")
    print()
    print(f"  >>> Δ vs current realistic model: ${delta:,.0f}/window "
          f"= ${delta/n_years:,.0f}/yr = {delta/n_years/avg_equity*1e4:.1f} bps of equity/yr")
    print(f"  >>> Δ vs legacy fixed model:      ${delta_legacy:,.0f}/window "
          f"= ${delta_legacy/n_years:,.0f}/yr = {delta_legacy/n_years/avg_equity*1e4:.1f} bps of equity/yr")
    print()
    print("  fees (SEC §31 + TAF) identical in both conventions — excluded from Δ.")
    print("  execution-cost accounting on an existing book — no backtest run, no N_trials consumed.")


if __name__ == "__main__":
    main()
