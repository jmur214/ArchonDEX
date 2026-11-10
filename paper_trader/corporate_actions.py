# paper_trader/corporate_actions.py
"""The corporate-action (split) feed and the gate that consumes it.

WHY THIS EXISTS (2026-11-05, account 2): MTUM split 4-for-1. The price series
the loop fetches is split-ADJUSTED by the vendor (``Adjustment.ALL``), so the
moment the vendor knew about the split every close read ~1/4 of the day
before — while the ledger AND the paper broker still showed the PRE-split share
count. Price basis and quantity basis disagreed; the constructor read a 75%
weight collapse and bought 18 shares. ``ReconcileInputs.corporate_action_tickers``
had existed since T-163 and nothing in production ever fed it.

Three independent pieces live here:

  1. THE FEED — ``fetch_splits`` returns a ``SplitFeedResult`` that is either
     AVAILABLE (possibly with zero events: the provider was asked and answered)
     or UNAVAILABLE with a reason. An empty list never stands in for "could not
     ask". The fetch is injected (``FetchFn``); nothing here opens a socket.
  2. THE PRICE-BASIS GUARD — ``price_split_ratio``: a mark that moved by a
     near-clean split ratio between two runs. It needs no feed, which is the
     point: it is the witness that still works when the feed is dead.
  3. THE GATE — ``CorporateActionGate`` applies confirmed splits to the ledger
     (exactly once, journaled), compares ledger vs broker share basis, runs the
     price guard, and decides whether the day's orders may be staged.

THE DECISION (item 4 of the build brief), stated once:
  A ticker is FROZEN when its share basis or price basis cannot be proven
  consistent. ANY frozen ticker stands the WHOLE book down for the day: the plan
  is still constructed (so the record shows what was prevented) but NOTHING is
  staged, and the run is NON-CANONICAL with the reason named. The book is not
  traded "around" a frozen name because (a) a budget-constrained book's weights
  are interdependent — the cash leg absorbs whatever the frozen name's value is
  believed to be — and (b) the ledger converges to broker truth all-or-nothing
  (strict equality with the journal), so fills in the other names could not be
  adopted while one position sits in a different share basis, and the run would
  manufacture a cash-drift HALT of its own.
  When the split is CONFIRMED and only the broker lags, the plan is constructed
  on the split-adjusted quantity, so the recorded plan is the honest one.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import (Any, Callable, Dict, Iterable, List, Mapping, Optional,
                    Sequence, Tuple)

# provider keys → meaning. Splits change the share count by a ratio. Cash-only
# actions change nothing we hold in shares. EVERYTHING ELSE (stock dividends,
# spin-offs, mergers, name changes, unit splits, redemptions, …) changes share
# count or symbol in a way this module does not model: it is surfaced as
# UNHANDLED and freezes the ticker — never silently dropped.
SPLIT_KEYS: Tuple[str, ...] = ("forward_splits", "reverse_splits")
CASH_ONLY_KEYS: Tuple[str, ...] = ("cash_dividends", "rights_distributions")

# How far back the gate keeps asking about a split after its ex-date, so a
# broker that applies it late is still classified by the feed (calendar days).
SETTLE_LOOKBACK_DAYS = 7
# |observed/clean − 1| tolerance for the PRICE guard. A split-day price is the
# clean ratio times an ordinary daily move, so this must be wider than a normal
# day and far narrower than the gap between ratios: 0.12 flags a 4-for-1 across
# a ±12% session and leaves an ordinary −8% day (ratio 1.087) untouched.
PRICE_RATIO_TOL = 0.12
_CLEAN_RATIOS: Tuple[float, ...] = tuple(
    [1.5] + [float(n) for n in range(2, 21)])
_QTY_TOL = 1e-9

# fetch(symbols, start_inclusive, end_inclusive) -> the provider's raw mapping
FetchFn = Callable[[List[str], _dt.date, _dt.date], Mapping[str, Any]]


# --------------------------------------------------------------------------- #
# types
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SplitEvent:
    """One split. ``ratio`` = NEW shares per OLD share (4.0 for a 4-for-1,
    0.1 for a 1-for-10 reverse split)."""
    ticker: str
    ex_date: _dt.date
    ratio: float

    def __post_init__(self) -> None:
        if not self.ticker or self.ticker != self.ticker.upper():
            raise ValueError(f"SplitEvent ticker must be upper-case: {self.ticker!r}")
        if not isinstance(self.ex_date, _dt.date):
            raise ValueError("SplitEvent ex_date must be a date")
        r = float(self.ratio)
        if not math.isfinite(r) or r <= 0 or abs(r - 1.0) < 1e-12:
            raise ValueError(f"SplitEvent ratio must be finite, >0 and !=1: {self.ratio!r}")

    @property
    def key(self) -> str:
        """Idempotence key: one split per ticker per ex-date."""
        return f"{self.ticker}:{self.ex_date.isoformat()}"

    def to_dict(self) -> Dict[str, Any]:
        return {"ticker": self.ticker, "ex_date": self.ex_date.isoformat(),
                "ratio": self.ratio}


@dataclass(frozen=True)
class UnhandledAction:
    """A share-count/symbol-changing action this module does not model."""
    ticker: str
    kind: str
    date: Optional[_dt.date]

    def to_dict(self) -> Dict[str, Any]:
        return {"ticker": self.ticker, "kind": self.kind,
                "date": self.date.isoformat() if self.date else None}


@dataclass(frozen=True)
class SplitFeedResult:
    """FEED OK (``available=True``, events possibly empty) or FEED UNAVAILABLE
    (``available=False`` + a reason). The two are different facts and the type
    refuses to blur them: an unavailable result cannot carry events, and it
    cannot be built without saying why."""
    available: bool
    events: Tuple[SplitEvent, ...] = ()
    unhandled: Tuple[UnhandledAction, ...] = ()
    reason: str = ""
    tickers: Tuple[str, ...] = ()
    start: Optional[_dt.date] = None      # inclusive
    end: Optional[_dt.date] = None        # inclusive

    def __post_init__(self) -> None:
        if not self.available:
            if self.events or self.unhandled:
                raise ValueError("an UNAVAILABLE feed result cannot carry events")
            if not self.reason:
                raise ValueError("an UNAVAILABLE feed result must state its reason")

    @classmethod
    def ok(cls, events: Sequence[SplitEvent] = (),
           unhandled: Sequence[UnhandledAction] = (), *,
           tickers: Sequence[str] = (), start: Optional[_dt.date] = None,
           end: Optional[_dt.date] = None, reason: str = "") -> "SplitFeedResult":
        return cls(True, tuple(sorted(events, key=lambda e: (e.ex_date, e.ticker))),
                   tuple(unhandled), reason, tuple(tickers), start, end)

    @classmethod
    def unavailable(cls, reason: str, *, tickers: Sequence[str] = (),
                    start: Optional[_dt.date] = None,
                    end: Optional[_dt.date] = None) -> "SplitFeedResult":
        return cls(False, (), (), reason, tuple(tickers), start, end)

    def confirmed(self, ticker: str) -> List[SplitEvent]:
        return [e for e in self.events if e.ticker == ticker.upper()]

    def to_dict(self) -> Dict[str, Any]:
        return {"available": self.available, "reason": self.reason or None,
                "tickers": list(self.tickers),
                "start": self.start.isoformat() if self.start else None,
                "end": self.end.isoformat() if self.end else None,
                "events": [e.to_dict() for e in self.events],
                "unhandled": [u.to_dict() for u in self.unhandled]}


# --------------------------------------------------------------------------- #
# the feed
# --------------------------------------------------------------------------- #
def _as_date(v: Any) -> _dt.date:
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    return _dt.date.fromisoformat(str(v)[:10])


def parse_alpaca_corporate_actions(
        raw: Mapping[str, Any]) -> Tuple[List[SplitEvent], List[UnhandledAction]]:
    """Alpaca ``/v1/corporate-actions`` payload → (splits, unhandled).

    Accepts the body either bare (``{"forward_splits": [...]}`` — what the SDK's
    raw mode hands back) or wrapped (``{"corporate_actions": {...}}`` — the HTTP
    body). RAISES ``ValueError`` on anything it cannot read: a malformed row is
    "the feed could not be read", never "there was no split"."""
    if not isinstance(raw, Mapping):
        raise ValueError(f"corporate-actions payload is {type(raw).__name__}, not a mapping")
    body = raw.get("corporate_actions", raw)
    if body is None:
        body = {}
    if not isinstance(body, Mapping):
        raise ValueError("corporate_actions body is not a mapping")
    events: List[SplitEvent] = []
    unhandled: List[UnhandledAction] = []
    for kind, rows in body.items():
        if kind in ("next_page_token",) or kind in CASH_ONLY_KEYS:
            continue
        if rows is None:
            continue
        if not isinstance(rows, list):
            raise ValueError(f"corporate-actions '{kind}' is not a list")
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError(f"corporate-actions '{kind}' row is not a mapping")
            if kind in SPLIT_KEYS:
                try:
                    new, old = float(row["new_rate"]), float(row["old_rate"])
                    if old <= 0 or new <= 0:
                        raise ValueError("non-positive rate")
                    events.append(SplitEvent(str(row["symbol"]).upper(),
                                             _as_date(row["ex_date"]), new / old))
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"unreadable {kind} row ({type(exc).__name__}: {exc})") from exc
            else:
                syms = sorted({str(v).upper() for k, v in row.items()
                               if k.endswith("symbol") and isinstance(v, str) and v})
                d_raw = (row.get("ex_date") or row.get("effective_date")
                         or row.get("process_date"))
                try:
                    d = _as_date(d_raw) if d_raw else None
                except ValueError:
                    d = None
                for s in syms:
                    unhandled.append(UnhandledAction(s, str(kind), d))
    return events, unhandled


def fetch_splits(fetch_fn: Optional[FetchFn], tickers: Iterable[str],
                 since: _dt.date, today: _dt.date) -> SplitFeedResult:
    """Ask the feed for splits on ``tickers`` with ex-date in ``(since, today]``.

    NEVER raises and NEVER returns a bare list. No fetcher, a raising fetcher,
    or an unreadable payload → UNAVAILABLE with the reason. Nothing to ask about
    (no tickers, or an empty window) → OK-and-empty WITH that stated, because in
    that case there genuinely is nothing the provider could have said."""
    syms = sorted({str(t).upper() for t in tickers if t})
    start = since + _dt.timedelta(days=1)
    if not syms:
        return SplitFeedResult.ok(tickers=syms, start=start, end=today,
                                  reason="no tickers to ask about")
    if start > today:
        return SplitFeedResult.ok(tickers=syms, start=start, end=today,
                                  reason="empty window")
    if fetch_fn is None:
        return SplitFeedResult.unavailable(
            "no corporate-actions fetcher configured", tickers=syms,
            start=start, end=today)
    try:
        raw = fetch_fn(list(syms), start, today)
    except Exception as exc:  # noqa: BLE001 — every failure is "could not ask"
        return SplitFeedResult.unavailable(
            f"fetch raised {type(exc).__name__}", tickers=syms, start=start, end=today)
    try:
        events, unhandled = parse_alpaca_corporate_actions(raw)
    except ValueError as exc:
        return SplitFeedResult.unavailable(
            f"unparseable response: {exc}", tickers=syms, start=start, end=today)
    want = set(syms)
    events = [e for e in events if e.ticker in want and start <= e.ex_date <= today]
    unhandled = [u for u in unhandled if u.ticker in want]
    return SplitFeedResult.ok(events, unhandled, tickers=syms, start=start, end=today)


# --------------------------------------------------------------------------- #
# the price-basis guard (needs no feed)
# --------------------------------------------------------------------------- #
def price_split_ratio(prev_px: Optional[float], px: Optional[float],
                      tol: float = PRICE_RATIO_TOL) -> Optional[float]:
    """If ``prev_px → px`` looks like a split, return the implied ratio (NEW
    shares per OLD: 4.0 when the price fell to a quarter, 0.1 when it rose
    tenfold); else None. The price analogue of reconciliation's
    ``_looks_like_corporate_action`` — but with a tolerance, because a split-day
    price is the clean ratio TIMES that day's ordinary move."""
    try:
        a, b = float(prev_px), float(px)   # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(a) and math.isfinite(b)) or a <= 0 or b <= 0:
        return None
    r = a / b
    # the NEAREST clean ratio (in relative terms), then the tolerance — not the
    # first one inside it: 10× sits within 12% of both 1/9 and 1/10.
    cands = [c for c in _CLEAN_RATIOS] + [1.0 / c for c in _CLEAN_RATIOS]
    best = min(cands, key=lambda c: abs(r / c - 1.0))
    return best if abs(r / best - 1.0) <= tol else None


def split_qty(qty: float, ratio: float) -> Optional[int]:
    """``qty × ratio`` as a whole number of shares, or None when the split
    leaves a fraction (cash-in-lieu — not something to round away)."""
    v = float(qty) * float(ratio)
    return int(round(v)) if abs(v - round(v)) < 1e-6 else None


def _fill_date(order: Any) -> Optional[_dt.date]:
    for attr in ("filled_at", "trade_date"):
        v = getattr(order, attr, None)
        if v:
            try:
                return _as_date(v)
            except ValueError:
                continue
    return None


def split_adjusted_journal_net(orders: Iterable[Any],
                               splits: Iterable[SplitEvent]) -> Dict[str, int]:
    """Net signed quantity per ticker implied by OBSERVED fills, with every fill
    dated BEFORE a split's ex-date scaled by that split. A fill on or after the
    ex-date is already in the new share basis. RAISES ``ValueError`` if a
    pre-split fill does not scale to whole shares — the caller must not adopt
    on a rounded guess."""
    by_ticker: Dict[str, List[SplitEvent]] = {}
    for ev in splits:
        by_ticker.setdefault(ev.ticker, []).append(ev)
    net: Dict[str, float] = {}
    for o in orders:
        fq = int(getattr(o, "filled_qty", 0) or 0)
        if fq <= 0:
            continue
        t = str(o.ticker).upper()
        signed = float(fq if str(o.side).lower() in ("buy", "long", "cover") else -fq)
        fd = _fill_date(o)
        for ev in by_ticker.get(t, ()):
            if fd is None:
                raise ValueError(f"{t} fill has no date; cannot place it against "
                                 f"the {ev.ex_date} split")
            if fd < ev.ex_date:
                signed *= ev.ratio
        net[t] = net.get(t, 0.0) + signed
    out: Dict[str, int] = {}
    for t, q in net.items():
        if abs(q - round(q)) > 1e-6:
            raise ValueError(f"{t} split-adjusted journal net {q} is not whole shares")
        if int(round(q)) != 0:
            out[t] = int(round(q))
    return out


# --------------------------------------------------------------------------- #
# the gate
# --------------------------------------------------------------------------- #
MARKS_REL = "data/state/price_basis_marks.json"
MARKS_SCHEMA = "price_basis_marks/v1"


@dataclass
class CorporateActionGate:
    """One run's corporate-action verdict. Build it, then call, in order:
    ``apply_to_ledger`` → ``assess_broker`` → (construct the plan on
    ``positions_for_sizing``) → ``check_prices`` → ``screen``. ``to_block`` is the
    record that rides the heartbeat."""
    today: _dt.date
    feed: SplitFeedResult
    marks_path: Optional[Path] = None
    frozen: Dict[str, str] = field(default_factory=dict)          # ticker → reason
    applied: List[str] = field(default_factory=list)              # journaled THIS run
    in_play: Dict[str, SplitEvent] = field(default_factory=dict)  # journaled, in window
    unjournaled: Dict[str, SplitEvent] = field(default_factory=dict)
    reconcile_tickers: set = field(default_factory=set)
    sizing_overrides: Dict[str, int] = field(default_factory=dict)
    refused_orders: List[Dict[str, Any]] = field(default_factory=list)
    price_checked: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    def _freeze(self, ticker: str, reason: str) -> None:
        prev = self.frozen.get(ticker)
        self.frozen[ticker] = f"{prev} | {reason}" if prev else reason

    @property
    def stand_down(self) -> bool:
        """True ⇒ nothing may be staged today and the run is non-canonical."""
        return bool(self.frozen)

    # ---- 1. ledger: apply confirmed splits, exactly once ---------------- #
    def apply_to_ledger(self, ledger: Any, orders: Sequence[Any]) -> None:
        """Apply each confirmed split to the ledger as an explicit journaled
        event. A split is applied ONLY when the held position is provably in the
        PRE-split basis: every observed fill in that ticker predates the
        ex-date. A position built entirely on/after the ex-date needs nothing. A
        MIXED position (fills on both sides — the 2026-11-05 account-2 state) is
        never auto-scaled: it is frozen for manual review."""
        done = set(ledger.applied_split_keys())
        for ev in self.feed.events:
            held = int(ledger.positions().get(ev.ticker, 0))
            if ev.key in done:
                self.in_play[ev.ticker] = ev
                continue
            if held == 0:
                continue
            dates = [_fill_date(o) for o in orders
                     if str(o.ticker).upper() == ev.ticker
                     and int(getattr(o, "filled_qty", 0) or 0) > 0]
            if not dates or any(d is None for d in dates):
                self._freeze(ev.ticker,
                             f"{ev.ticker} split {ev.ratio:g}:1 ex {ev.ex_date} on the feed "
                             f"but the journal cannot date the held {held} shares — "
                             "share basis unknown; manual review")
                self.unjournaled[ev.ticker] = ev
                continue
            pre = [d for d in dates if d < ev.ex_date]
            if not pre:
                continue                      # bought post-split: already new basis
            if len(pre) != len(dates):
                self._freeze(ev.ticker,
                             f"{ev.ticker} split {ev.ratio:g}:1 ex {ev.ex_date} was never "
                             f"applied to the ledger and the held {held} shares mix "
                             "pre- and post-split fills — NOT auto-scaled; manual review")
                self.unjournaled[ev.ticker] = ev
                continue
            try:
                ledger.apply_split(ev.ticker, ev.ratio, ev.ex_date)
            except ValueError as exc:
                self._freeze(ev.ticker, f"{ev.ticker} split {ev.ratio:g}:1 ex {ev.ex_date} "
                                        f"could not be applied ({exc}); manual review")
                self.unjournaled[ev.ticker] = ev
                continue
            self.applied.append(ev.key)
            self.in_play[ev.ticker] = ev
        for u in self.feed.unhandled:
            if int(ledger.positions().get(u.ticker, 0)) != 0:
                self._freeze(u.ticker, f"{u.ticker} has an unmodelled corporate action "
                                       f"on the feed ({u.kind}, {u.date}); manual review")

    def ledger_splits(self, ledger: Any) -> List[SplitEvent]:
        """Every split the ledger has journaled (all time) — what the
        journal-net explanation must scale pre-split fills by."""
        return list(ledger.applied_splits())

    # ---- 2. broker: is the broker in the same share basis? -------------- #
    def assess_broker(self, ledger_positions: Mapping[str, int],
                      broker_positions: Mapping[str, int]) -> None:
        for t, ev in self.in_play.items():
            lq, bq = int(ledger_positions.get(t, 0)), int(broker_positions.get(t, 0))
            if lq == bq:
                continue                                   # settled
            if abs(lq / ev.ratio - bq) < _QTY_TOL:
                self._freeze(t, f"{t} split {ev.ratio:g}:1 ex {ev.ex_date} CONFIRMED by the "
                                f"feed; ledger {lq} is post-split, broker still shows {bq} "
                                "(pre-split) — broker has not applied it yet")
                self.reconcile_tickers.add(t)
                self.sizing_overrides[t] = lq
            else:
                self._freeze(t, f"{t} ledger {lq} vs broker {bq} matches NEITHER side of the "
                                f"confirmed {ev.ratio:g}:1 split — position drift stands")
        for t, ev in self.unjournaled.items():
            lq, bq = int(ledger_positions.get(t, 0)), int(broker_positions.get(t, 0))
            if lq != bq and split_qty(lq, ev.ratio) == bq:
                self.reconcile_tickers.add(t)              # a morph matching the split

    def positions_for_sizing(self, broker_positions: Mapping[str, int]) -> Dict[str, int]:
        """Broker positions with a LAGGING confirmed split shown in the
        post-split basis the price series is already in."""
        out = {t: int(q) for t, q in broker_positions.items()}
        out.update(self.sizing_overrides)
        return out

    def explained_modulo_lag(self, broker_positions: Mapping[str, int],
                             journal_net: Mapping[str, int]) -> bool:
        """Is the broker state explained once a confirmed-but-lagging split is
        read in its post-split basis? (The ledger is NOT adopted on this.)"""
        b = {t: q for t, q in self.positions_for_sizing(broker_positions).items() if q}
        return b == {t: int(q) for t, q in journal_net.items() if int(q)}

    # ---- 3. prices: did a mark move by a split ratio? ------------------- #
    def _load_marks(self) -> Dict[str, Dict[str, Any]]:
        if self.marks_path is None or not self.marks_path.exists():
            return {}
        try:
            d = json.loads(self.marks_path.read_text())
            m = d.get("marks")
            return dict(m) if isinstance(m, dict) else {}
        except (OSError, ValueError):
            return {}                    # unreadable == no reference (handled as blind)

    def check_prices(self, closes: Mapping[str, float], held: Iterable[str],
                     traded: Iterable[str] = ()) -> None:
        """Compare today's mark with the mark the PREVIOUS run recorded, for
        every held or to-be-traded ticker. A near-clean split ratio that the
        feed does not explain FREEZES the ticker. A HELD ticker with no prior
        mark while the feed is unavailable is BLIND — no witness at all — and is
        frozen too. Marks of tickers that pass are advanced; a frozen ticker's
        mark is left where it was, so it stays frozen until explained."""
        marks = self._load_marks()
        held_set = {str(t).upper() for t in held}
        check = held_set | {str(t).upper() for t in traded}
        for t in sorted(closes):
            px = closes.get(t)
            try:
                px_f = float(px)                 # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
            if not math.isfinite(px_f) or px_f <= 0:
                continue
            m = marks.get(t)
            ok = True
            if t in check:
                self.price_checked.append(t)
                if m is None:
                    if t in held_set and not self.feed.available:
                        ok = False
                        self._freeze(t, f"{t} share/price basis UNVERIFIABLE: no prior price "
                                        f"mark and the feed is UNAVAILABLE ({self.feed.reason})")
                else:
                    prev = float(m["px"])
                    seen = _as_date(m["run_date"])
                    confirmed = [e for e in self.feed.confirmed(t) if e.ex_date > seen]
                    for ev in confirmed:
                        prev /= ev.ratio
                    r = price_split_ratio(prev, px_f)
                    if r is not None:
                        ok = False
                        why = ("price is NOT in the confirmed split's basis"
                               if confirmed else
                               ("feed UNAVAILABLE: " + self.feed.reason
                                if not self.feed.available else
                                "feed answered and reports NO split"))
                        self._freeze(t, f"{t} mark moved {float(m['px']):.4f} ({m['run_date']}) "
                                        f"→ {px_f:.4f}: a ~{r:g}:1 split-shaped move, "
                                        f"UNCONFIRMED ({why})")
            if ok:
                marks[t] = {"px": px_f, "run_date": self.today.isoformat()}
        if self.marks_path is not None:
            self.marks_path.parent.mkdir(parents=True, exist_ok=True)
            self.marks_path.write_text(json.dumps(
                {"_schema": MARKS_SCHEMA, "marks": marks}, indent=1, sort_keys=True))

    # ---- 4. orders -------------------------------------------------------- #
    def screen(self, orders: Sequence[Any]) -> List[Any]:
        """The orders that may be staged. A stand-down refuses ALL of them and
        records each one (what the gate prevented is the evidence it worked)."""
        if not self.stand_down:
            return list(orders)
        for o in orders:
            self.refused_orders.append({
                "ticker": getattr(o, "ticker", None), "side": getattr(o, "side", None),
                "qty": getattr(o, "qty", None),
                "frozen_ticker": getattr(o, "ticker", None) in self.frozen})
        return []

    def to_block(self) -> Dict[str, Any]:
        return {"_schema": "paper_corporate_actions/v1",
                "feed": self.feed.to_dict(),
                "applied_this_run": list(self.applied),
                "frozen": dict(self.frozen),
                "stand_down": self.stand_down,
                "reconcile_tickers": sorted(self.reconcile_tickers),
                "refused_orders": list(self.refused_orders),
                "price_checked": sorted(set(self.price_checked)),
                "degraded": bool(self.frozen) or not self.feed.available}


def gate_query_window(last_ledger_date: Optional[_dt.date],
                      today: _dt.date) -> _dt.date:
    """The exclusive lower bound of the feed query: the last dated ledger event
    or ``SETTLE_LOOKBACK_DAYS`` ago, whichever is EARLIER — so a late-applying
    broker is still classified, and a long gap between runs is still covered."""
    floor = today - _dt.timedelta(days=SETTLE_LOOKBACK_DAYS)
    return min(last_ledger_date, floor) if last_ledger_date else floor
