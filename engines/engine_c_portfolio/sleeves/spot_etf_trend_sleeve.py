"""Spot 8-ETF cross-asset trend sleeve (T-120 Phase 1 integration).

This sleeve trades a cross-asset diversified-futures-style ETF basket
[SPY, TLT, GLD, USO, UUP, EEM, IEF, DBC]. It is the spot-ETF version
of the cross-asset managed-futures concept — NOT equity-trend.

CRITICAL — DO NOT REUSE TrendFollowingSleeve FOR THIS:
    TrendFollowingSleeve filters Engine A's EQUITY signals by
    momentum+inverse-vol — i.e. equity-trend, which T-007 falsified
    twice (negative skew, -23%/-43% MDD). Wiring TrendFollowingSleeve
    as the host for the spot-ETF basket would silently re-run a dead
    test (the inbox flagged this trap explicitly).

This sleeve has its OWN universe (the 8 ETFs), OWN data path (Stooq
mirror), and OWN bar-by-bar accounting that runs independently of
Engine A/B's order flow. Its PnL contribution to total portfolio
equity is injected into PortfolioEngine.snapshot() — that's the
"trades the 8-ETF basket bar-by-bar" claim, satisfied without
requiring the 8 ETFs to be in the engine's data_map (which is the
equity universe).

Parameters fixed at the T-115 spec defaults (validated configuration):
    top_n = 4
    max_position_weight = 0.30
    lookback_days = 252
    vol_window_days = 63
    rebalance_cadence = "monthly"

Determinism: random_state not used (no RNG); the sleeve is purely
deterministic given the input data. The 8-ETF Stooq history is a
static substrate.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


_REPO_ROOT: Optional[Path] = None


def _repo_root() -> Path:
    global _REPO_ROOT
    if _REPO_ROOT is None:
        # engines/engine_c_portfolio/sleeves/ → repo root is parents[3]
        _REPO_ROOT = Path(__file__).resolve().parents[3]
    return _REPO_ROOT


# 8-ETF diversified-futures-style basket. Order matches T-108 / T-115.
UNIVERSE: List[str] = ["SPY", "TLT", "GLD", "USO", "UUP", "EEM", "IEF", "DBC"]

# Stooq mirror paths (relative to repo root).
STOOQ_PATHS: Dict[str, str] = {
    "SPY": "data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt",
    "TLT": "data/raw/stooq/daily/us/nasdaq etfs/tlt.us.txt",
    "GLD": "data/raw/stooq/daily/us/nyse etfs/1/gld.us.txt",
    "USO": "data/raw/stooq/daily/us/nyse etfs/2/uso.us.txt",
    "UUP": "data/raw/stooq/daily/us/nyse etfs/2/uup.us.txt",
    "EEM": "data/raw/stooq/daily/us/nyse etfs/1/eem.us.txt",
    "IEF": "data/raw/stooq/daily/us/nasdaq etfs/ief.us.txt",
    "DBC": "data/raw/stooq/daily/us/nyse etfs/1/dbc.us.txt",
}

# T-115 / T-108 spec defaults.
LOOKBACK_DAYS = 252
VOL_WINDOW_DAYS = 63
TOP_N = 4
MAX_POSITION_WEIGHT = 0.30


def _load_stooq_close(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df = df.set_index("date").sort_index()
    return df["close"].astype(float)


def _load_basket() -> pd.DataFrame:
    """Load 8 ETF close prices into a single DataFrame, indexed by date."""
    cols: Dict[str, pd.Series] = {}
    for t in UNIVERSE:
        path = _repo_root() / STOOQ_PATHS[t]
        if not path.exists():
            raise FileNotFoundError(
                f"SpotETFTrendSleeve substrate missing: {path}. "
                f"Required: 8-ETF basket from Stooq mirror."
            )
        cols[t] = _load_stooq_close(path)
    df = pd.DataFrame(cols)
    return df.sort_index()


class SpotETFTrendSleeve:
    """Self-contained spot-ETF cross-asset trend sleeve.

    Holds its own capital pool, advances day-by-day, rebalances monthly
    via momentum-rank + inverse-volatility weighting. PortfolioEngine
    calls `advance_to(date, ...)` to roll the sleeve forward one bar
    and adds the resulting equity contribution to total portfolio
    equity in snapshot().

    Lifecycle:
        sleeve = SpotETFTrendSleeve(initial_capital=250_000)
        # PortfolioEngine calls sleeve.advance_to(date) each bar
        sleeve.advance_to(pd.Timestamp("2010-01-04"))
        # Then read sleeve.equity for the current sleeve value
    """

    def __init__(self, initial_capital: float):
        self._initial_capital = float(initial_capital)
        self._equity = float(initial_capital)
        self._holdings: Dict[str, float] = {}  # ticker → notional dollars
        self._last_rebalance: Optional[pd.Timestamp] = None
        self._last_advanced_to: Optional[pd.Timestamp] = None

        # Pre-load the 8 ETF substrate
        self._prices = _load_basket()
        # Cache trading-day index from SPY (the canonical calendar).
        self._calendar = pd.DatetimeIndex(self._prices.index).normalize()

    @property
    def equity(self) -> float:
        """Current sleeve equity (cash + market value, single bucket)."""
        return self._equity

    @property
    def initial_capital(self) -> float:
        return self._initial_capital

    @property
    def holdings(self) -> Dict[str, float]:
        return dict(self._holdings)

    def _is_rebalance_due(self, as_of: pd.Timestamp) -> bool:
        """Monthly cadence — first observable trading day of a new month."""
        if self._last_rebalance is None:
            return True
        return (as_of.year, as_of.month) != (
            self._last_rebalance.year, self._last_rebalance.month,
        )

    def _compute_target_weights(self, as_of: pd.Timestamp) -> Dict[str, float]:
        """Momentum-rank + inverse-vol on the 8 ETFs, top-N=4, max_pos=0.30."""
        # Find the closest prior trading day with full data.
        idx = self._prices.index
        valid_idx = idx[idx <= as_of]
        if len(valid_idx) < LOOKBACK_DAYS + 1:
            return {}  # insufficient history; abstain
        end = valid_idx[-1]
        start = valid_idx[-(LOOKBACK_DAYS + 1)]

        window = self._prices.loc[start:end]
        if window.isna().any().any() or window.shape[0] < LOOKBACK_DAYS:
            # If any ETF has missing data over the lookback, drop it
            avail = window.dropna(axis=1, how="any")
            if avail.shape[1] < TOP_N:
                return {}
            window = avail

        # Momentum: total return over the lookback
        mom = (window.iloc[-1] / window.iloc[0]) - 1.0
        # Inverse volatility: 1 / annualized std of last vol_window daily returns
        rets = window.pct_change().dropna()
        if rets.shape[0] < VOL_WINDOW_DAYS:
            return {}
        recent_rets = rets.iloc[-VOL_WINDOW_DAYS:]
        std = recent_rets.std(ddof=1)
        inv_vol = (1.0 / std.replace(0.0, np.nan)).dropna()

        # Rank by momentum, pick top N
        ranked = mom.sort_values(ascending=False)
        top = [t for t in ranked.index if t in inv_vol.index][:TOP_N]
        if not top:
            return {}

        # Inverse-vol weights, then normalize, then cap
        w = inv_vol.loc[top]
        w = w / w.sum()
        capped = w.clip(upper=MAX_POSITION_WEIGHT)
        # Re-normalize after cap (with remaining headroom)
        if capped.sum() > 0:
            capped = capped / capped.sum()
        return {t: float(capped[t]) for t in top}

    def advance_to(self, as_of: pd.Timestamp) -> None:
        """Advance the sleeve to `as_of`, processing each trading day
        between the prior position and `as_of`. Idempotent re-calls on
        the same date are no-ops.

        Equity compounds via per-bar mark-to-market on current holdings;
        rebalances fire on the first trading day of each new calendar
        month (deterministic monthly cadence).

        FIRST-CALL SEMANTICS: on the very first advance_to call, we
        establish the sleeve's start position AT `as_of` without
        back-compounding through the entire pre-loaded Stooq history.
        The lookback-window for the first rebalance still uses prior
        Stooq closes (the basket's deep history is the FEATURE input),
        but the sleeve's compounding equity curve starts AT `as_of`.
        Without this guard, opening the sleeve in 2024 would start with
        ~19yr of accumulated paper gains as if the sleeve had been
        running since 2005 — corrupting the run's initial equity.
        """
        as_of = pd.Timestamp(as_of).normalize()
        if self._last_advanced_to is not None and as_of <= self._last_advanced_to:
            return

        cal = self._calendar
        if self._last_advanced_to is None:
            # First call — establish position AT as_of. We rebalance ONCE
            # using the trailing 252-day lookback (feature input), then mark
            # _last_advanced_to so future calls only process forward-step
            # bars.
            if self._is_rebalance_due(as_of):
                target = self._compute_target_weights(as_of)
                if target:
                    self._holdings = {t: self._equity * w for t, w in target.items()}
                    self._last_rebalance = as_of
            self._last_advanced_to = as_of
            return

        # Trading days strictly after _last_advanced_to and up to as_of.
        mask = (cal > self._last_advanced_to) & (cal <= as_of)
        days = cal[mask]
        if len(days) == 0:
            self._last_advanced_to = as_of
            return

        for day in days:
            # 1) Mark-to-market existing holdings using today's close
            #    (notional → notional * (px_today / px_yesterday))
            if self._holdings:
                # Find the prior trading day for ratio calc; if first-ever,
                # we set holdings at *today's* close so the ratio is 1.0.
                day_idx_pos = cal.get_loc(day)
                if day_idx_pos > 0:
                    prev = cal[day_idx_pos - 1]
                    prev_prices = self._prices.loc[prev]
                    today_prices = self._prices.loc[day]
                    new_eq = 0.0
                    new_holdings: Dict[str, float] = {}
                    for t, notional in self._holdings.items():
                        if t not in today_prices.index or t not in prev_prices.index:
                            new_holdings[t] = notional
                            new_eq += notional
                            continue
                        py = float(prev_prices[t])
                        px = float(today_prices[t])
                        if py <= 0 or not np.isfinite(py) or not np.isfinite(px):
                            new_holdings[t] = notional
                            new_eq += notional
                            continue
                        nt = notional * (px / py)
                        new_holdings[t] = nt
                        new_eq += nt
                    self._holdings = new_holdings
                    self._equity = new_eq
                # else: very first day, no prior price → no MTM step

            # 2) Rebalance check — first trading day of a new month
            if self._is_rebalance_due(day):
                target = self._compute_target_weights(day)
                if target:
                    eq_now = self._equity
                    self._holdings = {t: eq_now * w for t, w in target.items()}
                    self._last_rebalance = day

        self._last_advanced_to = as_of

    def state_dict(self) -> Dict:
        """For diagnostics + journaling — current sleeve state."""
        return {
            "equity": self._equity,
            "initial_capital": self._initial_capital,
            "holdings": dict(self._holdings),
            "last_rebalance": str(self._last_rebalance) if self._last_rebalance is not None else None,
            "last_advanced_to": str(self._last_advanced_to) if self._last_advanced_to is not None else None,
        }
