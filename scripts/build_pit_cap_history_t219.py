#!/usr/bin/env python3
"""T-2026-06-18-219 — cap-AT-DELISTING for the delisted PIT cohort, in two EXPLICIT modes.

Why (June 2026): close the T-210/T-215 cap-join under-count — give the DELISTED PIT cohort a
real cap (cap-at-delisting) instead of the current-snapshot's null → ADV-15bps fallback.
yfinance ``get_shares_full`` carries shares history up to a name's delisting/acquisition
(back to ~2015), so cap_at_delist = late-period median(close × shares). Names delisted
BEFORE ~2015 (no shares data) are the FREE-DATA WALL — left null (honest), still ADV
fallback. Merged into ``data/universe/market_cap_tiers.json`` as
``{ticker: {marketCap, tier, asof, source: "delist_shares"}}`` so the existing slippage
cap-cache tiers them with NO model change.

Re-pin #1 (2026-11-05, T-375 C4): the bare live-fetch ``main()`` is RETIRED — one call that
fetched AND rewrote the real tiers file in place, every failed or empty fetch swallowed to
None. Two explicit modes replace it; ``_tier`` and the cap arithmetic (``cap_at_delist``)
are UNCHANGED.

    python scripts/build_pit_cap_history_t219.py --write-snapshot data/universe/delist_shares_snapshot.parquet
        NETWORK, run ONCE (re-pin #1's data half, D1). For every delisted-cohort name
        (sp500_membership.parquet, ``included_until`` set) that has data/processed/<t>_1d.csv:
        one ``yfinance.Ticker(t).get_shares_full(start="2010-01-01")`` call. The series are
        stored LONG (ticker, date, shares) in one parquet; beside it ``<stem>.meta.json``
        records the counts {fetched, empty, failed}, the cohort sizes, the date and the
        per-name status list. An empty result is RECORDED as "empty", an exception as
        "failed" with its type and message — never swallowed. Exit 1 if nothing was fetched.

    python scripts/build_pit_cap_history_t219.py --from-snapshot <path> [--out <path>]
        HERMETIC (re-pin #2's recompute). A snapshot name with a price file gets its
        cap-at-delist from the snapshot + the price cache with the unchanged arithmetic,
        merged into a COPY of the current tiers and written to --out, which DEFAULTS to a
        scratch file under the system temp dir — never data/universe/market_cap_tiers.json
        unless passed explicitly (that write is re-pin #2's own act). This path never
        imports yfinance: locked with a stub module whose Ticker raises if constructed.

        THE SELECTION RULE (owed before re-pin #2; reviewer F1 of 2026-11-05). ``cap_at_delist``
        keys its 12-month window on the price file's LAST BAR, so for a name that still trades
        it is a trailing median, not a cap at leaving the index — the bare recompute of D1
        would have replaced the 55 cohort names that carry a current-snapshot cap and moved
        the 8 still-trading ``delist_shares`` entries. A name is WRITTEN only when BOTH hold;
        otherwise it is SKIPPED and reported with its reason:

          (2) NEVER OVERWRITE A CURRENT-SNAPSHOT CAP — the current tiers entry is absent, or
              carries ``source == "delist_shares"`` (this script's own), or is a NULL placeholder
              (``marketCap`` None: no cap to keep — June's ``not entry.get("marketCap")``). An
              entry with no ``source`` and a cap (the T-210/T-215 current-snapshot shape) is kept
              byte-for-byte → reason ``current_snapshot_kept``. Checked FIRST: it does not depend
              on the cache, and a current-snapshot cap is never replaced by this script even for
              a name the cache says is delisted.
          (1) DELISTED BY THE CACHE — the name's last bar is STRICTLY earlier than
              ``cache_end − CACHE_END_TOLERANCE_BDAYS`` trading days. ``cache_end`` is the
              last-bar date shared by the MAJORITY of the ``*_1d.csv`` files under
              data/processed (see ``cache_end_from``: the literal maximum is refuted on the real
              cache, and SPY is itself an early-ender there). A last bar at/after the bound →
              reason ``still_trading``. A LIVE name whose file ends early (the baked-at-write-time
              class) looks delisted under (1) alone; (2) is what keeps its current-snapshot cap.

        Names the snapshot lacks stay as they are (the wall); ``resolved`` counts exactly the
        entries WRITTEN; the skipped names are listed per reason in the stats and printed.

    --root <dir>   the checkout holding data/ (default: this one; scratch and test roots only).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TIERS_REL = "data/universe/market_cap_tiers.json"
MEMBERSHIP_REL = "data/universe/sp500_membership.parquet"
SHARES_START = "2010-01-01"
SNAPSHOT_SCHEMA = "delist_shares_snapshot/v1"
TIERS = [(200e9, "mega"), (10e9, "large"), (2e9, "mid"), (300e6, "small")]
FETCHED, EMPTY, FAILED = "fetched", "empty", "failed"
#: The selection rule's two skip reasons (module docstring, "--from-snapshot").
STILL_TRADING, CURRENT_SNAPSHOT_KEPT = "still_trading", "current_snapshot_kept"
#: Trading days a price file may end before the cache's end and still count as trading: the
#: stale-files guard's END_SLACK_DAYS (engines/data_manager/coverage.py). Strictly earlier = delisted.
CACHE_END_TOLERANCE_BDAYS = 5
#: `cache_end` must be the last bar of at least this share of the price files; below it the cache
#: has no established end and the recompute REFUSES (exit 2) rather than guess one.
CACHE_END_MIN_SHARE = 0.5
#: Reported beside `cache_end` as the cross-check (the project's reference calendar), never used as it.
CACHE_END_REFERENCE = "SPY"


def _tier(cap: float) -> str:
    for floor, label in TIERS:
        if cap >= floor:
            return label
    return "micro"


def _delisted_cohort(root: Path = ROOT) -> Dict[str, pd.Timestamp]:
    m = pd.read_parquet(root / MEMBERSHIP_REL)
    left = m[m["included_until"].notna()].copy()
    left["iu"] = pd.to_datetime(left["included_until"])
    return dict(zip(left["ticker"], left["iu"]))


def _names_with_price(root: Path = ROOT) -> set:
    # ticker-exclusions: bypassed — data-ops on the cost join: the cap-at-delist builder must see every
    # cached delisted name; the exclusion is a measurement-universe rule (grandfathered by name, 2026-10-15)
    return {os.path.basename(p).replace("_1d.csv", "")
            for p in glob.glob(str(root / "data/processed/*_1d.csv"))}


def _load_price(t: str, root: Path = ROOT) -> pd.DataFrame:
    # ticker-exclusions: bypassed — see _names_with_price (the same data-ops read, per name)
    return pd.read_csv(root / f"data/processed/{t}_1d.csv", parse_dates=["Date"]).set_index("Date")


def cap_at_delist(px: pd.DataFrame, sh: pd.Series) -> Optional[Tuple[float, pd.Timestamp]]:
    """THE T-219 ARITHMETIC, UNCHANGED from the June live-fetch main(): align shares to price
    dates near delisting (the last 12 months of overlap), forward-fill, median of Close × shares.
    Returns (cap, end) — `end` is the overlap's last date, the entry's `asof` — or None when
    there is no overlap, no finite product, or a non-positive cap (the free-data wall)."""
    sh = sh[~sh.index.duplicated(keep="last")].sort_index()
    sh.index = pd.to_datetime(sh.index).tz_localize(None)
    end = min(px.index.max(), sh.index.max())
    win = px[(px.index >= end - pd.DateOffset(months=12)) & (px.index <= end)]
    if not len(win):
        return None
    shares_ff = sh.reindex(win.index, method="ffill")
    cap_series = (win["Close"] * shares_ff).dropna()
    if not len(cap_series):
        return None
    cap = float(cap_series.median())
    return (cap, end) if cap > 0 else None


def tier_entry(cap: float, end: pd.Timestamp) -> Dict[str, Any]:
    return {"marketCap": cap, "tier": _tier(cap), "asof": str(end.date()), "source": "delist_shares"}


# ── --write-snapshot (NETWORK) ──────────────────────────────────────────────────

def _empty_long() -> pd.DataFrame:
    return pd.DataFrame({"ticker": pd.Series(dtype="object"), "date": pd.Series(dtype="datetime64[ns]"),
                         "shares": pd.Series(dtype="float64")})


def fetch_shares_snapshot(names: Iterable[str], start: str = SHARES_START,
                          sleep_s: float = 0.05) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """ONE `get_shares_full(start=...)` per name. Returns the LONG frame (ticker, date, shares; the
    date is the series' own index as naive wall dates — the arithmetic's normalisation, so the
    recompute reproduces the live path exactly) and one status record per name: `fetched` with
    the row count and span, `empty` (None or zero rows), or `failed` with the exception's type and
    message. Nothing is swallowed. yfinance is imported HERE and only here."""
    import yfinance as yf                       # the module's ONLY yfinance import — never on --from-snapshot
    frames: List[pd.DataFrame] = []
    statuses: List[Dict[str, Any]] = []
    for t in sorted(names):
        try:
            sh = yf.Ticker(t).get_shares_full(start=start)
        except Exception as exc:                # recorded with its reason, never None
            statuses.append({"ticker": t, "status": FAILED, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        if sh is None or len(sh) == 0:
            statuses.append({"ticker": t, "status": EMPTY, "reason": "get_shares_full returned "
                             + ("None" if sh is None else "an empty series")})
            continue
        s = pd.Series(sh)
        dates = pd.DatetimeIndex(pd.to_datetime(s.index)).tz_localize(None)
        frames.append(pd.DataFrame({"ticker": t, "date": dates, "shares": s.to_numpy(dtype="float64")}))
        statuses.append({"ticker": t, "status": FETCHED, "rows": int(len(s)),
                         "first": str(dates.min().date()), "last": str(dates.max().date())})
        time.sleep(sleep_s)
    long = pd.concat(frames, ignore_index=True) if frames else _empty_long()
    return long, statuses


def snapshot_meta_path(snapshot: Path) -> Path:
    """`<same stem>.meta.json` beside the parquet."""
    return snapshot.with_name(snapshot.stem + ".meta.json")


def write_snapshot(snapshot: Path, root: Path = ROOT, start: str = SHARES_START) -> Dict[str, Any]:
    cohort = _delisted_cohort(root)
    names = sorted(t for t in cohort if t in _names_with_price(root))
    print(f"[PITCAP] delisted cohort {len(cohort)}; with a price file {len(names)}; "
          f"fetching shares ONCE each (start={start})", flush=True)
    long, statuses = fetch_shares_snapshot(names, start=start)
    counts = {k: sum(1 for s in statuses if s["status"] == k) for k in (FETCHED, EMPTY, FAILED)}
    snapshot = Path(snapshot)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    long.to_parquet(snapshot, index=False)
    meta = {"schema": SNAPSHOT_SCHEMA, "written_on": _dt.date.today().isoformat(), "shares_start": start,
            "cohort_delisted": len(cohort), "cohort_with_price": len(names), "counts": counts,
            "rows": int(len(long)), "statuses": statuses}
    snapshot_meta_path(snapshot).write_text(json.dumps(meta, indent=1) + "\n")
    return meta


# ── --from-snapshot (HERMETIC) ──────────────────────────────────────────────────

def load_snapshot(snapshot: Path) -> pd.DataFrame:
    long = pd.read_parquet(snapshot)
    missing = [c for c in ("ticker", "date", "shares") if c not in long.columns]
    if missing:
        raise ValueError(f"snapshot {snapshot} lacks column(s) {missing}")
    return long


class CacheEndUnresolved(ValueError):
    """The price cache has no established end (no files, or no last-bar date shared by
    `CACHE_END_MIN_SHARE` of them): the selection rule cannot classify anything — refuse."""


def last_bar_date(path: Path) -> pd.Timestamp:
    """The date on the file's last line — the cache's last bar for the name — read from the file's
    TAIL (every file in the cache is read for `cache_end`; parsing 730 whole files is not a tail
    read). The cache's csvs are date-sorted with `Date` first; for every name whose price frame is
    loaded, `recompute_from_snapshot` proves this equals `px.index.max()`. A file whose last line
    is not a dated bar (header-only, truncated) RAISES naming the file: it cannot be classified,
    and the recompute halts rather than skip it."""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - 512))
        lines = [l for l in f.read().decode("utf-8", errors="replace").splitlines() if l.strip()]
    if not lines:
        raise ValueError(f"{path}: empty price file — no last bar to classify")
    field = lines[-1].split(",", 1)[0].strip()
    try:
        ts = pd.Timestamp(field)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{path}: the last line is not a dated bar ({lines[-1][:60]!r})") from exc
    if pd.isna(ts):
        raise ValueError(f"{path}: the last line is not a dated bar ({lines[-1][:60]!r})")
    return ts.tz_localize(None).normalize() if ts.tzinfo is not None else ts.normalize()


def price_cache_ends(root: Path = ROOT) -> Dict[str, pd.Timestamp]:
    """ticker → last bar for EVERY `data/processed/*_1d.csv` (the same glob as `_names_with_price`)."""
    # ticker-exclusions: bypassed — see _names_with_price (the cache's end is a property of the whole cache)
    return {os.path.basename(p).replace("_1d.csv", ""): last_bar_date(Path(p))
            for p in sorted(glob.glob(str(root / "data/processed/*_1d.csv")))}


def cache_end_from(ends: Dict[str, pd.Timestamp], min_share: float = CACHE_END_MIN_SHARE,
                   tolerance_bdays: int = CACHE_END_TOLERANCE_BDAYS) -> Dict[str, Any]:
    """`cache_end` = the last-bar date shared by the MAJORITY of the price files — the bulk refresh's
    date — with the evidence both ways: its file count and share, the literal latest end and who
    holds it, and the reference name's own last bar. Why not the literal maximum: on the real cache
    (2026-11-05) five files end after the bulk (AGG/EFA/VNQ 2026-05-21, BF.B/BRK.B 2026-05-07) while
    492/730 end 2026-04-24 — the maximum would class the whole bulk as delisted and rewrite the 8
    still-trading `delist_shares` names. Why not SPY: SPY ends 2026-04-17 there, one of 105 files a
    week behind the bulk — a sentinel that is itself an early-ender. A tie between dates takes the
    EARLIER (fewer names classed delisted). Below `min_share`, or with no files, RAISES
    `CacheEndUnresolved`. `delisted_bound` is `cache_end − tolerance_bdays` business days."""
    if not ends:
        raise CacheEndUnresolved("no *_1d.csv under data/processed — the cache has no end")
    counts = Counter(pd.Timestamp(d).normalize() for d in ends.values())
    top = max(counts.values())
    cache_end = min(d for d, n in counts.items() if n == top)
    share = top / len(ends)
    if share < min_share:
        raise CacheEndUnresolved(
            f"no last-bar date is shared by {min_share:.0%} of the {len(ends)} price files — the most common, "
            f"{cache_end.date()}, ends {top} ({share:.0%}); the cache has no established end")
    latest = max(counts)
    ref = ends.get(CACHE_END_REFERENCE)
    return {"cache_end": cache_end, "n_files": len(ends), "n_at_end": top, "share": share,
            "latest_end": latest, "latest_names": sorted(t for t, d in ends.items() if pd.Timestamp(d).normalize() == latest),
            "reference": CACHE_END_REFERENCE, "reference_last_bar": pd.Timestamp(ref).normalize() if ref is not None else None,
            "tolerance_bdays": tolerance_bdays,
            "delisted_bound": cache_end - tolerance_bdays * pd.offsets.BDay()}


def delisted_by_cache(last_bar: pd.Timestamp, cache_end: pd.Timestamp,
                      tolerance_bdays: int = CACHE_END_TOLERANCE_BDAYS) -> bool:
    """Rule (1): the name's last bar is STRICTLY earlier than `cache_end` less the tolerance in
    business days. At or after the bound the name is still trading by the cache."""
    return pd.Timestamp(last_bar) < pd.Timestamp(cache_end) - tolerance_bdays * pd.offsets.BDay()


def may_overwrite(current_entry: Optional[Dict[str, Any]]) -> bool:
    """Rule (2): this script may write over an ABSENT entry, its OWN (`source == "delist_shares"`),
    or a NULL placeholder (`marketCap` None — no cap to keep; June's `not entry.get("marketCap")`).
    An entry carrying a cap with no `source` is a current-snapshot cap: never replaced."""
    if not current_entry:
        return True
    if current_entry.get("source") == "delist_shares":
        return True
    return current_entry.get("marketCap") is None


def recompute_from_snapshot(snapshot: Path, root: Path = ROOT, tiers: Optional[Dict[str, Any]] = None,
                            cache_end_info: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """A snapshot name with a price file that passes the SELECTION RULE (module docstring: (2) the
    current entry may be overwritten, then (1) the cache says delisted) → `cap_at_delist` on the
    snapshot's series + the price cache; the entries merged into a COPY of the current tiers (the
    file, or `tiers`), which is never mutated. Names the snapshot lacks (empty / failed fetches:
    see its meta) keep whatever the current tiers say — the wall; those among them carrying a
    `delist_shares` entry are counted under `kept_absent_from_snapshot`, so the output's
    `delist_shares` count reconciles (D1 read 193 in the file against `resolved` 191: COL and ESRX,
    June-fetched, absent from the snapshot). `resolved` == the entries WRITTEN == len(written_names).
    Returns (new_tiers, stats). Raises `CacheEndUnresolved` when the cache has no established end.
    Never imports yfinance."""
    long = load_snapshot(snapshot)
    current = json.loads((root / TIERS_REL).read_text()) if tiers is None else tiers
    new = json.loads(json.dumps(current))         # a COPY
    ends = price_cache_ends(root)
    ce = cache_end_from(ends) if cache_end_info is None else cache_end_info   # main() passes its own, once
    cache_end = ce["cache_end"]
    stats: Dict[str, Any] = {
        "snapshot_names": 0, "resolved": 0, "wall": 0, "no_price_file": 0,
        "skipped_still_trading": 0, "skipped_current_snapshot_kept": 0,
        "changed_vs_current": 0, "new_vs_current": 0, "kept_absent_from_snapshot": 0,
        "cache_end": str(cache_end.date()), "cache_end_files": f"{ce['n_at_end']}/{ce['n_files']}",
        "delisted_bound": str(ce["delisted_bound"].date()), "tolerance_bdays": ce["tolerance_bdays"],
        "written_names": [], "skipped_still_trading_names": [], "skipped_current_snapshot_kept_names": [],
        "wall_names": [], "no_price_file_names": [], "kept_absent_from_snapshot_names": []}
    snapshot_names = set()
    for t, g in long.groupby("ticker", sort=True):
        stats["snapshot_names"] += 1
        snapshot_names.add(t)
        if t not in ends:
            stats["no_price_file"] += 1
            stats["no_price_file_names"].append(t)
            continue
        if not may_overwrite(current.get(t)):                    # rule (2) first: never a current-snapshot cap
            stats["skipped_current_snapshot_kept"] += 1
            stats["skipped_current_snapshot_kept_names"].append(t)
            continue
        if not delisted_by_cache(ends[t], cache_end):            # rule (1): the cache says it still trades
            stats["skipped_still_trading"] += 1
            stats["skipped_still_trading_names"].append(t)
            continue
        px = _load_price(t, root)
        if len(px) and px.index.max() != ends[t]:                # the tail read proven against the frame
            raise ValueError(f"{t}: the file's last line {ends[t].date()} is not its latest bar "
                             f"{px.index.max().date()} — an unsorted price file cannot be classified")
        sh = pd.Series(g["shares"].to_numpy(dtype="float64"),
                       index=pd.DatetimeIndex(pd.to_datetime(g["date"])))
        r = cap_at_delist(px, sh)
        if r is None:
            stats["wall"] += 1
            stats["wall_names"].append(t)
            continue
        entry = tier_entry(*r)
        if t not in current:
            stats["new_vs_current"] += 1
        elif current[t] != entry:
            stats["changed_vs_current"] += 1
        new[t] = entry
        stats["resolved"] += 1
        stats["written_names"].append(t)
    for t, v in sorted(current.items()):
        if t not in snapshot_names and isinstance(v, dict) and v.get("source") == "delist_shares":
            stats["kept_absent_from_snapshot"] += 1
            stats["kept_absent_from_snapshot_names"].append(t)
    assert stats["resolved"] == len(stats["written_names"])
    return new, stats


def _describe_cache_end(ce: Dict[str, Any]) -> str:
    ref = ce["reference_last_bar"]
    return (f"[PITCAP] cache end {ce['cache_end'].date()} = the last bar of {ce['n_at_end']}/{ce['n_files']} price "
            f"files ({ce['share']:.0%}); latest file end {ce['latest_end'].date()} "
            f"({', '.join(ce['latest_names'][:8])}{'…' if len(ce['latest_names']) > 8 else ''}); "
            f"{ce['reference']} ends {ref.date() if ref is not None else 'ABSENT'}; delisted by the cache = last bar "
            f"before {ce['delisted_bound'].date()} ({ce['tolerance_bdays']} trading days)")


def default_scratch_out() -> Path:
    """Where `--from-snapshot` writes when `--out` is absent: the system temp dir, never data/."""
    return Path(tempfile.gettempdir()) / f"market_cap_tiers_from_snapshot_{_dt.date.today().isoformat()}.json"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write-snapshot", metavar="PATH", type=Path,
                   help="NETWORK: fetch every delisted-cohort name's shares history ONCE into this parquet "
                        "(+ <stem>.meta.json with per-name fetched/empty/failed statuses)")
    g.add_argument("--from-snapshot", metavar="PATH", type=Path,
                   help="HERMETIC: recompute cap-at-delist from this snapshot + the price cache; never fetches")
    ap.add_argument("--out", metavar="PATH", type=Path, default=None,
                    help="--from-snapshot only: the recomputed tiers json (default: a scratch file under the "
                         "system temp dir; the real data/universe/market_cap_tiers.json only when named here)")
    ap.add_argument("--root", metavar="DIR", type=Path, default=ROOT,
                    help="the checkout holding data/ (default: this one; scratch and test roots only)")
    a = ap.parse_args(argv)

    if a.write_snapshot is not None:
        if a.out is not None:
            ap.error("--out belongs to --from-snapshot")
        meta = write_snapshot(a.write_snapshot, root=a.root)
        c = meta["counts"]
        print(f"[PITCAP] snapshot {a.write_snapshot}: fetched={c[FETCHED]} empty={c[EMPTY]} failed={c[FAILED]} "
              f"of {meta['cohort_with_price']} cohort names with a price file "
              f"(meta: {snapshot_meta_path(Path(a.write_snapshot))})")
        if c[FETCHED] == 0:
            print("[PITCAP] ERROR: nothing fetched — the snapshot holds no series; the meta records every "
                  "per-name reason", file=sys.stderr)
            return 1
        return 0

    out = a.out if a.out is not None else default_scratch_out()
    try:
        ce = cache_end_from(price_cache_ends(a.root))
        new, stats = recompute_from_snapshot(a.from_snapshot, root=a.root, cache_end_info=ce)
    except CacheEndUnresolved as exc:
        print(f"[PITCAP] REFUSED: {exc} — nothing written", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(new, indent=0))
    delist = {t: v for t, v in new.items() if (v or {}).get("source") == "delist_shares"}
    dist = Counter(v["tier"] for v in delist.values())
    counts = {k: v for k, v in stats.items() if not isinstance(v, list)}
    print(_describe_cache_end(ce))
    print(f"[PITCAP] from-snapshot {a.from_snapshot}: {counts}")
    for label, key in (("written", "written_names"), (f"skipped {STILL_TRADING}", "skipped_still_trading_names"),
                       (f"skipped {CURRENT_SNAPSHOT_KEPT}", "skipped_current_snapshot_kept_names"),
                       ("wall (no overlap / no positive cap)", "wall_names"), ("no price file", "no_price_file_names"),
                       ("kept, absent from the snapshot", "kept_absent_from_snapshot_names")):
        names = stats[key]
        print(f"[PITCAP] {label} ({len(names)}): {', '.join(names) if names else '-'}")
    print(f"[PITCAP] delist_shares entries in the output: {len(delist)} = written {stats['resolved']} + carried "
          f"{len(delist) - stats['resolved']}; tier distribution: {dict(dist)}")
    print(f"[PITCAP] wrote {out}" + ("" if a.out is not None else "  (the SCRATCH default; pass --out to choose)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
