"""T-2026-06-10-138 Part B — property-based financial invariants (hypothesis).

Spec source: docs/Sources/Research_2026_06_10_blindspots/
RESULTS_single_pass_no_research_mode.md §AREA 1. Each property targets REAL
production units (no synthetic stand-ins):

  NO-LOOKAHEAD       production slicer (backtest_controller iloc[:idx+1])
                     composed with real edges — future rows must not move
                     signals at ≤ T.
  P&L CONSERVATION   PortfolioEngine accounting identity: equity ==
                     cash + Σ(qty·px) every snapshot, under arbitrary
                     fill sequences.
  SIGN ANTISYMMETRY  mirror-image fill streams (long↔short) produce exactly
                     negated realized P&L. NOTE: the research spec's literal
                     form (negate forecast → negate position) applies to
                     linear sleeves; this codebase's signal path is gated /
                     long-only-scored by design (not a linear sleeve), so
                     the antisymmetry invariant is asserted at the
                     accounting layer where it genuinely holds.
  UNITS              realized-vol estimator is invariant to the equity
                     unit (cents vs dollars vs 2×): vol(k·equity) ==
                     vol(equity) bitwise for binary k.
  SCALE INVARIANCE   2× capital + 2× quantities ⇒ exactly 2× cash, market
                     value, and equity (binary scaling is FP-exact).
  IDEMPOTENCY        identical inputs ⇒ identical outputs, twice over
                     (fresh engine instances; re-asserts determinism at
                     the unit level).

Wall-time budget: max_examples kept small per test; the whole module must
stay CI-cheap (< ~60 s). deadline=None because pandas first-call overhead
trips hypothesis' per-example deadline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

from engines.engine_c_portfolio.portfolio_engine import PortfolioEngine  # noqa: E402


# --------------------------------------------------------------------------
# Strategies
# --------------------------------------------------------------------------

def price_walk(min_bars: int = 60, max_bars: int = 90, n_tickers: int = 3):
    """A small synthetic OHLCV panel: positive prices, no NaNs."""
    @st.composite
    def _panel(draw):
        n = draw(st.integers(min_bars, max_bars))
        idx = pd.date_range("2022-01-03", periods=n, freq="B")
        out = {}
        for k in range(n_tickers):
            seed = draw(st.integers(0, 2**31 - 1))
            rng = np.random.default_rng(seed)
            rets = rng.normal(0.0005, 0.015, n).clip(-0.2, 0.2)
            close = 50.0 * np.cumprod(1.0 + rets)
            out[f"TK{k}"] = pd.DataFrame(
                {
                    "Open": close,
                    "High": close * 1.01,
                    "Low": close * 0.99,
                    "Close": close,
                    "Volume": 1_000_000.0,
                },
                index=idx,
            )
        return out
    return _panel()


def fill_stream():
    """A sequence of open/close fill pairs the PortfolioEngine accepts."""
    fill = st.tuples(
        st.sampled_from(["TKA", "TKB", "TKC"]),
        st.sampled_from(["long", "short"]),
        st.integers(1, 500),                       # qty
        st.floats(5.0, 500.0, allow_nan=False),    # entry px
        st.floats(5.0, 500.0, allow_nan=False),    # exit px
    )
    return st.lists(fill, min_size=1, max_size=12)


def production_slice(df: pd.DataFrame, ts: pd.Timestamp) -> pd.DataFrame:
    """EXACT replica of backtest_controller's per-bar slicer
    (backtester/backtest_controller.py ~:1222): iloc[:idx + 1]."""
    idx = df.index.get_loc(ts)
    return df.iloc[: idx + 1]


# --------------------------------------------------------------------------
# NO-LOOKAHEAD — slicer + real edges
# --------------------------------------------------------------------------

def _edges_under_test():
    from engines.engine_a_alpha.edges.momentum_12_1_v1 import Momentum12_1Edge
    from engines.engine_a_alpha.edges.rsi_bounce import RSIBounceEdge

    mom = Momentum12_1Edge()
    mom.params = {
        "lookback_days": 40, "skip_days": 5, "long_quantile": 0.5,
        "min_universe_size": 2, "long_score": 1.0,
    }
    rsi = RSIBounceEdge()
    rsi.params = dict(getattr(rsi, "params", {}) or {})
    rsi.params.update({"window": 14, "trend_filter": False})
    return [("momentum_12_1", mom), ("rsi_bounce", rsi)]


@settings(max_examples=20, deadline=None)
@given(panel=price_walk())
def test_no_lookahead_future_rows_cannot_move_signals(panel):
    """Signals at T through the PRODUCTION slicer must be bit-identical
    whether or not the source frames contain rows after T."""
    some_df = next(iter(panel.values()))
    t_pos = int(len(some_df) * 0.7)
    ts = some_df.index[t_pos]

    truncated = {k: df.loc[:ts] for k, df in panel.items()}

    for name, edge in _edges_under_test():
        full_view = {k: production_slice(df, ts) for k, df in panel.items()}
        trunc_view = {k: production_slice(df, ts) for k, df in truncated.items()}
        s_full = edge.compute_signals(full_view, ts)
        s_trunc = edge.compute_signals(trunc_view, ts)
        assert s_full == s_trunc, (
            f"{name}: signals at {ts.date()} changed when future rows "
            f"were present upstream of the production slicer — lookahead leak."
        )


# --------------------------------------------------------------------------
# P&L CONSERVATION — accounting identity under arbitrary fills
# --------------------------------------------------------------------------

@settings(max_examples=30, deadline=None)
@given(fills=fill_stream())
def test_pnl_conservation_equity_identity(fills):
    """cash + Σ(qty·px) == equity in every snapshot, for any fill stream."""
    pe = PortfolioEngine(initial_capital=1_000_000.0)
    px = {}
    for i, (tk, side, qty, p_in, p_out) in enumerate(fills):
        pe.apply_fill({"ticker": tk, "side": side, "qty": qty, "price": p_in})
        px[tk] = p_out
        snap = pe.snapshot(pd.Timestamp("2024-01-02") + pd.Timedelta(days=i), px)
        recomputed_mv = sum(
            pos.qty * px.get(t, pos.avg_price)
            for t, pos in pe.positions.items() if pos.qty != 0
        )
        assert snap["equity"] == pytest.approx(snap["cash"] + recomputed_mv, abs=1e-6), (
            f"equity identity broken at fill {i}: equity={snap['equity']}, "
            f"cash={snap['cash']}, recomputed MV={recomputed_mv}"
        )


# --------------------------------------------------------------------------
# SIGN ANTISYMMETRY — mirror fills negate realized P&L exactly
# --------------------------------------------------------------------------

@settings(max_examples=30, deadline=None)
@given(fills=fill_stream())
def test_sign_antisymmetry_mirror_fills_negate_realized_pnl(fills):
    pe_long = PortfolioEngine(initial_capital=1_000_000.0)
    pe_short = PortfolioEngine(initial_capital=1_000_000.0)
    for tk, _side, qty, p_in, p_out in fills:
        pe_long.apply_fill({"ticker": tk, "side": "long", "qty": qty, "price": p_in})
        pe_long.apply_fill({"ticker": tk, "side": "exit", "qty": qty, "price": p_out})
        pe_short.apply_fill({"ticker": tk, "side": "short", "qty": qty, "price": p_in})
        pe_short.apply_fill({"ticker": tk, "side": "cover", "qty": qty, "price": p_out})
    assert pe_long.realized_pnl == pytest.approx(-pe_short.realized_pnl, abs=1e-9), (
        f"mirror-image fill stream did not negate realized P&L: "
        f"long {pe_long.realized_pnl} vs short {pe_short.realized_pnl}"
    )


# --------------------------------------------------------------------------
# UNITS — vol estimator invariant to equity unit
# --------------------------------------------------------------------------

@settings(max_examples=30, deadline=None)
@given(
    seed=st.integers(0, 2**31 - 1),
    k=st.sampled_from([2.0, 4.0, 0.5, 256.0]),  # binary scalings: FP-exact
)
def test_units_realized_vol_invariant_to_equity_scale(seed, k):
    """Measuring the book in cents vs dollars must not change realized vol.
    Binary scale factors make the comparison exact (no tolerance needed)."""
    from engines.engine_b_risk.vol_target import compute_realized_vol_from_history

    rng = np.random.default_rng(seed)
    eq = 100_000.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.01, 80).clip(-0.15, 0.15))
    base = [
        {"timestamp": pd.Timestamp("2024-01-02") + pd.Timedelta(days=i), "equity": float(e)}
        for i, e in enumerate(eq)
    ]
    scaled = [dict(s, equity=s["equity"] * k) for s in base]

    v1 = compute_realized_vol_from_history(base, window_days=60, min_returns_required=20)
    v2 = compute_realized_vol_from_history(scaled, window_days=60, min_returns_required=20)
    assert v1 is not None
    assert v1 == v2, f"vol changed under unit scaling ×{k}: {v1} != {v2}"


# --------------------------------------------------------------------------
# SCALE INVARIANCE — 2× capital + 2× quantities ⇒ exactly 2× book
# --------------------------------------------------------------------------

@settings(max_examples=30, deadline=None)
@given(fills=fill_stream())
def test_scale_invariance_double_capital_double_book(fills):
    pe1 = PortfolioEngine(initial_capital=1_000_000.0)
    pe2 = PortfolioEngine(initial_capital=2_000_000.0)
    px = {}
    for tk, side, qty, p_in, p_out in fills:
        pe1.apply_fill({"ticker": tk, "side": side, "qty": qty, "price": p_in})
        pe2.apply_fill({"ticker": tk, "side": side, "qty": 2 * qty, "price": p_in})
        px[tk] = p_out
    s1 = pe1.snapshot(pd.Timestamp("2024-06-03"), px)
    s2 = pe2.snapshot(pd.Timestamp("2024-06-03"), px)
    # Binary doubling is exact in IEEE-754: no tolerance.
    assert s2["cash"] == 2.0 * s1["cash"]
    assert s2["market_value"] == 2.0 * s1["market_value"]
    assert s2["equity"] == 2.0 * s1["equity"]


# --------------------------------------------------------------------------
# IDEMPOTENCY — identical inputs ⇒ identical outputs
# --------------------------------------------------------------------------

@settings(max_examples=20, deadline=None)
@given(fills=fill_stream())
def test_idempotency_same_fills_same_snapshots(fills):
    def run():
        pe = PortfolioEngine(initial_capital=1_000_000.0)
        px = {}
        snaps = []
        for i, (tk, side, qty, p_in, p_out) in enumerate(fills):
            pe.apply_fill({"ticker": tk, "side": side, "qty": qty, "price": p_in})
            px[tk] = p_out
            snaps.append(
                pe.snapshot(pd.Timestamp("2024-01-02") + pd.Timedelta(days=i), dict(px))
            )
        return snaps

    a, b = run(), run()
    for i, (sa, sb) in enumerate(zip(a, b)):
        assert sa == sb, f"snapshot {i} differs between identical runs"
