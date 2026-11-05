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
        HERMETIC (re-pin #2's recompute). Every snapshot name with a price file gets its
        cap-at-delist from the snapshot + the price cache with the unchanged arithmetic,
        merged into a COPY of the current tiers and written to --out, which DEFAULTS to a
        scratch file under the system temp dir — never data/universe/market_cap_tiers.json
        unless passed explicitly (that write is re-pin #2's own act). This path never
        imports yfinance: locked with a stub module whose Ticker raises if constructed.

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


def recompute_from_snapshot(snapshot: Path, root: Path = ROOT,
                            tiers: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Every snapshot name with a price file → `cap_at_delist` on the snapshot's series + the
    price cache; the entries merged into a COPY of the current tiers (the file, or `tiers`),
    which is never mutated. Names the snapshot lacks (empty / failed fetches: see its meta) keep
    whatever the current tiers say — the wall. Returns (new_tiers, stats). Never imports yfinance."""
    long = load_snapshot(snapshot)
    current = json.loads((root / TIERS_REL).read_text()) if tiers is None else tiers
    new = json.loads(json.dumps(current))         # a COPY
    have = _names_with_price(root)
    stats = {"snapshot_names": 0, "resolved": 0, "wall": 0, "no_price_file": 0,
             "changed_vs_current": 0, "new_vs_current": 0}
    for t, g in long.groupby("ticker", sort=True):
        stats["snapshot_names"] += 1
        if t not in have:
            stats["no_price_file"] += 1
            continue
        sh = pd.Series(g["shares"].to_numpy(dtype="float64"),
                       index=pd.DatetimeIndex(pd.to_datetime(g["date"])))
        r = cap_at_delist(_load_price(t, root), sh)
        if r is None:
            stats["wall"] += 1
            continue
        entry = tier_entry(*r)
        if t not in current:
            stats["new_vs_current"] += 1
        elif current[t] != entry:
            stats["changed_vs_current"] += 1
        new[t] = entry
        stats["resolved"] += 1
    return new, stats


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
    new, stats = recompute_from_snapshot(a.from_snapshot, root=a.root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(new, indent=0))
    delist = {t: v for t, v in new.items() if (v or {}).get("source") == "delist_shares"}
    dist = Counter(v["tier"] for v in delist.values())
    print(f"[PITCAP] from-snapshot {a.from_snapshot}: {stats}")
    print(f"[PITCAP] delisted-cohort cap-at-delist tier distribution: {dict(dist)}")
    print(f"[PITCAP] wrote {out}" + ("" if a.out is not None else "  (the SCRATCH default; pass --out to choose)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
