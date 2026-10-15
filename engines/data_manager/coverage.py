"""The stale/holed-files guard (adopted 2026-10-15; docs/Sources/proposal_stale_and_holed_files_guard_2026-10-15.md).

Coverage counts BARS, never file presence. The pre-T-167 global-median×3 band, applied at WRITE time,
ended 33 live files early (28 at their all-time highs) and holed 114 more; every count the system had
was a count of FILES or FRAMES (`discover_cached_tickers` admits by row count; the run census's
`n_resolved` / `n_in_panel` count frames; B-1's `coverage_pct` counted a file on disk), so none of it
showed. This module is the ONE function both census producers call, so they cannot drift; the gate
and the measured-run admission read its record through ONE reader (`core.census.coverage_defects`).

R's binding correction: the END test runs PER NAME against the EARLIER of the window end and the
member's exit — a name that left the index is required to have bars up to its exit, not to the
window end; a name that is still a member (or is outside the membership — the essential ETFs, a
static list) is required to the window end. Holes are counted only where the name was required to
trade: inside its membership in the window, inside the span its file covers.

THE CALENDAR: the dates on which a MAJORITY of the names active that day have a bar (data-derived; no
holiday table, no new dependency). It is PROVEN against SPY in both directions before any count is
trusted: a majority day SPY lacks inside SPY's own span is a holed SPY; a day SPY has that the
majority lacks is a holed CALENDAR (a mass hole the majority cannot see — on the real cache
1999-11-16, which 244 of 248 active files lack). Either fails the gate; so does a run with no SPY to
check against. SPY's own early END is SPY's per-name stale entry, never a calendar hole.

DECLARATIONS (`config/data_gaps.json`) excuse exactly what they declare, facet by facet:
  * `holed_inside` — runs of missing trading days `[[lo, hi], …]` inside the file's span that no
    provider can fill. A missing day is excused only if it falls inside a declared run; any other
    hole is undeclared.
  * `ends_at_delisting` — `{"last_bar": date}`: the file's last bar is the security's last print.
    It excuses an early END only when the file's last bar IS that date. It never excuses a hole, and
    a `holed_inside` declaration never excuses an early end.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_GAPS_PATH = ROOT / "config" / "data_gaps.json"
#: A file may end this many trading days before its required end (a genuine exit's last prints, a
#: holiday at the edge) — A found genuine exits ending days before the recorded exit (CTXS, TWTR, IPG).
#: A longer gap between a delisting's last print and the index's recorded exit is DECLARED
#: (`ends_at_delisting`), never absorbed by widening this (JNPR: last print 2025-07-01, exit 07-09).
END_SLACK_DAYS = 5
#: Missing trading days tolerated per name beyond the calendar: 0 (R and the director, 2026-10-15). A
#: real halt or a single provider gap is a fact to DECLARE in `config/data_gaps.json`, not tolerate.
HOLE_TOLERANCE = 0
MAJORITY = 0.5
FORMATION_FLOOR = 0.80
CALENDAR_REFERENCE = "SPY"
DECLARATION_FACETS = ("holed_inside", "ends_at_delisting")


def load_data_gaps(path: Path = DATA_GAPS_PATH) -> Dict[str, dict]:
    """The declared data gaps, validated. An absent file means no declarations; a malformed one
    RAISES (a declaration that cannot be read must never excuse anything — fail closed). Each entry
    carries `reason` and `source` and at least one facet of `DECLARATION_FACETS`."""
    path = Path(path)
    if not path.exists():
        return {}
    decls = json.loads(path.read_text()).get("declarations", {})
    for t, d in decls.items():
        facets = [f for f in DECLARATION_FACETS if f in d]
        if not facets or not d.get("reason") or not d.get("source"):
            raise ValueError(f"data_gaps[{t}]: needs reason, source and one of {DECLARATION_FACETS}")
        for lo, hi in _runs(d):
            if lo > hi:
                raise ValueError(f"data_gaps[{t}]: run {lo.date()}..{hi.date()} is reversed")
        if "ends_at_delisting" in d:
            pd.Timestamp(d["ends_at_delisting"]["last_bar"])
    return decls


def _runs(decl: dict) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    return [(pd.Timestamp(lo), pd.Timestamp(hi))
            for lo, hi in (decl.get("holed_inside") or {}).get("runs", [])]


def _dates(df: pd.DataFrame) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(pd.to_datetime(df.index))
    return idx.tz_localize(None) if idx.tz is not None else idx


def majority_calendar(data_map: Dict[str, pd.DataFrame], start: pd.Timestamp,
                      end: pd.Timestamp, share: float = MAJORITY) -> pd.DatetimeIndex:
    """Trading days in [start, end]: dates on which at least `share` of the names ACTIVE that day
    (first bar ≤ date ≤ last bar) have a bar."""
    idxs = {t: _dates(df) for t, df in data_map.items() if df is not None and len(df)}
    if not idxs:
        return pd.DatetimeIndex([])
    all_dates = pd.DatetimeIndex(sorted(set().union(*[set(i) for i in idxs.values()])))
    all_dates = all_dates[(all_dates >= start) & (all_dates <= end)]
    have = pd.Series(0, index=all_dates)
    active = pd.Series(0, index=all_dates)
    for i in idxs.values():
        lo, hi = i.min(), i.max()
        active[(all_dates >= lo) & (all_dates <= hi)] += 1
        have[all_dates.isin(i)] += 1
    keep = (active > 0) & (have >= share * active)
    return pd.DatetimeIndex(all_dates[keep.values])


def _required_spans(ticker: str, start: pd.Timestamp, end: pd.Timestamp,
                    intervals: Optional[pd.DataFrame]) -> Tuple[list, Optional[pd.Timestamp], bool]:
    """The [lo, hi] spans inside the window where the name was REQUIRED to trade, its required end,
    and whether it left the index inside the window (`exited`). Outside the membership → the whole
    window, required to the window end."""
    if intervals is None or ticker not in set(intervals["ticker"]):
        return [(start, end)], end, False
    rows = intervals[intervals["ticker"] == ticker]
    spans = []
    for s, e in zip(rows["start"], rows["end"]):
        lo = max(pd.Timestamp(s), start)
        hi = end if pd.isna(e) else min(pd.Timestamp(e), end)
        if lo <= hi:
            spans.append((lo, hi))
    if not spans:
        return [], None, False
    req_end = max(hi for _, hi in spans)
    return spans, req_end, req_end < end


def _longest_run(missing: List[pd.Timestamp], cal: pd.DatetimeIndex) -> int:
    if not missing:
        return 0
    pos = np.searchsorted(cal.values, pd.DatetimeIndex(sorted(missing)).values)
    run = longest = 1
    for a, b in zip(pos[:-1], pos[1:]):
        run = run + 1 if b == a + 1 else 1
        longest = max(longest, run)
    return longest


def stale_files_record(data_map: Dict[str, pd.DataFrame], start, end, *,
                       intervals: Optional[pd.DataFrame] = None,
                       declared: Optional[Dict[str, dict]] = None,
                       formation_dates: Optional[Iterable] = None) -> dict:
    """The `stale_files` census block. Per name: first/last bar, the REQUIRED end (the earlier of
    the window end and the member's exit), `ends_before_required` (stale), missing trading days
    inside the required spans (holes) and how many of them no declaration covers, the longest run,
    and the declared facets. Plus the calendar's proof against SPY and `formation_coverage` — rows
    FORMED on each formation date, never a file on disk."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    declared = load_data_gaps() if declared is None else declared
    cal = majority_calendar(data_map, start, end)
    names: Dict[str, dict] = {}
    n_stale = n_holed = n_declared = n_exits = 0
    pre = {}                                   # per name, once: its bar dates and required spans
    for t, df in data_map.items():
        if df is None or not len(df):
            continue
        idx = _dates(df)
        pre[t] = (idx, set(idx), _required_spans(t, start, end, intervals))
    for t in sorted(pre):
        idx, present, (spans, req_end, exited) = pre[t]
        if req_end is None:          # no membership inside the window: nothing was required of it
            continue
        n_exits += int(exited)
        last = idx.max()
        req_end_cal = cal[cal <= req_end]
        stale = not (len(req_end_cal) == 0
                     or last >= req_end_cal[-min(END_SLACK_DAYS, len(req_end_cal))])
        missing: List[pd.Timestamp] = []
        for lo, hi in spans:
            hi_eff = min(hi, last)          # holes are inside the span the file covers
            span_days = cal[(cal >= max(lo, idx.min())) & (cal <= hi_eff)]
            missing.extend(d for d in span_days if d not in present)
        decl = declared.get(t) or {}
        runs = _runs(decl)
        undeclared = [d for d in missing if not any(lo <= d <= hi for lo, hi in runs)]
        delisting = (decl.get("ends_at_delisting") or {}).get("last_bar")
        end_excused = bool(stale and delisting is not None and pd.Timestamp(delisting) == last)
        stale_open = stale and not end_excused
        holed_open = len(undeclared) > HOLE_TOLERANCE
        n_stale += int(stale_open)
        n_holed += int(holed_open)
        n_declared += int((stale or bool(missing)) and not stale_open and not holed_open)
        if stale or missing or decl:
            names[t] = {"first_bar": str(idx.min().date()), "last_bar": str(last.date()),
                        "required_end": str(pd.Timestamp(req_end).date()),
                        "exited_in_window": bool(exited),
                        "ends_before_required": bool(stale),
                        "end_declared_as_delisting": end_excused,
                        "missing_trading_days": len(missing),
                        "undeclared_missing_days": len(undeclared),
                        "longest_missing_run": _longest_run(missing, cal),
                        "declared": [f for f in DECLARATION_FACETS if f in decl]}
    # The calendar's proof, both directions, against SPY (never trusted as the calendar itself).
    checked_against, spy_missing, cal_missing = None, [], []
    if CALENDAR_REFERENCE in pre:
        checked_against = CALENDAR_REFERENCE
        sidx, spy = pre[CALENDAR_REFERENCE][0], pre[CALENDAR_REFERENCE][1]
        cal_set = set(cal)
        spy_missing = [str(d.date()) for d in cal if sidx.min() <= d <= sidx.max() and d not in spy]
        cal_missing = [str(d.date()) for d in sorted(spy)
                       if start <= d <= end and d not in cal_set]
    fdates = (pd.DatetimeIndex(pd.to_datetime(list(formation_dates))) if formation_dates is not None
              else pd.DatetimeIndex(pd.Series(cal, index=cal).groupby(cal.to_period("M")).max().values))
    shares = []
    for d in fdates:
        members = [t for t, (_i, _p, (spans, _r, _x)) in pre.items()
                   if any(lo <= d <= hi for lo, hi in spans)]
        if members:
            formed = sum(1 for t in members if d in pre[t][1])
            shares.append(formed / len(members))
    cov = {"rule": "rows FORMED on the formation date", "dates": len(shares),
           "min": float(min(shares)) if shares else None,
           "median": float(np.median(shares)) if shares else None,
           "dates_below_0_80": int(sum(1 for x in shares if x < FORMATION_FLOOR))}
    return {"window": [str(start.date()), str(end.date())],
            "calendar": {"source": "majority of active names", "trading_days": len(cal),
                         "checked_against": checked_against,
                         "spy_missing_days": spy_missing,
                         "calendar_missing_days": cal_missing},
            "membership": ("pit intervals" if intervals is not None
                           else "none (every name live to the window end)"),
            "names": names, "n_stale": n_stale, "n_holed": n_holed, "n_declared": n_declared,
            "n_exited_in_window": n_exits, "formation_coverage": cov}
