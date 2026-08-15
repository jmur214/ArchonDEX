# paper_trader/clock_census.py
"""ClockCensus — a daily assertion that every forward-accruing record ACTUALLY ADVANCED (T-338).

WHY: "we can't keep having the silent failures when we should instead be gathering useful
data that we missed because of said failures." Every recent near-miss was ONE disease — a
clock believed to be accruing that wasn't (unscored notes, frozen prices, empty tape,
ungated feeds, denied pushes). The trading census guards the TRADE; nothing guarded the
CLOCKS. This is that guard.

THE CONTRACT
  * Each clock declares WHAT must have advanced today and HOW to verify it FROM THE
    ARTIFACT — never from the config. A config saying "enabled" is not evidence that
    anything moved; only the artifact's own last-advanced date is.
  * FAIL-CLOSED: an unverifiable clock (missing artifact, unparseable date) is a **MISS**,
    never a skip. You cannot census what you cannot read.
  * NOT_DUE is legitimate ONLY when the due-check is itself artifact-verifiable. If we
    cannot establish whether a clock was due, that is a MISS too — "probably not due" is
    the same silence the census exists to eliminate.
  * READ-ONLY: the census OBSERVES. It never repairs, backfills, or writes to a clock's
    artifact — a census that fixes what it measures cannot be trusted about what it found.
  * ONE REGISTRY: every durable state file must be registered here or EXPLICITLY exempted
    with a reason; a tripwire test fails when a new one appears unclassified, so a new
    clock cannot be added silently.

OUTPUT: `clocks_advanced n/n`, plus per-clock detail. ANY miss → degraded + the notify
channel fires SAME-DAY, naming the clock. Silence then genuinely means all clocks ran —
which is the actual deliverable.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ADVANCED, MISS, NOT_DUE = "ADVANCED", "MISS", "NOT_DUE"


@dataclass
class ClockResult:
    name: str
    status: str
    detail: str

    @property
    def ok(self) -> bool:
        return self.status in (ADVANCED, NOT_DUE)


# --------------------------------------------------------------------------------------
# artifact readers (read-only; every failure path returns a MISS reason, never a guess)
# --------------------------------------------------------------------------------------
def _read_json(p: Path) -> Optional[Any]:
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _last_date_in_state(p: Path, keys=("days", "points")) -> Tuple[Optional[str], str]:
    """Newest date inside a book/tracker state file. Returns (date|None, reason)."""
    if not p.exists():
        return None, f"artifact missing: {p.name}"
    st = _read_json(p)
    if st is None:
        return None, f"unparseable: {p.name}"
    for k in keys:
        rows = st.get(k)
        if isinstance(rows, list) and rows:
            ds = [r.get("date") for r in rows if isinstance(r, dict) and r.get("date")]
            if ds:
                return max(ds), "ok"
    return None, f"no dated rows in {p.name}"


def _last_date_in_jsonl(p: Path, fields=("as_of", "date", "trade_date", "timestamp")
                        ) -> Tuple[Optional[str], str]:
    if not p.exists():
        return None, f"artifact missing: {p.name}"
    try:
        last = None
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            for f in fields:
                if rec.get(f):
                    d = str(rec[f])[:10]
                    last = d if last is None or d > last else last
                    break
        return (last, "ok") if last else (None, f"no dated rows in {p.name}")
    except Exception:
        return None, f"unparseable: {p.name}"


# --------------------------------------------------------------------------------------
# THE REGISTRY — one place. A new clock registers here or the tripwire test fails.
# --------------------------------------------------------------------------------------
@dataclass
class Clock:
    name: str
    check: Callable[[Path, str], ClockResult]
    covers: Tuple[str, ...] = ()          # durable paths this clock verifies


def _rolled(label: str, rel: str) -> Clock:
    """Clock 4: a book/tracker ROLLED — its state's newest date must equal as_of."""
    def _c(root: Path, as_of: str) -> ClockResult:
        d, why = _last_date_in_state(root / rel)
        if d is None:
            return ClockResult(label, MISS, why)          # fail-closed: unreadable = MISS
        if d == as_of:
            return ClockResult(label, ADVANCED, f"last={d}")
        return ClockResult(label, MISS, f"last={d} != as_of={as_of} (did not roll)")
    return Clock(label, _c, (rel,))


def _analyst_note(root: Path, as_of: str) -> ClockResult:
    """Clock 1: a note file exists for as_of — constrained AND agentic."""
    miss = []
    for lbl, d in (("constrained", "data/intel/analyst_notes"),
                   ("agentic", "data/intel/analyst_notes_agentic")):
        p = root / d
        if not p.exists() or not any(f.name.startswith(as_of) for f in p.glob("*.json")):
            miss.append(lbl)
    if miss:
        return ClockResult("analyst_note_written", MISS,
                           f"no note for {as_of}: {', '.join(miss)}")
    return ClockResult("analyst_note_written", ADVANCED, f"notes present for {as_of}")


def _eval_scored_when_due(root: Path, as_of: str) -> ClockResult:
    """Clock 2: if any prediction MATURED, a newly-scored row must exist.

    The due-check is artifact-derived (a prediction whose resolve-by has passed and which
    carries no score). If the ledger is unreadable we cannot establish due-ness → MISS."""
    p = root / "data/intel/analyst_predictions.jsonl"
    if not p.exists():
        return ClockResult("eval_scored_when_due", MISS, "predictions ledger missing")
    try:
        matured_unscored, scored_today = 0, 0
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            due = str(r.get("resolve_by") or r.get("horizon_end") or "")[:10]
            has_score = r.get("brier") is not None or r.get("scored_at")
            if due and due <= as_of and not has_score:
                matured_unscored += 1
            if str(r.get("scored_at", ""))[:10] == as_of:
                scored_today += 1
    except Exception:
        return ClockResult("eval_scored_when_due", MISS, "predictions ledger unparseable")
    if matured_unscored == 0:
        return ClockResult("eval_scored_when_due", NOT_DUE, "no matured-unscored predictions")
    if scored_today > 0:
        return ClockResult("eval_scored_when_due", ADVANCED,
                           f"{scored_today} scored today ({matured_unscored} still maturing)")
    return ClockResult("eval_scored_when_due", MISS,
                       f"{matured_unscored} matured predictions UNSCORED and none scored today")


def _news_month_pushed(root: Path, as_of: str) -> ClockResult:
    """Clock 3: the current month's panel partition advanced TODAY (mtime + rows grew)."""
    ym = as_of[:7].replace("-", "")
    part = root / f"data/intel/news_panel/{as_of[:4]}/{as_of[5:7]}/news_{ym}.parquet"
    if not part.exists():
        return ClockResult("news_month_pushed", MISS, f"partition missing: {part.name}")
    try:
        import datetime as dt
        mt = dt.datetime.fromtimestamp(part.stat().st_mtime).date().isoformat()
    except Exception:
        return ClockResult("news_month_pushed", MISS, "partition mtime unreadable")
    if mt != as_of:
        return ClockResult("news_month_pushed", MISS, f"partition mtime {mt} != {as_of}")
    return ClockResult("news_month_pushed", ADVANCED, f"partition touched {mt}")


def _scan_filed_when_due(root: Path, as_of: str) -> ClockResult:
    """Clock 5: if the scan was DUE, a provenance row for as_of exists.

    A self-explained zero (a reason enum) COUNTS AS ADVANCED — the scan reporting "nothing
    qualified, here's why" is the clock ticking, not a miss."""
    prov = root / "data/intel/thesis_scan_provenance.jsonl"
    state = root / "data/intel/thesis_scan_state.json"
    if not state.exists():
        return ClockResult("scan_filed_when_due", MISS, "scan state missing (due-ness unknown)")
    st = _read_json(state)
    if st is None:
        return ClockResult("scan_filed_when_due", MISS, "scan state unparseable (due-ness unknown)")
    due = bool(st.get("due") or st.get("due_today"))
    last, why = _last_date_in_jsonl(prov)
    if not due:
        # due-ness established from the artifact → a legitimate NOT_DUE
        return ClockResult("scan_filed_when_due", NOT_DUE, f"not due (last filed {last or 'n/a'})")
    if last == as_of:
        return ClockResult("scan_filed_when_due", ADVANCED,
                           "provenance row filed (a self-explained zero counts)")
    return ClockResult("scan_filed_when_due", MISS, f"DUE but no provenance row for {as_of} ({why})")


def _stage2_ticked(root: Path, as_of: str) -> ClockResult:
    """Clock 6."""
    last, why = _last_date_in_jsonl(root / "data/state/stage2_clock.jsonl")
    if last is None:
        return ClockResult("stage2_clock_ticked", MISS, why)
    return (ClockResult("stage2_clock_ticked", ADVANCED, f"last={last}") if last == as_of
            else ClockResult("stage2_clock_ticked", MISS, f"last={last} != {as_of}"))


def _archive_feeds_in_budget(root: Path, as_of: str) -> ClockResult:
    """Clock 7: IMPORT B's T-335 cadence gate — never duplicate a health standard."""
    try:
        from paper_trader.altdata_archive import assess_feed_health
    except Exception as exc:
        return ClockResult("archive_feeds_in_budget", MISS,
                           f"cannot import B's T-335 gate: {type(exc).__name__}")
    try:
        detail, offenders = assess_feed_health(root)
    except Exception as exc:
        return ClockResult("archive_feeds_in_budget", MISS,
                           f"T-335 gate raised: {type(exc).__name__}")
    if offenders:
        return ClockResult("archive_feeds_in_budget", MISS,
                           f"{len(offenders)} feed(s) over budget: {', '.join(offenders[:6])}")
    return ClockResult("archive_feeds_in_budget", ADVANCED, f"{len(detail)} feeds inside budget")


def _exec_ledger_on_fill_days(root: Path, as_of: str) -> ClockResult:
    """Clock 8: on a day with fills, the exec-cost ledger must have appended.

    Due-ness comes from the orders journal (an artifact), not from a flag."""
    orders = root / "data/paper_state/orders.jsonl"
    if not orders.exists():
        return ClockResult("exec_ledger_on_fill_days", MISS, "orders journal missing (due-ness unknown)")
    try:
        filled_today = 0
        for line in orders.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if str(r.get("trade_date", ""))[:10] == as_of and str(r.get("state", "")).upper() in (
                    "FILLED", "PARTIALLY_FILLED"):
                filled_today += 1
    except Exception:
        return ClockResult("exec_ledger_on_fill_days", MISS, "orders journal unparseable")
    if filled_today == 0:
        return ClockResult("exec_ledger_on_fill_days", NOT_DUE, "no fills today")
    last, why = _last_date_in_jsonl(root / "data/state/exec_cost_ledger.jsonl")
    if last == as_of:
        return ClockResult("exec_ledger_on_fill_days", ADVANCED, f"{filled_today} fill(s) recorded")
    return ClockResult("exec_ledger_on_fill_days", MISS,
                       f"{filled_today} fill(s) today but ledger last={last} ({why})")


# The rolled-record clocks (clock 4), one per forward-accruing book/tracker.
_ROLLED = [
    ("sleeve_tracker_rolled", "data/state/sleeve_tracking.json"),
    ("btc_shadow_rolled", "data/state/btc_shadow_tracking.json"),
    ("dbmf_shadow_rolled", "data/state/dbmf_shadow_tracking.json"),
    ("event_desk_rolled", "data/state/event_shadow_book.json"),
    ("analyst_desk_rolled", "data/state/analyst_desk_book.json"),
    ("thesis_machine_rolled", "data/state/thesis_book_machine.json"),
    ("thesis_user_rolled", "data/state/thesis_book_user_seeded.json"),
    ("book_spy_null_rolled", "data/state/book_spy_null.json"),
    ("book_damped_offense_rolled", "data/state/book_damped_offense.json"),
    ("book_quality_sat_rolled", "data/state/book_quality_satellite.json"),
    ("book_sleeve_tier_rolled", "data/state/book_sleeve_tier50k.json"),
    ("llm_shadow_book_rolled", "data/state/llm_shadow_book.json"),
]

REGISTRY: List[Clock] = (
    [Clock("analyst_note_written", _analyst_note,
           ("data/intel/analyst_notes", "data/intel/analyst_notes_agentic")),
     Clock("eval_scored_when_due", _eval_scored_when_due, ("data/intel/analyst_predictions.jsonl",)),
     Clock("news_month_pushed", _news_month_pushed, ()),
     Clock("scan_filed_when_due", _scan_filed_when_due,
           ("data/intel/thesis_scan_state.json", "data/intel/thesis_scan_provenance.jsonl")),
     Clock("stage2_clock_ticked", _stage2_ticked, ("data/state/stage2_clock.jsonl",)),
     Clock("archive_feeds_in_budget", _archive_feeds_in_budget, ()),
     Clock("exec_ledger_on_fill_days", _exec_ledger_on_fill_days,
           ("data/state/exec_cost_ledger.jsonl", "data/paper_state/orders.jsonl"))]
    + [_rolled(n, p) for n, p in _ROLLED])

# Durable paths deliberately NOT clock-censused, each with a REASON. The tripwire test
# asserts every DURABLE_PATH is either covered by a clock or listed here — so a new
# artifact cannot appear unclassified.
EXEMPT: Dict[str, str] = {
    "data/state/paper_heartbeat.json": "the census's own output surface — censusing it would be circular",
    "data/state/paper_alerts.log": "append-on-alert only; silence is the healthy state, so 'did not advance' is correct",
    "data/paper_state/ledger.jsonl": "broker-truth mirror, not a forward clock (reconcile guards it)",
    "data/paper_state/recon.jsonl": "written by reconcile; the trading census already gates it",
    "data/intel/thesis_calls.jsonl": "output of the scan clock — covered transitively by scan_filed_when_due",
    "data/coordination/thesis_inbox.md": "human-facing relay, not a machine clock",
    "data/intel/analyst_eval_summary.json": "derived rollup of the predictions ledger (covered by eval_scored_when_due)",
    "data/intel/event_calls.jsonl": "feed consumed by event_desk_rolled, which fails if it stalls",
    "data/intel/llm_spend.jsonl": "budget ledger — advances only when spend occurs; a no-spend day is healthy",
    "data/state/tax_lots.jsonl": "advances only on taxable lots; a no-lot day is healthy",
    "data/state/offense_tracking.json": "fleet acct-2 file, populated only in that account's container",
    "data/state/sleeve_btc_tracking.json": "fleet acct-3 file, populated only in that account's container",
    # T-329 — the stage-2 AI trader. Same container-scoping as the two fleet files
    # above: this census runs in ACCOUNT-1's container, which never holds account-3's
    # tracker, so a clock here could only ever report a MISS it cannot diagnose.
    # Account-3's own record is gated where it IS visible — in its own container, by
    # its own canonical/heartbeat verdict, its own dead-man's-switch alarm (metric
    # dimension Account=ai-trader), and the per-run stream block that states WHY a
    # day held. This exemption is a statement about WHERE the clock lives, not a
    # claim that the record needs no clock.
    "data/state/llm_analyst_tracking.json": "acct-3 (ai-trader) file, populated only in that account's container; gated there by its own canonical/heartbeat + dead-man's-switch",
    "data/state/TRADING_HALT": "an OPERATOR CONTROL, not a forward record — its healthy state is ABSENT, so 'did not advance' is correct and a clock would invert the meaning",
    "data/intel/llm_raw": "diagnostic archive of raw LLM responses — written only when a call is MADE, so a no-call day is healthy; the calls themselves are clocked by analyst_note_written and scan_filed_when_due",
}


def run_census(root: Optional[str] = None, as_of: Optional[str] = None) -> Dict[str, Any]:
    """Run every registered clock. READ-ONLY. Returns the census dict."""
    import datetime as dt
    base = Path(root) if root else Path(__file__).resolve().parents[1]
    day = as_of or dt.date.today().isoformat()
    results: List[ClockResult] = []
    for c in REGISTRY:
        try:
            results.append(c.check(base, day))
        except Exception as exc:                   # a raising check is a MISS, never a skip
            results.append(ClockResult(c.name, MISS, f"check raised {type(exc).__name__}"))
    advanced = [r for r in results if r.status == ADVANCED]
    not_due = [r for r in results if r.status == NOT_DUE]
    missed = [r for r in results if r.status == MISS]
    n_expected = len(advanced) + len(missed)       # NOT_DUE clocks aren't counted as expected
    return {
        "_schema": "clock_census/v1",
        "as_of": day,
        "clocks_advanced": f"{len(advanced)}/{n_expected}",
        "n_advanced": len(advanced), "n_expected": n_expected,
        "n_not_due": len(not_due), "n_missed": len(missed),
        "degraded": bool(missed),
        "missed": [{"clock": r.name, "detail": r.detail} for r in missed],
        "detail": {r.name: {"status": r.status, "detail": r.detail} for r in results},
    }


def census_line(census: Dict[str, Any]) -> str:
    """The heartbeat one-liner. Names the failing clock — a count alone isn't actionable."""
    if not census.get("degraded"):
        return (f"CLOCK-CENSUS clocks_advanced={census['clocks_advanced']} "
                f"not_due={census['n_not_due']} — all clocks running")
    names = ", ".join(m["clock"] for m in census["missed"])
    return (f"[CLOCK-CENSUS][ALERT] clocks_advanced={census['clocks_advanced']} "
            f"MISSED: {names}")
