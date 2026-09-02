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
    """Clock 1: a note exists for as_of — constrained AND agentic.

    T-348 — THIS CLOCK COULD NEVER ADVANCE. It matched `<as_of>*.json` while the pulse
    writes `note_<as_of>.json`, so it reported a miss every day of its life. Worse than
    useless: the permanent false alarm HID A REAL MISS — no constrained note exists for
    2026-08-27, and nobody could see it inside a clock already crying wolf daily. That is
    the concrete cost of a clock that never clears.

    It is the THIRD instance of one disease (T-331 in the eval harness, T-346 in the news
    clock, this): a reader encoding a writer's naming independently of the writer. The
    name now comes from `artifact_paths`, the one place it is declared — the same object
    the pulse writes through, so the two cannot drift apart again."""
    from paper_trader.artifact_paths import ANALYST_NOTE, ANALYST_NOTE_AGENTIC
    miss = [lbl for lbl, art in (("constrained", ANALYST_NOTE),
                                 ("agentic", ANALYST_NOTE_AGENTIC))
            if not art.exists_for(root, as_of)]
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


def _newest_ingest_date(part: Path) -> Tuple[Optional[str], str]:
    """Newest ingest date inside a news partition, read from ONE parquet column.

    Fail-closed: every path that cannot establish the date returns None WITH a reason,
    so the caller can report "not checked" instead of passing quietly."""
    try:
        import pyarrow.parquet as pq
    except Exception:
        return None, "pyarrow unavailable — row freshness NOT verifiable"
    try:
        f = pq.ParquetFile(part)
        names = set(f.schema_arrow.names)
        col = next((c for c in ("ingest_ts", "created_at") if c in names), None)
        if col is None:
            return None, f"no ingest_ts/created_at column in {part.name}"
        vals = f.read(columns=[col]).column(col).to_pylist()
        stamps = [str(v)[:10] for v in vals if v is not None]
        if not stamps:
            return None, f"{col} column is entirely null"
        return max(stamps), "ok"
    except Exception as exc:
        return None, f"partition unreadable ({type(exc).__name__})"


def _news_month_pushed(root: Path, as_of: str) -> ClockResult:
    """Clock 3: the current month's news panel advanced TODAY.

    T-346 — THIS CLOCK WAS A PERMANENT FALSE MISS. It built the S3 date-partitioned key
    (`news_panel/YYYY/MM/news_YYYYMM.parquet`) and then looked for it on the LOCAL disk,
    where D's layout is FLAT (`news_panel/news_YYYYMM.parquet`). The partitioned path
    never existed locally, so the clock reported "partition missing" every day of its
    life — a miss that could not clear, which is precisely how a census trains its
    operators to ignore it. A clock that cries wolf daily is worse than no clock. The
    path now comes from `cloud_state` BY IMPORT: one layout, one owner, no second copy
    to drift.

    Two halves, because they answer different questions:
      * `mtime == as_of` proves the PUSHER RAN today;
      * the newest ingest stamp proves the TAPE ACTUALLY MOVED.
    A file touched today whose newest row is weeks old is the frozen-feed class this
    program has already been bitten by twice (an empty news tape, a price source months
    stale) — and it reads perfectly healthy on mtime alone. Where the row half cannot be
    performed the clock MISSES and names why, rather than passing on the half it did.
    """
    try:
        from paper_trader.cloud_state import CloudState
        rel = CloudState._news_rel(int(as_of[:4]), int(as_of[5:7]))
    except Exception as exc:
        return ClockResult("news_month_pushed", MISS,
                           f"cannot resolve the panel path from cloud_state "
                           f"({type(exc).__name__}) — layout unknown, not assumed")
    part = root / rel
    if not part.exists():
        return ClockResult("news_month_pushed", MISS, f"month panel missing: {rel}")
    try:
        import datetime as dt
        mt = dt.datetime.fromtimestamp(part.stat().st_mtime).date().isoformat()
    except Exception:
        return ClockResult("news_month_pushed", MISS, "panel mtime unreadable")
    if mt != as_of:
        return ClockResult("news_month_pushed", MISS,
                           f"panel mtime {mt} != {as_of} — the push did not run today")
    newest, why = _newest_ingest_date(part)
    if newest is None:
        return ClockResult("news_month_pushed", MISS,
                           f"touched {mt} but row freshness UNVERIFIED: {why}")
    if newest != as_of:
        return ClockResult("news_month_pushed", MISS,
                           f"panel touched {mt} but newest row is {newest} — the file "
                           f"moved and the TAPE DID NOT (frozen-feed class)")
    return ClockResult("news_month_pushed", ADVANCED,
                       f"panel touched {mt}, newest row {newest}")


DIGEST_BUDGET_DAYS = 9
"""A weekly cadence plus a 2-day grace, so a holiday-shifted run is not a false alarm
while a genuinely skipped week still fires."""

ADVISOR_BUDGET_DAYS = 35
"""T-347: a MONTHLY cadence plus grace. The advisor surface also regenerates on-change,
so it may advance far more often — the budget is the OUTER bound (has it rendered at all
this month?), never a claim about how often it should."""


def _md_header_date(p: Path) -> Tuple[Optional[str], str]:
    """The `as_of` stamped in a rendered markdown surface's own H1.

    Both A's surfaces render `# <Title> \u2014 YYYY-MM-DD`. The date is read from the
    ARTIFACT, never from mtime (a git checkout rewrites mtime and would fake an advance)
    and never from a schedule (the config is not the artifact). ONE parser for both
    surfaces — a second copy is a second thing to drift."""
    try:
        head = p.read_text().splitlines()[0]
    except Exception:
        return None, "surface unreadable"
    stamp = head.rsplit("\u2014", 1)[-1].strip()[:10]
    try:
        import datetime as _dt
        _dt.datetime.strptime(stamp, "%Y-%m-%d")
    except Exception:
        return None, "header carries no parseable as_of date (fail-closed)"
    return stamp, "ok"


def _dated_surface_clock(name: str, rel: str, budget: int, what: str):
    """A cadence clock over a rendered markdown surface that stamps its own date.

    ADVANCED written today / NOT_DUE inside budget / MISS past it. NOT_DUE is what a
    healthy periodic artifact looks like on most days — and because NOT_DUE is excluded
    from the expected count, a correctly-silent surface can never dilute the ratio."""
    def _c(root: Path, as_of: str) -> ClockResult:
        p = root / rel
        if not p.exists():
            return ClockResult(name, MISS, f"no {what} at {rel} \u2014 it has never rendered")
        stamp, why = _md_header_date(p)
        if stamp is None:
            return ClockResult(name, MISS, why)
        import datetime as _dt
        age = (_dt.datetime.strptime(as_of, "%Y-%m-%d")
               - _dt.datetime.strptime(stamp, "%Y-%m-%d")).days
        if age == 0:
            return ClockResult(name, ADVANCED, f"{what} written today ({stamp})")
        if age <= budget:
            return ClockResult(name, NOT_DUE,
                               f"{what} {age}d old (budget {budget}d) \u2014 inside cadence")
        return ClockResult(name, MISS,
                           f"{what} last written {stamp} ({age}d ago) EXCEEDS the "
                           f"{budget}d budget")
    return _c


_digest_written_weekly = _dated_surface_clock(
    "digest_written_weekly", "docs/State/performance_digest.md", DIGEST_BUDGET_DAYS,
    "digest")
"""Clock 9 (T-346): the WEEKLY PERFORMANCE DIGEST \u2014 the user's main window.

Registered because it had ZERO production callers and sat frozen at 2026-07-28: built,
verified once, and orphaned. Nothing required its registration, so nothing caught it."""

_advisor_surface_rendered = _dated_surface_clock(
    "advisor_surface_rendered", "docs/State/advisor_surface.md", ADVISOR_BUDGET_DAYS,
    "advisor surface")
"""Clock 10 (T-347): the ADVISOR MEMO \u2014 the lint's first catch, now given a CONSUMER
rather than an exemption (director ruling, 2026-08-26).

It claimed a weekly cadence, had zero production callers, and had NEVER rendered its
artifact once. A is wiring the census-independent generator on a monthly/on-change
cadence; this clock watches it from the moment it lands. Until then it reports the honest
state \u2014 "it has never rendered" \u2014 which is a true finding, not a broken clock."""


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


def _similarity_panel_refreshed(root: Path, as_of: str) -> ClockResult:
    """T-341b: the T-237 similarity panel must be REFRESHED on its cadence.

    It went 8 weeks stale with no clock at all. The clock ages the refresh RECEIPT,
    not the panel's newest decision_date, because that date conflates two states a
    census must never confuse: "no new 10-Ks were filed" (healthy — filings are
    sharply seasonal, 2026 ran Feb 408 -> Jun 5) and "the refresh never ran" (a dead
    clock). Both leave the panel unchanged. The receipt distinguishes them: a refresh
    that ran and found nothing is ADVANCED and says so.

    Budget 45d, set from the panel's OWN measured cadence (distinct decision-date
    gaps: median 2d, p95 14d, MAX 35d all-time) — clears the largest natural lull
    with margin while still catching the 53-day stall that prompted this.
    FAIL-CLOSED: missing or unparseable receipt is a MISS, never a skip."""
    rel = "data/edgar/similarity_panel_refresh.json"
    p = root / rel
    if not p.exists():
        return ClockResult("similarity_panel_refreshed", MISS,
                           f"no refresh receipt at {rel} — the panel has no clock")
    try:
        import datetime as _dt          # module-local: the file has no top-level datetime
        r = json.loads(p.read_text())
        ts = str(r.get("refreshed_at", ""))[:10]
        budget = int(r.get("budget_days", 45))
        age = (_dt.datetime.strptime(as_of, "%Y-%m-%d")
               - _dt.datetime.strptime(ts, "%Y-%m-%d")).days
    except Exception as exc:
        return ClockResult("similarity_panel_refreshed", MISS,
                           f"receipt unparseable ({type(exc).__name__}) — cannot census it")
    newest = r.get("newest_decision_date")
    if age <= budget:
        return ClockResult("similarity_panel_refreshed", ADVANCED,
                           f"refreshed {age}d ago (budget {budget}d); "
                           f"newest filing {newest}; +{r.get('rows_added', 0)} rows")
    return ClockResult("similarity_panel_refreshed", MISS,
                       f"last refresh {age}d ago EXCEEDS the {budget}d budget "
                       f"(newest filing {newest}) — the panel is going stale unnoticed")


REGISTRY: List[Clock] = (
    [Clock("analyst_note_written", _analyst_note,
           ("data/intel/analyst_notes", "data/intel/analyst_notes_agentic")),
     Clock("eval_scored_when_due", _eval_scored_when_due, ("data/intel/analyst_predictions.jsonl",)),
     Clock("news_month_pushed", _news_month_pushed, ()),
     Clock("scan_filed_when_due", _scan_filed_when_due,
           ("data/intel/thesis_scan_state.json", "data/intel/thesis_scan_provenance.jsonl")),
     Clock("stage2_clock_ticked", _stage2_ticked, ("data/state/stage2_clock.jsonl",)),
     Clock("archive_feeds_in_budget", _archive_feeds_in_budget, ()),
     Clock("similarity_panel_refreshed", _similarity_panel_refreshed,
           ("data/edgar/similarity_panel_refresh.json",)),
     Clock("exec_ledger_on_fill_days", _exec_ledger_on_fill_days,
           ("data/state/exec_cost_ledger.jsonl", "data/paper_state/orders.jsonl")),
     Clock("digest_written_weekly", _digest_written_weekly,
           ("docs/State/performance_digest.md",)),
     Clock("advisor_surface_rendered", _advisor_surface_rendered,
           ("docs/State/advisor_surface.md",)),
     # Phase-6 rung 0: "the census watches the watchmen" — a silent janitor alarms
     # like any dead feed. Budget 2d gives a nightly job one night of grace before
     # it is called a MISS.
     Clock("janitor_ran_nightly",
           _dated_surface_clock("janitor_ran_nightly", "docs/State/janitor_report.md", 2,
                                "the nightly janitor report"),
           ("docs/State/janitor_report.md",))]
    + [_rolled(n, p) for n, p in _ROLLED])

# T-346 — notes that travel WITH a clock's result. A clock can be forward-correct and
# still be guarding something nothing reads yet; deleting it would lose a real guard, and
# leaving it unannotated lets a reader assume a consumer exists. Say which, in the record.
CLOCK_NOTES: Dict[str, str] = {
    "similarity_panel_refreshed": (
        "EXEMPT-WITH-REASON from the consumer requirement: this dataset currently has NO "
        "consumer — its intended one is the T-341 filing-change flag, pending the parser "
        "repair (15.1% of filings fail the section carve; 15 tickers fully blind). The "
        "clock is forward-correct and stays: it costs nothing and the panel already went "
        "8 weeks stale once with no clock at all. Re-point this note when T-341 lands."),
    "digest_written_weekly": (
        "Registered by T-346 while the generator has ZERO production callers. Until the "
        "digest is wired into the pulse this clock reports a TRUE miss, not a false one."),
}

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


# ======================================================================================
# CADENCE REGISTRATION (T-346) — the class fix behind the orphaned digest.
#
# The digest was built, verified once, and then sat frozen for a month. Nothing was
# broken: no clock was missing an artifact, no channel was empty, no test failed. It was
# simply never CALLED, and nothing in the system required it to be registered anywhere.
# The covered-or-exempted tripwire already guards durable PATHS; this extends the same
# pattern to CONSUMERS. Any module whose own docstring claims a cadence — "runs weekly",
# "per-run", "daily" — is making a promise about a clock, and a promise nobody watches is
# how "built-with-a-cadence-but-unwatched" becomes a discovery for the next external
# review instead of a failing test.
#
# The rule: claim a cadence in your module docstring => appear HERE, mapped either to the
# clock that watches you or to an explicit reason you need no clock. Neither is a
# judgement about code quality; both are a refusal to let the claim go unexamined.
# ======================================================================================
CADENCE_SCAN_DIRS: Tuple[str, ...] = ("paper_trader", "intelligence")

CADENCE_CLAIMS: Dict[str, str] = {
    # --- watched by a registered clock ---
    "intelligence/analyst/anthropic_adapter.py": "clock:analyst_note_written",
    "intelligence/analyst/context_builder.py": "clock:analyst_note_written",
    "intelligence/analyst/eval_harness.py": "clock:eval_scored_when_due",
    "intelligence/analyst/note_schema.py": "clock:analyst_note_written",
    "intelligence/analyst/performance_digest.py": "clock:digest_written_weekly",
    "intelligence/event_call/run_forward.py": "clock:event_desk_rolled",
    "intelligence/news_panel.py": "clock:news_month_pushed",
    "intelligence/thesis_desk/thesis_desk.py": "clock:scan_filed_when_due",
    "intelligence/watchdog.py": "clock:analyst_note_written",
    "paper_trader/altdata_archive.py": "clock:archive_feeds_in_budget",
    "paper_trader/btc_shadow.py": "clock:btc_shadow_rolled",
    "paper_trader/dbmf_shadow.py": "clock:dbmf_shadow_rolled",
    "paper_trader/sleeve_tracker.py": "clock:sleeve_tracker_rolled",
    "paper_trader/clock_census.py": "clock:SELF — the census runs every pulse and its own "
                                    "absence is caught by the heartbeat's census key",
    "paper_trader/heartbeat.py": "clock:SELF — the heartbeat IS the per-run receipt every "
                                 "other clock is read out of",
    # --- no clock needed, with the reason ---
    # T-348: caught by this very lint on its author. The module claims no cadence — the
    # word appears in prose ("crying wolf daily"). The scan matches anywhere in the
    # docstring on purpose: a conservative matcher that demands an exemption line is
    # better than a clever one that misses a real claim. This is the cost, paid once.
    "paper_trader/artifact_paths.py": "exempt: a pure DECLARATION of artifact names — no "
                                      "cadence of its own, no I/O, nothing that can stall; "
                                      "the artifacts it names are clocked individually",
    "paper_trader/__init__.py": "exempt: package docstring describes the package's cadence, "
                                "not a surface of its own",
    "paper_trader/scheduler.py": "exempt: decides WHETHER today is a run day; it has no "
                                 "forward record of its own, and the pulse not running at "
                                 "all is what the dead-man's-switch alarm covers",
    "paper_trader/intel_pulse.py": "exempt: the orchestrator — every step it drives is "
                                   "individually clocked, and its own failure surfaces as "
                                   "those steps missing",
    "paper_trader/held_reconcile.py": "exempt: runs inside the trading path and is gated by "
                                      "the trading census (canonical verdict), not this one",
    "paper_trader/sleeve_constructor.py": "exempt: pure constructor — emits weights on demand, "
                                          "holds no forward record; the BOOKS it feeds are clocked",
    "paper_trader/offense_sso_constructor.py": "exempt: pure constructor, as sleeve_constructor; "
                                               "acct-2 fleet record is clocked in its own container",
    "paper_trader/econ_health.py": "exempt: read-only diagnostic over other artifacts; it "
                                   "accrues nothing that could silently stall",
    "paper_trader/paper_telemetry.py": "exempt: emits CloudWatch metrics as a side effect of "
                                       "runs that are themselves clocked; no durable record here",
    "intelligence/analyst/cost_governor.py": "exempt: a BUDGET GATE, not a forward record — its "
                                             "healthy state on a no-spend day is not advancing "
                                             "(same class as the llm_spend.jsonl exemption)",
"intelligence/analyst/advisor_surface.py": "clock:advisor_surface_rendered",
}


def cadence_claimants(root: Optional[str] = None) -> Dict[str, str]:
    """Every module whose docstring claims a cadence -> the cadence word it claimed."""
    import ast
    import re as _re
    pat = _re.compile(r"\b(weekly|daily|hourly|monthly|nightly|per[- ]run|every run|"
                      r"each run|fortnight)\b", _re.I)
    base = Path(root) if root else Path(__file__).resolve().parents[1]
    out: Dict[str, str] = {}
    for d in CADENCE_SCAN_DIRS:
        for f in sorted((base / d).rglob("*.py")):
            try:
                doc = ast.get_docstring(ast.parse(f.read_text())) or ""
            except Exception:
                continue
            m = pat.search(doc)
            if m:
                out[str(f.relative_to(base))] = m.group(0).lower()
    return out


def unregistered_cadences(root: Optional[str] = None) -> Dict[str, str]:
    """The tripwire's finding set: claims a cadence, appears in no registry entry."""
    return {k: v for k, v in cadence_claimants(root).items() if k not in CADENCE_CLAIMS}


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
        "detail": {r.name: dict({"status": r.status, "detail": r.detail},
                                 **({"note": CLOCK_NOTES[r.name]} if r.name in CLOCK_NOTES
                                    else {}))
                   for r in results},
    }


def census_line(census: Dict[str, Any]) -> str:
    """The heartbeat one-liner. Names the failing clock — a count alone isn't actionable."""
    if not census.get("degraded"):
        return (f"CLOCK-CENSUS clocks_advanced={census['clocks_advanced']} "
                f"not_due={census['n_not_due']} — all clocks running")
    names = ", ".join(m["clock"] for m in census["missed"])
    return (f"[CLOCK-CENSUS][ALERT] clocks_advanced={census['clocks_advanced']} "
            f"MISSED: {names}")


# ======================================================================================
# CHANNEL LIVENESS (T-342) — the class fix behind the shadow book's 14 dark days.
#
# The census above asks "did this clock ADVANCE today?". That question is blind to a
# different failure: a consumer that runs perfectly every day while the field it consumes
# has NEVER ONCE been non-empty. The llm_shadow_book spent 14 days honestly reporting
# action:'applied' over a structurally empty `hypothetical_actions` — applying nothing IS
# applying the note, so every clock ticked, every record was truthful, and the channel was
# dead the whole time.
#
# E's rule is the charter: AN ALWAYS-EMPTY CHANNEL DEGRADES NOTHING, so no freshness gate,
# no clock, and no daily assertion can see it. Only an EXISTENCE-OVER-HISTORY assertion can:
#   "has this load-bearing field EVER been non-empty, across its entire observed history?"
#
# Fail-closed in spirit: a channel we cannot verify is FLAGGED, never assumed alive.
# Read-only, like the census.
# ======================================================================================
LIVE, NEVER_ALIVE, UNVERIFIABLE, NO_HISTORY = "LIVE", "NEVER_ALIVE", "UNVERIFIABLE", "NO_HISTORY"


@dataclass
class Channel:
    """One load-bearing consumed field, declared BY ITS CONSUMER."""
    name: str                                    # the field, e.g. "hypothetical_actions"
    consumer: str                                # who breaks if it is dead
    check: Callable[[Path], Tuple[str, str]]     # -> (status, detail); scans ALL history


def _scan_dir_field(rel_dir: str, field: str, sub: Optional[str] = None):
    """Has `field` EVER been non-empty across every file in a per-day directory?"""
    def _c(root: Path) -> Tuple[str, str]:
        d = root / rel_dir
        if not d.exists():
            return UNVERIFIABLE, f"source dir missing: {rel_dir} (cannot establish liveness)"
        files = sorted(d.glob("*.json"))
        if not files:
            return NO_HISTORY, f"no records yet in {rel_dir} — nothing to assert"
        n_seen, n_nonempty, bad = 0, 0, 0
        for f in files:
            try:
                rec = json.loads(f.read_text())
            except Exception:
                bad += 1
                continue
            n_seen += 1
            vals = rec.get(field)
            if sub and isinstance(vals, list):
                vals = [v for v in vals if isinstance(v, dict) and v.get(sub)]
            if vals:
                n_nonempty += 1
        if n_seen == 0:
            return UNVERIFIABLE, f"{bad} record(s) in {rel_dir} but none parseable"
        if n_nonempty == 0:
            return NEVER_ALIVE, (f"'{field}' EMPTY in all {n_seen} record(s) of its entire "
                                 f"observed history — channel never non-empty; "
                                 f"VERIFY UPSTREAM INTENT")
        return LIVE, f"'{field}' non-empty in {n_nonempty}/{n_seen} record(s)"
    return _c


def _scan_jsonl_field(rel: str, field: str):
    """Has `field` EVER been non-empty across every row of a jsonl ledger?"""
    def _c(root: Path) -> Tuple[str, str]:
        p = root / rel
        if not p.exists():
            return UNVERIFIABLE, f"source missing: {rel} (cannot establish liveness)"
        n_seen = n_nonempty = 0
        try:
            for line in p.read_text().splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                n_seen += 1
                if rec.get(field):
                    n_nonempty += 1
        except Exception:
            return UNVERIFIABLE, f"unparseable: {rel}"
        if n_seen == 0:
            return NO_HISTORY, f"no rows yet in {rel} — nothing to assert"
        if n_nonempty == 0:
            return NEVER_ALIVE, (f"'{field}' EMPTY in all {n_seen} row(s) of its entire "
                                 f"observed history — channel never non-empty; "
                                 f"VERIFY UPSTREAM INTENT")
        return LIVE, f"'{field}' non-empty in {n_nonempty}/{n_seen} row(s)"
    return _c


# THE CHANNEL REGISTRY — declared per consumer. A consumer that reads a load-bearing
# field registers it here, so "my input has never carried anything" becomes visible.
CHANNELS: List[Channel] = [
    Channel("hypothetical_actions", "llm_shadow_book",
            _scan_dir_field("data/intel/analyst_notes", "hypothetical_actions")),
    Channel("hypothetical_actions", "llm_shadow_book(agentic)",
            _scan_dir_field("data/intel/analyst_notes_agentic", "hypothetical_actions")),
    Channel("predictions", "eval_harness",
            _scan_dir_field("data/intel/analyst_notes", "predictions")),
    Channel("event_calls", "event_shadow_book",
            _scan_jsonl_field("data/intel/event_calls.jsonl", "symbol")),
    Channel("thesis_calls", "thesis_book",
            _scan_jsonl_field("data/intel/thesis_calls.jsonl", "instruments")),
]


def channel_liveness(root: Optional[str] = None) -> Dict[str, Any]:
    """Assert every declared load-bearing channel has EVER been non-empty. READ-ONLY.

    Distinct from the clock census by design: a clock can tick perfectly forever while its
    input channel is dead. Only this existence-over-history assertion sees that."""
    base = Path(root) if root else Path(__file__).resolve().parents[1]
    results = []
    for ch in CHANNELS:
        try:
            status, detail = ch.check(base)
        except Exception as exc:                 # a raising check is UNVERIFIABLE, not alive
            status, detail = UNVERIFIABLE, f"check raised {type(exc).__name__}"
        results.append({"channel": ch.name, "consumer": ch.consumer,
                        "status": status, "detail": detail})
    dead = [r for r in results if r["status"] == NEVER_ALIVE]
    unver = [r for r in results if r["status"] == UNVERIFIABLE]
    return {"_schema": "channel_liveness/v1",
            "n_channels": len(results), "n_live": sum(1 for r in results if r["status"] == LIVE),
            "n_never_alive": len(dead), "n_unverifiable": len(unver),
            "n_no_history": sum(1 for r in results if r["status"] == NO_HISTORY),
            # a dead OR unverifiable channel is a FINDING — never assumed benign
            "findings": dead + unver,
            "degraded": bool(dead or unver),
            "detail": results}


def liveness_line(live: Dict[str, Any]) -> str:
    if not live.get("degraded"):
        return (f"CHANNEL-LIVENESS {live['n_live']}/{live['n_channels']} live "
                f"({live['n_no_history']} awaiting first record) — all consumed channels alive")
    names = ", ".join(f"{f['consumer']}:{f['channel']}" for f in live["findings"])
    return (f"[CHANNEL-LIVENESS][ALERT] {live['n_never_alive']} never-alive / "
            f"{live['n_unverifiable']} unverifiable — {names}")
