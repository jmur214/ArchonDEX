#!/usr/bin/env python
# scripts/demo_position_buffering_t148.py
"""T-148 demonstration — what buffering is worth, COUPLED through costs
and taxes (zero N_trials).

Takes the OFF and ON run directories of the same cell (the standing
ON-smoke pair) and computes engineering ACCOUNTING deltas — turnover,
trade count, execution cost (per-fill ADV-bucketed realistic model, the
T-146 convention), and — via T-141's after-tax module — the tax-drag
delta. NO performance claims: Sharpe/CAGR of the ON path are
deliberately not compared (a real enable rides a pre-registered A/B;
the T-098 precedent demands the deep-window test).

The tracking-error price is shown honestly two ways: the band-implied
bound (positions may drift up to buffer_fraction × |optimal| per name)
and the REALIZED on-vs-off tracking error (std of daily return
differences, annualized) — the actual dispersion cost paid in this
cell.

Run:  python -m scripts.demo_position_buffering_t148 <off_run_dir> <on_run_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.after_tax_metrics import compute_after_tax_report

ROOT = Path(__file__).resolve().parents[1]
TRADING_DAYS = 252.0


def _load(run_dir: Path):
    trades = pd.read_csv(run_dir / "trades.csv", engine="python", on_bad_lines="skip")
    snaps = pd.read_csv(run_dir / "portfolio_snapshots.csv")
    trades["timestamp"] = pd.to_datetime(trades["timestamp"])
    snaps["timestamp"] = pd.to_datetime(snaps["timestamp"])
    equity = pd.Series(
        pd.to_numeric(snaps["equity"], errors="coerce").values, index=snaps["timestamp"]
    ).dropna()
    return trades, equity


def _exec_cost_usd(trades: pd.DataFrame, sx: dict, adv_lb: int, bars_cache: dict) -> float:
    """Per-fill ADV-bucketed realistic-model cost (T-146 accounting)."""
    total = 0.0
    for _, t in trades.iterrows():
        if str(t.get("trigger", "")) not in ("entry", "exit"):
            continue  # stop/tp fills excluded from the convention Δ
        tkr = str(t["ticker"])
        if tkr not in bars_cache:
            p = ROOT / "data" / "processed" / f"{tkr}_1d.csv"
            bars_cache[tkr] = (
                pd.read_csv(p, parse_dates=[0], index_col=0) if p.exists() else None
            )
        bars = bars_cache[tkr]
        if bars is None or not {"Close", "Volume"}.issubset(bars.columns):
            continue
        win = bars.loc[bars.index <= t["timestamp"]].tail(adv_lb)
        if len(win) < 3:
            continue
        adv_usd = float((win["Close"] * win["Volume"]).mean())
        adv_sh = float(win["Volume"].mean())
        sigma = float(win["Close"].pct_change().dropna().std())
        if adv_usd >= float(sx.get("mega_cap_threshold_usd", 5e8)):
            half = float(sx.get("mega_cap_half_spread_bps", 1.0))
        elif adv_usd >= float(sx.get("mid_cap_threshold_usd", 1e8)):
            half = float(sx.get("mid_cap_half_spread_bps", 5.0))
        else:
            half = float(sx.get("small_cap_half_spread_bps", 15.0))
        impact = 0.0
        if adv_sh > 0 and np.isfinite(sigma):
            impact = float(sx.get("impact_coefficient", 0.5)) * sigma * np.sqrt(
                float(t["qty"]) / adv_sh) * 1e4
        total += float(t["qty"]) * float(t["fill_price"]) * (half + impact) / 1e4
    return total


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: python -m scripts.demo_position_buffering_t148 <off_dir> <on_dir>")
    off_dir, on_dir = Path(sys.argv[1]), Path(sys.argv[2])
    cfg = json.load(open(ROOT / "config" / "backtest_settings.json"))
    sx = cfg.get("slippage_extra", {})
    adv_lb = int(sx.get("adv_lookback", 20))
    tax_cfg = cfg["tax_drag_model"]
    buffer_fraction = float(
        json.load(open(ROOT / "config" / "portfolio_settings.json")).get("buffer_fraction", 0.10)
    )

    rows = {}
    bars_cache: dict = {}
    for label, d in (("OFF", off_dir), ("ON", on_dir)):
        trades, equity = _load(d)
        elig = trades[trades["trigger"].isin(["entry", "exit"])]
        notional = float((elig["qty"] * elig["fill_price"]).abs().sum())
        years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
        tax = compute_after_tax_report(trades, equity, tax_cfg)
        rows[label] = {
            "trades": trades, "equity": equity, "years": years,
            "n_fills": int(len(trades)), "n_eligible": int(len(elig)),
            "turnover_usd": notional,
            "turnover_x": notional / float(equity.mean()) / years,
            "exec_cost_usd": _exec_cost_usd(trades, sx, adv_lb, bars_cache),
            "tax_usd": tax["total_tax_usd"],
            "tax_drag_pct": tax["tax_drag_pct"],
            "after_tax_sharpe": tax["after_tax_sharpe_taxable"],
            "avg_equity": float(equity.mean()),
        }

    off, on = rows["OFF"], rows["ON"]
    yrs = off["years"]
    avg_eq = off["avg_equity"]
    d_turn = off["turnover_usd"] - on["turnover_usd"]
    d_cost = off["exec_cost_usd"] - on["exec_cost_usd"]
    d_tax = (off["tax_usd"] or 0.0) - (on["tax_usd"] or 0.0)

    # Realized ON-vs-OFF tracking error (the dispersion price actually paid)
    r_off = off["equity"].pct_change().dropna()
    r_on = on["equity"].pct_change().dropna()
    joined = pd.DataFrame({"off": r_off, "on": r_on}).dropna()
    te_realized = float((joined["on"] - joined["off"]).std() * np.sqrt(TRADING_DAYS))

    print(f"T-148 buffering coupled accounting — OFF {off_dir.name[:8]} vs ON {on_dir.name[:8]}")
    print(f"  window {off['years']:.2f}y, avg equity ${avg_eq:,.0f}, "
          f"buffer_fraction {buffer_fraction:.0%}\n")
    print(f"  {'':24} {'OFF':>14} {'ON':>14} {'Δ (OFF−ON)':>14}")
    print(f"  {'fills (all)':24} {off['n_fills']:>14,} {on['n_fills']:>14,} "
          f"{off['n_fills']-on['n_fills']:>14,}")
    print(f"  {'turnover $':24} {off['turnover_usd']:>14,.0f} {on['turnover_usd']:>14,.0f} "
          f"{d_turn:>14,.0f}")
    print(f"  {'turnover ×equity/yr':24} {off['turnover_x']:>14.1f} {on['turnover_x']:>14.1f} "
          f"{off['turnover_x']-on['turnover_x']:>14.1f}")
    print(f"  {'exec cost $ (realistic)':24} {off['exec_cost_usd']:>14,.0f} "
          f"{on['exec_cost_usd']:>14,.0f} {d_cost:>14,.0f}")
    print(f"  {'tax owed $ (taxable-IL)':24} {off['tax_usd']:>14,.2f} {on['tax_usd']:>14,.2f} "
          f"{d_tax:>14,.2f}")
    print()
    pct_turn = 100.0 * d_turn / off["turnover_usd"] if off["turnover_usd"] else 0.0
    print(f"  >>> turnover ↓{pct_turn:.0f}% ⇒ exec cost ↓${d_cost/yrs:,.0f}/yr "
          f"({d_cost/yrs/avg_eq*1e4:.1f} bps/yr) + tax ↓${d_tax/yrs:,.0f}/yr "
          f"({d_tax/yrs/avg_eq*1e4:.1f} bps/yr)")
    print(f"  >>> tracking-error price: band-implied bound ≤ {buffer_fraction:.0%} of each "
          f"position; REALIZED on-vs-off TE this cell = {te_realized:.2%} annualized")
    print("\n  accounting on existing artifacts — no performance comparison made, "
          "no N_trials consumed; enable decision rides a pre-registered A/B (T-098 precedent).")


if __name__ == "__main__":
    main()
