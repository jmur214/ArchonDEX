"""T-350 (Act 2 / Phase 1) — the DEPLOY-CANDIDATE constructor: the structural stack.

The allocation the real-money option would eventually read: a VOO core, a
long-only momentum satellite (MTUM — the ONLY CI-significant tilt T-318/T-320
found, and half its premium already decayed), and **SGOV as the cash leg** so no
dollar sits idle at 0%. Same shape as ``llm_analyst_constructor``: target weights
→ whole-share deltas → ``OrderSpec``s, duck-typed ``.construct()``, fail-closed.

Three things here are deliberate and worth reading before changing anything.

**1. The weights are CONFIG, not constants in code.** The approved plan gives
RANGES (VOO ~80-85%, MTUM 15-20%), which means the exact split is a judgement
inside an approved envelope — so it lives where it can be changed without a code
deploy. The default sits at the CONSERVATIVE end (85/15) on non-data grounds:
T-318/T-320 found the momentum tilt CI-significant but with ~half its premium
decayed, and the program's standing posture is the smallest honest dose of an
edge that is real-but-fading. This is a stated judgement, not a measurement.

**2. The bands are frozen on NON-DATA grounds, and scaled to the trade quantum.**
T-297's argument, re-used exactly: *a band below the quantum cannot bind*. At a
$10k sub-budget one VOO share is ~6% of the book and one MTUM share ~2.3%, so a
flat "±2% deadband" would be unreachable for the core and trivially crossed by
the satellite — the same band meaning two different things. Bands are therefore
expressed in SHARE QUANTA of the instrument they govern, which makes them binding
by construction and keeps them out of the data (nothing here is fitted).

**3. The buy/hold spread is asymmetric, and the mapping is a judgement I am
flagging.** Novy-Marx–Velikov's spread is "stricter to enter than to maintain".
For a *static* allocation there is no entry/exit — you always hold both legs — so
the faithful translation is a choice, and I made it explicit rather than implying
a derivation I do not have: **buying is held to a wider band than trimming.**
Rationale: the wide buy band stops the book averaging into a satellite that is
falling (the failure mode a momentum tilt is most exposed to), while the tighter
sell band keeps the core anchored. If D or the director prefers the mirror
mapping (let winners run: wide on both sides, widest on the sell), it is one
config change — the asymmetry is parameterised, not baked.

CASH-FLOW-AWARE (the Phase-1.5 machine-side rule): when the book is under target
and cash is available, the gap is closed by BUYING WITH CASH before anything is
sold. Selling to fund a rebalance realises gains and burns the wash-guard window
for no reason when a contribution can do the same work.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from paper_trader.order_construction import OrderSpec

STREAM = "deploy_candidate"
EDGE = "deploy_candidate"
CONFIG_REL = "config/deploy_candidate.json"

# --- defaults, used only when the config file is absent (tests, first run) ------
# Weights are a JUDGEMENT inside the approved range (see module docstring §1).
DEFAULT_CORE = ("VOO", 0.85)
DEFAULT_SATELLITE = ("MTUM", 0.15)
DEFAULT_CASH = "SGOV"          # the cash leg — every idle dollar, never 0% cash

# Bands in SHARE QUANTA of the instrument they govern (docstring §2/§3).
# buy > sell ⇒ stricter to add than to trim.
DEFAULT_BUY_BAND_Q = 1.5
DEFAULT_SELL_BAND_Q = 1.0

# A weight that drifts this far is corrected regardless of the quantum bands — the
# backstop that keeps a cheap instrument from wandering unboundedly.
DEFAULT_MAX_DRIFT = 0.10


@dataclass
class DeployCandidatePlan:
    orders: List[OrderSpec] = field(default_factory=list)
    targets: Dict[str, float] = field(default_factory=dict)
    target_qty: Dict[str, int] = field(default_factory=dict)
    held_qty: Dict[str, int] = field(default_factory=dict)
    signals: Dict[str, float] = field(default_factory=dict)   # == targets (fleet parity)
    stream: str = STREAM
    degraded: bool = False
    reject_reason: Optional[str] = None
    # Why each name did or did not trade — a no-trade day must never be
    # indistinguishable from a broken constructor (the daily/v2 lesson).
    band_report: Dict[str, str] = field(default_factory=dict)
    cash_deployed: float = 0.0
    funded_by_cash: List[str] = field(default_factory=list)   # gaps closed WITHOUT selling


class DeployCandidateConstructor:
    """Static-target rebalancer with quantum-scaled asymmetric bands + a cash leg."""

    def __init__(self, *, trade_date: str, root: Optional[str] = None,
                 tif: str = "day", sub_budget: float = 1.0,
                 config: Optional[dict] = None):
        self.trade_date = str(trade_date)
        self.root = root
        self.tif = tif
        # FLEET IDIOM: ``sub_budget`` is a FRACTION of the sizing equity, not a
        # dollar figure — the dollar budget is ``equity * sub_budget``, and the
        # pipeline hands us ``sizing_equity = min(equity, notional_cap)``. Getting
        # this wrong would have silently bypassed the notional cap at exactly the
        # moment it matters most: the arrival-event tier reset.
        self.sub_budget = float(sub_budget)
        cfg = config if config is not None else self._load_config()
        core = cfg.get("core", {})
        sat = cfg.get("satellite", {})
        self.core_ticker = str(core.get("ticker", DEFAULT_CORE[0])).upper()
        self.core_weight = float(core.get("weight", DEFAULT_CORE[1]))
        self.sat_ticker = str(sat.get("ticker", DEFAULT_SATELLITE[0])).upper()
        self.sat_weight = float(sat.get("weight", DEFAULT_SATELLITE[1]))
        self.cash_ticker = str(cfg.get("cash_ticker", DEFAULT_CASH)).upper()
        bands = cfg.get("bands", {})
        self.buy_band_q = float(bands.get("buy_quanta", DEFAULT_BUY_BAND_Q))
        self.sell_band_q = float(bands.get("sell_quanta", DEFAULT_SELL_BAND_Q))
        self.max_drift = float(bands.get("max_drift", DEFAULT_MAX_DRIFT))
        # FAIL-CLOSED on an incoherent allocation: weights that do not sum to 1.0
        # would silently leave (or over-commit) a slice of the book, and a
        # deploy-candidate record built on a mis-specified allocation measures
        # nothing. Refuse to construct rather than trade a config typo.
        total = self.core_weight + self.sat_weight
        if not (0.0 < total <= 1.0 + 1e-9):
            raise ValueError(
                f"deploy-candidate weights must sum to (0, 1]: "
                f"{self.core_ticker}={self.core_weight} + {self.sat_ticker}="
                f"{self.sat_weight} = {total}")
        if self.buy_band_q < self.sell_band_q:
            raise ValueError(
                "buy band must be >= sell band (stricter to add than to trim — the "
                f"buy/hold spread): buy={self.buy_band_q}q sell={self.sell_band_q}q")

    def _load_config(self) -> dict:
        base = Path(self.root) if self.root else Path(__file__).resolve().parents[1]
        p = base / CONFIG_REL
        try:
            return json.loads(p.read_text()) if p.exists() else {}
        except Exception:      # noqa: BLE001 — a broken config must never ENABLE trading
            raise ValueError(f"deploy-candidate config unreadable at {CONFIG_REL} "
                             "— refusing to construct on a guessed allocation")

    # ------------------------------------------------------------------ #
    def targets(self) -> Dict[str, float]:
        return {self.core_ticker: self.core_weight, self.sat_ticker: self.sat_weight}

    def _band(self, px: float, side: str, budget: float) -> float:
        """The no-trade band for one name, as a WEIGHT, scaled to its own share
        quantum (docstring §2). Below the quantum a band cannot bind, so the band
        is denominated in quanta rather than in flat percentage points."""
        quantum = px / budget if budget > 0 else 0.0
        q = self.buy_band_q if side == "buy" else self.sell_band_q
        return quantum * q

    # ---- the fleet constructor interface ----
    def construct(self, equity: float, current_positions: Dict[str, int],
                  closes: Dict[str, "object"]) -> DeployCandidatePlan:
        plan = DeployCandidatePlan()
        plan.targets = {k: round(v, 4) for k, v in self.targets().items()}
        plan.signals = dict(plan.targets)

        def _last(t: str) -> Optional[float]:
            c = closes.get(t) if closes else None
            if c is None:
                return None
            try:
                c = c.dropna() if hasattr(c, "dropna") else c
                v = float(c.iloc[-1]) if hasattr(c, "iloc") else float(c)
                return v if v > 0 else None
            except Exception:   # noqa: BLE001
                return None

        budget = float(equity) * self.sub_budget
        need = [self.core_ticker, self.sat_ticker, self.cash_ticker]
        px = {t: _last(t) for t in need}
        # FAIL-CLOSED: a missing price on a name we would TRADE holds the whole day
        # with a stated reason. Never a partial rebalance on a guessed price.
        missing = [t for t in (self.core_ticker, self.sat_ticker) if px.get(t) is None]
        if missing:
            plan.degraded = True
            plan.reject_reason = f"missing_price:{','.join(sorted(missing))}"
            return plan

        held = {t: int(current_positions.get(t, 0)) for t in need}
        plan.held_qty = dict(held)

        # 1. what the book SHOULD hold, in whole shares
        for t, w in self.targets().items():
            plan.target_qty[t] = int(budget * w / px[t])

        # 2. cash available BEFORE any sale: the slice of the budget not already
        #    committed to core/satellite/cash-leg holdings.
        invested = sum(held[t] * px[t] for t in need if px.get(t))
        free_cash = max(0.0, budget - invested)

        # 3. per-name band decision. Buying is held to the WIDER band.
        deltas: Dict[str, int] = {}
        for t in (self.core_ticker, self.sat_ticker):
            tgt_w = self.targets()[t]
            cur_w = held[t] * px[t] / budget if budget > 0 else 0.0
            gap = tgt_w - cur_w                      # >0 underweight, <0 overweight
            side = "buy" if gap > 0 else "sell"
            band = self._band(px[t], side, budget)
            if abs(gap) <= band and abs(gap) < self.max_drift:
                plan.band_report[t] = (
                    f"HOLD gap {gap:+.4f} within {side} band {band:.4f} "
                    f"({self.buy_band_q if side == 'buy' else self.sell_band_q}q "
                    f"@ {px[t]:.2f})")
                continue
            d = plan.target_qty[t] - held[t]
            if d == 0:
                plan.band_report[t] = f"HOLD gap {gap:+.4f} but whole-share delta is 0"
                continue
            deltas[t] = d
            why = "max_drift" if abs(gap) >= self.max_drift else f"{side} band {band:.4f}"
            plan.band_report[t] = f"TRADE {d:+d} sh — gap {gap:+.4f} exceeds {why}"

        # 4. CASH-FLOW-AWARE: fund buys from cash before selling anything. If cash
        #    (incl. what the cash leg can free) covers the buys, no sale is needed —
        #    selling to fund a rebalance realises gains and burns wash-guard window
        #    for work a contribution can do for free.
        buys = {t: d for t, d in deltas.items() if d > 0}
        buy_cost = sum(d * px[t] for t, d in buys.items())
        cash_leg_value = held[self.cash_ticker] * (px.get(self.cash_ticker) or 0.0)
        if buy_cost > 0 and (free_cash + cash_leg_value) >= buy_cost:
            plan.funded_by_cash = sorted(buys)
        plan.cash_deployed = round(min(buy_cost, free_cash + cash_leg_value), 2)

        # 5. the cash leg sweeps whatever remains — every idle dollar, never 0%.
        #    Computed AFTER the core/satellite deltas so it sweeps the true residue.
        if px.get(self.cash_ticker):
            cash_after = free_cash - buy_cost + sum(
                -d * px[t] for t, d in deltas.items() if d < 0)
            target_cash_sh = held[self.cash_ticker] + int(cash_after / px[self.cash_ticker])
            target_cash_sh = max(0, target_cash_sh)
            plan.target_qty[self.cash_ticker] = target_cash_sh
            d = target_cash_sh - held[self.cash_ticker]
            if d != 0:
                deltas[self.cash_ticker] = d
                plan.band_report[self.cash_ticker] = (
                    f"CASH-LEG {d:+d} sh — sweeping idle cash "
                    f"({cash_after:.2f} at {px[self.cash_ticker]:.2f})")
        else:
            plan.band_report[self.cash_ticker] = (
                "CASH-LEG unpriced — idle cash left uninvested (stated, not silent)")

        # 6. emit
        for t in sorted(deltas):
            d = deltas[t]
            plan.orders.append(OrderSpec(
                ticker=t, side=("buy" if d > 0 else "sell"), qty=abs(d),
                tif=self.tif, engine_side=("long" if d > 0 else "exit"), edge=EDGE))
        return plan
