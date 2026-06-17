"""
core/combined_candidate_scorecard.py
====================================
T-2026-06-16-176 — the combined-candidate scorecard.

Measures the user's deploy bar (GOAL.md: *beat the Schwab robo,
net-of-cost / after-tax, paper-confirmed*). Tracks the REAL candidate
— **base + 20% DBMF** — against the **base alone** and a **robo
benchmark proxy**, over any return series (a paper window OR a backtest).

Data-processing only — NO UI, NO real-money path. The 20% DBMF is a
SIMULATED hold (DBMF daily returns from the STOOQ cache), never
machine-traded. Reuses MetricsEngine (Sharpe + block-bootstrap CI per
CLAUDE.md #6, MaxDD, CAGR) — the project measurement standard.

PRE-REGISTERED ROBO PROXY (honest about what it does/doesn't capture)
--------------------------------------------------------------------
The real target — **Schwab Intelligent Portfolios** — is a ~12-asset-class
*target-risk* blend (US + international equity, REITs, fixed income, TIPS,
gold/commodities, ...) with a **MANDATORY 6-30% cash allocation** that is
Schwab's monetization in lieu of an advisory fee. That cash sleeve is a
structural **return drag in bull markets** and the single most important
thing a naive proxy misses.

Two pre-registered proxies (declared here, before any result is selected on):
  * ``"60_40"`` — 60% SPY / 40% AGG, daily-rebalanced. The classic
    balanced benchmark. CAPTURES the equity/bond risk balance. MISSES:
    multi-asset diversification AND the cash drag (so it FLATTERS the robo
    in bull markets — it has no cash drag — and is a HARDER bar for us).
  * ``"schwab_like"`` — 45% SPY / 30% AGG / 5% GLD / 20% cash@rf, a
    multi-asset target-risk blend WITH an explicit cash drag. CLOSER to
    the real robo's structure. STILL MISSES: international equity / REITs /
    TIPS (not in our cache — US-centric proxy), the exact per-risk-profile
    cash % (real Schwab varies 6-30% and glides), and Schwab's specific
    rebalancing band rules.
The scorecard reports BOTH so the reader sees the proxy sensitivity; the
``60_40`` is the conservative (harder) bar, ``schwab_like`` the
structurally-faithful one. Neither is the real robo; the only definitive
test is the paper run vs the user's actual Schwab account (GOAL.md).

This module is PRE-TAX on return series. After-tax (Roth vs taxable) is a
separate layer (the existing tax engine / after_tax_metrics) — the deploy
bar is after-tax, so the consumer must apply that on top per account.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

from core.metrics_engine import MetricsEngine

ROOT = Path(__file__).resolve().parents[1]
TRADING_DAYS = 252
DBMF_STOOQ = ROOT / "data" / "raw" / "stooq" / "daily" / "us" / "nyse etfs" / "1" / "dbmf.us.txt"
PROCESSED = ROOT / "data" / "processed"

# Pre-registered robo proxies (weights; "_cash" is a cash sleeve at rf).
ROBO_PROXIES: Dict[str, Dict[str, float]] = {
    "60_40": {"SPY": 0.60, "AGG": 0.40},
    "schwab_like": {"SPY": 0.45, "AGG": 0.30, "GLD": 0.05, "_cash": 0.20},
}
# Embedded ETF expense drags (annual). DBMF ER is already in its NAV/price,
# so it needs NO extra deduction; these are for the robo proxy's holdings.
ETF_ER_ANNUAL = {"SPY": 0.0009, "AGG": 0.0003, "GLD": 0.0040}


@dataclass
class ScorecardRow:
    label: str
    n_days: int
    start: str
    end: str
    sharpe: float
    ci_low: float
    ci_high: float
    maxdd_pct: float
    cagr_pct: float
    ann_vol_pct: float


# --------------------------------------------------------------------- #
# Series helpers
# --------------------------------------------------------------------- #
def to_returns(series: pd.Series) -> pd.Series:
    """Coerce an equity curve OR a return series to daily returns.

    Heuristic: a series whose values are far from ~0 (mean |x| > 0.5) is
    treated as an equity curve and differenced; otherwise it is assumed to
    already be returns. Index is coerced to DatetimeIndex.
    """
    s = series.dropna().copy()
    s.index = pd.to_datetime(s.index)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if len(s) and float(np.nanmean(np.abs(s.values))) > 0.5:
        return s.pct_change().dropna()
    return s


def _load_close(path: Path, date_fmt: Optional[str] = None) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [c.strip("<>").strip().lower() for c in df.columns]
    date_col = next(c for c in df.columns if c in ("date", "index", "timestamp"))
    close_col = next(c for c in df.columns if c in ("close", "adj close", "adj_close"))
    idx = pd.to_datetime(df[date_col].astype(str), format=date_fmt, errors="coerce")
    s = pd.Series(pd.to_numeric(df[close_col], errors="coerce").values, index=idx).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def load_dbmf_returns() -> pd.Series:
    """DBMF (iMGP DBi Managed Futures) daily returns from the STOOQ cache.

    The STOOQ price series embeds DBMF's ~0.85% expense ratio in its NAV,
    so these returns are already net of the fund's ER (documented).
    """
    if not DBMF_STOOQ.exists():
        raise FileNotFoundError(f"DBMF not in STOOQ cache: {DBMF_STOOQ}")
    return _load_close(DBMF_STOOQ, date_fmt="%Y%m%d").pct_change().dropna()


def load_processed_returns(ticker: str) -> pd.Series:
    p = PROCESSED / f"{ticker}_1d.csv"
    if not p.exists():
        raise FileNotFoundError(f"{ticker} not in data/processed")
    return _load_close(p).pct_change().dropna()


# --------------------------------------------------------------------- #
# Combination + robo
# --------------------------------------------------------------------- #
def combine_fixed_weight(
    base_ret: pd.Series,
    overlay_ret: pd.Series,
    w_overlay: float = 0.20,
    rebalance: str = "monthly",
    rebalance_cost_bps: float = 2.0,
) -> pd.Series:
    """Fixed-weight combined daily return: (1-w)·base + w·overlay.

    Aligned on the COMMON dates (overlay availability binds — DBMF starts
    2019-05). ``rebalance`` controls how often the constant weight is
    restored; between rebalances the two sleeves drift (a realistic
    SIMULATED hold, not a costless daily-rebalanced abstraction).
    ``rebalance_cost_bps`` is charged on the turnover at each rebalance.
    """
    df = pd.concat({"base": base_ret, "ov": overlay_ret}, axis=1, sort=True).dropna()
    if df.empty:
        return pd.Series(dtype=float)
    w = float(w_overlay)
    # Drift the two sleeves between rebalances; restore weight on rebalance bars.
    if rebalance == "daily":
        combined = (1 - w) * df["base"] + w * df["ov"]
        # daily rebalance turnover is small but nonzero; approximate cost
        cost = (rebalance_cost_bps / 1e4) * (2 * w * (1 - w)) * np.abs(df["base"] - df["ov"])
        return (combined - cost).rename("combined")
    # period-rebalanced buy-hold within each period
    period = df.index.to_period("M") if rebalance == "monthly" else df.index.to_period("Q")
    out = []
    rebal_marks = []
    for _, grp in df.groupby(period):
        wb, wo = (1 - w), w
        for i, (dt, row) in enumerate(grp.iterrows()):
            r = wb * row["base"] + wo * row["ov"]
            out.append((dt, r))
            # drift weights with realized returns
            wb *= (1 + row["base"]); wo *= (1 + row["ov"])
            tot = wb + wo
            wb, wo = wb / tot, wo / tot
            rebal_marks.append(i == 0)
    combined = pd.Series(dict(out)).sort_index()
    # charge rebalance cost on turnover back to target at each period start
    marks = pd.Series(rebal_marks, index=combined.index)
    turnover = (marks.astype(float)) * 2 * w * (1 - w)  # round-trip approx
    combined = combined - (rebalance_cost_bps / 1e4) * turnover
    return combined.rename("combined")


def robo_proxy_returns(name: str = "60_40", rf_annual: float = 0.04) -> pd.Series:
    """Daily-rebalanced robo proxy return from the pre-registered weights.

    Equity/bond/gold sleeves load from data/processed (net of their ER);
    the ``_cash`` sleeve earns the daily risk-free rate (the cash drag).
    """
    weights = ROBO_PROXIES[name]
    parts = {}
    for tkr, w in weights.items():
        if tkr == "_cash":
            continue
        r = load_processed_returns(tkr) - ETF_ER_ANNUAL.get(tkr, 0.0) / TRADING_DAYS
        parts[tkr] = w * r
    blend = pd.concat(parts, axis=1, sort=True).dropna().sum(axis=1)
    cash_w = weights.get("_cash", 0.0)
    if cash_w > 0:
        blend = blend + cash_w * (rf_annual / TRADING_DAYS)
    return blend.rename(f"robo_{name}")


# --------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------- #
def score(returns: pd.Series, label: str, rf_annual: float = 0.0,
          n_boot: int = 1000, seed: int = 0) -> ScorecardRow:
    """Sharpe + block-bootstrap CI + MaxDD + CAGR + vol for a return series."""
    r = returns.dropna()
    rf_daily = rf_annual / TRADING_DAYS
    sharpe = MetricsEngine.sharpe_ratio(r, risk_free_rate=rf_daily)
    boot = MetricsEngine.bootstrap_distribution(
        r, lambda x: MetricsEngine.sharpe_ratio(x, risk_free_rate=rf_daily),
        n_iterations=n_boot, seed=seed)
    eq = (1 + r).cumprod()
    mdd = MetricsEngine.max_drawdown(eq)
    cagr = (eq.iloc[-1]) ** (TRADING_DAYS / len(r)) - 1 if len(r) else 0.0
    vol = float(r.std()) * np.sqrt(TRADING_DAYS)
    return ScorecardRow(
        label=label, n_days=len(r),
        start=str(r.index.min().date()), end=str(r.index.max().date()),
        sharpe=round(float(sharpe), 4), ci_low=round(float(boot["ci_low"]), 4),
        ci_high=round(float(boot["ci_high"]), 4),
        maxdd_pct=round(float(mdd) * 100, 2),
        cagr_pct=round(float(cagr) * 100, 3), ann_vol_pct=round(vol * 100, 2))


def build_scorecard(
    base: pd.Series,
    *,
    w_dbmf: float = 0.20,
    robo: Union[str, Sequence[str]] = ("60_40", "schwab_like"),
    rf_annual: float = 0.04,
    rebalance: str = "monthly",
    rebalance_cost_bps: float = 2.0,
    n_boot: int = 1000,
) -> Dict[str, List[ScorecardRow]]:
    """One self-consistent block PER robo proxy: base / base+20%DBMF / robo.

    Each block is aligned to base ∩ combined ∩ *that robo's* window, so a
    proxy with shorter history (e.g. schwab_like's GLD sleeve starts
    2020-04) does NOT truncate the comparison against a longer-history
    proxy (60_40 keeps the full DBMF window, COVID included). Inside a
    block all three rows share one window → apples-to-apples. ``base`` may
    be an equity curve OR a return series (paper or backtest).

    Returns ``{robo_name: [base_row, combined_row, robo_row]}``.
    """
    base_ret = to_returns(base)
    dbmf = load_dbmf_returns()
    combined = combine_fixed_weight(base_ret, dbmf, w_dbmf, rebalance, rebalance_cost_bps)
    robo_names = [robo] if isinstance(robo, str) else list(robo)
    cand_label = f"base + {int(w_dbmf*100)}% DBMF"

    blocks: Dict[str, List[ScorecardRow]] = {}
    for n in robo_names:
        robo_ret = robo_proxy_returns(n, rf_annual)
        common = combined.index.intersection(robo_ret.index).intersection(base_ret.index)
        blocks[n] = [
            score(base_ret.reindex(common).dropna(), "base", rf_annual, n_boot),
            score(combined.reindex(common).dropna(), cand_label, rf_annual, n_boot),
            score(robo_ret.reindex(common).dropna(), f"robo:{n}", rf_annual, n_boot),
        ]
    return blocks


def format_scorecard(blocks: Dict[str, List[ScorecardRow]], rf_annual: float = 0.04) -> str:
    """Presentation only — one fixed-width block per robo + the deploy read."""
    hdr = (f"{'candidate':22s} {'Sharpe':>7s} {'ci_low':>7s} {'MaxDD%':>8s} "
           f"{'CAGR%':>7s} {'vol%':>6s} {'days':>6s}")
    out: List[str] = []
    for name, rows in blocks.items():
        out.append(f"\n=== vs robo:{name}  (window {rows[0].start}..{rows[0].end}) ===")
        out.append(hdr); out.append("-" * len(hdr))
        for r in rows:
            out.append(f"{r.label:22s} {r.sharpe:7.3f} {r.ci_low:7.3f} {r.maxdd_pct:8.2f} "
                       f"{r.cagr_pct:7.2f} {r.ann_vol_pct:6.2f} {r.n_days:6d}")
        cand, rb = rows[1], rows[2]
        beats = "BEATS" if cand.sharpe > rb.sharpe else "TRAILS"
        out.append(f"deploy-bar: base+DBMF Sharpe {cand.sharpe:.3f} {beats} {rb.label} "
                   f"{rb.sharpe:.3f}  (ci_low {cand.ci_low:.3f} vs {rb.ci_low:.3f}; "
                   f"MaxDD {cand.maxdd_pct:.1f}% vs {rb.maxdd_pct:.1f}%)")
    out.append(f"\nrf={rf_annual:.1%} | net-of-cost: base=backtest-net (already net of slippage/"
               f"commission); DBMF net-of-ER (embedded in NAV); robo net-of-ER + cash drag.")
    out.append("PRE-TAX. After-tax (Roth vs taxable) is a separate layer — the deploy bar is "
               "after-tax; apply per account. The only definitive robo test is the paper run "
               "vs the user's actual Schwab account.")
    return "\n".join(out)


def rows_to_dicts(blocks: Dict[str, List[ScorecardRow]]) -> Dict[str, List[dict]]:
    return {name: [asdict(r) for r in rows] for name, rows in blocks.items()}
