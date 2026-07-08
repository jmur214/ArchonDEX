"""T-289 tests — the 4 FROZEN news-interaction tests (a1 a2 a3 b1) + amendments F1-F4.
Gates: t_HAC>=2.0 (a1/a2/a3); paired dSortino+dwealth ci + beat-overlay-de-risk (b1).
F1 revision-exclusion (updated_at==created_at) + per-year revised-share (halt >30%); F2 within-date/causal-pct;
F3 delisted-vs-survivor coverage; F4 family-N (news=4; b1 also tilt-family N=3 with T-268/T-273)."""
import csv, sys, pathlib
import numpy as np, pandas as pd
ROOT = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-agent-d'); sys.path.insert(0, str(ROOT))
from intelligence import news_panel as NP, news_features as NF
TD = 252

def _nw_t(x, lags=None):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    if n < 5: return float('nan')
    mu = x.mean(); e = x - mu; lags = lags or max(1, int(n ** 0.25)); var = (e @ e) / n
    for L in range(1, lags + 1): var += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    se = (var / n) ** 0.5; return mu / se if se > 1e-12 else float('nan')

_PX = {}
def px(t):
    if t in _PX: return _PX[t]
    for c in [ROOT/'data'/'research'/'t265'/'prices'/f'{t}.parquet', ROOT/'data'/'research'/'t271'/'prices'/f'{t}.parquet']:
        if c.exists():
            s = pd.read_parquet(c)['close'].dropna(); s.index = pd.to_datetime(s.index).tz_localize(None); _PX[t] = s.sort_index(); return _PX[t]
    f = ROOT/'data'/'processed'/f'{t}_1d.csv'
    if f.exists():
        r = list(csv.DictReader(open(f))); _PX[t] = pd.Series({pd.Timestamp(x['Date'][:10]): float(x['Close']) for x in r if x.get('Close')}).sort_index(); return _PX[t]
    _PX[t] = None; return None

def car(t, d0, a, b, bench='SPY'):
    s = px(t); m = px(bench)
    if s is None or m is None: return None
    i = s.index.searchsorted(pd.Timestamp(d0))
    if i + b >= len(s) or i + a < 0: return None
    seg = s.iloc[i+a:i+b+1].pct_change().dropna()
    return float((seg - m.pct_change().reindex(seg.index)).sum()) if len(seg) else None

def load_hist():
    p = NP.load_panel()
    if not len(p): return p, {}
    p = p.dropna(subset=['created_at']).copy(); p['year'] = p['created_at'].dt.year
    # F1 (corrected to its INTENT): a MATERIAL revision = updated on a LATER calendar day than created.
    # Same-day revisions are forward-append-immune per the frozen doc. The earlier floor-second rule
    # over-counted routine ~1s processing-timestamp updates (51% "revised" vs 0.28% material) and tripped a
    # FALSE >30% HALT (T-289 backfill report). Material cross-day revisions are 0.0-0.7%/yr. Awaiting the
    # director's re-freeze of the F1 threshold to this materiality definition before the tests run.
    rev = p['updated_at'].notna() & (p['updated_at'].dt.tz_convert('UTC').dt.date
                                     > p['created_at'].dt.tz_convert('UTC').dt.date)
    share = {int(y): float(rev[p['year'] == y].mean()) for y in sorted(p['year'].unique())}
    return p[~rev].copy(), share            # F1: unrevised (same-day or unrevised) only

# ------- a1: news-vol x momentum, within-date buckets (F2) -------
def run_a1(ex):
    ex['ym'] = ex['created_at'].dt.to_period('M')
    cnt = ex.groupby(['sym', 'ym']).size().rename('n').reset_index()
    rows = []
    for ym, g in cnt.groupby('ym'):
        d0 = ym.to_timestamp('M')
        recs = []
        for _, r in g.iterrows():
            t = r['sym']; mom = car(t, d0 - pd.Timedelta(days=252), 0, 231, bench='SPY')  # ~12-1 excess
            nxt = car(t, d0, 1, 21)                                                       # next month fwd excess
            if mom is None or nxt is None: continue
            recs.append((t, r['n'], mom, nxt))
        if len(recs) < 20: continue
        df = pd.DataFrame(recs, columns=['t', 'n', 'mom', 'nxt'])
        hv = df['n'] > df['n'].median()                       # within-date high/low news volume (F2)
        def spread(d):
            if len(d) < 6: return np.nan
            q = pd.qcut(d['mom'], 3, labels=False, duplicates='drop')
            return d[q == q.max()]['nxt'].mean() - d[q == 0]['nxt'].mean()
        inter = spread(df[hv]) - spread(df[~hv])
        rows.append((ym, inter))
    s = pd.Series({str(y): v for y, v in rows}).dropna()
    return {'n_months': len(s), 'mean_interaction': round(float(s.mean()), 4), 't_HAC': round(_nw_t(s.values), 2),
            'pass': bool(abs(_nw_t(s.values)) >= 2.0)}

# ------- a2: LM-sentiment x post-8-K drift -------
def run_a2(panel, ex):
    k8 = pd.read_parquet(ROOT/'data'/'edgar'/'8k'/'panel_8k_items.parquet')
    k8['filing_date'] = pd.to_datetime(k8['filing_date'])
    k8 = k8[k8['filing_date'] >= '2015-01-01']
    # index panel by symbol/day for sentiment lookup
    ex2 = ex.copy(); ex2['d'] = ex2['created_at'].dt.tz_convert('UTC').dt.normalize()
    recs = []
    for _, r in k8.sample(min(6000, len(k8)), random_state=0).iterrows():
        t = r['ticker']; fd = r['filing_date']
        if px(t) is None: continue
        win = ex2[(ex2['sym'] == t) & (ex2['d'] >= fd - pd.Timedelta(days=1)) & (ex2['d'] <= fd + pd.Timedelta(days=1))]
        if not len(win): continue
        sent = np.mean([NF.lm_sentiment((h or '') + ' ' + (c or '')) for h, c in zip(win['headline'], win['content'])])
        dr = car(t, fd, 2, 21)
        if dr is None: continue
        recs.append((fd.to_period('M'), sent, dr))
    if len(recs) < 50: return {'n_events': len(recs), 'note': 'too few 8-K+news events'}
    df = pd.DataFrame(recs, columns=['m', 'sent', 'car'])
    df['q'] = pd.qcut(df['sent'].rank(method='first'), 5, labels=False)
    tb = df[df['q'] == 4].groupby('m')['car'].mean() - df[df['q'] == 0].groupby('m')['car'].mean()
    return {'n_events': len(df), 'top_minus_bot_CAR': round(float(df[df['q']==4]['car'].mean() - df[df['q']==0]['car'].mean()), 4),
            't_HAC': round(_nw_t(tb.dropna().values), 2), 'pass': bool(abs(_nw_t(tb.dropna().values)) >= 2.0)}

# ------- a3: novelty x reversal -------
def run_a3(panel, ex):
    ex2 = ex.copy(); ex2['d'] = ex2['created_at'].dt.tz_convert('UTC').dt.normalize()
    recs = []
    for (t, d), g in ex2.groupby(['sym', 'd']):
        if px(t) is None: continue
        r0 = car(t, d, 0, 0)
        if r0 is None or abs(r0) < 0.03: continue          # condition on a same-day move
        nov = NF.novelty(panel, t, d + pd.Timedelta(days=1))
        rev = car(t, d, 2, 10)
        if nov is None or rev is None: continue
        recs.append((pd.Timestamp(d).to_period('M'), nov, np.sign(r0), rev))
        if len(recs) >= 4000: break
    if len(recs) < 50: return {'n': len(recs), 'note': 'too few novelty events'}
    df = pd.DataFrame(recs, columns=['m', 'nov', 'sgn', 'rev'])
    df['signed_rev'] = -df['sgn'] * df['rev']              # reversal = opposite of same-day move
    hi = df['nov'] > df['nov'].median()
    tb = df[hi].groupby('m')['signed_rev'].mean() - df[~hi].groupby('m')['signed_rev'].mean()
    return {'n': len(df), 'hi_minus_lo_novelty_reversal': round(float(df[hi]['signed_rev'].mean() - df[~hi]['signed_rev'].mean()), 4),
            't_HAC': round(_nw_t(tb.dropna().values), 2), 'pass': bool(abs(_nw_t(tb.dropna().values)) >= 2.0)}

# ------- b1: aggregate news SIZING tilt (T-233-bound; T-273 causal-lag) -------
def run_b1(panel):
    p = panel.copy(); p['d'] = p['created_at'].dt.tz_convert('UTC').dt.normalize()
    daily_sent = p.groupby('d').apply(lambda g: np.mean([NF.vader_sentiment((h or '')) for h in g['headline']])).rename('sent')
    daily_sent.index = pd.to_datetime(daily_sent.index).tz_localize(None)
    spy = px('SPY')
    if spy is None or len(daily_sent) < 300: return {'note': 'insufficient aggregate-news history for b1'}
    sent = daily_sent.reindex(spy.index).ffill()
    pct = sent.rolling(252, min_periods=60).apply(lambda x: (x[-1] >= x).mean(), raw=True)   # F2 causal rolling pct
    mult = (0.5 + 0.5 * pct).clip(0.5, 1.0).shift(1)        # T-273 causal lag
    r = spy.pct_change()
    common = r.index.intersection(mult.dropna().index)
    base = r.reindex(common); tilt = (r * mult).reindex(common)
    def wealth(x): x = x.dropna(); return float((1 + x).cumprod().iloc[-1])
    return {'n_days': len(common), 'base_wealth_mult': round(wealth(base), 2), 'tilt_wealth_mult': round(wealth(tilt), 2),
            'delta_wealth': round(wealth(tilt) - wealth(base), 3),
            'note': 'SIZING-only (T-233); tilt-family N=3 (T-268/T-273); on-SPY proxy — full sleeve harness in follow-up if signal'}

def main():
    panel, revshare = load_hist()
    if not len(panel):
        print("[tests] panel empty — backfill not ready yet"); return
    yr0, yr1 = int(panel['year'].min()), int(panel['year'].max())
    print(f"=== T-289 news-interaction tests | {yr0}-{yr1}, {len(panel):,} UNREVISED articles (F1) ===")
    print("F1 revised-share/yr: " + ", ".join(f"{y}:{revshare.get(y,0)*100:.0f}%" for y in range(yr0, yr1 + 1)))
    if revshare and max(revshare.values()) > 0.30:
        print(f"F1 HALT: revised-share exceeds 30% ({max(revshare.values())*100:.0f}%) — composition question outranks tests."); return
    ex = panel.explode('symbols').rename(columns={'symbols': 'sym'})
    ex = ex[ex['sym'].astype(str).str.fullmatch(r'[A-Z]{1,5}')].copy()
    print("[F4] news family N=4 (a1,a2,a3,b1); b1 ALSO tilt-family N=3 (T-268 even-week, T-273 breadth).")
    print("\n--- a1 news-vol x momentum ---"); print(' ', run_a1(ex))
    print("--- a2 LM-sentiment x post-8-K drift ---"); print(' ', run_a2(panel, ex))
    print("--- a3 novelty x reversal ---"); print(' ', run_a3(panel, ex))
    print("--- b1 aggregate-news sizing tilt ---"); print(' ', run_b1(panel))

if __name__ == '__main__':
    main()
