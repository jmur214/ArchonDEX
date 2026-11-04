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

THE `pre_seam_drip_gap` CLASS (ruled 2026-10-23, built 2026-11-04; option (a) of the cutover): the
kept pre-seam DRIP carries the pre-T-167 band's own holes (on the candidate: 215 names, 380 days,
one to four per name, mostly 2000–2002 and 2011), and option (a) keeps them with it. They are a
DECLARED, COUNTED class keyed to the convention LABEL, never a tolerance: a hole is excused under it
only when (1) the name's label carries a drip pre-seam span (`convention.drip_spans` — the same
resolution as the census label, so the class can never excuse a hole on a span the label does not
call drip); (2) the hole falls strictly BEFORE the seam; (3) the file under `cache_dir` IS the kept
drip — its bars before the seam number exactly what the write record (`n_pre_seam_bars_kept`) or
the merge record (`n_stooq_pre_seam`) says were kept; and (4) the file lacks the bar too (a hole
the frame has and the file does not is NOT the drip's). A post-seam hole, a pre-seam hole on a
file whose kept count no longer matches, a hole the file does not have, an unlabelled name, or a
call with no `cache_dir` (the class is then OFF — fail closed) all stay UNDECLARED and fail. The
record counts the excused days per name and in total (`pre_seam_drip_gaps`), and says per name why
the class did not excuse what remains (`not_excused`). Both census producers and the measured-run
admission pass the canonical cache; the pass driver's `guard` passes the copy it reads.
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
#: The declared, counted class for the kept drip's own pre-seam holes (keyed to the convention
#: label, never a `data_gaps.json` facet; module docstring).
PRE_SEAM_DRIP_GAP = "pre_seam_drip_gap"
DRIP_GAP_RULE = ("a missing trading day is excused under pre_seam_drip_gap only when the name's "
                 "convention label carries a drip pre-seam span, the day is strictly before the seam, "
                 "the file's bars before the seam number exactly the kept count its record carries, and "
                 "the file lacks the day too; counted per name and in total; anything else stays "
                 "undeclared and fails")


def _file_dates(cache_dir: Path, ticker: str) -> Optional[pd.DatetimeIndex]:
    """The bar dates of the cache's own file for the name (parquet first, then csv), or None when
    the cache holds neither — the witness for the kept drip (never the frame, which may be clipped
    to the run window or truncated by a declared exclusion)."""
    pq = Path(cache_dir) / "parquet" / f"{ticker}_1d.parquet"
    if pq.exists():
        return _dates(pd.read_parquet(pq, columns=["Close"]))
    csv = Path(cache_dir) / f"{ticker}_1d.csv"
    if csv.exists():
        return _dates(pd.read_csv(csv, usecols=[0], index_col=0))
    return None


def _witness_pre_seam(cache_dir: Path, ticker: str, seam: pd.Timestamp, n_kept: Optional[int],
                      holes: List[pd.Timestamp]) -> Optional[str]:
    """None when the pre-seam `holes` in the frame are the kept drip's own; else why not."""
    if n_kept is None:
        return "the record carries no kept pre-seam bar count — the kept drip cannot be witnessed"
    fd = _file_dates(cache_dir, ticker)
    if fd is None:
        return f"no {ticker}_1d file under {cache_dir} — the kept drip cannot be witnessed"
    n_file = int((fd < seam).sum())
    if n_file != n_kept:
        return (f"the file's pre-seam span is NOT the kept drip: {n_file} bars before {seam.date()} vs "
                f"{n_kept} kept in the record")
    fset = set(fd)
    not_in_file = [d for d in holes if d in fset]
    if not_in_file:
        return (f"{len(not_in_file)} pre-seam hole(s) in the frame that the file does not have — not the "
                f"kept drip's: {', '.join(str(d.date()) for d in not_in_file[:5])}")
    return None


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


def formation_coverage(pre: Dict[str, tuple], cal: pd.DatetimeIndex, *,
                       intervals: Optional[pd.DataFrame], universe: Optional[Iterable[str]],
                       formation_dates: Optional[Iterable] = None) -> dict:
    """Rows FORMED on each formation date over EVERY member on that date — never over the names that
    happen to have a file (R, 2026-10-15: a denominator taken from the data map drops a member with
    NO file, A's §14.3 file-presence defect in a new form, and the number then moves with whichever
    files sit in the map). The member set: under PIT, every interval covering the date; under a
    static universe, the static list. A member with no file, or no bar on the date, is NOT formed.
    With neither a membership nor a static list there is no member set, and the record says so
    rather than falling back to the data map's own names."""
    rule = "rows FORMED on the formation date, over every member on the date"
    fdates = (pd.DatetimeIndex(pd.to_datetime(list(formation_dates))) if formation_dates is not None
              else pd.DatetimeIndex(pd.Series(cal, index=cal).groupby(cal.to_period("M")).max().values))
    if intervals is not None:
        member_set = "pit intervals"
        t_arr = intervals["ticker"].to_numpy()
        s_arr = pd.to_datetime(intervals["start"]).to_numpy()
        e_arr = pd.to_datetime(intervals["end"]).to_numpy()

        def members_on(d: pd.Timestamp) -> set:
            dv = np.datetime64(d)
            return set(t_arr[(s_arr <= dv) & (np.isnat(e_arr) | (e_arr >= dv))])
    elif universe is not None:
        member_set = "static list"
        static = set(universe)

        def members_on(d: pd.Timestamp) -> set:
            return static
    else:
        return {"rule": rule, "member_set": None, "dates": 0, "min": None, "median": None,
                "dates_below_0_80": None,
                "unmeasured": "no membership and no static list — counting the data map's own names "
                              "would count file presence"}
    shares = []
    for d in fdates:
        members = members_on(d)
        if members:
            formed = sum(1 for t in members if t in pre and d in pre[t][1])
            shares.append(formed / len(members))
    return {"rule": rule, "member_set": member_set, "dates": len(shares),
            "min": float(min(shares)) if shares else None,
            "median": float(np.median(shares)) if shares else None,
            "dates_below_0_80": int(sum(1 for x in shares if x < FORMATION_FLOOR))}


def stale_files_record(data_map: Dict[str, pd.DataFrame], start, end, *,
                       intervals: Optional[pd.DataFrame] = None,
                       universe: Optional[Iterable[str]] = None,
                       declared: Optional[Dict[str, dict]] = None,
                       formation_dates: Optional[Iterable] = None,
                       cache_dir: Optional[Path] = None) -> dict:
    """The `stale_files` census block. Per name: first/last bar, the REQUIRED end (the earlier of
    the window end and the member's exit), `ends_before_required` (stale), missing trading days
    inside the required spans (holes) and how many of them no declaration covers, the longest run,
    and the declared facets. Plus the calendar's proof against SPY and `formation_coverage` — rows
    FORMED on each formation date over every MEMBER on the date (`intervals` under PIT; `universe`,
    the static list, otherwise), never a file on disk. `cache_dir` is the cache the frames were
    loaded from: with it the `pre_seam_drip_gap` class (module docstring) excuses and COUNTS the
    kept drip's own pre-seam holes; without it the class is OFF and every such hole fails."""
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
    drip: Dict[str, dict] = {}
    if cache_dir is not None:
        from engines.data_manager.convention import drip_spans
        drip = drip_spans(cache_dir, sorted(pre), data_map)
    drip_per_name: Dict[str, int] = {}
    not_excused: Dict[str, str] = {}
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
        # The pre_seam_drip_gap class, after the explicit declarations: only the holes those left.
        drip_days = 0
        if undeclared:
            spec = drip.get(t)
            if cache_dir is None:
                not_excused[t] = "no cache_dir given — the pre_seam_drip_gap class is off (fail closed)"
            elif spec is None or "seam_date" not in spec:
                not_excused[t] = (spec or {}).get("refused", "the name was not resolved")
            else:
                seam = pd.Timestamp(spec["seam_date"])
                pre_holes = [d for d in undeclared if d < seam]
                post_holes = [d for d in undeclared if d >= seam]
                why = (_witness_pre_seam(cache_dir, t, seam, spec.get("n_pre_seam_kept"), pre_holes)
                       if pre_holes else None)
                if pre_holes and why is None:
                    drip_days = len(pre_holes)
                    undeclared = post_holes
                    if post_holes:
                        not_excused[t] = (f"{len(post_holes)} hole(s) on or after the seam {seam.date()} — "
                                          f"post-seam, never the kept drip's")
                elif pre_holes:
                    not_excused[t] = why
                else:
                    not_excused[t] = (f"{len(post_holes)} hole(s) on or after the seam {seam.date()} — "
                                      f"post-seam, never the kept drip's")
        if drip_days:
            drip_per_name[t] = drip_days
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
                        "pre_seam_drip_gap_days": drip_days,
                        "longest_missing_run": _longest_run(missing, cal),
                        "declared": ([f for f in DECLARATION_FACETS if f in decl]
                                     + ([PRE_SEAM_DRIP_GAP] if drip_days else []))}
            if t in not_excused:
                names[t]["pre_seam_drip_gap_not_excused"] = not_excused[t]
    # The calendar's proof, both directions, against SPY (never trusted as the calendar itself).
    checked_against, spy_missing, cal_missing = None, [], []
    if CALENDAR_REFERENCE in pre:
        checked_against = CALENDAR_REFERENCE
        sidx, spy = pre[CALENDAR_REFERENCE][0], pre[CALENDAR_REFERENCE][1]
        cal_set = set(cal)
        spy_missing = [str(d.date()) for d in cal if sidx.min() <= d <= sidx.max() and d not in spy]
        cal_missing = [str(d.date()) for d in sorted(spy)
                       if start <= d <= end and d not in cal_set]
    cov = formation_coverage(pre, cal, intervals=intervals, universe=universe,
                             formation_dates=formation_dates)
    return {"window": [str(start.date()), str(end.date())],
            "calendar": {"source": "majority of active names", "trading_days": len(cal),
                         "checked_against": checked_against,
                         "spy_missing_days": spy_missing,
                         "calendar_missing_days": cal_missing},
            "membership": ("pit intervals" if intervals is not None
                           else "none (every name live to the window end)"),
            "names": names, "n_stale": n_stale, "n_holed": n_holed, "n_declared": n_declared,
            "n_exited_in_window": n_exits, "formation_coverage": cov,
            # The kept drip's own pre-seam holes, excused under the declared class and COUNTED —
            # per name and in total — with, per name, why the class did not excuse what remains.
            "pre_seam_drip_gaps": {"class": PRE_SEAM_DRIP_GAP, "rule": DRIP_GAP_RULE,
                                   "cache_dir": str(cache_dir) if cache_dir is not None else None,
                                   "n_names": len(drip_per_name),
                                   "n_days": int(sum(drip_per_name.values())),
                                   "per_name": drip_per_name, "not_excused": not_excused}}
