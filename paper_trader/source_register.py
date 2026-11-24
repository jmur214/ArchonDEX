# paper_trader/source_register.py
"""The information-source register (T-412; T-411 Part 5, component C1).

WHY. T-411 found the system's information did not reach the books built to use it, in
three silent ways: a file that is in no container (the 8-K panel), a file read BEFORE the
step that brings it into the container (the alt-data the eval harness reads), and a
reader nobody feeds. Each read as a plausible quiet day — "0 documents", "0 of 59
resolved", "no source yet" — because nothing checked, at the moment a reader ran, whether
its input had arrived.

WHAT. One declaration of every information source the daily run consumes: where it
lives (relative to the run's root), which step brings it into the container, which
readers consume it, and how its freshness is judged. On each run the driver tells the
register when an ARRIVAL step ran and when each READER ran; at the reader's call site the
register probes the source on disk (present? rows? newest date? fresh?). At the tail it
probes again, so a source that was absent or stale when read but present and fresh by the
end is named for what it is — READ BEFORE ARRIVAL, the step-order defect.

VERDICTS, per (source, reader): fresh | absent | empty | stale | undated |
read_before_arrival | not_run | retired. Anything but fresh/retired is a ``degraded``
reason, never a silent pass. A declared-retired source (its writer stopped, stated with a
reason) is listed every run, not flagged — the census's expected-dormant allowlist, in
this register's terms.

A SEPARATE CHANNEL. The block rides the heartbeat as ``source_register`` and fires the
notify path when degraded. It never touches the trading verdict (``canonical``): an input
that did not reach a report-only reader is an information-path finding, not an
operational failure of the trading run.

READ-ONLY: the register observes; it never fetches, repairs or writes a source.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FRESH, ABSENT, EMPTY, STALE, UNDATED = "fresh", "absent", "empty", "stale", "undated"
READ_BEFORE_ARRIVAL, NOT_RUN, RETIRED = "read_before_arrival", "not_run", "retired"
_OK_VERDICTS = frozenset({FRESH, RETIRED})

# The arrival steps the driver reports (one name per step that brings a source in).
DURABLE_PULL = "durable_pull"                    # cloud.pull() — DURABLE_PATHS / DIRS
ALTDATA_PULL = "altdata_pull"                    # cloud.pull_altdata() — the alt-data hoard
EDGAR_8K_FETCH = "edgar_8k_fetch"                # altdata_archive.run_8k_feed()
NEWS_RECENT_PULL = "news_recent_pull"            # cloud.pull_news_recent()
CROSS_ACCOUNT_NOTE_PULL = "cross_account_note_pull"   # cloud.pull_readonly_from() (acct 3)

# The readers (one name per call site in scripts/run_paper_cloud_day.py).
EVAL_HARNESS = "eval_harness"
EVENT_DESK = "event_desk"
THESIS_BOOK = "thesis_book"
LLM_SHADOW = "llm_shadow_book"
LLM_SHADOW_AGENTIC = "llm_shadow_book_agentic"
INTEL_PULSE = "intel_pulse"
LLM_ANALYST_CONSTRUCTOR = "llm_analyst_constructor"

ACCOUNT_1, ACCOUNT_3 = "trend_sleeve", "llm_analyst"


@dataclass(frozen=True)
class Source:
    """One information source a daily run consumes.

    ``kind`` says how it is probed: ``parquet`` (rows + newest ``date_field``), ``jsonl``
    (rows + newest ``date_field``), ``note_dir`` (per-day JSON notes; newest date from the
    filename), ``news_dir`` (month partitions; newest ``created_at``). ``max_age_days``
    None = presence-only (an append-only ledger may rightly gain nothing on a quiet day)."""
    id: str
    rel: str
    kind: str
    readers: Tuple[str, ...]
    arrives_by: Tuple[str, ...]
    strategies: Tuple[str, ...]
    date_field: Optional[str] = None
    max_age_days: Optional[int] = None
    retired: Optional[str] = None
    note: str = ""
    # A LATER step of the same run appends to this source by design (the event ledger is
    # written by the interpreter after the desk reads yesterday's calls; the news month by
    # step 8). Absent at the read and created by that writer is ABSENT — the reader had
    # nothing — never "read before arrival", which would wrongly say "move a sync".
    same_run_writer: Optional[str] = None

    def freshness_rule(self) -> str:
        if self.retired:
            return "retired"
        if self.max_age_days is None:
            return "present and non-empty"
        return f"newest {self.date_field or 'date'} within {self.max_age_days}d of the run date"


# THE REGISTER. Budgets reuse the T-335 feed budgets (paper_trader/altdata_archive.py
# _FEED_HEALTH) where the same file is gated there; a tripwire test keeps them in step.
SOURCES: Tuple[Source, ...] = (
    Source("kxfed_snapshots", "data/macro_data/alt/kalshi_kxfed_snapshots.parquet", "parquet",
           readers=(EVAL_HARNESS, THESIS_BOOK), arrives_by=(ALTDATA_PULL,),
           strategies=(ACCOUNT_1,), date_field="snap_date", max_age_days=4,
           note="kalshi_settlement resolutions + the market-implied baseline; "
                "falsifier resolution"),
    Source("fred_rate_path", "data/macro_data/alt/fred_rate_path.parquet", "parquet",
           readers=(EVAL_HARNESS, THESIS_BOOK, INTEL_PULSE), arrives_by=(ALTDATA_PULL,),
           strategies=(ACCOUNT_1,), date_field="observation_date", max_age_days=7,
           note="FOMC/KXFED settlement; the agentic query_rate_path tool; the scan context"),
    Source("edgar_8k_items", "data/macro_data/alt/edgar_8k_items.parquet", "parquet",
           readers=(INTEL_PULSE,), arrives_by=(ALTDATA_PULL, EDGAR_8K_FETCH),
           strategies=(ACCOUNT_1,), date_field="filing_date", max_age_days=5,
           note="the event interpreter's forward 8-K feed (T-412)"),
    Source("news_panel", "data/intel/news_panel", "news_dir",
           readers=(INTEL_PULSE,), arrives_by=(NEWS_RECENT_PULL,),
           strategies=(ACCOUNT_1,), date_field="created_at", max_age_days=4,
           same_run_writer="step 8 news append",
           note="the analyst bundle, the agentic query_news tool, the scan's tape"),
    Source("analyst_notes", "data/intel/analyst_notes", "note_dir",
           readers=(EVAL_HARNESS, LLM_SHADOW), arrives_by=(DURABLE_PULL,),
           strategies=(ACCOUNT_1,), date_field="as_of", max_age_days=4,
           same_run_writer=INTEL_PULSE),
    Source("analyst_notes_agentic", "data/intel/analyst_notes_agentic", "note_dir",
           readers=(EVAL_HARNESS, LLM_SHADOW_AGENTIC), arrives_by=(DURABLE_PULL,),
           strategies=(ACCOUNT_1,), date_field="as_of", max_age_days=4,
           same_run_writer=INTEL_PULSE),
    Source("event_calls", "data/intel/event_calls.jsonl", "jsonl",
           readers=(EVENT_DESK, EVAL_HARNESS), arrives_by=(DURABLE_PULL,),
           strategies=(ACCOUNT_1,), date_field="note_date", same_run_writer=INTEL_PULSE,
           note="the event interpreter's ledger; presence-only — a quiet filing day adds no row"),
    Source("thesis_calls", "data/intel/thesis_calls.jsonl", "jsonl",
           readers=(THESIS_BOOK,), arrives_by=(DURABLE_PULL,),
           strategies=(ACCOUNT_1,), date_field="as_of", same_run_writer=INTEL_PULSE,
           note="presence-only — the weekly scan files theses, most days add none"),
    Source("special_situations", "data/research/special_situations/events.parquet", "parquet",
           readers=(INTEL_PULSE,), arrives_by=(), strategies=(ACCOUNT_1,),
           retired=("watcher stopped 2026-07-02 (11-14 audit); in no image and no sync, so "
                    "context_builder and eightk_feed read nothing from it (T-411 Part 3 "
                    "row 7). Un-retire with a writer AND a sync.")),
    Source("analyst_notes_from_account_1", "data/intel/analyst_notes", "note_dir",
           readers=(LLM_ANALYST_CONSTRUCTOR,), arrives_by=(CROSS_ACCOUNT_NOTE_PULL,),
           strategies=(ACCOUNT_3,), date_field="as_of", max_age_days=4,
           note="account 3 trades yesterday's account-1 note, pulled read-only"),
)

# Sources the system COLLECTS that no daily-run code reads (T-411 Part 3 rows 10-22).
# Listed every run so the keep-or-retire choice stays in view; never a degraded reason.
UNREAD_SOURCES: Tuple[Tuple[str, str, str], ...] = (
    ("kalshi_macro_snapshots", "data/macro_data/alt/kalshi_snapshots.parquet", "row 10"),
    ("polymarket_snapshots", "data/macro_data/alt/polymarket_snapshots.parquet", "row 11"),
    ("polymarket_resolutions", "data/macro_data/alt/polymarket_resolutions.parquet", "row 12"),
    ("edgar_form4_index", "data/macro_data/alt/edgar_form4_index.parquet", "row 13"),
    ("epu_daily", "data/macro_data/alt/epu_daily_us.parquet", "row 14"),
    ("gpr_daily", "data/macro_data/alt/gpr_daily_recent.parquet", "row 15 (laptop only)"),
    ("usaspending_awards", "data/macro_data/alt/usaspending_awards.parquet", "row 16"),
    ("credit_spread_oas", "data/macro_data/alt/credit_spread_oas.parquet", "row 17 (laptop only)"),
    ("finra_regsho_short_volume", "data/positioning/finra_regsho_short_volume.parquet", "row 18"),
    ("finra_short_interest", "data/positioning/finra_short_interest.parquet", "row 19"),
    ("sec_ftd", "data/positioning/sec_ftd.parquet", "row 20"),
    ("finra_margin_debt", "data/positioning/finra_margin_debt.parquet", "row 21 (laptop only)"),
    ("naaim_exposure", "data/positioning/naaim_exposure.parquet", "row 22 (collector broken)"),
)

_DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")


# --------------------------------------------------------------------------------------
# probes (read-only; every failure is a stated state, never an exception)
# --------------------------------------------------------------------------------------
def _parquet_rows_and_newest(p: Path, col: Optional[str]) -> Tuple[int, Optional[str], str]:
    import pyarrow.parquet as pq
    f = pq.ParquetFile(p)
    n = int(f.metadata.num_rows)
    if not col:
        return n, None, "ok"
    if col not in set(f.schema_arrow.names):
        return n, None, f"no {col} column"
    from paper_trader.altdata_archive import _newest     # the T-335 date parser, reused
    newest = _newest(p, col, "iso")
    if newest is None or newest != newest:                # None or NaT
        return n, None, f"{col} unparseable"
    return n, str(newest)[:10], "ok"


def _jsonl_rows_and_newest(p: Path, col: Optional[str]) -> Tuple[int, Optional[str], str]:
    n, newest = 0, None
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        n += 1
        if col:
            try:
                d = str(json.loads(line).get(col) or "")[:10]
            except Exception:
                continue
            if _DATE_IN_NAME.fullmatch(d) and (newest is None or d > newest):
                newest = d
    return n, newest, "ok"


def _note_dir_rows_and_newest(d: Path) -> Tuple[int, Optional[str], str]:
    from paper_trader.artifact_paths import ANALYST_NOTE
    files = {f for pat in ANALYST_NOTE.globs() for f in d.rglob(pat) if f.is_file()}
    dates = [m.group(1) for f in files for m in [_DATE_IN_NAME.search(f.name)] if m]
    return len(files), (max(dates) if dates else None), "ok"


def _news_dir_rows_and_newest(d: Path) -> Tuple[int, Optional[str], str]:
    import pyarrow.parquet as pq
    parts = sorted(d.glob("news_*.parquet"))[-2:]        # the two newest months suffice
    n, newest = 0, None
    for p in parts:
        t = pq.read_table(p, columns=["created_at"]).column("created_at").to_pylist()
        n += len(t)
        stamps = [str(v)[:10] for v in t if v is not None]
        if stamps:
            newest = max(newest or "", max(stamps))
    return n, newest, "ok"


def probe(src: Source, root: Path, as_of: str) -> Dict[str, Any]:
    """The state of one source on disk right now. Never raises."""
    p = Path(root) / src.rel
    out: Dict[str, Any] = {"present": False, "n": 0, "newest": None, "age_days": None,
                           "fresh": False, "why": ""}
    try:
        if src.kind in ("note_dir", "news_dir"):
            if not p.is_dir():
                return {**out, "why": "directory absent"}
            n, newest, why = (_note_dir_rows_and_newest(p) if src.kind == "note_dir"
                              else _news_dir_rows_and_newest(p))
        else:
            if not p.is_file():
                return {**out, "why": "file absent"}
            n, newest, why = (_parquet_rows_and_newest(p, src.date_field)
                              if src.kind == "parquet"
                              else _jsonl_rows_and_newest(p, src.date_field))
    except Exception as exc:                               # unreadable is a state, not a crash
        return {**out, "present": p.exists(), "why": f"unreadable ({type(exc).__name__})"}
    out.update(present=True, n=int(n), newest=newest, why=why)
    if newest:
        try:
            out["age_days"] = (_dt.date.fromisoformat(as_of[:10])
                               - _dt.date.fromisoformat(newest)).days
        except ValueError:
            out["age_days"] = None
    if src.max_age_days is None:
        out["fresh"] = n > 0
    else:
        out["fresh"] = (n > 0 and out["age_days"] is not None
                        and out["age_days"] <= src.max_age_days)
    return out


def _verdict(src: Source, at_read: Optional[Dict[str, Any]],
             at_tail: Dict[str, Any]) -> str:
    if src.retired:
        return RETIRED
    if at_read is None:
        return NOT_RUN
    late = at_tail["fresh"] and not src.same_run_writer   # fresh only after the read, and
    if not at_read["present"]:                             # no same-run writer explains it
        return READ_BEFORE_ARRIVAL if late else ABSENT
    if at_read["n"] == 0:
        return READ_BEFORE_ARRIVAL if late else EMPTY
    if not at_read["fresh"]:
        if late:
            return READ_BEFORE_ARRIVAL                    # it became fresh after the read
        return UNDATED if src.max_age_days is not None and at_read["age_days"] is None else STALE
    return FRESH


# --------------------------------------------------------------------------------------
# the per-run register
# --------------------------------------------------------------------------------------
class SourceRegister:
    """One run's observations. The driver calls ``arrived()`` after each arrival step,
    ``read()`` immediately before each reader runs, optionally ``outcome()`` after it, and
    ``block()`` at the tail. Every method is no-raise: the register must never be able to
    break the run it watches."""

    def __init__(self, root: str | Path, strategy: str, as_of: str,
                 sources: Tuple[Source, ...] = SOURCES) -> None:
        self.root = Path(root)
        self.strategy = strategy
        self.as_of = str(as_of)[:10]
        self.sources = tuple(s for s in sources if strategy in s.strategies)
        self._arrivals: Dict[str, Dict[str, Any]] = {}
        self._reads: Dict[str, Dict[str, Any]] = {}
        self._outcomes: Dict[str, Dict[str, Any]] = {}
        self._seq = 0

    def _tick(self) -> int:
        self._seq += 1
        return self._seq

    def arrived(self, step: str, ok: bool, detail: str = "") -> None:
        """An arrival step ran (``ok`` = it did what it is for)."""
        try:
            self._arrivals[step] = {"ok": bool(ok), "detail": str(detail)[:300],
                                    "seq": self._tick()}
        except Exception:
            pass

    def read(self, reader: str) -> None:
        """``reader`` is about to read its sources: probe each, now."""
        try:
            self._reads[reader] = {
                "seq": self._tick(),
                "probes": {s.id: probe(s, self.root, self.as_of)
                           for s in self.sources if reader in s.readers}}
        except Exception:
            pass

    def outcome(self, reader: str, detail: Dict[str, Any],
                problem: Any = None) -> None:
        """What the reader made of its input. ``problem`` — a string or a list of them — is
        a degraded reason. "The input was there" is not "the path works": a reader that
        raised, refused, or produced nothing from fresh input reports it here (T-412
        review: 14 of 14 reads were fresh while the eval and the pulse both raised)."""
        try:
            probs = [problem] if isinstance(problem, str) else list(problem or [])
            prev = self._outcomes.get(reader) or {"detail": {}, "problems": []}
            self._outcomes[reader] = {"detail": {**prev["detail"], **(detail or {})},
                                      "problems": prev["problems"] + probs}
        except Exception:
            pass

    def raised(self, reader: str, exc: BaseException) -> None:
        """``reader`` raised: whatever it was fed, it produced nothing."""
        self.outcome(reader, {"raised": type(exc).__name__},
                     problem=f"raised {type(exc).__name__}: {str(exc)[:120]}")

    def block(self) -> Dict[str, Any]:
        """The heartbeat block. Re-probes every source at the tail. Never raises."""
        try:
            return self._block()
        except Exception as exc:                      # a broken register says so, loudly
            return {"_schema": "source_register/v1", "as_of": self.as_of,
                    "strategy": self.strategy, "degraded": True, "failed": True,
                    "n_sources": None, "n_problems": 1,
                    "problems": [f"the register itself failed: {type(exc).__name__}: {exc}"]}

    def _block(self) -> Dict[str, Any]:
        problems: List[str] = []
        sources: Dict[str, Any] = {}
        n_reads = n_fresh = 0
        for s in self.sources:
            tail = probe(s, self.root, self.as_of)
            reads: Dict[str, Any] = {}
            for r in s.readers:
                at_read = (self._reads.get(r) or {}).get("probes", {}).get(s.id)
                v = _verdict(s, at_read, tail)
                reads[r] = {"verdict": v, "at_read": at_read}
                if s.retired:
                    continue
                n_reads += 1
                n_fresh += v == FRESH
                if v not in _OK_VERDICTS:
                    why = (at_read or {}).get("why") or ""
                    problems.append(f"{s.id} -> {r}: {v}"
                                    + (f" ({why})" if why and why != "ok" else "")
                                    + (f" [newest {at_read['newest']}, "
                                       f"{at_read['age_days']}d]"
                                       if at_read and at_read.get("newest") else ""))
            arrivals = {}
            for step in s.arrives_by:
                a = self._arrivals.get(step)
                arrivals[step] = a
                if s.retired:
                    continue
                if a is None:
                    problems.append(f"{s.id}: its arrival step {step} did not run")
                elif not a["ok"]:
                    problems.append(f"{s.id}: its arrival step {step} FAILED"
                                    + (f" ({a['detail']})" if a["detail"] else ""))
            sources[s.id] = {"rel": s.rel, "kind": s.kind, "freshness": s.freshness_rule(),
                             "arrives_by": arrivals, "at_tail": tail, "reads": reads,
                             **({"retired": s.retired} if s.retired else {}),
                             **({"same_run_writer": s.same_run_writer}
                                if s.same_run_writer else {}),
                             **({"note": s.note} if s.note else {})}
        declared_readers = sorted({r for s in self.sources for r in s.readers})
        readers = {r: {"ran": r in self._reads,
                       **({"outcome": self._outcomes[r]["detail"]}
                          if r in self._outcomes else {})}
                   for r in declared_readers}
        problems = [f"{r}: {p}" for r, o in sorted(self._outcomes.items())
                    for p in o["problems"]] + problems      # what broke, before what was read
        unread = {sid: {"rel": rel, "present": (self.root / rel).exists(),
                        "why_unread": f"no daily-run consumer (T-411 Part 3 {row})"}
                  for sid, rel, row in UNREAD_SOURCES} if self.strategy == ACCOUNT_1 else {}
        return {"_schema": "source_register/v1", "as_of": self.as_of,
                "strategy": self.strategy, "degraded": bool(problems),
                "n_sources": len(self.sources), "n_reads": n_reads, "n_fresh": n_fresh,
                "problems": problems[:20], "n_problems": len(problems),
                "readers": readers, "sources": sources, "unread_collected": unread}


# --------------------------------------------------------------------------------------
# judging a reader's outcome (pure functions; the driver feeds the result to outcome())
# --------------------------------------------------------------------------------------
#: Of the documents the event interpreter looked at, the shares that count as a problem.
MAX_NO_BODY_SHARE = 0.25
MAX_INVALID_SHARE = 0.50


def event_interpreter_problems(ev: Any) -> List[str]:
    """Why the event interpreter's day was not whole. Anything but status ``ok`` is a
    problem (a raise, a refusal, no model key, a missing panel), and so is an ``ok`` day
    that read documents and interpreted none, was refused its budget, or ran out of room."""
    if not isinstance(ev, dict) or not ev:
        return ["event interpreter returned nothing"]
    out: List[str] = []
    status, reason = str(ev.get("status") or "unknown"), ev.get("reason")
    if status != "ok":
        out.append(f"event interpreter {status}" + (f": {reason}" if reason else ""))
    feed = ev.get("feed") or {}
    if feed and not feed.get("ok") and str(feed.get("reason")) != str(reason):
        out.append(f"event interpreter's 8-K feed: {feed.get('reason')}")
    if feed.get("n_bad_dates"):
        out.append(f"event interpreter's 8-K feed: {feed['n_bad_dates']} row(s) with an "
                   f"unparseable filing date")

    def n(k: str) -> int:
        return int(ev.get(k) or 0)
    docs, looked = n("n_documents"), n("n_documents") - n("n_deferred")
    if docs and not n("n_ok"):
        out.append(f"event interpreter read {docs} document(s) and interpreted none "
                   f"(no body {n('n_no_body')}, invalid {n('n_invalid')}, refused "
                   f"{n('n_skipped')}, deferred {n('n_deferred')})")
    elif looked > 0:
        if n("n_no_body") / looked > MAX_NO_BODY_SHARE:
            out.append(f"event interpreter: no filing body for {n('n_no_body')} of {looked} "
                       f"document(s) (threshold {MAX_NO_BODY_SHARE:.0%})")
        if n("n_invalid") / looked > MAX_INVALID_SHARE:
            out.append(f"event interpreter: {n('n_invalid')} of {looked} replies invalid "
                       f"(threshold {MAX_INVALID_SHARE:.0%})")
    if n("n_skipped"):
        out.append(f"event interpreter: {n('n_skipped')} call(s) refused or failed "
                   f"(budget, kill switch or model error)")
    if n("n_deferred"):
        out.append(f"event interpreter: {n('n_deferred')} of {docs} document(s) deferred to "
                   f"the next run")
    return out


def register_line(block: Dict[str, Any]) -> str:
    """The run-log one-liner. Names the problem — a count alone is not actionable."""
    if block.get("n_sources") is None:       # it could not be built, or it failed itself
        return ("[SOURCE-REGISTER][DEGRADED] the register FAILED — information paths "
                "UNVERIFIED: " + " | ".join(map(str, block.get("problems") or ["no reason"])))
    if not block["n_sources"] and not block.get("degraded"):
        return (f"SOURCE-REGISTER no declared information sources for "
                f"{block.get('strategy')} (prices only)")
    head = (f"SOURCE-REGISTER fresh_reads={block.get('n_fresh')}/{block.get('n_reads')} "
            f"sources={block.get('n_sources')}")
    if not block.get("degraded"):
        return head + " — every declared reader ran after its data arrived"
    return (f"[SOURCE-REGISTER][DEGRADED] {head} — {block.get('n_problems')} problem(s): "
            + " | ".join(block.get("problems", [])[:4]))
