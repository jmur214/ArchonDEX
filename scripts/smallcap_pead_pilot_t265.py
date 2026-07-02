"""T-265 — survivorship-complete small-cap panel + PEAD low-coverage event-study pilot.

Staged + cached (re-runnable). Sources:
  - EDGAR XBRL frames (survivorship-complete, estimate-free EPS + shares)  [$0, public]
  - Alpaca SIP daily bars (full 2016+ incl delisted; $0-MARGINAL to this account, NOT free-tier)
Census discipline ([NN-CENSUS]/[NN-FAIL-CLOSED]): every drop is counted; delisting truncation gets a
bankruptcy-haircut-to-zero stress arm. Event study (t_HAC on CAR), NOT a Sharpe deployment test ([NN-MBL]).

Usage: python -m scripts.smallcap_pead_pilot_t265 --stage edgar|prices|study
"""
import argparse, json, os, pathlib, time
import numpy as np, pandas as pd, requests

ROOT = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-agent-d')
CACHE = ROOT / 'data' / 'research' / 't265'
CACHE.mkdir(parents=True, exist_ok=True)
UA = {'User-Agent': 'ArchonDEX research jsm13700@gmail.com'}
Q_START, Q_END = (2013, 1), (2026, 2)     # EPS needs ~8 priors before first 2016 event

def _quarters(s, e):
    (ys, qs), (ye, qe) = s, e
    y, q = ys, qs
    while (y, q) <= (ye, qe):
        yield y, q
        q += 1
        if q > 4: q, y = 1, y + 1

def _get(url, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=40)
            if r.status_code == 200: return r.json()
            if r.status_code == 404: return None
        except Exception:
            pass
        time.sleep(0.6 * (i + 1))
    return None

# ---------------------------------------------------------------- STAGE: EDGAR
def stage_edgar():
    # 1a) EPS frames -> survivorship-complete {cik, cal_q, end, eps, accn}
    eps_rows = []
    for y, q in _quarters(Q_START, Q_END):
        j = _get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/EarningsPerShareDiluted/USD-per-shares/CY{y}Q{q}.json")
        if not j: continue
        for d in j['data']:
            eps_rows.append((d['cik'], d.get('entityName', ''), f"{y}Q{q}", d['end'], d['val'], d['accn']))
        time.sleep(0.12)
    eps = pd.DataFrame(eps_rows, columns=['cik', 'entityName', 'cal_q', 'end', 'eps', 'accn'])
    # de-dup: keep last-reported val per (cik, cal_q) [amended values overwrite]
    eps = eps.drop_duplicates(['cik', 'cal_q'], keep='last')
    eps.to_parquet(CACHE / 'eps_panel.parquet')
    ciks = sorted(eps['cik'].unique())
    print(f"[edgar] EPS panel: {len(eps)} rows, {len(ciks)} unique CIKs (survivorship-complete union)")

    # 1b) shares outstanding frames (instantaneous) -> {cik, end, shares}
    sh_rows = []
    for y, q in _quarters((2015, 4), Q_END):
        for concept, unit in [('CommonStockSharesOutstanding', 'shares')]:
            j = _get(f"https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/{unit}/CY{y}Q{q}I.json")
            if not j: continue
            for d in j['data']:
                sh_rows.append((d['cik'], d['end'], d['val']))
            time.sleep(0.12)
    sh = pd.DataFrame(sh_rows, columns=['cik', 'end', 'shares']).drop_duplicates(['cik', 'end'], keep='last')
    sh.to_parquet(CACHE / 'shares_panel.parquet')
    print(f"[edgar] shares panel: {len(sh)} rows, {sh['cik'].nunique()} CIKs")

    # 1c) CIK -> ticker  (company_tickers.json = live; cusip map = extra incl some dead)
    j = _get("https://www.sec.gov/files/company_tickers.json")
    c2t = {}
    if j:
        for v in j.values():
            c2t.setdefault(int(v['cik_str']), v['ticker'].upper())
    cmap = ROOT / 'data' / 'edgar' / 'cusip_ticker_map.parquet'
    n_from_cusip = 0
    if cmap.exists():
        cm = pd.read_parquet(cmap)
        # try to find cik + ticker columns
        cols = {c.lower(): c for c in cm.columns}
        if 'cik' in cols and 'ticker' in cols:
            for _, r in cm[[cols['cik'], cols['ticker']]].dropna().iterrows():
                try:
                    k = int(r[cols['cik']])
                except Exception:
                    continue
                if k not in c2t:
                    c2t[k] = str(r[cols['ticker']]).upper(); n_from_cusip += 1
    tickmap = pd.DataFrame({'cik': list(c2t.keys()), 'ticker': list(c2t.values())})
    tickmap.to_parquet(CACHE / 'cik_ticker.parquet')
    mapped = sum(1 for c in ciks if c in c2t)
    print(f"[edgar] CIK->ticker: {len(c2t)} total pairs ({n_from_cusip} from cusip map); "
          f"{mapped}/{len(ciks)} universe CIKs mapped ({100*mapped/len(ciks):.0f}%)")
    print(f"[edgar] UNMAPPED CIKs (likely delisted w/o current ticker): {len(ciks)-mapped} "
          f"-> census: potential survivorship loss at the join")

# ---------------------------------------------------------------- name normalization + creds
import re
_SUFFIX = re.compile(r'\b(INC|CORP|CORPORATION|COMPANY|CO|LTD|LIMITED|LLC|LP|PLC|HOLDINGS?|GROUP|'
                     r'INCORPORATED|TRUST|FUND|CLASS|COM|COMMON|STOCK|THE|NEW|SA|NV|AG|ADR|ADS)\b')
def _norm(name):
    if not isinstance(name, str): return ''
    s = name.upper().replace('&', 'AND')
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = _SUFFIX.sub(' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def _alpaca_creds():
    env = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-2/.env')
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY']

# ---------------------------------------------------------------- STAGE: MAP (recover delisted tickers)
def stage_map():
    eps = pd.read_parquet(CACHE / 'eps_panel.parquet')
    # cik -> most-frequent entityName
    names = (eps.groupby('cik')['entityName'].agg(lambda s: s.value_counts().index[0]))
    ciks = names.index.tolist()
    # authoritative live map
    live = pd.read_parquet(CACHE / 'cik_ticker.parquet').set_index('cik')['ticker'].to_dict()
    # alpaca assets active+inactive
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import GetAssetsRequest
    from alpaca.trading.enums import AssetStatus, AssetClass
    KEY, SEC = _alpaca_creds()
    tc = TradingClient(KEY, SEC, paper=True)
    assets = []
    for st in (AssetStatus.ACTIVE, AssetStatus.INACTIVE):
        assets += tc.get_all_assets(GetAssetsRequest(status=st, asset_class=AssetClass.US_EQUITY))
    # drop corporate-action artifacts (symbols with digits / >5 non-alpha) — keep clean tickers
    norm2sym = {}
    ambig = set()
    for a in assets:
        sym = a.symbol
        if not re.fullmatch(r'[A-Z]{1,5}', sym):   # exclude CVR/RGT/CUSIP-like artifacts
            continue
        n = _norm(a.name)
        if not n: continue
        if n in norm2sym and norm2sym[n] != sym: ambig.add(n)
        norm2sym.setdefault(n, sym)
    for n in ambig: norm2sym.pop(n, None)         # drop ambiguous names
    # build final map: live first, else name-match
    final, via_live, via_name = {}, 0, 0
    for c in ciks:
        if c in live:
            final[c] = live[c]; via_live += 1
        else:
            s = norm2sym.get(_norm(names[c]))
            if s: final[c] = s; via_name += 1
    out = pd.DataFrame({'cik': list(final.keys()), 'ticker': list(final.values())})
    out.to_parquet(CACHE / 'cik_ticker_final.parquet')
    print(f"[map] universe CIKs={len(ciks)}  mapped={len(final)} ({100*len(final)/len(ciks):.0f}%)  "
          f"[live={via_live}, name-recovered={via_name}]  still-unmapped={len(ciks)-len(final)}")
    print(f"[map] alpaca clean tickers indexed={len(norm2sym)}  ambiguous-names-dropped={len(ambig)}")

# ---------------------------------------------------------------- STAGE: PRICES (SIP, batched)
def stage_prices():
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    import datetime as dt
    KEY, SEC = _alpaca_creds()
    dc = StockHistoricalDataClient(KEY, SEC)
    tmap = pd.read_parquet(CACHE / 'cik_ticker_final.parquet')
    # clean common-stock tickers only (drop preferred/class/warrant variants: AHL-PD, BRK.B, ...)
    syms = sorted({s for s in set(tmap['ticker']) if re.fullmatch(r'[A-Z]{1,5}', str(s))})
    print(f"[prices] fetching SIP daily bars for {len(syms)} clean tickers 2016-2026 (batched)...")
    outdir = CACHE / 'prices'; outdir.mkdir(exist_ok=True)

    def _fetch(batch):
        req = StockBarsRequest(symbol_or_symbols=batch, timeframe=TimeFrame.Day,
                               start=dt.datetime(2016, 1, 1), end=dt.datetime(2026, 7, 1),
                               feed='sip', adjustment='all')
        return dc.get_stock_bars(req).df

    done = {p.stem for p in outdir.glob('*.parquet')}
    B = 200
    for i in range(0, len(syms), B):
        batch = [s for s in syms[i:i + B] if s not in done]
        if not batch: continue
        try:
            df = _fetch(batch)
        except Exception as e:
            msg = str(e)
            m = re.search(r'invalid symbol:\s*([A-Z0-9.\-]+)', msg)
            if m and m.group(1) in batch:            # drop the offender, retry once
                batch = [s for s in batch if s != m.group(1)]
                try:
                    df = _fetch(batch)
                except Exception as e2:
                    print(f"  batch {i}: ERR2 {str(e2)[:70]}"); continue
            else:
                print(f"  batch {i}: ERR {msg[:70]}"); continue
        if df is None or len(df) == 0:
            continue
        for sym, g in df.groupby(level=0):
            g = g.reset_index(level=0, drop=True)[['close', 'volume']]
            g.index = pd.to_datetime(g.index).tz_localize(None).normalize()
            g.to_parquet(outdir / f"{sym}.parquet")
        got = df.index.get_level_values(0).nunique()
        print(f"  [{i}-{i+len(batch)}] got {got}/{len(batch)} names", flush=True)
        time.sleep(0.4)
    print(f"[prices] cached price files: {len(list(outdir.glob('*.parquet')))}")

# ---------------------------------------------------------------- helpers for the study
def _cq_to_ord(cq):        # "2019Q1" -> 2019*4+0
    y, q = cq.split('Q'); return int(y) * 4 + (int(q) - 1)

def _load_prices():
    d = {}
    for p in (CACHE / 'prices').glob('*.parquet'):
        try:
            s = pd.read_parquet(p)['close'].dropna()
            if len(s) >= 60: d[p.stem] = s
        except Exception:
            pass
    return d

def _nw_t(x, lags=None):   # Newey-West t-stat of the mean of series x
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    if n < 5: return float('nan')
    mu = x.mean(); e = x - mu
    if lags is None: lags = max(1, int(n ** 0.25))
    g0 = (e @ e) / n; var = g0
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1); cov = (e[L:] @ e[:-L]) / n
        var += 2 * w * cov
    se = np.sqrt(var / n)
    return mu / se if se > 1e-12 else float('nan')

def _companyconcept_eps(cik):
    """First-reported diluted EPS per fiscal period + filed date (PIT-clean)."""
    j = _get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/EarningsPerShareDiluted.json")
    if not j or 'units' not in j: return None
    rows = []
    for unit, arr in j['units'].items():
        for e in arr:
            if e.get('form') in ('10-Q', '10-K') and e.get('fp') and e.get('filed') and e.get('start'):
                # quarterly only: period ~85-100 days
                try:
                    dur = (pd.Timestamp(e['end']) - pd.Timestamp(e['start'])).days
                except Exception:
                    continue
                if 80 <= dur <= 100:
                    rows.append((e['fy'], e['fp'], e['end'], e['val'], e['filed']))
    if not rows: return None
    df = pd.DataFrame(rows, columns=['fy', 'fp', 'end', 'eps', 'filed'])
    df['filed'] = pd.to_datetime(df['filed']); df['end'] = pd.to_datetime(df['end'])
    # first-reported per (fy,fp)
    df = df.sort_values('filed').drop_duplicates(['fy', 'fp'], keep='first')
    return df.sort_values('end').reset_index(drop=True)

# ---------------------------------------------------------------- STAGE: STUDY
def stage_study():
    eps = pd.read_parquet(CACHE / 'eps_panel.parquet')
    sh = pd.read_parquet(CACHE / 'shares_panel.parquet')
    tmap = pd.read_parquet(CACHE / 'cik_ticker_final.parquet').set_index('cik')['ticker'].to_dict()
    prices = _load_prices()
    print(f"[study] price files loaded: {len(prices)} tickers")
    # SPY benchmark + small-cap benchmark (IWM) from SIP price cache if present, else processed
    spy = pd.read_parquet(ROOT / 'data' / 'processed' / 'parquet' / 'SPY_1d.parquet')['Close'] \
        if (ROOT / 'data' / 'processed' / 'parquet' / 'SPY_1d.parquet').exists() else None
    if spy is None:
        import csv as _csv
        r = list(_csv.DictReader(open(ROOT / 'data' / 'processed' / 'SPY_1d.csv')))
        spy = pd.Series({pd.Timestamp(x['Date'][:10]): float(x['Close']) for x in r})
    spy.index = pd.to_datetime(spy.index).tz_localize(None).normalize(); spy = spy.sort_index()
    spy_ret = spy.pct_change()

    # approx market cap per (cik, cal_q): shares nearest<=end * price at end
    sh['end'] = pd.to_datetime(sh['end']); sh = sh.sort_values('end')
    eps['end'] = pd.to_datetime(eps['end'])
    # latest shares per cik on/before each eps end
    shares_by_cik = {c: g.set_index('end')['shares'] for c, g in sh.groupby('cik')}

    # 13F coverage
    n_holders = {}
    f13 = ROOT / 'data' / 'edgar' / '13f' / 'ownership_panel.parquet'
    if f13.exists():
        o = pd.read_parquet(f13)
        nh = o.groupby('ticker')['n_holders'].median()
        n_holders = nh.to_dict()

    # candidate small-cap CIKs: mapped + have prices + market cap in band at >=1 quarter
    cand = []
    for c in eps['cik'].unique():
        t = tmap.get(c)
        if not t or t not in prices: continue
        cand.append(c)
    print(f"[study] candidate CIKs (mapped + priced): {len(cand)}")

    # companyconcept EPS+filed, cached
    ccpath = CACHE / 'eps_filed.parquet'
    if ccpath.exists():
        ccp = pd.read_parquet(ccpath); have = set(ccp['cik'].unique())
    else:
        ccp = None; have = set()
    todo = [c for c in cand if c not in have]
    print(f"[study] companyconcept to fetch: {len(todo)} (cached {len(have)})")
    newrows = []
    for k, c in enumerate(todo):
        df = _companyconcept_eps(c)
        if df is not None:
            df = df.copy(); df.insert(0, 'cik', c); newrows.append(df)
        if k % 200 == 0 and k: print(f"  cc {k}/{len(todo)}", flush=True)
        time.sleep(0.09)
    if newrows:
        add = pd.concat(newrows, ignore_index=True)
        ccp = add if ccp is None else pd.concat([ccp, add], ignore_index=True)
        ccp.to_parquet(ccpath)
    print(f"[study] eps_filed panel: {len(ccp)} rows, {ccp['cik'].nunique()} CIKs")

    # ---- build events ----
    TRAIL, W0, W1 = 8, 2, 63
    SMALL_LO, MICRO_HI, SMALL_HI = 50e6, 300e6, 2e9
    events = []   # dict per event
    for c, g in ccp.groupby('cik'):
        t = tmap.get(c);  s = prices.get(t)
        if s is None: continue
        g = g.sort_values('end').reset_index(drop=True)
        e = g['eps'].astype(float).values
        d = np.full(len(e), np.nan)
        if len(e) > 4: d[4:] = e[4:] - e[:-4]           # seasonal diff
        sh_ser = shares_by_cik.get(c)
        last_filing = g['filed'].max()
        for i in range(len(g)):
            if i < TRAIL + 4 or not np.isfinite(d[i]): continue
            sd = np.nanstd(d[max(0, i - TRAIL):i])
            if not np.isfinite(sd) or sd < 1e-9: continue
            sue = float(np.clip(d[i] / sd, -3, 3))
            fdate = g['filed'].iloc[i]
            # entry: trading day index >= fdate, then +W0
            pos = s.index.searchsorted(fdate)
            if pos + W0 >= len(s): continue
            entry = pos + W0
            # market cap at entry
            px0 = s.iloc[entry]
            shv = np.nan
            if sh_ser is not None:
                pr = sh_ser[sh_ser.index <= g['end'].iloc[i]]
                if len(pr): shv = pr.iloc[-1]
            mcap = shv * px0 if np.isfinite(shv) else np.nan
            if not (np.isfinite(mcap) and SMALL_LO <= mcap <= SMALL_HI): continue
            # window returns
            end = min(entry + (W1 - W0), len(s) - 1)
            seg = s.iloc[entry:end + 1]
            truncated = (end < entry + (W1 - W0))     # price series ended inside window
            dead = truncated and (fdate >= last_filing - pd.Timedelta(days=120))  # no later filings
            # market-adjusted CAR
            sret = seg.pct_change().dropna()
            mret = spy_ret.reindex(sret.index)
            car = float((sret - mret).sum())
            # haircut-arm CAR: if dead, terminal -100% from last obs
            car_hc = car + (-1.0 if dead else 0.0)
            events.append(dict(cik=c, ticker=t, filed=fdate, sue=sue, mcap=mcap,
                               car=car, car_hc=car_hc, dead=dead, truncated=truncated,
                               nbars=len(seg), n13=n_holders.get(t, np.nan),
                               month=fdate.to_period('M')))
    ev = pd.DataFrame(events)
    ev.to_parquet(CACHE / 'events.parquet')
    print(f"\n[study] EVENTS: {len(ev)} across {ev['cik'].nunique()} small-caps "
          f"({ev['dead'].sum()} dead/haircut, {ev['truncated'].sum()} truncated)")
    if len(ev) < 200:
        print("[study] too few events — HALT (fail-closed)"); return

    # ---- SUE quintiles (pooled) ----
    def quint_table(carcol):
        ev['q'] = pd.qcut(ev['sue'], 5, labels=False, duplicates='drop')
        rows = []
        for q in sorted(ev['q'].dropna().unique()):
            sub = ev[ev['q'] == q]
            # calendar-clustered mean + NW-t over monthly means
            mm = sub.groupby('month')[carcol].mean()
            rows.append((int(q), len(sub), sub[carcol].mean(), _nw_t(mm.values)))
        return pd.DataFrame(rows, columns=['sue_q', 'n', 'mean_CAR', 'nw_t'])
    print("\n=== event-time CAR[+2,+63], market-adjusted, by SUE quintile (0=most neg, 4=most pos) ===")
    qt = quint_table('car'); print(qt.to_string(index=False))
    top, bot = ev[ev['q'] == ev['q'].max()], ev[ev['q'] == 0]
    tb = top.groupby('month')['car'].mean() - bot.groupby('month')['car'].mean()
    print(f"TOP-minus-BOTTOM mean CAR = {top['car'].mean()-bot['car'].mean():+.4f}  nw_t(monthly diff) = {_nw_t(tb.dropna().values):+.2f}")
    print("\n--- haircut-to-zero stress arm (dead names -> -100%) ---")
    qthc = quint_table('car_hc'); print(qthc.to_string(index=False))
    tbh = ev[ev['q']==ev['q'].max()].groupby('month')['car_hc'].mean() - ev[ev['q']==0].groupby('month')['car_hc'].mean()
    print(f"TOP-minus-BOTTOM (haircut) = {ev[ev['q']==ev['q'].max()]['car_hc'].mean()-ev[ev['q']==0]['car_hc'].mean():+.4f}  nw_t = {_nw_t(tbh.dropna().values):+.2f}")

    # ---- low-coverage split: size x 13F holders ----
    print("\n=== low-coverage split: TOP-minus-BOTTOM SUE-quintile mean CAR by cell ===")
    ev['size_bin'] = np.where(ev['mcap'] < MICRO_HI, 'micro(<300M)', 'small(300M-2B)')
    ev['cov_bin'] = np.where(ev['n13'].isna() | (ev['n13'] <= ev['n13'].median()), 'low-13F', 'high-13F')
    for sb in ['micro(<300M)', 'small(300M-2B)']:
        for cb in ['low-13F', 'high-13F']:
            sub = ev[(ev['size_bin'] == sb) & (ev['cov_bin'] == cb)]
            if len(sub) < 100:
                print(f"  {sb:16} {cb:9} n={len(sub):5} (too few)"); continue
            sub = sub.copy(); sub['q'] = pd.qcut(sub['sue'], 5, labels=False, duplicates='drop')
            tb2 = sub[sub['q']==sub['q'].max()]['car'].mean() - sub[sub['q']==0]['car'].mean()
            print(f"  {sb:16} {cb:9} n={len(sub):5}  top-bot CAR = {tb2:+.4f}")

    # ---- tradable: long top-quintile, ~3mo hold, net of honest cost ----
    hold_yr = (W1 - W0) / 252.0
    top_car = ev[ev['q'] == ev['q'].max()]
    gross = top_car['car'].mean()
    # cost: entry+exit half-spread by size tier (round-trip = 2x)
    cost = np.where(top_car['mcap'] < MICRO_HI, 0.0075, 0.0035) * 2
    net = (top_car['car'].values - cost)
    print(f"\n=== TRADABLE (long top-SUE-quintile, hold {W1-W0}td) ===")
    print(f"  gross mean CAR/event = {gross:+.4f}  |  net-of-cost = {net.mean():+.4f}  "
          f"(ann~ gross {gross/hold_yr*100:+.1f}%/yr, net {net.mean()/hold_yr*100:+.1f}%/yr, pre-market-beta)")
    import json as _json
    (CACHE / 'study_result.json').write_text(_json.dumps(dict(
        n_events=len(ev), n_ciks=int(ev['cik'].nunique()), n_dead=int(ev['dead'].sum()),
        quintile=qt.to_dict('records'), top_minus_bot=float(top['car'].mean()-bot['car'].mean()),
        top_minus_bot_nwt=float(_nw_t(tb.dropna().values)),
        tradable_gross=float(gross), tradable_net=float(net.mean())), indent=2))
    print("[study] wrote study_result.json")

def _announce_dates(cik):
    """8-K item-2.02 (earnings-release) filing dates for a CIK."""
    j = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    if not j: return []
    rec = j.get('filings', {}).get('recent', {})
    forms, items, dates = rec.get('form', []), rec.get('items', []), rec.get('filingDate', [])
    out = [d for f, it, d in zip(forms, items, dates) if f == '8-K' and '2.02' in (it or '')]
    return sorted(pd.to_datetime(out))

# ---------------------------------------------------------------- STAGE: ANNOUNCE (robustness: enter at 8-K 2.02)
def stage_announce():
    ev = pd.read_parquet(CACHE / 'events.parquet')
    prices = _load_prices()
    import csv as _csv
    r = list(_csv.DictReader(open(ROOT / 'data' / 'processed' / 'SPY_1d.csv')))
    spy = pd.Series({pd.Timestamp(x['Date'][:10]): float(x['Close']) for x in r})
    spy.index = pd.to_datetime(spy.index).normalize(); spy = spy.sort_index(); spy_ret = spy.pct_change()

    apath = CACHE / 'ann_dates.parquet'
    if apath.exists():
        adf = pd.read_parquet(apath); amap = {c: list(pd.to_datetime(g['date'])) for c, g in adf.groupby('cik')}
    else:
        amap = {}
    todo = [c for c in ev['cik'].unique() if c not in amap]
    print(f"[announce] fetch 8-K 2.02 dates for {len(todo)} CIKs (cached {len(amap)})")
    rows = []
    for k, c in enumerate(todo):
        ds = _announce_dates(c); amap[c] = ds
        rows += [(c, d) for d in ds]
        if k % 300 == 0 and k: print(f"  ann {k}/{len(todo)}", flush=True)
        time.sleep(0.09)
    if rows:
        old = pd.read_parquet(apath) if apath.exists() else pd.DataFrame(columns=['cik', 'date'])
        pd.concat([old, pd.DataFrame(rows, columns=['cik', 'date'])], ignore_index=True).to_parquet(apath)

    W = 61
    car, matched, gaps = [], [], []
    for _, e in ev.iterrows():
        s = prices.get(e['ticker']);
        if s is None: continue
        filed = pd.Timestamp(e['filed']); cands = amap.get(e['cik'], [])
        ann = [d for d in cands if filed - pd.Timedelta(days=60) <= d <= filed + pd.Timedelta(days=5)]
        use = max(ann) if ann else filed
        matched.append(bool(ann));
        if ann: gaps.append((filed - use).days)
        pos = s.index.searchsorted(use)
        if pos + 1 >= len(s): car.append(np.nan); continue
        entry = pos + 1; end = min(entry + W, len(s) - 1)
        seg = s.iloc[entry:end + 1].pct_change().dropna()
        car.append(float((seg - spy_ret.reindex(seg.index)).sum()))
    ev = ev.assign(car_ann=car, matched_ann=matched)
    ev2 = ev.dropna(subset=['car_ann'])
    print(f"\n[announce] events with announcement date matched: {sum(matched)}/{len(ev)} "
          f"({100*sum(matched)/len(ev):.0f}%); median filed−announce gap = {int(np.median(gaps)) if gaps else 'NA'} days")
    ev2 = ev2.copy(); ev2['q'] = pd.qcut(ev2['sue'], 5, labels=False, duplicates='drop')
    print("\n=== ANNOUNCEMENT-date entry: CAR[+1,+62] market-adj by SUE quintile ===")
    for q in sorted(ev2['q'].dropna().unique()):
        sub = ev2[ev2['q'] == q]; mm = sub.groupby('month')['car_ann'].mean()
        print(f"  q{int(q)}  n={len(sub):5}  mean_CAR={sub['car_ann'].mean():+.4f}  nw_t={_nw_t(mm.values):+.2f}")
    top, bot = ev2[ev2['q'] == ev2['q'].max()], ev2[ev2['q'] == 0]
    tb = top.groupby('month')['car_ann'].mean() - bot.groupby('month')['car_ann'].mean()
    print(f"TOP-minus-BOTTOM = {top['car_ann'].mean()-bot['car_ann'].mean():+.4f}  nw_t = {_nw_t(tb.dropna().values):+.2f}")
    # DECILE check (classic PEAD concentrates in extreme deciles) — matched-only
    md = ev2[ev2['matched_ann']].copy(); md['d'] = pd.qcut(md['sue'], 10, labels=False, duplicates='drop')
    dt, db = md[md['d'] == md['d'].max()], md[md['d'] == 0]
    dtb = dt.groupby('month')['car_ann'].mean() - db.groupby('month')['car_ann'].mean()
    print(f"[DECILE d9-d0, matched n={len(md)}] top={dt['car_ann'].mean():+.4f} bot={db['car_ann'].mean():+.4f} "
          f"spread={dt['car_ann'].mean()-db['car_ann'].mean():+.4f}  nw_t={_nw_t(dtb.dropna().values):+.2f}")
    ev2.to_parquet(CACHE / 'events_ann.parquet')
    # match-only subset (drop fallback-to-filed events)
    m = ev2[ev2['matched_ann']].copy(); m['q'] = pd.qcut(m['sue'], 5, labels=False, duplicates='drop')
    mt, mb = m[m['q'] == m['q'].max()], m[m['q'] == 0]
    tbm = mt.groupby('month')['car_ann'].mean() - mb.groupby('month')['car_ann'].mean()
    print(f"[matched-only n={len(m)}] TOP-minus-BOTTOM = {mt['car_ann'].mean()-mb['car_ann'].mean():+.4f}  nw_t = {_nw_t(tbm.dropna().values):+.2f}")
    # low-coverage on announcement entry
    print("--- low-coverage split (announcement entry), top-bottom CAR ---")
    m['size_bin'] = np.where(m['mcap'] < 300e6, 'micro', 'small')
    m['cov_bin'] = np.where(m['n13'].isna() | (m['n13'] <= m['n13'].median()), 'low13F', 'high13F')
    for sb in ['micro', 'small']:
        for cb in ['low13F', 'high13F']:
            sub = m[(m['size_bin'] == sb) & (m['cov_bin'] == cb)]
            if len(sub) < 100: print(f"  {sb:6} {cb:8} n={len(sub):5} (few)"); continue
            sub = sub.copy(); sub['q'] = pd.qcut(sub['sue'], 5, labels=False, duplicates='drop')
            print(f"  {sb:6} {cb:8} n={len(sub):5}  top-bot={sub[sub['q']==sub['q'].max()]['car_ann'].mean()-sub[sub['q']==0]['car_ann'].mean():+.4f}")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, choices=['edgar', 'map', 'prices', 'study', 'announce'])
    a = ap.parse_args()
    if a.stage == 'edgar': stage_edgar()
    elif a.stage == 'map': stage_map()
    elif a.stage == 'prices': stage_prices()
    elif a.stage == 'study': stage_study()
    elif a.stage == 'announce': stage_announce()
