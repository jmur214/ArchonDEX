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

AFTER-TAX (T-191): the deploy bar is "beat the robo net-of-cost AND
after-tax", so ``build_scorecard(account=...)`` carries both halves. Roth =
no tax (after-tax == pre-tax). Taxable = a per-line year-end tax on realized
gains, REUSING the T-141 rates (config/backtest_settings.json::tax_drag_model
via backtester.tax_drag_model.TaxDragConfig) with a per-line realization
profile — because the robo/DBMF lines are synthetic series with no fill log.
The base's authoritative after-tax number is its own backtest after_tax_detail
(FIFO lots, measured 100% short-term); this layer approximates that so the
robo and sleeve are judged on the same basis. See the After-tax section below.
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
# After-tax layer (T-191) — the second half of the deploy bar.
# GOAL.md is "beat the robo net-of-cost AND after-tax". A Roth dollar and a
# taxable dollar are not the same, so the comparison must be per-account.
#
# REUSES the existing tax model: rates come from
# config/backtest_settings.json::tax_drag_model via the T-141
# `backtester.tax_drag_model.TaxDragConfig` (single source — fed ST/LT +
# additive IL state 4.95%). This is a SERIES-LEVEL layer because the robo
# and DBMF lines are synthetic return series with no fill log: it applies a
# year-end tax on each line's realized positive gains, scaled by a per-line
# realization profile (a turnover proxy). The base's AUTHORITATIVE after-tax
# number is its own backtest `after_tax_detail` (FIFO lots, measured 100%
# short-term); this layer approximates that with `st_fraction`/
# `realized_fraction` so the robo and sleeve can be judged on the SAME basis.
#
# STATED ASSUMPTIONS (honest, per the dispatch):
#  - Roth = pre-tax (no tax); taxable = year-end tax on realized gains.
#  - Per-line realization profiles below are ASSUMPTIONS (turnover→tax is the
#    T-148 finding: turnover is a tax lever ~29x the cost lever). The base is
#    the worst case (the 3rd taxable indictment: 100% ST, full realization →
#    taxable CAGR craters vs Roth). Override via `tax_profiles=`.
#  - Year-end synthetic realization; losses carry forward (no rebate); no
#    wash-sale modelling at the series level (the FIFO model handles that for
#    the base's own after_tax_detail). Planning estimates, not tax advice.
# --------------------------------------------------------------------- #
@dataclass
class TaxRates:
    """Effective combined (federal + state) cap-gains rates."""
    st: float = 0.3495   # fed 0.30 + IL 0.0495  (== T-141 effective_st_rate)
    lt: float = 0.1995   # fed 0.15 + IL 0.0495  (== T-141 effective_lt_rate)
    source: str = "default(IL)"


@dataclass
class TaxProfile:
    """Per-line realization profile for the series-level tax.

    ``realized_fraction`` — fraction of each year's POSITIVE return realized
    (taxed) that year; a turnover proxy (buy-hold ≈ 0.1-0.2, high-churn ≈ 1.0).
    ``st_fraction`` — fraction of realized gains taxed at the short-term rate.
    """
    realized_fraction: float
    st_fraction: float


# Defaults keyed by line ROLE. base = the measured production reality
# (after_tax_detail: pct_lots_short_term=100, full realization). combined =
# 0.8*base + 0.2*DBMF (T-120 monthly-rebal sleeve: slow tilt, low realization,
# harvestable losses → more LT). robo = tax-efficient buy-hold (low turnover,
# mostly LT; some ordinary income from bond coupons).
DEFAULT_TAX_PROFILES: Dict[str, TaxProfile] = {
    "base":     TaxProfile(realized_fraction=1.00, st_fraction=1.00),
    "combined": TaxProfile(realized_fraction=0.84, st_fraction=0.84),
    "robo":     TaxProfile(realized_fraction=0.20, st_fraction=0.30),
}

_TAX_SETTINGS = ROOT / "config" / "backtest_settings.json"


def load_tax_rates() -> TaxRates:
    """Effective ST/LT rates from the SAME source the backtest tax model uses
    (config/backtest_settings.json::tax_drag_model via TaxDragConfig). Falls
    back to the IL defaults if the config/module is unavailable."""
    try:
        import json
        from backtester.tax_drag_model import TaxDragConfig  # reuse, don't rebuild
        blk = json.loads(_TAX_SETTINGS.read_text()).get("tax_drag_model", {})
        cfg = TaxDragConfig(
            short_term_rate=float(blk.get("short_term_rate", 0.30)),
            long_term_rate=float(blk.get("long_term_rate", 0.15)),
            state_st_rate=float(blk.get("state_st_rate", 0.0)),
            state_lt_rate=float(blk.get("state_lt_rate", 0.0)),
        )
        return TaxRates(st=round(cfg.short_term_rate + cfg.state_st_rate, 4),
                        lt=round(cfg.long_term_rate + cfg.state_lt_rate, 4),
                        source="backtest_settings.json::tax_drag_model")
    except Exception:
        return TaxRates()


def after_tax_returns(
    returns: pd.Series,
    profile: TaxProfile,
    rates: Optional[TaxRates] = None,
    *,
    carry_forward: bool = True,
) -> pd.Series:
    """Series-level after-tax DAILY returns for a TAXABLE account.

    Within-year daily returns are unchanged (vol/MDD shape preserved); a
    year-end tax haircut is applied to each year's realized positive gain.
    Taxes paid reduce the capital that compounds into the next year. Returns
    the after-tax daily-return series (Roth callers should not call this).
    """
    rates = rates or TaxRates()
    r = returns.dropna()
    if r.empty:
        return r
    rate = profile.st_fraction * rates.st + (1.0 - profile.st_fraction) * rates.lt
    after_eq = pd.Series(index=r.index, dtype=float)
    base_eq = 1.0
    cf_loss = 0.0  # carry-forward loss, in equity-dollar terms
    for yr in sorted(set(r.index.year)):
        seg = r[r.index.year == yr]
        path = base_eq * (1.0 + seg).cumprod()
        end_pre = float(path.iloc[-1])
        realized = (end_pre - base_eq) * profile.realized_fraction
        tax = 0.0
        if realized > 0:
            taxable = realized - cf_loss
            cf_loss = max(0.0, cf_loss - realized)
            if taxable > 0:
                tax = taxable * rate
        elif realized < 0 and carry_forward:
            cf_loss += -realized
        if tax > 0 and end_pre > 0:
            path.iloc[-1] = end_pre - tax
        after_eq.loc[seg.index] = path
        base_eq = float(path.iloc[-1])
    at = after_eq.pct_change()
    at.iloc[0] = float(after_eq.iloc[0]) - 1.0  # first day's return vs start=1.0
    return at.dropna()


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
    account: str = "roth",
    tax_profiles: Optional[Dict[str, TaxProfile]] = None,
    tax_rates: Optional[TaxRates] = None,
) -> Dict[str, List[ScorecardRow]]:
    """One self-consistent block PER robo proxy: base / base+20%DBMF / robo.

    Each block is aligned to base ∩ combined ∩ *that robo's* window, so a
    proxy with shorter history (e.g. schwab_like's GLD sleeve starts
    2020-04) does NOT truncate the comparison against a longer-history
    proxy (60_40 keeps the full DBMF window, COVID included). Inside a
    block all three rows share one window → apples-to-apples. ``base`` may
    be an equity curve OR a return series (paper or backtest).

    ``account`` — ``"roth"`` (default; net-of-cost == after-tax, no tax) or
    ``"taxable"`` (the T-191 after-tax layer applies a per-line year-end tax;
    each line uses its role profile in ``tax_profiles`` / DEFAULT_TAX_PROFILES,
    rates from ``tax_rates`` / ``load_tax_rates()``). The deploy bar is
    after-tax, so the taxable block is the per-account comparison.

    Returns ``{robo_name: [base_row, combined_row, robo_row]}``.
    """
    base_ret = to_returns(base)
    dbmf = load_dbmf_returns()
    combined = combine_fixed_weight(base_ret, dbmf, w_dbmf, rebalance, rebalance_cost_bps)
    robo_names = [robo] if isinstance(robo, str) else list(robo)
    cand_label = f"base + {int(w_dbmf*100)}% DBMF"

    taxable = account.lower() == "taxable"
    profiles = {**DEFAULT_TAX_PROFILES, **(tax_profiles or {})}
    rates = tax_rates or load_tax_rates()

    def _tax(series: pd.Series, role: str) -> pd.Series:
        """Apply the after-tax layer for the taxable account; pass-through for Roth."""
        if not taxable:
            return series
        return after_tax_returns(series, profiles[role], rates)

    blocks: Dict[str, List[ScorecardRow]] = {}
    for n in robo_names:
        robo_ret = robo_proxy_returns(n, rf_annual)
        common = combined.index.intersection(robo_ret.index).intersection(base_ret.index)
        blocks[n] = [
            score(_tax(base_ret.reindex(common).dropna(), "base"), "base", rf_annual, n_boot),
            score(_tax(combined.reindex(common).dropna(), "combined"), cand_label, rf_annual, n_boot),
            score(_tax(robo_ret.reindex(common).dropna(), "robo"), f"robo:{n}", rf_annual, n_boot),
        ]
    return blocks


def format_scorecard(blocks: Dict[str, List[ScorecardRow]], rf_annual: float = 0.04,
                     account: str = "roth") -> str:
    """Presentation only — one fixed-width block per robo + the deploy read."""
    taxable = account.lower() == "taxable"
    tag = "AFTER-TAX (taxable)" if taxable else "after-tax == pre-tax (Roth, no tax)"
    hdr = (f"{'candidate':22s} {'Sharpe':>7s} {'ci_low':>7s} {'MaxDD%':>8s} "
           f"{'CAGR%':>7s} {'vol%':>6s} {'days':>6s}")
    out: List[str] = [f"=== account: {account.upper()} — {tag} ==="]
    for name, rows in blocks.items():
        out.append(f"\n--- vs robo:{name}  (window {rows[0].start}..{rows[0].end}) ---")
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
    if taxable:
        rt = load_tax_rates()
        out.append(f"after-tax: per-line year-end tax on realized gains; rates ST {rt.st:.2%} / "
                   f"LT {rt.lt:.2%} ({rt.source}); profiles base={DEFAULT_TAX_PROFILES['base'].realized_fraction:.2f}"
                   f"r/{DEFAULT_TAX_PROFILES['base'].st_fraction:.2f}st (measured 100% ST — the 3rd taxable "
                   f"indictment), combined 0.84/0.84, robo 0.20/0.30 (tax-efficient buy-hold). "
                   f"Base's authoritative after-tax is its own backtest after_tax_detail (FIFO).")
    else:
        out.append("Roth: after-tax == pre-tax. Run account='taxable' for the taxed comparison "
                   "(the base book is 100% short-term → the taxable line is materially worse).")
    out.append("The only definitive robo test is the paper run vs the user's actual Schwab account.")
    return "\n".join(out)


def rows_to_dicts(blocks: Dict[str, List[ScorecardRow]]) -> Dict[str, List[dict]]:
    return {name: [asdict(r) for r in rows] for name, rows in blocks.items()}
