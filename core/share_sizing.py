"""Integer share counts under a DECLARED price basis (L4, approved 2026-10-22).

The defect (item (d) scan, L4 — ``docs/Sources/scan_price_level_consumers_item_d_2026_10_15.md``):
the canonical price cache is TOTAL-RETURN back-adjusted, so a past ``Close`` is the true print
multiplied by the cumulative dividend factor still to come (SPY 2000: 0.625 of its print; XOM: 0.43).
``int(delta_notional / Close)`` therefore bought 1.6 SPY "shares" per dollar in 2000 where the real
print allowed 1.0 — the integer constraint was applied to a quantity that is not a share.

The arithmetic, stated once here and nowhere else (the one helper rule, locked by AST):

  * The ledger (Engine C ``Position.qty``) and every mark, fill and cash movement are in ADJUSTED
    units: one unit is worth ``Close`` today and is filled at the adjusted next-bar Open. A unit is
    the DRIP-equivalent of a real share: ``units = real_shares * close_unadj / Close``.
  * Reality constrains REAL shares to integers at the price that traded, ``close_unadj``
    (split-adjusted, dividend-UNadjusted — the total-return writer's unadjusted mode):

        shares_traded = trunc(notional / close_unadj)             # the shares that could trade
        qty (units)   = trunc(shares_traded * close_unadj / Close) # their value, in ledger units

    so ``qty * Close == shares_traded * close_unadj`` to within one unit: the dollars deployed are
    the dollars that would have traded. (Sizing on ``close_unadj`` but carrying the real count as
    the ledger qty — "71 shares marked at the adjusted $87.5" — would deploy only 62% of a 2000 SPY
    ticket and leave the rest in cash: a yield-correlated under-investment larger than the defect.)
  * Where ``close_unadj`` is ABSENT (today's canonical cache, before the cutover writer lands
    the column) the count is ``int(notional / Close)`` EXACTLY as before — byte-identical canon — and
    the basis is RECORDED: the census field ``share_price_basis`` reads ``total_return``. In a
    measured/canonical run that is a census FACT, not a failure, until the cutover lands (the user
    ruled the cutover; the field flips to ``unadjusted`` when the new substrate carries the column).
  * Where the column is PRESENT but the bar's value is NaN or non-positive, the substrate declares
    the column and has a hole in it: in a MEASURED run that is a missing load-bearing input and the
    read HALTS (``core.measured.halt_or_degrade``); outside measured mode the bar sizes on ``Close``
    and is recorded as ``unadjusted_nan`` — never silently as ``unadjusted``.

Engine boundary: this is sizing ARITHMETIC (a unit conversion), consumed by Engine B's sizing and by
Engine C's production-parity baseline. It carries no risk policy and no signal logic. The paper and
live paths size on live broker prices and never import this module (locked).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from core.measured import halt_or_degrade

__all__ = [
    "BASIS_TOTAL_RETURN",
    "BASIS_UNADJUSTED",
    "BASIS_UNADJUSTED_NAN",
    "CLOSE_UNADJ_COLUMN",
    "ShareSizing",
    "trunc_shares",
    "size_shares",
    "size_units",
    "size_real_shares",
    "read_close_unadj",
    "share_price_basis_summary",
]

#: The split-adjusted, dividend-unadjusted close the total-return writer lands beside ``Close``.
CLOSE_UNADJ_COLUMN = "close_unadj"

BASIS_UNADJUSTED = "unadjusted"          # integer shares from close_unadj, carried as ledger units
BASIS_TOTAL_RETURN = "total_return"      # the column is absent (pre-cutover cache): int(notional/Close)
BASIS_UNADJUSTED_NAN = "unadjusted_nan"  # the column is present, this bar is NaN/<=0 (non-measured only)

#: Integer-boundary tolerance on the unadjusted path, in shares, applied TOWARD the trade direction:
#: ``(k * Close) / Close`` is not always ``k`` in IEEE arithmetic, and a non-payer's ``close_unadj``
#: equals its ``Close`` — without this, an exact 3-share trade could truncate to 2. The total-return
#: path carries NO tolerance: it is today's ``int(notional / price)`` byte for byte.
_SHARE_TOL = 1e-9


@dataclass(frozen=True)
class ShareSizing:
    """One sizing decision: the ledger qty the order carries, and the basis that produced it."""
    qty: int                          # ledger units (adjusted-Close units); what the order carries
    shares_traded: Optional[int]      # real shares at close_unadj; None unless basis == unadjusted
    basis: str                        # BASIS_UNADJUSTED | BASIS_TOTAL_RETURN | BASIS_UNADJUSTED_NAN
    close: float                      # the adjusted Close sized against
    close_unadj: Optional[float]      # the unadjusted close used (None unless basis == unadjusted)


def trunc_shares(
    notional: Any, close: Any, close_unadj: Optional[Any] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """THE arithmetic, vectorised (scalars and same-shape arrays alike).

    Returns ``(units, shares_traded)`` with truncation toward zero (the sign of ``notional`` is the
    trade direction). ``shares_traded`` is NaN wherever the basis is total return. ``close_unadj``
    may be None (all total return) or an array whose NaN / non-positive entries mean "absent" for
    that element — those elements size on ``close`` exactly as before.
    """
    notional = np.asarray(notional, dtype=float)
    close = np.asarray(close, dtype=float)
    units_tr = np.trunc(notional / close)
    if close_unadj is None:
        return units_tr, np.full(np.shape(units_tr), np.nan)
    cu = np.asarray(close_unadj, dtype=float)
    have = np.isfinite(cu) & (cu > 0.0)
    cu_safe = np.where(have, cu, 1.0)
    nudge = np.sign(notional) * _SHARE_TOL
    shares = np.trunc(notional / cu_safe + nudge)
    units_un = np.trunc(shares * cu_safe / close + nudge)
    units = np.where(have, units_un, units_tr)
    shares_out = np.where(have, shares, np.nan)
    return units, shares_out


def _basis_of(close_unadj: Optional[float]) -> str:
    if close_unadj is None:
        return BASIS_TOTAL_RETURN
    try:
        v = float(close_unadj)
    except (TypeError, ValueError):
        return BASIS_UNADJUSTED_NAN
    return BASIS_UNADJUSTED if (np.isfinite(v) and v > 0.0) else BASIS_UNADJUSTED_NAN


def size_shares(notional: float, close: float, close_unadj: Optional[float]) -> ShareSizing:
    """Dollars -> ledger units (Engine B Path A: ``delta_notional``).

    Total-return basis (``close_unadj`` None): ``qty == int(notional / close)`` exactly.
    """
    basis = _basis_of(close_unadj)
    cu = float(close_unadj) if basis == BASIS_UNADJUSTED else None
    units, shares = trunc_shares(float(notional), float(close), cu)
    return ShareSizing(
        qty=int(units), shares_traded=(int(shares) if cu is not None else None),
        basis=basis, close=float(close), close_unadj=cu,
    )


def size_units(units: float, close: float, close_unadj: Optional[float]) -> ShareSizing:
    """A unit count -> ledger units (Engine B Path B: ATR sizing lands in adjusted units).

    Total-return basis: ``qty == int(units)`` exactly — no multiply/divide is introduced on the
    canon path. Unadjusted basis: the units' dollars go through ``size_shares``.
    """
    basis = _basis_of(close_unadj)
    if basis != BASIS_UNADJUSTED:
        return ShareSizing(qty=int(units), shares_traded=None, basis=basis,
                           close=float(close), close_unadj=None)
    return size_shares(float(units) * float(close), close, close_unadj)


def size_real_shares(n_real: int, close: float, close_unadj: Optional[float]) -> ShareSizing:
    """A REAL share count (a 1-share probe, an ADV clip in shares) -> ledger units.

    Total-return basis: ``qty == int(n_real)`` exactly (a share and a unit are the same thing there).
    """
    basis = _basis_of(close_unadj)
    if basis != BASIS_UNADJUSTED:
        return ShareSizing(qty=int(n_real), shares_traded=None, basis=basis,
                           close=float(close), close_unadj=None)
    return size_shares(float(n_real) * float(close_unadj), close, close_unadj)


def read_close_unadj(row: Any, ticker: str = "") -> Optional[float]:
    """The bar's ``close_unadj``, read ONCE per sizing from the same row the ``Close`` came from.

    * column absent -> None (the pre-cutover cache; the basis is recorded ``total_return``);
    * present and finite/positive -> the float;
    * present but NaN / non-positive -> a hole in a declared, load-bearing column: in a MEASURED run
      ``halt_or_degrade`` raises ``MeasurementHalt`` here; otherwise NaN is returned and the sizing
      records ``unadjusted_nan`` (never a silent ``unadjusted``, never a silent ``total_return``).
    """
    if row is None:
        return None
    try:
        if CLOSE_UNADJ_COLUMN not in row:
            return None
        raw = row[CLOSE_UNADJ_COLUMN]
        if isinstance(raw, pd.Series):
            raw = raw.iloc[-1]
        v = float(raw)
    except (TypeError, ValueError):
        v = float("nan")
    if np.isfinite(v) and v > 0.0:
        return v
    halt_or_degrade(
        f"share_sizing:{ticker or '<ticker>'}", load_bearing=True, active=True,
        reason=f"{CLOSE_UNADJ_COLUMN} is present but {raw!r} on the sizing bar — a hole in the "
               f"declared unadjusted column",
    )
    return float("nan")


def share_price_basis_summary(counts: Optional[Mapping[str, int]]) -> Dict[str, Any]:
    """The census record: which price basis sized integer shares this run.

    ``{"basis": "unadjusted" | "total_return" | "unadjusted_nan" | "mixed" | "none",
       "counts": {basis: n_sizings}, "n_sized": total}``

    ``mixed`` when more than one basis was observed (its counts say how many each); ``none`` when
    nothing was sized. ``counts`` None — the producer was called without the run's sizing counts —
    is an ERROR record: the basis was never measured, and ``assert_census`` fails an errored record.
    A ``total_return`` basis is a recorded fact, not a failure, until the cutover lands.
    """
    if counts is None:
        return {"error": "share price basis never measured — no sizing counts were supplied"}
    clean = {str(k): int(v) for k, v in sorted(dict(counts).items()) if int(v) > 0}
    n = int(sum(clean.values()))
    if n == 0:
        basis = "none"
    elif len(clean) == 1:
        basis = next(iter(clean))
    else:
        basis = "mixed"
    return {"basis": basis, "counts": clean, "n_sized": n}
