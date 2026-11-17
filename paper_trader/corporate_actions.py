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

RESIDUAL RISK, stated and not designed away: the price guard compares today's
mark with the PREVIOUS run's. On a seeding day there is no previous mark, and
on the run after it the only reference is the mark laid the day before — in
whatever basis the price happened to be in. If a split landed unreported by
the feed just before the seed, nothing here can see it. Those two sessions are
flagged in the heartbeat block (`marks_age_sessions` 0 then 1) as weakly
witnessed; they are not protected.
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
# a ±12% session. The SMALL ratios (5-for-4, 3-for-2) sit close to 1, where a
# 12% band would swallow ordinary bad days (1.25 ± 12% reaches a −9% session),
# so below 2:1 the band is 6%. `price_ratio_bands()` prints the resulting table.
PRICE_RATIO_TOL = 0.12
PRICE_RATIO_TOL_SMALL = 0.06
_CLEAN_RATIOS: Tuple[float, ...] = tuple(
    [1.25, 1.5, 2.5] + [float(n) for n in range(2, 21)] + [25.0, 30.0, 40.0, 50.0])
# A mark older than this many trading days is not a witness (treated as no mark).
MARK_MAX_AGE_TRADING_DAYS = 10
# Feed AVAILABLE and silent on this many consecutive sessions releases an
# UNCONFIRMED price freeze as a real move. Never with the feed unavailable.
NO_SPLIT_RELEASE_SESSIONS = 3
# This many consecutive runs with the feed UNAVAILABLE make the run non-canonical.
FEED_DEAD_ALARM_RUNS = 3
# The feed query never reaches further back than this (stated in the block).
WINDOW_CAP_DAYS = 60
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
    if raw.get("next_page_token"):
        # a PARTIAL page: the split may be on the page we were not given
        raise ValueError("response is paginated (next_page_token set); a partial "
                         "page is not an answer")
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
    # one event per (ticker, ex_date, ratio): a provider that repeats a row has
    # not announced two splits. Nothing dated after `today` is an event yet.
    events = list(dict.fromkeys(
        e for e in events if e.ticker in want and start <= e.ex_date <= today))
    unhandled = list(dict.fromkeys(u for u in unhandled if u.ticker in want))
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
    return best if abs(r / best - 1.0) <= _tol_for(best, tol) else None


def _tol_for(ratio: float, tol: float = PRICE_RATIO_TOL) -> float:
    """The band for one clean ratio: ``tol`` from 2:1 up, the narrow band below."""
    return tol if max(ratio, 1.0 / ratio) >= 2.0 else min(tol, PRICE_RATIO_TOL_SMALL)


def price_ratio_bands() -> List[Dict[str, Any]]:
    """The false-positive table: for each clean ratio, the one-session price
    move (as a return) that the guard reads as that split. Merged where bands
    touch. A reviewer reads THIS, not the constants."""
    spans = []
    for c in list(_CLEAN_RATIOS) + [1.0 / c for c in _CLEAN_RATIOS]:
        t = _tol_for(c)
        # prev/px = r in [c(1−t), c(1+t)]  →  return = 1/r − 1
        spans.append((1.0 / (c * (1 + t)) - 1.0, 1.0 / (c * (1 - t)) - 1.0, c))
    spans.sort()
    out: List[Dict[str, Any]] = []
    for lo, hi, c in spans:
        if out and lo <= out[-1]["ret_hi"] + 1e-12:
            out[-1]["ret_hi"] = max(out[-1]["ret_hi"], hi)
            out[-1]["ratios"].append(round(c, 4))
        else:
            out.append({"ret_lo": lo, "ret_hi": hi, "ratios": [round(c, 4)]})
    return out


def near_basis(expected_px: Optional[float], px: Optional[float]) -> bool:
    """Is ``px`` NEAR ``expected_px`` — closer than the lower edge of the first
    ratio band (the smallest move the guard would read as a split)? This, and
    not "the price is not split-shaped", is what releases a ``basis_lag``
    freeze: "not split-shaped" is also true in every GAP between the bands, so
    an unadjusted 276.56 drifting to 240.00 read as "arrived" (expected 69.14)
    and the freeze released on drift."""
    try:
        a, b = float(expected_px), float(px)      # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(a) and math.isfinite(b)) or a <= 0 or b <= 0:
        return False
    first = min(_CLEAN_RATIOS)
    return max(a / b, b / a) < first * (1.0 - _tol_for(first))


def confirmed_ratio_explains(confirmed_ratio: float, ref_px: Optional[float],
                             px: Optional[float]) -> bool:
    """Does a feed-confirmed split of ``confirmed_ratio`` explain the observed
    move ``ref_px → px``? Only if the OBSERVED ratio sits inside that ratio's
    own band. (Dividing the reference by the confirmed ratio and asking "is
    what remains split-shaped?" let a 3:1 confirmation explain a 4:1 move —
    4/3 falls in a gap between bands.)"""
    try:
        a, b, c = float(ref_px), float(px), float(confirmed_ratio)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if not all(math.isfinite(v) and v > 0 for v in (a, b, c)):
        return False
    return abs((a / b) / c - 1.0) <= _tol_for(c)


def releases_on_feed_silence(ratio: Optional[float]) -> bool:
    """May an UNCONFIRMED freeze of this matched ratio release when the feed
    answers "no split" three sessions running? Only below 2:1 (1.25, 1.5 and
    their reciprocals), where a real one-session move is plausible. An unknown
    ratio is treated as 2:1 or more — it does not release."""
    try:
        r = float(ratio)                 # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return math.isfinite(r) and r > 0 and max(r, 1.0 / r) < 2.0


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
# the gate's durable state: marks, FREEZES, the feed-outage count, a journal
# --------------------------------------------------------------------------- #
MARKS_REL = "data/state/price_basis_marks.json"
MARKS_SCHEMA = "price_basis_marks/v2"

# Freeze kinds and the ONLY ways each one releases. None of them releases
# because the price drifted out of a band — that was the 2026-11-10 blocker.
KIND_UNCONFIRMED = "unconfirmed"   # split-shaped move, no feed confirmation
#   → a feed-confirmed split whose ratio MATCHES the observed move, or an ack.
#     ONLY when the move matched a ratio class BELOW 2:1 (1.25, 1.5 and their
#     reciprocals — where a real one-session move is plausible) may it also release
#     on the feed answering "no split" on NO_SPLIT_RELEASE_SESSIONS consecutive
#     sessions. A move of 2:1 or more NEVER releases on feed silence: a feed that
#     simply never reports a real split would otherwise reopen the 2026-11-05 buy.
KIND_BASIS_LAG = "basis_lag"       # split confirmed + journaled, price not adjusted yet
#   → the price arriving in the confirmed basis, or an ack
KIND_BLIND = "blind"               # held, no mark, feed unavailable
#   → the feed answering (then: seed, or blind_split if it reports a split)
KIND_BLIND_SPLIT = "blind_split"   # held, no mark, a confirmed split in the window → ack only
KIND_LEDGER = "ledger"             # share basis not provable from the journal → ack only
KIND_ACTION = "action"             # an unmodelled corporate action → ack only


def _prev_business_day(d: _dt.date) -> _dt.date:
    d -= _dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= _dt.timedelta(days=1)
    return d


def _business_days_between(a: _dt.date, b: _dt.date) -> int:
    """Weekdays in (a, b]. The gate has no exchange calendar; weekdays over-count
    a holiday week by a day, which errs toward calling a mark stale."""
    n, d = 0, a
    while d < b:
        d += _dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def _valid_mark(entry: Any) -> Optional[Tuple[float, _dt.date]]:
    try:
        px = float(entry["px"])
        day = _as_date(entry["run_date"])
    except (KeyError, TypeError, ValueError):
        return None
    return (px, day) if math.isfinite(px) and px > 0 else None


@dataclass
class GateState:
    """The marks file, validated entry by entry. An invalid MARK is "no mark"
    and is named in ``problems``; an invalid FREEZE entry stays a freeze (a
    freeze must never be lost to a parse error)."""
    marks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    frozen: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    feed_unavailable_streak: int = 0
    feed_streak_date: Optional[str] = None
    journal: List[Dict[str, Any]] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)
    # the file EXISTS but cannot be parsed as a whole: whatever freezes it held are
    # unknowable, so nothing may be inferred from it and nothing written over it
    unreadable: bool = False
    # sessions since marks were last SEEDED (0 on the seeding day, 1 the run after,
    # None from then on) and the run date that count was last stepped on
    seed_sessions: Optional[int] = None
    seed_step_date: Optional[str] = None
    # which account this file belongs to (written on the first save); the ack
    # tool refuses to stamp a file for a different, or an unnamed, account
    account: Optional[str] = None

    @classmethod
    def load(cls, path: Optional[Path]) -> "GateState":
        st = cls()
        if path is None or not Path(path).exists():
            return st
        try:
            d = json.loads(Path(path).read_text())
            if not isinstance(d, dict):
                raise ValueError(f"top level is {type(d).__name__}, not an object")
        except (OSError, ValueError) as exc:
            st.problems.append(f"marks file unreadable ({type(exc).__name__}: {exc})")
            st.unreadable = True
            return st
        marks = d.get("marks")
        if marks is not None and not isinstance(marks, dict):
            st.problems.append("marks is not an object — treated as empty")
            marks = {}
        for t, e in (marks or {}).items():
            v = _valid_mark(e)
            if v is None:
                st.problems.append(f"invalid mark for {t} ({e!r}) — treated as NO mark")
            else:
                st.marks[str(t).upper()] = {"px": v[0], "run_date": v[1].isoformat()}
        frozen = d.get("frozen")
        if frozen is not None and not isinstance(frozen, dict):
            st.problems.append("frozen is not an object — cannot be read")
            frozen = {}
        for t, e in (frozen or {}).items():
            if not isinstance(e, dict) or not e.get("reason"):
                st.problems.append(f"unreadable freeze entry for {t} — kept FROZEN")
                e = {"kind": KIND_LEDGER, "reason": f"{t} freeze entry was unreadable; "
                     "kept frozen (acknowledge to release)", "frozen_on": None}
            st.frozen[str(t).upper()] = dict(e)
        try:
            st.feed_unavailable_streak = max(0, int(d.get("feed_unavailable_streak") or 0))
        except (TypeError, ValueError):
            st.problems.append("feed_unavailable_streak unreadable — reset to 0")
        st.feed_streak_date = d.get("feed_streak_date") if isinstance(
            d.get("feed_streak_date"), str) else None
        st.journal = [j for j in (d.get("journal") or []) if isinstance(j, dict)][-200:]
        st.account = d.get("account") if isinstance(d.get("account"), str) else None
        ss = d.get("seed_sessions")
        st.seed_sessions = ss if isinstance(ss, int) and not isinstance(ss, bool) else None
        st.seed_step_date = d.get("seed_step_date") if isinstance(
            d.get("seed_step_date"), str) else None
        return st

    def save(self, path: Path) -> None:
        """Atomic: write a temp file beside it, fsync, rename over."""
        import os
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "_schema": MARKS_SCHEMA, "account": self.account,
                "marks": self.marks, "frozen": self.frozen,
                "feed_unavailable_streak": self.feed_unavailable_streak,
                "feed_streak_date": self.feed_streak_date,
                "seed_sessions": self.seed_sessions,
                "seed_step_date": self.seed_step_date,
                "journal": self.journal[-200:]}, indent=1, sort_keys=True))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def oldest_reference(self) -> Optional[_dt.date]:
        """The earliest date any persisted freeze still refers to — the feed
        window must reach back to it or the split that explains it is invisible."""
        days: List[_dt.date] = []
        for e in self.frozen.values():
            for k in ("ref_date", "frozen_on"):
                try:
                    if e.get(k):
                        days.append(_as_date(e[k]))
                except ValueError:
                    continue
        return min(days) if days else None


def gate_query_window(last_ledger_date: Optional[_dt.date], today: _dt.date,
                      oldest_reference: Optional[_dt.date] = None
                      ) -> Tuple[_dt.date, bool]:
    """``(since, capped)`` — ``since`` is the EXCLUSIVE lower bound handed to
    ``fetch_splits``. The window's first day is the EARLIEST of:
      * the trading day BEFORE the ledger's last dated event (the last event
        can itself be the ex-date — an exclusive bound there blinded the gate
        to account 2's own split from 2026-11-12);
      * ``SETTLE_LOOKBACK_DAYS`` ago;
      * the oldest date a persisted freeze refers to.
    Never more than ``WINDOW_CAP_DAYS`` back; ``capped`` says when that bit."""
    first = today - _dt.timedelta(days=SETTLE_LOOKBACK_DAYS - 1)
    if last_ledger_date:
        first = min(first, _prev_business_day(last_ledger_date))
    if oldest_reference:
        first = min(first, oldest_reference)
    cap = today - _dt.timedelta(days=WINDOW_CAP_DAYS)
    capped = first < cap
    return max(first, cap) - _dt.timedelta(days=1), capped


# --------------------------------------------------------------------------- #
# the gate
# --------------------------------------------------------------------------- #
@dataclass
class CorporateActionGate:
    """One run's corporate-action verdict. Build it, then call, in order:
    ``apply_to_ledger`` → ``assess_broker`` → (construct the plan on
    ``positions_for_sizing``) → ``check_prices`` → ``screen`` → ``save``.
    ``to_block`` is the record that rides the heartbeat."""
    today: _dt.date
    feed: SplitFeedResult
    marks_path: Optional[Path] = None
    state: Optional[GateState] = None
    window_capped: bool = False
    account: Optional[str] = None
    run_frozen: Dict[str, str] = field(default_factory=dict)      # this run only
    applied: List[str] = field(default_factory=list)              # journaled THIS run
    in_play: Dict[str, List[SplitEvent]] = field(default_factory=dict)
    unjournaled: Dict[str, SplitEvent] = field(default_factory=dict)
    reconcile_tickers: set = field(default_factory=set)
    sizing_overrides: Dict[str, int] = field(default_factory=dict)
    refused_orders: List[Dict[str, Any]] = field(default_factory=list)
    price_checked: List[str] = field(default_factory=list)
    seeding: List[str] = field(default_factory=list)
    released: List[Dict[str, Any]] = field(default_factory=list)
    future_events: List[str] = field(default_factory=list)
    notices: List[str] = field(default_factory=list)
    _acked: set = field(default_factory=set)
    foreign: bool = False

    def __post_init__(self) -> None:
        if self.state is None:
            self.state = GateState.load(self.marks_path)
        st, day = self.state, self.today.isoformat()
        if self.account:
            if st.account is None:
                st.account = self.account
            elif st.account != self.account:
                st.problems.append(f"marks file belongs to account {st.account!r}; "
                                   f"this run is {self.account!r}")
                self.foreign = True
        # a mark too old to be a witness is not a mark
        for t in list(st.marks):
            v = _valid_mark(st.marks[t])
            if v and _business_days_between(v[1], self.today) > MARK_MAX_AGE_TRADING_DAYS \
                    and t not in st.frozen:
                st.problems.append(f"mark for {t} is from {v[1]} (> "
                                   f"{MARK_MAX_AGE_TRADING_DAYS} trading days) — NO mark")
                del st.marks[t]
        # the consecutive-outage count, one step per run DATE
        if st.feed_streak_date != day:
            st.feed_unavailable_streak = (0 if self.feed.available
                                          else st.feed_unavailable_streak + 1)
            st.feed_streak_date = day
        # the first two sessions after a seed are weakly witnessed; count them
        if st.seed_step_date != day:
            if st.seed_sessions is not None:
                st.seed_sessions = st.seed_sessions + 1 if st.seed_sessions < 1 else None
            st.seed_step_date = day
        # an operator acknowledgement releases a freeze — and is journaled
        for t in list(st.frozen):
            ack = st.frozen[t].get("ack")
            if isinstance(ack, dict) and ack.get("why"):
                self._release(t, f"operator acknowledgement by {ack.get('who') or 'unnamed'}: "
                                 f"{ack['why']}")
                self._acked.add(t)

    # ------------------------------------------------------------------ #
    @property
    def frozen(self) -> Dict[str, str]:
        """ticker → reason: every PERSISTED freeze plus this run's own."""
        out = {t: str(e.get("reason")) for t, e in self.state.frozen.items()}
        for t, why in self.run_frozen.items():
            out[t] = f"{out[t]} | {why}" if t in out else why
        return out

    def _freeze(self, ticker: str, reason: str) -> None:
        """A freeze that is a function of THIS run's facts (a lagging broker)."""
        prev = self.run_frozen.get(ticker)
        self.run_frozen[ticker] = f"{prev} | {reason}" if prev else reason

    def _persist_freeze(self, ticker: str, kind: str, reason: str,
                        ref_px: Optional[float] = None,
                        ref_date: Optional[str] = None,
                        ratio: Optional[float] = None) -> None:
        """A freeze that must SURVIVE the run. Written once; never rewritten by
        a later day's price."""
        prior = self.state.frozen.get(ticker)
        ack_only = (KIND_LEDGER, KIND_ACTION, KIND_BLIND_SPLIT)
        if prior is not None:
            if not (kind in ack_only and prior.get("kind") not in ack_only):
                return
            # an ACK-ONLY freeze must not be swallowed by a weaker one already on
            # the ticker: the weaker one can release by rule (a matching split, an
            # arriving price) and would take this reason with it.
            reason = f"{reason} [supersedes the earlier {prior.get('kind')} freeze of " \
                     f"{prior.get('frozen_on')}: {prior.get('reason')}]"
        self.state.frozen[ticker] = {
            "kind": kind, "reason": reason, "frozen_on": self.today.isoformat(),
            "ref_px": ref_px, "ref_date": ref_date, "ratio": ratio,
            "no_split_streak": 0, "streak_date": None}
        self.state.journal.append({"date": self.today.isoformat(), "ticker": ticker,
                                   "event": "freeze", "kind": kind, "why": reason})

    def _release(self, ticker: str, why: str) -> None:
        entry = self.state.frozen.pop(ticker, None)
        rec = {"date": self.today.isoformat(), "ticker": ticker, "event": "release",
               "why": why, "was": entry}
        self.state.journal.append(rec)
        self.released.append({"ticker": ticker, "why": why})
        self.notices.append(f"[CORPORATE-ACTION] {ticker} RELEASED — {why}")

    def _confirmed(self, ticker: str) -> List[SplitEvent]:
        """Feed-confirmed splits for a ticker, none dated after today."""
        return [e for e in dict.fromkeys(self.feed.confirmed(ticker))
                if e.ex_date <= self.today]

    @property
    def stand_down(self) -> bool:
        """True ⇒ nothing may be staged today and the run is non-canonical."""
        return (bool(self.frozen) or bool(self.seeding) or self.state.unreadable
                or self.foreign)

    @property
    def noncanonical_reasons(self) -> List[str]:
        out = [f"FROZEN {t}: {r}" for t, r in sorted(self.frozen.items())]
        if self.foreign:
            out.append("price-basis marks belong to ANOTHER account — "
                       + "; ".join(self.state.problems))
        if self.state.unreadable:
            out.append("price-basis marks unreadable — operator must restore or "
                       "acknowledge (" + "; ".join(self.state.problems) + ")")
        if self.seeding:
            out.append("seeding price-basis marks (first run) for "
                       + ", ".join(sorted(self.seeding)))
        if self.state.feed_unavailable_streak >= FEED_DEAD_ALARM_RUNS:
            out.append(f"split feed UNAVAILABLE on {self.state.feed_unavailable_streak} "
                       f"consecutive runs ({self.feed.reason})")
        return out

    # ---- 1. ledger: apply confirmed splits, exactly once ---------------- #
    def apply_to_ledger(self, ledger: Any, orders: Sequence[Any]) -> None:
        """Apply each confirmed split to the ledger as an explicit journaled
        event. A split is applied ONLY when the held position is provably in the
        PRE-split basis: every observed fill in that ticker predates the
        ex-date. A position built entirely on/after the ex-date needs nothing. A
        MIXED position (fills on both sides — the 2026-11-05 account-2 state) is
        never auto-scaled: it is frozen, persistently, for manual review."""
        journaled = {s.key: s.ratio for s in ledger.applied_splits()}
        done = set(journaled)
        for ev in dict.fromkeys(self.feed.events):
            if ev.ex_date > self.today:          # the gate's OWN date check
                self.future_events.append(ev.key)
                continue
            held = int(ledger.positions().get(ev.ticker, 0))
            if ev.key in done:
                was = journaled.get(ev.key)
                if was is not None and abs(was - ev.ratio) > 1e-9:
                    # the feed CORRECTED a ratio the ledger already acted on. The
                    # ledger is never re-scaled automatically on a second opinion.
                    self._persist_freeze(
                        ev.ticker, KIND_LEDGER,
                        f"{ev.ticker} split ex {ev.ex_date} was journaled into the ledger "
                        f"at {was:g}:1 and the feed now confirms {ev.ratio:g}:1 for the "
                        "same ex-date — the ledger is NOT re-scaled automatically; "
                        "manual review")
                    continue
                self.in_play.setdefault(ev.ticker, []).append(ev)
                continue
            if held == 0:
                continue
            dates = [_fill_date(o) for o in orders
                     if str(o.ticker).upper() == ev.ticker
                     and int(getattr(o, "filled_qty", 0) or 0) > 0]
            if not dates or any(d is None for d in dates):
                self._persist_freeze(
                    ev.ticker, KIND_LEDGER,
                    f"{ev.ticker} split {ev.ratio:g}:1 ex {ev.ex_date} on the feed but "
                    f"the journal cannot date the held {held} shares — share basis "
                    "unknown; manual review")
                self.unjournaled[ev.ticker] = ev
                continue
            pre = [d for d in dates if d < ev.ex_date]
            if not pre:
                continue                      # bought post-split: already new basis
            if len(pre) != len(dates):
                self._persist_freeze(
                    ev.ticker, KIND_LEDGER,
                    f"{ev.ticker} split {ev.ratio:g}:1 ex {ev.ex_date} was never applied "
                    f"to the ledger and the held {held} shares mix pre- and post-split "
                    "fills — NOT auto-scaled; manual review")
                self.unjournaled[ev.ticker] = ev
                continue
            try:
                did = ledger.apply_split(ev.ticker, ev.ratio, ev.ex_date)
            except ValueError as exc:
                self._persist_freeze(
                    ev.ticker, KIND_LEDGER,
                    f"{ev.ticker} split {ev.ratio:g}:1 ex {ev.ex_date} could not be "
                    f"applied ({exc}); manual review")
                self.unjournaled[ev.ticker] = ev
                continue
            done.add(ev.key)
            if did:
                self.applied.append(ev.key)
            self.in_play.setdefault(ev.ticker, []).append(ev)
        for u in self.feed.unhandled:
            if int(ledger.positions().get(u.ticker, 0)) != 0:
                self._persist_freeze(
                    u.ticker, KIND_ACTION,
                    f"{u.ticker} has an unmodelled corporate action on the feed "
                    f"({u.kind}, {u.date}); manual review")

    def ledger_splits(self, ledger: Any) -> List[SplitEvent]:
        """Every split the ledger has journaled (all time) — what the
        journal-net explanation must scale pre-split fills by."""
        return list(ledger.applied_splits())

    # ---- 2. broker: is the broker in the same share basis? -------------- #
    def assess_broker(self, ledger_positions: Mapping[str, int],
                      broker_positions: Mapping[str, int]) -> None:
        for t, evs in self.in_play.items():
            lq, bq = int(ledger_positions.get(t, 0)), int(broker_positions.get(t, 0))
            if lq == bq:
                continue                                   # settled
            now = [e.ratio for e in evs if e.key in self.applied]
            cands = [math.prod(now)] if now else (
                [e.ratio for e in evs] + [math.prod(e.ratio for e in evs)])
            names = ", ".join(f"{e.ratio:g}:1 ex {e.ex_date}" for e in evs)
            if any(abs(lq / c - bq) < _QTY_TOL for c in cands):
                self._freeze(t, f"{t} split {names} CONFIRMED by the feed; ledger {lq} is "
                                f"post-split, broker still shows {bq} (pre-split) — broker "
                                "has not applied it yet")
                self.reconcile_tickers.add(t)
                self.sizing_overrides[t] = lq
            else:
                self._freeze(t, f"{t} ledger {lq} vs broker {bq} matches NEITHER side of the "
                                f"confirmed split ({names}) — position drift stands")
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

    # ---- 3. prices -------------------------------------------------------- #
    def _mark(self, ticker: str, px: float) -> None:
        self.state.marks[ticker] = {"px": px, "run_date": self.today.isoformat()}

    def _review_freeze(self, t: str, fz: Dict[str, Any], px: float, held: bool) -> None:
        """A persisted freeze, looked at again. It releases ONLY by its kind's
        named rule — today's price being 'not split-shaped any more' is not one."""
        kind, confirmed = fz.get("kind"), self._confirmed(t)
        ref = fz.get("ref_px")
        if kind == KIND_UNCONFIRMED and ref:
            match = [e for e in confirmed
                     if confirmed_ratio_explains(e.ratio, ref, px)]
            if match:
                self._release(t, f"feed-confirmed split {match[0].ratio:g}:1 ex "
                                 f"{match[0].ex_date} matches the observed move "
                                 f"{float(ref):.4f} → {px:.4f}")
                self._mark(t, px)
                return
            day = self.today.isoformat()
            if fz.get("streak_date") == day:
                return
            fz["streak_date"] = day
            covers = (self.feed.start is not None and fz.get("frozen_on")
                      and self.feed.start <= _as_date(fz["frozen_on"]))
            if (self.feed.available and not confirmed and covers
                    and releases_on_feed_silence(fz.get("ratio"))):
                fz["no_split_streak"] = int(fz.get("no_split_streak") or 0) + 1
                if fz["no_split_streak"] >= NO_SPLIT_RELEASE_SESSIONS:
                    self._release(t, f"feed answered no-split ×{fz['no_split_streak']} — "
                                     f"treated as a real move ({float(ref):.4f} → {px:.4f})")
                    self._mark(t, px)
            else:
                fz["no_split_streak"] = 0      # consecutive means consecutive
        elif kind == KIND_BASIS_LAG and ref:
            if near_basis(ref, px):
                self._release(t, f"price {px:.4f} is now in the confirmed split's basis "
                                 f"(expected ≈ {float(ref):.4f})")
                self._mark(t, px)
        elif kind == KIND_BLIND and self.feed.available:
            if held and confirmed:
                fz["kind"] = KIND_BLIND_SPLIT
                fz["reason"] = (f"{t} has NO price mark and the feed confirms a split "
                                f"({confirmed[0].ratio:g}:1 ex {confirmed[0].ex_date}) in the "
                                "window — the price basis cannot be witnessed; acknowledge "
                                "to release")
            else:
                self._release(t, "the feed answered; the mark is seeded today")
                self._mark(t, px)
                self.seeding.append(t)

    def check_prices(self, closes: Mapping[str, float], held: Iterable[str],
                     traded: Iterable[str] = ()) -> None:
        """The price-basis witness, for every held or to-be-traded ticker.

        * NO valid mark → a SEEDING day for that ticker: the mark is recorded
          and the book stands down today. (Held + feed unavailable → BLIND, no
          mark is laid until the feed answers. Held + a confirmed split in the
          window → frozen: there is no witness for the basis.)
        * a split the gate journaled THIS run → the price must have moved by
          that ratio; if it has not, the vendor has not adjusted yet (frozen
          until it does).
        * a split-shaped move → fine if a feed-confirmed split's RATIO explains
          it (matched by ratio, not by which date the mark carries); otherwise
          FROZEN, persistently, with the reference mark it was measured from."""
        if self.state.unreadable or self.foreign:
            return                    # no marks laid, nothing written over the file
        held_set = {str(t).upper() for t in held}
        check = held_set | {str(t).upper() for t in traded}
        feed_why = ("feed UNAVAILABLE: " + self.feed.reason if not self.feed.available
                    else "feed answered and reports NO matching split")
        for t in sorted(closes):
            try:
                px = float(closes[t])                # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
            if not math.isfinite(px) or px <= 0:
                continue
            if t in self._acked:
                self._mark(t, px)
                continue
            if t in self.state.frozen:
                self._review_freeze(t, self.state.frozen[t], px, t in held_set)
                continue
            if t not in check:
                self._mark(t, px)                    # benchmarks: keep the mark fresh
                continue
            self.price_checked.append(t)
            confirmed = self._confirmed(t)
            v = _valid_mark(self.state.marks.get(t))
            if v is None:
                if t in held_set and not self.feed.available:
                    self._persist_freeze(
                        t, KIND_BLIND,
                        f"{t} share/price basis UNVERIFIABLE: no valid price mark and the "
                        f"feed is UNAVAILABLE ({self.feed.reason})")
                elif t in held_set and confirmed:
                    self._persist_freeze(
                        t, KIND_BLIND_SPLIT,
                        f"{t} has NO valid price mark and the feed confirms a split "
                        f"({confirmed[0].ratio:g}:1 ex {confirmed[0].ex_date}) in the window — "
                        "the price basis cannot be witnessed; acknowledge to release")
                else:
                    self.seeding.append(t)
                    self._mark(t, px)
                continue
            prev, seen = v
            now = [e for e in confirmed if e.key in self.applied]
            if now:
                exp = prev / math.prod(e.ratio for e in now)
                if near_basis(exp, px):
                    self._mark(t, px)
                else:
                    self._persist_freeze(
                        t, KIND_BASIS_LAG,
                        f"{t} split {now[0].ratio:g}:1 ex {now[0].ex_date} is CONFIRMED and "
                        f"journaled, but the price ({px:.4f}; mark {prev:.4f} on {seen}) is "
                        f"NOT yet in the split's basis (expected ≈ {exp:.4f}) — the vendor "
                        "has not adjusted the series",
                        ref_px=exp, ref_date=seen.isoformat())
                continue
            r = price_split_ratio(prev, px)
            if r is None or any(confirmed_ratio_explains(e.ratio, prev, px)
                                for e in confirmed):
                self._mark(t, px)
                continue
            self._persist_freeze(
                t, KIND_UNCONFIRMED,
                f"{t} mark moved {prev:.4f} ({seen}) → {px:.4f} on {self.today}: a "
                f"~{r:g}:1 split-shaped move, UNCONFIRMED ({feed_why})"
                + ("" if releases_on_feed_silence(r) else
                   " — 2:1 or more: releases ONLY on a ratio-matching confirmed split "
                   "or an operator acknowledgement, never on feed silence"),
                ref_px=prev, ref_date=seen.isoformat(), ratio=r)
            self._review_freeze(t, self.state.frozen[t], px, t in held_set)
        if self.seeding:
            self.state.seed_sessions = 0
        self.save()

    def save(self) -> None:
        """Write the state — unless the file on disk was UNREADABLE: that file
        is left exactly as it is until an operator restores or resets it."""
        if self.marks_path is None or self.state.unreadable or self.foreign:
            return
        self.state.save(Path(self.marks_path))

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
        st = self.state
        return {"_schema": "paper_corporate_actions/v2",
                "feed": self.feed.to_dict(),
                "feed_unavailable_streak": st.feed_unavailable_streak,
                "window_capped_at_days": WINDOW_CAP_DAYS if self.window_capped else None,
                "applied_this_run": list(self.applied),
                "future_events_ignored": list(self.future_events),
                "frozen": dict(self.frozen),
                "frozen_persisted": {t: dict(e) for t, e in st.frozen.items()},
                "seeding": sorted(self.seeding),
                # 0 on a seeding day, 1 on the run after: the two sessions in which
                # the price guard has no, or only a one-day-old, reference
                "marks_age_sessions": (st.seed_sessions if st.seed_sessions in (0, 1)
                                       else None),
                "marks_unreadable": st.unreadable,
                "released": list(self.released),
                "stand_down": self.stand_down,
                "noncanonical_reasons": self.noncanonical_reasons,
                "reconcile_tickers": sorted(self.reconcile_tickers),
                "refused_orders": list(self.refused_orders),
                "price_checked": sorted(set(self.price_checked)),
                "marks_problems": list(st.problems),
                "degraded": bool(self.noncanonical_reasons) or not self.feed.available
                            or bool(st.problems)}
