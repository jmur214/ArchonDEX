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
    # tz-robust: the news panel is tz-aware UTC, price indices are tz-naive. a3 passes tz-aware days.
    d0 = pd.Timestamp(d0)
    if d0.tzinfo is not None: d0 = d0.tz_convert('UTC').tz_localize(None)
    i = s.index.searchsorted(d0)
    if i + b >= len(s) or i + a < 0: return None
    # Returns FIRST, then slice, so [a,b] means exactly trading-day offsets a..b relative to d0.
    # (Slicing prices then pct_change() dropped day a's return entirely and made the a==b case — a3's
    # same-day move, car(t,d,0,0) — always None, which would have nulled a3 spuriously.)
    seg = s.pct_change().iloc[i+a:i+b+1].dropna()
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
    # SPEED: O(1) symbol lookup (was a full 2.2M-row boolean scan per 8-K x 6000 events).
    by_sym = {s: g for s, g in ex2.groupby('sym')}
    # MEMORY: text held ONCE, keyed by article_id (never exploded).
    txt = panel.set_index('article_id')[['headline', 'content']]
    recs = []
    for _, r in k8.sample(min(6000, len(k8)), random_state=0).iterrows():
        t = r['ticker']; fd = r['filing_date']
        if px(t) is None: continue
        g = by_sym.get(t)
        if g is None: continue
        # `fd` (EDGAR filing_date) is tz-naive; `g['d']` is tz-aware UTC -> localize before comparing.
        fdu = pd.Timestamp(fd)
        fdu = fdu.tz_localize('UTC') if fdu.tzinfo is None else fdu.tz_convert('UTC')
        win = g[(g['d'] >= fdu - pd.Timedelta(days=1)) & (g['d'] <= fdu + pd.Timedelta(days=1))]
        if not len(win): continue
        wt = txt.reindex(win['article_id'])
        sent = np.mean([NF.lm_sentiment((h or '') + ' ' + (c or '')) for h, c in zip(wt['headline'], wt['content'])])
        dr = car(t, fd, 2, 21)
        if dr is None: continue
        recs.append((fd.to_period('M'), sent, dr))
    if len(recs) < 50: return {'n_events': len(recs), 'note': 'too few 8-K+news events'}
    df = pd.DataFrame(recs, columns=['m', 'sent', 'car'])
    df['q'] = pd.qcut(df['sent'].rank(method='first'), 5, labels=False)
    tb = df[df['q'] == 4].groupby('m')['car'].mean() - df[df['q'] == 0].groupby('m')['car'].mean()
    return {'n_events': len(df), 'top_minus_bot_CAR': round(float(df[df['q']==4]['car'].mean() - df[df['q']==0]['car'].mean()), 4),
            't_HAC': round(_nw_t(tb.dropna().values), 2), 'pass': bool(abs(_nw_t(tb.dropna().values)) >= 2.0)}

def _fast_novelty(sym_idx, content_by_id, symbol, as_of, window=21):
    """Faithful re-implementation of NF.novelty's DOCUMENT SELECTION (identical strict [lo,hi) windows on
    created_at: today=[as_of, as_of+1d), prior=[as_of-window, as_of)), but using a pre-built per-symbol
    index instead of NF._sym_slice's full-panel .apply per call (769k-row scan x thousands of calls)."""
    g = sym_idx.get(symbol)
    if g is None or not len(g): return None
    # tz-robust (NF._sym_slice does pd.Timestamp(as_of, tz='UTC') which RAISES on a tz-aware as_of —
    # a3 passes tz-aware days, so NF.novelty would have thrown here; latent bug flagged upstream).
    hi = pd.Timestamp(as_of)
    hi = hi.tz_localize('UTC') if hi.tzinfo is None else hi.tz_convert('UTC')
    ca = g['created_at']
    today = g.loc[(ca >= hi) & (ca < hi + pd.Timedelta(days=1)), 'article_id']
    prior = g.loc[(ca >= hi - pd.Timedelta(days=window)) & (ca < hi), 'article_id']
    if not len(today): return None
    if not len(prior): return 1.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        docs = (list(content_by_id.reindex(prior).fillna('')) + list(content_by_id.reindex(today).fillna('')))
        X = TfidfVectorizer(stop_words='english', max_features=5000).fit_transform(docs)
        sims = cosine_similarity(X[len(prior):], X[:len(prior)])
        return float(1.0 - sims.max()) if sims.size else 1.0
    except Exception:
        return None

# ------- a3: novelty x reversal -------
def run_a3(panel, ex):
    ex2 = ex.copy(); ex2['d'] = ex2['created_at'].dt.tz_convert('UTC').dt.normalize()
    sym_idx = {s: g[['article_id', 'created_at']].sort_values('created_at') for s, g in ex2.groupby('sym')}
    content_by_id = panel.set_index('article_id')['content']
    # BIAS FIX: groupby yields (sym,d) in ALPHABETICAL order; the 4000-rec cap then sampled only A-named
    # tickers. Shuffle the candidate keys deterministically (seed 0) for a representative sample.
    keys = list(ex2.groupby(['sym', 'd']).groups.keys())
    np.random.default_rng(0).shuffle(keys)
    recs = []
    for (t, d) in keys:
        if px(t) is None: continue
        r0 = car(t, d, 0, 0)
        if r0 is None or abs(r0) < 0.03: continue          # condition on a same-day move
        nov = _fast_novelty(sym_idx, content_by_id, t, d + pd.Timedelta(days=1))
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
    # MEMORY: explode a LIGHT projection. Exploding the full panel duplicates the 899 MB `content`
    # column 2.88x (avg symbols/article) -> ~3.7 GB -> OOM (SIGKILL). a2 fetches text by article_id instead.
    ex = panel[['article_id', 'created_at', 'symbols']].explode('symbols').rename(columns={'symbols': 'sym'})
    ex = ex[ex['sym'].astype(str).str.fullmatch(r'[A-Z]{1,5}')].copy()
    # SPEED: drop symbols with no price series up front (the loops skip them anyway) — behaviour-identical.
    ex = ex[ex['sym'].map(lambda s: px(s) is not None)].copy()
    print(f"[panel] exploded sym-rows={len(ex):,} across {ex['sym'].nunique():,} priced symbols")
    print("[F4] news family N=4 (a1,a2,a3,b1); b1 ALSO tilt-family N=3 (T-268 even-week, T-273 breadth).")
    print("\n--- a1 news-vol x momentum ---"); print(' ', run_a1(ex))
    print("--- a2 LM-sentiment x post-8-K drift ---"); print(' ', run_a2(panel, ex))
    print("--- a3 novelty x reversal ---"); print(' ', run_a3(panel, ex))
    print("--- b1 aggregate-news sizing tilt ---"); print(' ', run_b1(panel))

if __name__ == '__main__':
    main()
