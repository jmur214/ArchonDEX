"""T-289a — Alpaca News (Benzinga) depth/survivorship/breadth PROBE. Gates the whole news lane.
Results -> data/intel/probe/. Verdicts: P1 D-deep/D-shallow, P2 S-clean/S-biased, P3 breadth."""
import os, json, pathlib, time, datetime as dt
from collections import defaultdict
ROOT = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-agent-d')
OUT = ROOT / 'data' / 'intel' / 'probe'; OUT.mkdir(parents=True, exist_ok=True)

env = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-2/.env')
for line in env.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest
from alpaca.common.enums import Sort
C = NewsClient(os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY'])

def fetch(symbols, start, end, limit=8000, asc=True):
    # alpaca-py get_news auto-paginates internally; `limit` is the TOTAL cap.
    req = NewsRequest(symbols=symbols, start=start, end=end, limit=limit, sort=Sort.ASC if asc else Sort.DESC)
    try:
        r = C.get_news(req); return r.data.get('news', []) if hasattr(r, 'data') else []
    except Exception as e:
        print(f"  ERR {symbols}: {str(e)[:80]}"); return []

results = {}

# ---- P1 DEPTH ----
print("=== P1 DEPTH (earliest created_at, fetch ASC from 2010) ===")
p1 = {}
for t in ['SPY', 'AAPL', 'TSLA']:
    it = fetch(t, dt.datetime(2010, 1, 1), dt.datetime(2026, 1, 1), limit=5)
    earliest = str(it[0].created_at)[:10] if it else None
    p1[t] = earliest
    print(f"  {t}: earliest article = {earliest}")
earliest_all = min([v for v in p1.values() if v], default=None)
D_verdict = 'D-deep' if (earliest_all and earliest_all <= '2016-12-31') else 'D-shallow'
print(f"  -> earliest across probes = {earliest_all}  VERDICT: {D_verdict}")
results['P1_depth'] = {'per_ticker': p1, 'earliest': earliest_all, 'verdict': D_verdict}

# ---- P2 SURVIVORSHIP (dead tickers over their pre-delisting window) ----
print("\n=== P2 SURVIVORSHIP (delisted tickers — is their news retained?) ===")
dead = {'SIVB': ('2016-01-01', '2023-03-09'), 'FRC': ('2016-01-01', '2023-04-28'),
        'TWTR': ('2015-01-01', '2022-10-27'), 'BBBY': ('2016-01-01', '2023-04-25')}
p2 = {}
for t, (s, e) in dead.items():
    it = fetch(t, dt.datetime.fromisoformat(s), dt.datetime.fromisoformat(e), limit=8000)
    dates = sorted(str(x.created_at)[:10] for x in it)
    p2[t] = {'n': len(it), 'first': dates[0] if dates else None, 'last': dates[-1] if dates else None}
    print(f"  {t}: {len(it)} articles, {p2[t]['first']}..{p2[t]['last']}")
covered = sum(1 for v in p2.values() if v['n'] >= 20)
S_verdict = 'S-clean' if covered >= 3 else 'S-biased'
print(f"  -> {covered}/4 dead tickers well-covered  VERDICT: {S_verdict}")
results['P2_survivorship'] = {'per_ticker': p2, 'covered': covered, 'verdict': S_verdict}

# ---- P3 BREADTH (articles/ticker across cap terciles, 2022-06) ----
print("\n=== P3 BREADTH (articles/ticker by cap tier, 2022-06) ===")
tiers = {
    'mega/large': ['AAPL', 'MSFT', 'JPM', 'XOM', 'PG', 'HD'],
    'mid': ['ETSY', 'DKS', 'BILL', 'RH', 'WING', 'DECK'],
    'small': ['PLCE', 'SBH', 'CAL', 'EGBN', 'SCVL', 'DXPE'],
}
s2, e2 = dt.datetime(2022, 6, 1), dt.datetime(2022, 7, 1)
p3 = {}
for tier, syms in tiers.items():
    per = {}
    for t in syms:
        it = fetch(t, s2, e2, limit=5000)
        per[t] = len(it)
    vals = list(per.values()); med = sorted(vals)[len(vals) // 2]
    p3[tier] = {'per_ticker': per, 'median': med, 'mean': round(sum(vals) / len(vals), 1)}
    print(f"  {tier:12}: median {med} art/ticker, mean {p3[tier]['mean']}  {per}")
results['P3_breadth'] = p3

(OUT / 'probe_results_t289a.json').write_text(json.dumps(results, indent=2, default=str))
print(f"\n[probe] results -> {OUT / 'probe_results_t289a.json'}")
print(f"\nVERDICTS: P1={D_verdict} (earliest {earliest_all}) | P2={S_verdict} ({covered}/4 dead covered) | "
      f"P3 breadth: large med {p3['mega/large']['median']}, mid {p3['mid']['median']}, small {p3['small']['median']}")
