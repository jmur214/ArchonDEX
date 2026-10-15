"""The fundamentals RE-BAKE: a deliberate, NON-canonical refresh of NAMED tickers' per-ticker
fundamentals (re-pin #1's declared step; the director's ruling, 2026-10-15).

A canonical run never fetches a missing fundamentals file: the data manager REFUSES the miss and the
census names it. So a new universe name's fundamentals enter the pinned scope only here, and only
deliberately:
  * names are EXPLICIT: `--tickers`, or a census's refused set (`--from-census`). Never a sweep;
  * refused under the canonical switch and under ARCHONDEX_HERMETIC (a re-bake IS the network);
  * MISSES ONLY, as the LOADER defines a miss: a name whose cached parquet is NON-EMPTY is
    reported "present, not refreshed" and left untouched. A cached parquet that is EMPTY is
    "present_empty": the loader treats it as a miss, so the next canonical run refuses it again. It
    is reported distinctly and left untouched, and the run exits non-zero. Overwriting a pinned
    file is a separate declared act (R, 2026-10-15);
  * every fetch attempt leaves a record under the pinned scope
    (`<cache>/parquet/_fundamentals_records/<T>.json`): the ticker, the source and the provider's
    VERSION, the provider attributes ACTUALLY READ (witnessed by a recording proxy, never a
    constant), the time, the outcome, the rows and columns, the frame's FIRST and LAST dates, and
    the written file's md5. A provider revision and a stale series are what the record exists to
    make diagnosable;
  * the WARN that the substrate manifest's verify reads red until a re-pin prints on every run.
It is never reachable from a backtest (tests/test_rebake_fundamentals_2026_10_15.py locks it).

Usage:
  python -m scripts.rebake_fundamentals --tickers CVNA,KG
  python -m scripts.rebake_fundamentals --from-census <path/to/performance_summary.json>
  (optional: --cache-dir data/processed)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_DIR = ROOT / "data" / "processed"
RECORDS_DIRNAME = "_fundamentals_records"
WARN = ("[REBAKE][WARN] this writes fundamentals INTO the pinned scope — the substrate manifest's "
        "verify reads red until a re-pin (scripts/gen_substrate_manifest.py generate)")


class RebakeRefused(SystemExit):
    """A re-bake that must not run: the canonical switch, hermetic mode, or no names."""


class _RecordingTicker:
    """Passes every attribute through to the provider's object and records the public names read."""

    def __init__(self, real, seen: List[str]) -> None:
        object.__setattr__(self, "_real", real)
        object.__setattr__(self, "_seen", seen)

    def __getattr__(self, name):
        if not name.startswith("_") and name not in self._seen:
            self._seen.append(name)
        return getattr(self._real, name)


@contextmanager
def _recording_provider(dmmod, seen: List[str]) -> Iterator[None]:
    orig = dmmod.yf.Ticker
    dmmod.yf.Ticker = lambda *a, **k: _RecordingTicker(orig(*a, **k), seen)
    try:
        yield
    finally:
        dmmod.yf.Ticker = orig


def names_from_census(path: Path) -> List[str]:
    """The census's refused fundamentals misses: the names a canonical run left blind."""
    summary = json.loads(Path(path).read_text())
    census = summary.get("census", summary)
    fm = census.get("fundamentals_misses")
    if not isinstance(fm, dict) or "refused" not in fm:
        raise RebakeRefused(f"[REBAKE] {path}: no census fundamentals_misses.refused record")
    return list(fm["refused"])


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _cached_state(path: Path) -> str:
    """'missing', 'present' (a NON-empty parquet: what the loader returns), or 'present_empty' (the
    loader falls through to a fetch, so it is still a miss)."""
    if not path.exists():
        return "missing"
    import pandas as pd
    try:
        return "present" if not pd.read_parquet(path).empty else "present_empty"
    except Exception:
        return "present_empty"


def rebake(names: List[str], cache_dir: Path = DEFAULT_CACHE_DIR) -> List[Dict]:
    """Fetch each NAMED ticker's missing fundamentals and record every attempt. Returns the records."""
    from core.hermetic import hermetic_mode
    from engines.data_manager import data_manager as dmmod

    names = [t.strip().upper() for t in names if t and t.strip()]
    if not names:
        raise RebakeRefused("[REBAKE] no names given — a re-bake names its tickers; there is no sweep")
    if os.environ.get(dmmod.REFUSE_YFINANCE_ENV):
        raise RebakeRefused(f"[REBAKE] refused: {dmmod.REFUSE_YFINANCE_ENV} is set — a re-bake is a "
                            f"deliberate NON-canonical step; run it outside a canonical runner")
    if hermetic_mode() != "off":
        raise RebakeRefused("[REBAKE] refused: ARCHONDEX_HERMETIC is on — a re-bake is the network")
    print(WARN)
    dm = dmmod.DataManager(cache_dir=str(cache_dir))
    records_dir = Path(dm.cache_dir) / "parquet" / RECORDS_DIRNAME
    out: List[Dict] = []
    for t in names:
        path = dm._fundamentals_cache_path(t)
        state = _cached_state(path)
        if state == "present":
            out.append({"ticker": t, "outcome": "present, not refreshed", "file": str(path)})
            print(f"[REBAKE] {t}: a non-empty cached file exists — left untouched (misses only)")
            continue
        if state == "present_empty":
            out.append({"ticker": t, "outcome": "present_empty", "file": str(path)})
            print(f"[REBAKE] {t}: the cached file is EMPTY — the loader treats it as a miss, but "
                  f"overwriting a pinned file is a separate declared act; left untouched")
            continue
        seen: List[str] = []
        with _recording_provider(dmmod, seen):
            df = dm.fetch_historical_fundamentals(t)
        written = path.exists()
        has = df is not None and len(df) > 0
        rec = {"ticker": t, "source": dmmod._FUNDAMENTALS_SOURCE,
               "provider_version": getattr(dmmod.yf, "__version__", "unknown"),
               "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "provider_attributes_read": seen,
               "outcome": "fetched" if written else "empty",
               "rows": int(len(df)) if df is not None else 0,
               "columns": list(df.columns) if has else [],
               "first_date": str(df.index.min().date()) if has else None,
               "last_date": str(df.index.max().date()) if has else None,
               "file": str(path) if written else None,
               "md5": _md5(path) if written else None}
        records_dir.mkdir(parents=True, exist_ok=True)
        tmp = records_dir / f".{t}.json.tmp"
        tmp.write_text(json.dumps(rec, indent=1) + "\n")
        tmp.replace(records_dir / f"{t}.json")
        out.append(rec)
        print(f"[REBAKE] {t}: {rec['outcome']} ({rec['rows']} rows; read {seen})")
    print(WARN)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--tickers", help="comma-separated names to re-bake")
    src.add_argument("--from-census", type=Path, help="a performance_summary.json whose census "
                                                     "names the refused fundamentals misses")
    ap.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = ap.parse_args(argv)
    names = (args.tickers.split(",") if args.tickers else names_from_census(args.from_census))
    try:
        recs = rebake(names, args.cache_dir)
    except RebakeRefused as e:
        print(str(e.code if e.code is not None else e), file=sys.stderr)
        return 2
    return 0 if all(r["outcome"] in ("fetched", "present, not refreshed") for r in recs) else 1


if __name__ == "__main__":
    from core.env import load_local_env
    load_local_env()
    sys.exit(main())
