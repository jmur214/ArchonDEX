"""T-205 standalone validation harness for the defensive-tilt signals.

STANDALONE / DESCRIPTIVE ONLY — composition + coverage of the quality tilt,
and the honest bull-vs-bear sub-period UNDER-PARTICIPATION of the high-IVOL
exclusion screen. This is NOT the beat-the-robo measurement (that is the
post-gate composition step after C's T-203); no Sharpe/ci_low gate here.

  python scripts/defensive_tilt_screens_t205.py

Loads the processed-universe price frames + the SimFin panel the edges use.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.engine_a_alpha.edges._fundamentals_helpers import get_panel, panel_is_blind  # noqa: E402
from engines.engine_a_alpha.screens import defensive_tilt as dt  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
QUALITY_GRID = [0.15, 0.20, 0.25]
IVOL_GRID = [0.60, 0.75, 0.90]
# Bull = recovery rallies (high-vol names rip); Bear = drawdowns.
SUBPERIODS = {
    "bull_2009": ("2009-03-09", "2009-12-31"),
    "bull_2020": ("2020-03-23", "2020-12-31"),
    "bear_2008": ("2008-01-01", "2008-12-31"),
    "bear_2022": ("2022-01-01", "2022-10-12"),
}


def _load_universe(limit: int = 200) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    for p in sorted(PROCESSED.glob("*_1d.csv"))[:limit]:
        tkr = p.name.replace("_1d.csv", "")
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        dcol = next((c for c in df.columns if c.lower() in ("date", "timestamp")), None)
        ccol = next((c for c in df.columns if c.lower() == "close"), None)
        if dcol is None or ccol is None:
            continue
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
        df = df.dropna(subset=[dcol]).set_index(dcol).sort_index()
        out[tkr] = df.rename(columns={ccol: "Close"})[["Close"]]
    return out


def _fwd_return(df: pd.DataFrame, start: str, end: str) -> float:
    s = df.loc[(df.index >= start) & (df.index <= end), "Close"].astype(float)
    if len(s) < 2:
        return float("nan")
    return float(s.iloc[-1] / s.iloc[0] - 1.0)


def main() -> int:
    print(f"[T205] fundamentals_blind = {panel_is_blind()} (expect False); "
          f"panel rows = {0 if get_panel() is None else len(get_panel())}")
    dmap = _load_universe()
    print(f"[T205] loaded {len(dmap)} processed tickers")

    # --- Quality tilt: coverage + basket size per quantile (as-of latest) ---
    asof = max(df.index.max() for df in dmap.values())
    scores = dt.quality_score(dmap, asof)
    print(f"\n[QUALITY] as-of {asof.date()}: {len(scores)} names scorable "
          f"(fundamentals coverage of {len(dmap)} universe)")
    if scores:
        for q in QUALITY_GRID:
            longs = dt.quality_tilt_longs(dmap, asof, quality_quantile=q)
            top = sorted(longs)[:8]
            print(f"  quality_quantile={q}: basket {len(longs)} names e.g. {top}")

    # --- IVOL exclusion: % excluded + bull/bear under-participation ---
    print("\n[IVOL EXCLUSION] excluded-vs-retained forward return per sub-period")
    print("(excluded = the high-vol names we SIT OUT; retained = what we keep)")
    for cutoff in IVOL_GRID:
        print(f"\n  ivol_cutoff={cutoff}:")
        for lbl, (s, e) in SUBPERIODS.items():
            asof_sub = pd.Timestamp(s)
            excl = dt.high_ivol_exclusion(dmap, asof_sub, ivol_cutoff=cutoff)
            if not excl:
                print(f"    {lbl}: abstain (universe floor not met as-of {s})")
                continue
            retained = [t for t in dmap if t not in excl]
            ex_rets = [_fwd_return(dmap[t], s, e) for t in excl]
            re_rets = [_fwd_return(dmap[t], s, e) for t in retained]
            ex_mean = np.nanmean(ex_rets) if ex_rets else float("nan")
            re_mean = np.nanmean(re_rets) if re_rets else float("nan")
            gap = (re_mean - ex_mean) * 100
            tag = "UNDER-PARTICIPATE (gave up upside)" if ("bull" in lbl and gap < 0) \
                else ("AVOIDED downside" if ("bear" in lbl and gap > 0) else "")
            print(f"    {lbl} ({len(excl)} excl): excluded {ex_mean*100:+6.1f}% | "
                  f"retained {re_mean*100:+6.1f}% | retained−excluded {gap:+6.1f}pp  {tag}")
    print("\n[T205] standalone validation only — NO beat-the-robo measurement (post-gate).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
