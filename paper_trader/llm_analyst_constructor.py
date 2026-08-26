# paper_trader/llm_analyst_constructor.py
"""LLMAnalystConstructor — account-3 (stage-2) order construction from the constrained
analyst's validated note. THE day-1 stream of the T-329 ladder (analyst-only; the event
desk joins on its T-304 bar, the thesis book on promotion_check — NOT here).

It is the REAL-ORDER sibling of ``LlmShadowBook``: the shadow book runs the analyst's
``hypothetical_actions`` as a virtual record; this constructor turns the SAME validated
target weights into actual account-3 paper orders. It reuses the shadow book's exact
safety discipline:

  * LOOK-AHEAD IMPOSSIBLE — consume YESTERDAY's note (``as_of < trade_date``); the note is
    written after that day's close, so the earliest fill is today's close (signal-t/fill-t+1).
  * FIREWALL RE-ENFORCED (defence in depth; the semantic firewall already bounded the
    shadow actions upstream): ≤``max_weight``/name, gross ≤``max_gross``, turnover
    ≤``max_turnover`` NAV/day. A violating note is REJECTED loudly — orders are held, never
    silently clamped.
  * FAIL-CLOSED — no note, or a missing/º price on any name we'd trade → HOLD (no orders),
    the day flagged ``degraded``; never a blind order.

It produces TARGET WEIGHTS and the whole-share order deltas to reach them; the existing
deterministic OrderManager / exec-gates / reconcile / heartbeat stack does everything else
(this constructor plugs into ``_run_family_strategy`` exactly like the sleeve constructors).

Sub-budget: day-1 the analyst is the ONLY stream, so ``sub_budget`` defaults to 1.0 (the
whole account). The T-329 structure (independent per-stream sub-budgets, no netting) is
carried by this parameter so a second stream can be added without a netting decision.
"""
from __future__ import annotations

import glob
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from paper_trader.order_construction import OrderSpec

NOTES_DIR = "data/intel/analyst_notes"
STREAM = "analyst"                 # the T-329 §3 stream token (day-1 stream)
EDGE = "llm_analyst"

# firewall re-enforcement — MUST match the Stage-1 / shadow-book caps (llm_shadow_book.py)
MAX_WEIGHT = 0.20                  # ≤20% per name
MAX_GROSS = 2.0                   # Σ|w| ≤ 2.0
MAX_TURNOVER = 0.50               # ≤50% NAV/day rebalance turnover

# T-329b: the STALENESS bound on "yesterday's note". `as_of < trade_date` alone is
# unbounded backwards — if the note feed stalls (the analyst step fails, the cloud
# secret lapses, the cross-account pull is denied), the newest note on disk stays
# eligible forever and the account keeps acting on a belief formed weeks ago. That
# is the frozen-price-CSV / stalled-archiver class this program has now hit five
# times, and its signature is always the same: a clock believed to be accruing that
# isn't. Beyond this many CALENDAR days the note is refused and the day HOLDS with a
# stated reason. 5 covers a long weekend plus a holiday; anything longer is a stall,
# not a gap.
MAX_NOTE_AGE_DAYS = 5


@dataclass
class LLMAnalystPlan:
    orders: List[OrderSpec] = field(default_factory=list)
    targets: Dict[str, float] = field(default_factory=dict)     # target WEIGHTS (the LLM decision)
    target_qty: Dict[str, int] = field(default_factory=dict)
    held_qty: Dict[str, int] = field(default_factory=dict)
    signals: Dict[str, float] = field(default_factory=dict)     # == targets (fleet-plan parity)
    note_as_of: Optional[str] = None
    # T-329c: WHICH prompt version produced the note that drove this day. The eval
    # record already segments by (model, prompt_version); the TRADING record must
    # too, or the daily/v2→v3 cohort boundary is invisible in the one place the
    # orders actually live.
    note_prompt_version: Optional[str] = None
    stream: str = STREAM
    degraded: bool = False
    reject_reason: Optional[str] = None     # non-None ⇒ HOLD (no orders); a stated, loud reason
    # T-329c: the analyst held NO view today (empty hypothetical_actions). A real,
    # healthy outcome — NOT degraded, NOT a rejection — but it must be stated, or
    # "the analyst chose to hold" is indistinguishable from "the channel is dead",
    # which is exactly what daily/v2 produced for 15 days running.
    no_view: bool = False
    no_view_reason: Optional[str] = None


class LLMAnalystConstructor:
    def __init__(self, *, trade_date: str, root: Optional[str] = None,
                 notes_dir: str = NOTES_DIR, tif: str = "day", sub_budget: float = 1.0,
                 allowlist: Optional[Tuple[str, ...]] = None,
                 max_weight: float = MAX_WEIGHT, max_gross: float = MAX_GROSS,
                 max_turnover: float = MAX_TURNOVER, note: Optional[dict] = None,
                 max_note_age_days: int = MAX_NOTE_AGE_DAYS):
        self.trade_date = str(trade_date)
        self.root = root
        self.notes_dir = notes_dir
        self.tif = tif
        self.sub_budget = float(sub_budget)
        self.allowlist = tuple(a.upper() for a in allowlist) if allowlist else None
        self.max_weight = float(max_weight)
        self.max_gross = float(max_gross)
        self.max_turnover = float(max_turnover)
        self.max_note_age_days = int(max_note_age_days)
        self._injected_note = note          # tests inject; else loaded from the notes dir

    # ---- note loading (yesterday's validated note — look-ahead impossible) ----
    def _load_yesterday_note(self) -> Tuple[Optional[dict], Optional[str]]:
        if self._injected_note is not None:
            return self._injected_note, None
        base = Path(self.root) if self.root else Path(__file__).resolve().parents[1]
        d = base / self.notes_dir
        if not d.exists():
            return None, "no notes dir yet (dormant-but-armed)"
        try:
            from intelligence.analyst.note_schema import validate_note
        except Exception:                    # pragma: no cover — defensive
            validate_note = None
        cands = []
        for f in glob.glob(str(d / "*.json")):
            try:
                payload = json.loads(Path(f).read_text())
            except Exception:
                continue
            as_of = payload.get("as_of", "")
            if as_of and as_of < self.trade_date:           # STRICTLY yesterday-or-earlier
                cands.append((as_of, payload))
        if not cands:
            return None, "no note with as_of < trade_date yet"
        as_of, payload = max(cands, key=lambda x: x[0])      # the latest such note
        stale = self._staleness(as_of)
        if stale is not None:                                # a stalled feed must HOLD
            return None, stale
        if validate_note is not None:                        # independent re-validation
            note, reason = validate_note(payload)
            if note is None:
                return None, f"note failed re-validation: {reason}"
            payload = note.model_dump()
        return payload, None

    def _staleness(self, as_of: str) -> Optional[str]:
        """None if the note is fresh enough to act on; a stated reason otherwise.

        Fail-closed on an UNPARSEABLE date too: a note we cannot age is a note we
        cannot trust, and 'assume it's fresh' is how a stalled feed keeps trading."""
        if self.max_note_age_days <= 0:                       # bound disabled explicitly
            return None
        import datetime as dt
        try:
            age = (dt.date.fromisoformat(self.trade_date[:10])
                   - dt.date.fromisoformat(str(as_of)[:10])).days
        except Exception:
            return f"unparseable_note_date:{as_of!r} (cannot age the note → HOLD)"
        if age > self.max_note_age_days:
            return (f"stale_note:as_of={as_of} is {age}d old "
                    f"(> {self.max_note_age_days}d) — the note feed has STALLED")
        return None

    def _targets(self, note: dict) -> Dict[str, float]:
        """{symbol: target_weight} from the shadow actions, allowlist-filtered."""
        out: Dict[str, float] = {}
        for a in note.get("hypothetical_actions", []):
            if a.get("account") != "shadow":                 # schema guarantees this, belt+braces
                continue
            sym = str(a.get("symbol", "")).upper()
            if self.allowlist is not None and sym not in self.allowlist:
                continue
            if sym:
                out[sym] = float(a.get("target_weight", 0.0))
        return out

    def _firewall(self, targets: Dict[str, float], held_w: Dict[str, float]) -> Optional[str]:
        for s, w in targets.items():
            if abs(w) > self.max_weight + 1e-9:
                return f"name {s} weight {w:.3f} exceeds ±{self.max_weight}"
        gross = sum(abs(w) for w in targets.values())
        if gross > self.max_gross + 1e-9:
            return f"gross {gross:.2f} exceeds {self.max_gross}"
        turn = sum(abs(targets.get(s, 0.0) - held_w.get(s, 0.0))
                   for s in set(targets) | set(held_w))
        if turn > self.max_turnover + 1e-9:
            return f"turnover {turn:.2f} exceeds {self.max_turnover}"
        return None

    # ---- the fleet constructor interface ----
    def construct(self, equity: float, current_positions: Dict[str, int],
                  closes: Dict[str, pd.Series]) -> LLMAnalystPlan:
        """Load yesterday's validated note → firewall-checked target weights → whole-share
        order deltas, sized off ``equity * sub_budget``. FAIL-CLOSED: any problem HOLDS the
        book (empty orders) and states why in ``reject_reason``; never a blind order."""
        plan = LLMAnalystPlan()
        note, reason = self._load_yesterday_note()
        if note is None:                                     # dormant-but-armed — a real no-trade day
            plan.degraded = True
            plan.reject_reason = f"no_note:{reason}"
            return plan
        plan.note_as_of = note.get("as_of")
        plan.note_prompt_version = (note.get("provenance") or {}).get("prompt_version")

        budget = float(equity) * self.sub_budget
        # held weights (against the SUB-BUDGET, the stream's own NAV slice)
        def _last_px(t: str) -> Optional[float]:
            c = closes.get(t)
            if c is None:
                return None
            c = c.dropna() if hasattr(c, "dropna") else c
            if len(c) == 0:
                return None
            px = float(c.iloc[-1])
            return px if px > 0 else None

        targets = self._targets(note)
        # T-329c: an EMPTY action list is a NAMED outcome, never a silent zero.
        # This is the defect that held ignition: with daily/v2 the analyst emitted
        # no actions for 15 straight days, and the plan came back
        # `orders=[], degraded=False, reject_reason=None` — indistinguishable from
        # "the analyst looked and chose to hold". Under daily/v3 an empty list is a
        # deliberate hold-the-book decision AND the model must say why, so record
        # which of the two it was. NOT degraded — a genuine no-view day is healthy
        # — but never again unstated.
        if not targets:
            plan.no_view = True
            plan.no_view_reason = (note.get("no_action_reason")
                                   or "UNSTATED (model emitted no actions and no reason)")
        # every name we'd TRADE (a target, or a held name we might sell) must be priceable
        need = set(targets) | {t for t, q in (current_positions or {}).items() if int(q or 0) != 0}
        px = {t: _last_px(t) for t in need}
        missing = sorted(t for t in need if px[t] is None)
        if missing:                                          # can't trade what we can't price → HOLD
            plan.degraded = True
            plan.reject_reason = f"missing_price:{missing}"
            return plan

        held_w = {t: (int(current_positions.get(t, 0)) * px[t] / budget if budget > 0 else 0.0)
                  for t in need}
        fw = self._firewall(targets, held_w)
        if fw is not None:                                   # REJECT loudly; hold the book
            plan.reject_reason = f"REJECTED:{fw}"
            plan.targets = {s: round(w, 4) for s, w in targets.items()}
            return plan

        for t in sorted(need):
            target_w = float(targets.get(t, 0.0))
            # T-329d3: whole-share rounding TRUNCATES TOWARD ZERO on both sides.
            # int() does that; math.floor does NOT for negatives — floor(-5.1) is
            # -6, so a -5% target on a $10k budget became a $588 (5.9%) short: the
            # realized weight EXCEEDED the requested one, the exact thing the
            # conservative long-side rounding exists to prevent. |realized| must
            # never exceed |requested| for any sign.
            target_qty = int(budget * target_w / px[t]) if target_w != 0 else 0
            held = int(current_positions.get(t, 0))
            plan.targets[t] = round(target_w, 4)
            plan.signals[t] = round(target_w, 4)
            plan.target_qty[t] = target_qty
            plan.held_qty[t] = held
            delta = target_qty - held
            if delta == 0:
                continue
            plan.orders.append(OrderSpec(
                ticker=t, side=("buy" if delta > 0 else "sell"), qty=abs(delta),
                tif=self.tif, engine_side=("long" if delta > 0 else "exit"), edge=EDGE))
        return plan
