"""scripts/lazy_prices/b6_smoke.py
=================================
T-383 (B-6) — the 30-filing smoke test of the repaired parser on REAL filings, before the bulk
fetch. A stratified random draw from the S&P fetch list (5 acceptance-year bins x {10-K, 10-Q},
seed fixed) plus forced 10-Ks of T-341b's always-fail Item-7 tickers, with each CIK's SIC
(from its submissions JSON) reported for sector spread. Writes data/b6_local/smoke/ only and
prints, per filing, the section statuses and the first/last characters of each carved section
for a human read. Exit 1 if any accepted section carries an end-of-document marker.

Usage:
  python -m scripts.lazy_prices.b6_smoke [--n-per-cell 2] [--seed 383]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from scripts.lazy_prices import b6_build_panel as B
from scripts.lazy_prices import b6_edgar as E
from scripts.lazy_prices import b6_parse as P

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "b6_local" / "smoke" / "smoke_sample.parquet"
YEAR_BINS = [(2004, 2008), (2009, 2013), (2014, 2018), (2019, 2022), (2023, 2026)]
ALWAYS_FAIL_CIKS = {"ETN": 1551182, "IBM": 51143, "XOM": 34088, "WFC": 72971, "C": 831001}


def draw(fl: pd.DataFrame, n_per_cell: int, seed: int) -> pd.DataFrame:
    fl = fl.assign(year=fl["acceptance_dt"].str[:4].astype(int))
    picks = []
    for lo, hi in YEAR_BINS:
        for form in ("10-K", "10-Q"):
            cell = fl[(fl.year >= lo) & (fl.year <= hi) & (fl.form == form)]
            cell = cell.drop_duplicates("cik")
            if len(cell):
                picks.append(cell.sample(min(n_per_cell, len(cell)), random_state=seed))
    for i, (_t, cik) in enumerate(ALWAYS_FAIL_CIKS.items()):
        k = fl[(fl.cik == cik) & (fl.form == "10-K")]
        if len(k):
            picks.append(k.sample(1, random_state=seed + i))
    return pd.concat(picks).drop_duplicates("accession").reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B-6 30-filing parser smoke test on real filings.")
    ap.add_argument("--n-per-cell", type=int, default=2)
    ap.add_argument("--seed", type=int, default=383)
    args = ap.parse_args(argv)
    E.assert_disk()
    fl = pd.read_parquet(B.FETCH_LIST)
    sample = draw(fl, args.n_per_cell, args.seed)
    sic = {}
    for cik in sample.cik.unique():
        sub, _ = E.fetch_json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
        sic[int(cik)] = (sub or {}).get("sicDescription", "") or ""
    rows = []
    for _, r in sample.iterrows():
        rec = B.process_filing(r)
        rec["sic"] = sic.get(int(r.cik), "")
        rows.append(rec)
    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    bad = 0
    for _, r in df.iterrows():
        print(f"\n== {r.form} cik {r.cik} {str(r.acceptance_dt)[:10]} {r.sic[:40]!r} "
              f"fetch {r.fetch_ok} {r.fetch_status} {r.fetch_reason or ''}")
        for s in ("risk", "mda"):
            t = r[f"{s}_text"] or ""
            print(f"   {s:4} {r[f'{s}_status']:<45} src={r.get(f'{s}_source', '')!s:<18} "
                  f"tier={r[f'{s}_tier']} term={r[f'{s}_terminator']} words={r[f'{s}_words']}")
            if t:
                print(f"        START {t[:150]!r}")
                print(f"        END   {t[-150:]!r}")
                if P._END_MARKERS.search(t):
                    bad += 1
    print("\nstatus table:")
    print(pd.crosstab(df.form, df.risk_status).to_string())
    print(pd.crosstab(df.form, df.mda_status).to_string())
    print(f"sample {len(df)} filings, {df.cik.nunique()} CIKs, {df.sic.nunique()} SIC descriptions; "
          f"contaminated accepted sections: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
