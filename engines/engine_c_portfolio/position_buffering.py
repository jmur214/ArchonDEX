# engines/engine_c_portfolio/position_buffering.py
"""Carver position buffering — 10% position inertia (T-148).

Trade only when the current position has drifted outside a band around
the optimal position, and then trade to the band EDGE, not the center.
Carver's convention (pysystemtrade / AFTS): buffer = ``buffer_fraction
× |optimal|`` with ``buffer_fraction = 0.10``.

HOW THIS DIFFERS FROM T-098's REFUTED NO-TRADE BAND (load-bearing —
the audit doc carries the full comparison):

  * T-098 was a WEIGHT-level no-trade-or-FULL-trade band: inside the
    band it suppressed the rebalance, outside it traded all the way to
    the target. Its measured failure mechanism: small-Δw rebalances got
    suppressed (trade count −17-19%) but the DOMINANT daily vol-target
    moves passed through at full size — dollar turnover essentially
    unchanged.
  * This is the POSITION-level Carver form with TRADE-TO-EDGE
    semantics: every trade that does execute is shrunk by the band
    width (a move that ends just outside the band executes only its
    excess; a large move executes ``move − band``). It attacks both
    margins — suppression of small moves AND a haircut on every large
    move. Whether that is enough on a diversified daily-vol-target book
    is exactly what the T-148 fixture measures; T-098's failure may
    still partially carry (the haircut on a large move is only
    ``band/move`` relative), and the audit reports that honestly.

Composition order (documented + tested): ``allocate → [dynamic
optimization, T-139] → [position buffering, THIS] → Engine B``. When
dyn-opt is ON, buffering operates on its integer-implied optimal
positions; when OFF, on the unrounded optimal share counts. Output
weights carry the same ±1e-6-share directional nudge as T-139 so
Engine B Path A truncation lands exactly on the buffered integers.

Whole-share awareness: the band edge is rounded INTO the band (lower
edge → ceil, upper edge → floor) so the executed position respects the
band; if the band is narrower than one share and contains no integer,
fall back to the nearest integer to the optimal (the minimal honest
expression). A zero optimal collapses the band to zero → positions
close fully.

Determinism: pure arithmetic over sorted tickers; no RNG, no I/O.
Fail-open contract: any unpriceable ticker passes through unchanged.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

__all__ = ["BufferingResult", "apply_position_buffering"]

_NUDGE_SHARES = 1e-6   # Engine B truncation contract (matches T-139)
_EDGE_TOL = 1e-9       # FP tolerance on band-membership comparisons


@dataclass
class BufferingResult:
    weights: Dict[str, float]            # Engine-B-feasible output weights
    targets: Dict[str, int]              # buffered integer share targets
    suppressed: List[str]                # tickers held (inside band)
    edge_trades: List[str]               # tickers traded to a band edge
    dropped: List[str]                   # unpriceable — passed through
    shares_traded_unbuffered: float      # Σ|round(N*) − C| (what full rebalance would trade)
    shares_traded_buffered: float        # Σ|n_target − C|
    notional_traded_unbuffered: float
    notional_traded_buffered: float
    diagnostics: Dict[str, float] = field(default_factory=dict)


def apply_position_buffering(
    target_weights: Dict[str, float],
    prices: Dict[str, float],
    current_positions: Dict[str, int],
    equity: float,
    buffer_fraction: float = 0.10,
) -> BufferingResult:
    """Apply Carver trade-to-edge buffering to a target-weight map.

    Parameters mirror the T-139 post-processor: ``target_weights`` are
    the (possibly dyn-opt-processed) Engine C weights; ``prices`` the
    same last Closes Engine B sizes from; ``current_positions`` signed
    integer share counts; ``equity`` the bar's sizing equity.
    """
    out_weights: Dict[str, float] = dict(target_weights)
    targets: Dict[str, int] = {}
    suppressed: List[str] = []
    edge_trades: List[str] = []
    dropped: List[str] = []
    sh_unbuf = sh_buf = 0.0
    nt_unbuf = nt_buf = 0.0

    f = max(0.0, float(buffer_fraction))
    valid_equity = equity is not None and math.isfinite(equity) and equity > 0.0

    for tkr in sorted(target_weights.keys()):
        w = target_weights[tkr]
        p = prices.get(tkr)
        if (
            not valid_equity
            or w is None or not math.isfinite(w)
            or p is None or not math.isfinite(p) or p <= 0.0
        ):
            dropped.append(tkr)
            continue

        n_star = w * equity / p                      # optimal shares (float)
        cur = int(current_positions.get(tkr, 0))
        band = f * abs(n_star)
        band_lo = n_star - band
        band_hi = n_star + band

        if band_lo - _EDGE_TOL <= cur <= band_hi + _EDGE_TOL:
            n_target = cur                            # inside the band: hold
            suppressed.append(tkr)
        else:
            if cur < band_lo:
                n_target = math.ceil(band_lo - _EDGE_TOL)
                if n_target > band_hi + _EDGE_TOL:    # band has no integer
                    n_target = round(n_star)
            else:
                n_target = math.floor(band_hi + _EDGE_TOL)
                if n_target < band_lo - _EDGE_TOL:    # band has no integer
                    n_target = round(n_star)
            n_target = int(n_target)
            if n_target == cur:
                suppressed.append(tkr)                # whole-share floor wins
            else:
                edge_trades.append(tkr)

        trade = n_target - cur
        full_trade = round(n_star) - cur
        sh_buf += abs(trade)
        sh_unbuf += abs(full_trade)
        nt_buf += abs(trade) * p
        nt_unbuf += abs(full_trade) * p

        targets[tkr] = n_target
        nudge = _NUDGE_SHARES * (1 if trade > 0 else (-1 if trade < 0 else 0))
        out_weights[tkr] = (n_target + nudge) * p / equity

    return BufferingResult(
        weights=out_weights,
        targets=targets,
        suppressed=suppressed,
        edge_trades=edge_trades,
        dropped=dropped,
        shares_traded_unbuffered=float(sh_unbuf),
        shares_traded_buffered=float(sh_buf),
        notional_traded_unbuffered=float(nt_unbuf),
        notional_traded_buffered=float(nt_buf),
        diagnostics={
            "buffer_fraction": f,
            "n_tickers": float(len(targets)),
        },
    )
