"""The stale/holed-files guard (adopted 2026-10-15; docs/Sources/proposal_stale_and_holed_files_guard_2026-10-15.md).

Coverage counts BARS, never file presence. The pre-T-167 global-median×3 band, applied at WRITE time,
ended 33 live files early (28 at their all-time highs) and holed 114 more; every count the system had
was a count of FILES or FRAMES (`discover_cached_tickers` admits by row count; the run census's
`n_resolved` / `n_in_panel` count frames; B-1's `coverage_pct` counted a file on disk), so none of it
showed. This module is the ONE function both census producers call, so they cannot drift.

R's binding correction: the END test runs PER NAME against the EARLIER of the window end and the
member's exit — a name that left the index is required to have bars up to its exit, not to the
window end (its file ending at the delisting is correct, "ends at delisting"); a name that is still a
member (or is outside the membership — the essential ETFs, a static list) is required to the window
end. Holes are counted only where the name was required to trade: inside its membership in the
window, against a trading calendar that is itself proven complete.

THE CALENDAR: the dates on which a MAJORITY of the names active that day have a bar (data-derived; no
holiday table, no new dependency). SPY's own file is a canonical file and can be holed, so SPY is
CHECKED against the majority calendar, never trusted as it: a majority-calendar date SPY lacks is a
holed calendar, recorded and failed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_GAPS_PATH = ROOT / "config" / "data_gaps.json"
#: A file may end this many trading days before its required end (a genuine exit's last prints, a
#: holiday at the edge) — A found genuine exits ending days before the recorded exit (CTXS, TWTR, IPG).
END_SLACK_DAYS = 5
#: Missing trading days tolerated per name beyond the calendar: 0 (R and the director, 2026-10-15). A
#: real halt or a single provider gap is a fact to DECLARE in `config/data_gaps.json`, not tolerate.
HOLE_TOLERANCE = 0
MAJORITY = 0.5
FORMATION_FLOOR = 0.80


def load_data_gaps(path: Path = DATA_GAPS_PATH) -> Dict[str, dict]:
    """Declared gaps: per name, `kind` ("holed" — missing bars inside its required span, e.g. no
    provider series to fill them; "stale_fetch" — a declared early end), `n`, `reason`, `source`.
    An absent file means no declarations; an unreadable one raises."""
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text()).get("declarations", {})


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


def stale_files_record(data_map: Dict[str, pd.DataFrame], start, end, *,
                       intervals: Optional[pd.DataFrame] = None,
                       declared: Optional[Dict[str, dict]] = None,
                       formation_dates: Optional[Iterable] = None) -> dict:
    """The `stale_files` census block. Per name: first/last bar, the REQUIRED end (the earlier of
    the window end and the member's exit), `ends_before_required` (stale), missing trading days
    inside the required spans (holes), the longest run, and its declaration. Plus the calendar's own
    completeness (SPY checked against the majority calendar) and `formation_coverage` — rows FORMED
    on each formation date, never a file on disk."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    declared = load_data_gaps() if declared is None else declared
    cal = majority_calendar(data_map, start, end)
    cal_set = set(cal)
    names, n_stale, n_holed, n_declared, n_exits = {}, 0, 0, 0, 0
    pre = {}                                   # per name, once: its bar dates and required spans
    for t, df in data_map.items():
        if df is None or not len(df):
            continue
        idx = _dates(df)
        pre[t] = (idx, set(idx), _required_spans(t, start, end, intervals))
    for t in sorted(pre):
        idx, _present, (spans, req_end, exited) = pre[t]
        if req_end is None:          # no membership inside the window: nothing was required of it
            continue
        n_exits += int(exited)
        last = idx.max()
        req_end_cal = cal[cal <= req_end]
        slack_ok = len(req_end_cal) == 0 or last >= req_end_cal[-min(END_SLACK_DAYS, len(req_end_cal))]
        stale = not slack_ok
        missing = []
        present = _present
        for lo, hi in spans:
            hi_eff = min(hi, last)          # holes are inside the span the file covers
            span_days = cal[(cal >= max(lo, idx.min())) & (cal <= hi_eff)]
            missing.extend(d for d in span_days if d not in present)
        longest = 0
        if missing:
            pos = np.searchsorted(cal.values, pd.DatetimeIndex(sorted(missing)).values)
            run = 1
            longest = 1
            for a, b in zip(pos[:-1], pos[1:]):
                run = run + 1 if b == a + 1 else 1
                longest = max(longest, run)
        decl = declared.get(t)
        holed = len(missing) > HOLE_TOLERANCE
        if decl:
            n_declared += int(stale or holed)
        else:
            n_stale += int(stale)
            n_holed += int(holed)
        if stale or holed or decl:
            names[t] = {"first_bar": str(idx.min().date()), "last_bar": str(last.date()),
                        "required_end": str(pd.Timestamp(req_end).date()),
                        "exited_in_window": bool(exited),
                        "ends_before_required": bool(stale),
                        "missing_trading_days": len(missing), "longest_missing_run": int(longest),
                        "declared": (decl or {}).get("kind")}
    spy_missing = []
    if "SPY" in pre:
        spy = pre["SPY"][1]
        spy_missing = [str(d.date()) for d in cal if d not in spy and d >= min(spy)]
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
                         "spy_missing_days": spy_missing},
            "membership": "pit intervals" if intervals is not None else "none (every name live to the window end)",
            "names": names, "n_stale": n_stale, "n_holed": n_holed, "n_declared": n_declared,
            "n_exited_in_window": n_exits, "formation_coverage": cov}
