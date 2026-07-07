"""T-289b — resumable PIT news-panel backfill. Writes data/intel/news_panel/news_YYYYMM.parquet per month,
skipping months already built. Universe = PIT membership ∪ delisted ∪ special-situations (over-inclusive is fine).

  python -m scripts.build_news_panel_t289 --month 2023-06        # one month (smoke)
  python -m scripts.build_news_panel_t289 --all                  # resumable full backfill 2015-01..now
  python -m scripts.build_news_panel_t289 --smoke                # tiny universe, 2023-06 (pipeline proof)
"""
import argparse, datetime as dt, pathlib
import pandas as pd
ROOT = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-agent-d')
import sys; sys.path.insert(0, str(ROOT))
from intelligence import news_panel as NP

SPECIAL_SITS = ['SIVB', 'FRC', 'TWTR', 'BBBY', 'GNC', 'JCP', 'WLL', 'REV', 'ATVI', 'CBL']

def full_universe():
    syms = set(SPECIAL_SITS)
    mem = ROOT / 'data' / 'universe' / 'sp500_membership_pit.parquet'
    if mem.exists():
        syms |= set(pd.read_parquet(mem)['ticker'].dropna().astype(str))
    return sorted(syms)

def months(a, b):
    y, m = a; out = []
    while (y, m) <= b:
        out.append((y, m)); m += 1
        if m > 12: m, y = 1, y + 1
    return out

def run_month(y, m, universe, run_id):
    p = NP._path(y, m)
    if p.exists():
        n = len(pd.read_parquet(p)); print(f"  {y}-{m:02d}: exists ({n} rows) — skip"); return n
    df = NP.build_month(y, m, universe, run_id)
    print(f"  {y}-{m:02d}: built {len(df)} articles -> {p.name}")
    return len(df)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--month'); ap.add_argument('--all', action='store_true'); ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    run_id = 'backfill_t289_' + dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')
    if a.smoke:
        uni = SPECIAL_SITS + ['AAPL', 'MSFT', 'TSLA', 'JPM']
        df = NP.build_month(2023, 6, uni, run_id)
        print(f"[smoke] 2023-06 tiny universe ({len(uni)} tickers): {len(df)} articles")
        if len(df):
            r = df.iloc[0]
            print(f"  schema OK: {list(df.columns)}")
            print(f"  sample: created_at={str(r['created_at'])[:19]} symbols={r['symbols'][:5]} "
                  f"headline={r['headline'][:50]!r} content_len={len(r['content'])} source={r['source']}")
            print(f"  PIT check: load_panel(as_of=2023-06-15) rows with created_at<that = "
                  f"{len(NP.load_panel(as_of='2023-06-15'))} (of {len(df)} in month)")
    elif a.month:
        y, m = map(int, a.month.split('-')); run_month(y, m, full_universe(), run_id)
    elif a.all:
        uni = full_universe(); print(f"[backfill] universe {len(uni)} tickers, months 2015-01..now")
        now = dt.date.today()
        for (y, m) in months((2015, 1), (now.year, now.month)):
            run_month(y, m, uni, run_id)
    else:
        print("specify --smoke | --month YYYY-MM | --all")
