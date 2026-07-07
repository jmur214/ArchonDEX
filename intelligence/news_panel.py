"""T-289b — PIT news panel (Alpaca News / Benzinga).

Monthly parquets `data/intel/news_panel/news_YYYYMM.parquet`. Keeps `symbols` + `content` (the collector
discarded both). PIT rule: a feature at decision-time t may use only rows with `created_at` < t — NEVER
`updated_at` (revised articles are a look-ahead channel). Depth floor = 2015-01 (T-289a: D-deep, S-clean).

Public API:
  build_month(year, month, universe, run_id) -> DataFrame      # backfill one month, write parquet
  append_today(as_of, universe, run_id)       -> dict          # daily forward append (B wires into the pulse)
  load_panel(start=None, end=None, as_of=None) -> DataFrame     # PIT-safe read (as_of filters created_at < as_of)
"""
from __future__ import annotations
import os, pathlib, datetime as dt, re
import pandas as pd

# T-290b: repo-relative (was a hardcoded agent-d worktree path). parents[1] is
# behaviour-identical in D's worktree (__file__ → agent-d) but resolves to the
# container/repo root in the cloud pulse, so append_today never writes to a dead
# absolute path. See the T-290b outbox note flagging the wider hardcoded pattern.
ROOT = pathlib.Path(__file__).resolve().parents[1]
PANEL_DIR = ROOT / 'data' / 'intel' / 'news_panel'; PANEL_DIR.mkdir(parents=True, exist_ok=True)
SCHEMA = ['article_id', 'created_at', 'updated_at', 'symbols', 'headline', 'summary',
          'content', 'source', 'url', 'author', 'ingest_ts', 'ingest_run_id']
DEPTH_FLOOR = dt.date(2015, 1, 1)   # T-289a hard Benzinga floor
_SYM_BATCH = 40                     # symbols per request

def _html_to_text(s: str) -> str:
    if not s:
        return ''
    try:
        from scripts.lazy_prices.similarity_t237 import html_to_text  # reuse (bs4/lxml)
        return html_to_text(s)
    except Exception:
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()

def _creds():
    for cand in ('/Users/jacksonmurphy/Dev/trading_machine-2/.env', str(ROOT / '.env')):
        p = pathlib.Path(cand)
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY']

def _client():
    from alpaca.data.historical.news import NewsClient
    k, s = _creds(); return NewsClient(k, s)

def _fetch(client, symbols_csv, start, end, limit=45000):
    """alpaca-py get_news auto-paginates; `limit` is the TOTAL cap. include_content=True keeps full body."""
    from alpaca.data.requests import NewsRequest
    from alpaca.common.enums import Sort
    req = NewsRequest(symbols=symbols_csv, start=start, end=end, limit=limit,
                      sort=Sort.ASC, include_content=True)
    r = client.get_news(req)
    return r.data.get('news', []) if hasattr(r, 'data') else []

def _rows(items, run_id, ingest_ts):
    out = []
    for it in items:
        aid = getattr(it, 'id', None) or getattr(it, 'article_id', None)
        out.append({
            'article_id': str(aid) if aid is not None else None,
            'created_at': pd.to_datetime(getattr(it, 'created_at', None), utc=True),
            'updated_at': pd.to_datetime(getattr(it, 'updated_at', None), utc=True),
            'symbols': list(getattr(it, 'symbols', []) or []),
            'headline': getattr(it, 'headline', '') or '',
            'summary': getattr(it, 'summary', '') or '',
            'content': _html_to_text(getattr(it, 'content', '') or ''),
            'source': getattr(it, 'source', '') or '',
            'url': getattr(it, 'url', '') or '',
            'author': getattr(it, 'author', '') or '',
            'ingest_ts': ingest_ts, 'ingest_run_id': run_id,
        })
    return out

def _fetch_universe(client, universe, start, end, run_id, ingest_ts):
    """Fetch all articles tagging any universe symbol in [start,end); dedup by article_id (union symbols).
    NOTE: the Alpaca News API honours `end` but NOT `start` (verified T-289b) — so we POST-FILTER on
    created_at ∈ [start, end) and guard completeness (a capped batch whose earliest article is still after
    `start` may be truncated → smaller _SYM_BATCH)."""
    lo = pd.Timestamp(start, tz='UTC'); hi = pd.Timestamp(end, tz='UTC')
    syms = sorted({s for s in universe if isinstance(s, str) and s})
    seen = {}
    for i in range(0, len(syms), _SYM_BATCH):
        batch = ','.join(syms[i:i + _SYM_BATCH])
        raw = _rows(_fetch(client, batch, start, end), run_id, ingest_ts)
        if raw:
            emin = min(r['created_at'] for r in raw if r['created_at'] is not None)
            if emin > lo and len(raw) >= 44000:      # capped AND didn't reach `start` → possible truncation
                print(f"[news_panel] WARN batch {i//_SYM_BATCH}: earliest {emin} > start {lo}, "
                      f"len={len(raw)} — reduce _SYM_BATCH; month may be incomplete for high-volume names")
        for row in raw:
            ca = row['article_id']
            if ca is None or row['created_at'] is None or not (lo <= row['created_at'] < hi):
                continue                              # POST-FILTER to [start, end)
            if ca in seen:
                seen[ca]['symbols'] = sorted(set(seen[ca]['symbols']) | set(row['symbols']))
            else:
                seen[ca] = row
    df = pd.DataFrame(list(seen.values()), columns=SCHEMA)
    return df.sort_values('created_at').reset_index(drop=True) if len(df) else df

def _path(year, month):
    return PANEL_DIR / f'news_{year}{month:02d}.parquet'

def build_month(year, month, universe, run_id):
    start = dt.datetime(year, month, 1)
    end = dt.datetime(year + (month == 12), (month % 12) + 1, 1)
    df = _fetch_universe(_client(), universe, start, end, run_id, dt.datetime.utcnow().isoformat())
    if len(df):
        df.to_parquet(_path(year, month), index=False)
    return df

def append_today(as_of, universe, run_id, degraded_reason=None):
    """Daily forward append (B wires into the post-reconcile pulse). Idempotent upsert by article_id into the
    current month's parquet. Fail-OPEN for trading (returns degraded=True, never raises); measurement gates
    must treat degraded=True as a FAIL. Returns {n_new, n_total, degraded, reason}."""
    as_of = pd.Timestamp(as_of).date() if not isinstance(as_of, dt.date) else as_of
    try:
        start = dt.datetime(as_of.year, as_of.month, as_of.day)
        end = start + dt.timedelta(days=1)
        new = _fetch_universe(_client(), universe, start, end, run_id, dt.datetime.utcnow().isoformat())
        p = _path(as_of.year, as_of.month)
        existing = pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=SCHEMA)
        merged = (pd.concat([existing, new], ignore_index=True)
                  .drop_duplicates('article_id', keep='first').sort_values('created_at'))
        merged.to_parquet(p, index=False)
        return {'n_new': int(len(merged) - len(existing)), 'n_total': int(len(merged)),
                'degraded': bool(degraded_reason), 'reason': degraded_reason}
    except Exception as e:
        return {'n_new': 0, 'n_total': 0, 'degraded': True, 'reason': f'fetch_error: {str(e)[:120]}'}

def load_panel(start=None, end=None, as_of=None):
    """Concat monthly parquets. If `as_of` is given, apply the PIT rule: keep only created_at < as_of
    (uses created_at ONLY; updated_at is never a filter/feature input)."""
    frames = []
    for p in sorted(PANEL_DIR.glob('news_*.parquet')):
        d = pd.read_parquet(p)
        if start is not None:
            d = d[d['created_at'] >= pd.Timestamp(start, tz='UTC')]
        if end is not None:
            d = d[d['created_at'] < pd.Timestamp(end, tz='UTC')]
        frames.append(d)
    if not frames:
        return pd.DataFrame(columns=SCHEMA)
    out = pd.concat(frames, ignore_index=True)
    if as_of is not None:
        out = out[out['created_at'] < pd.Timestamp(as_of, tz='UTC')]   # PIT: created_at ONLY
    return out.sort_values('created_at').reset_index(drop=True)
