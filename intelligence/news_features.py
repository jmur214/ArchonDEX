"""T-289c (DRAFT — features frozen by the director before any test runs).

PIT-safe news features over the T-289b panel. Every feature at decision-time `as_of` reads ONLY rows with
`created_at` < as_of (never `updated_at`). Reuses similarity_t237 (LM stopwords / TF-IDF / cosine) and the
existing edge's VADER analyzer. LM word lists live in data/intel/lm_dictionary/ (Loughran-McDonald master).
"""
from __future__ import annotations
import pathlib, math, re
from functools import lru_cache
import pandas as pd

ROOT = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-agent-d')
LM_DIR = ROOT / 'data' / 'intel' / 'lm_dictionary'
_WORD = re.compile(r"[A-Za-z']+")

# ---- Loughran-McDonald sentiment ----
_LM_FALLBACK_POS = {'GAIN', 'GAINS', 'PROFIT', 'PROFITABLE', 'GROWTH', 'STRONG', 'BEAT', 'BEATS', 'UPGRADE',
                    'OUTPERFORM', 'SURGE', 'RECORD', 'POSITIVE', 'IMPROVED', 'SUCCESS', 'OPPORTUNITY'}
_LM_FALLBACK_NEG = {'LOSS', 'LOSSES', 'DECLINE', 'WEAK', 'MISS', 'MISSES', 'DOWNGRADE', 'LAWSUIT', 'FRAUD',
                    'BANKRUPTCY', 'INVESTIGATION', 'RISK', 'NEGATIVE', 'DEFAULT', 'PLUNGE', 'WARNING', 'CUT'}

@lru_cache(maxsize=1)
def _lm_lists():
    """Load LM positive/negative word sets from data/intel/lm_dictionary/ (Loughran-McDonald master CSV);
    fall back to a small embedded list so the feature is testable before the dictionary is fetched."""
    pos, neg = set(), set()
    master = LM_DIR / 'lm_master.csv'
    if master.exists():
        d = pd.read_csv(master)
        cols = {c.lower(): c for c in d.columns}
        w = cols.get('word'); p = cols.get('positive'); n = cols.get('negative')
        if w and p and n:
            pos = set(d.loc[d[p].astype(float) > 0, w].astype(str).str.upper())
            neg = set(d.loc[d[n].astype(float) > 0, w].astype(str).str.upper())
    if not pos or not neg:
        pos, neg = _LM_FALLBACK_POS, _LM_FALLBACK_NEG        # documented fallback (flagged in the audit)
    return pos, neg

def lm_sentiment(text: str) -> float:
    """(pos − neg) / (pos + neg) over Loughran-McDonald word matches. 0.0 if no sentiment words."""
    pos, neg = _lm_lists()
    toks = [t.upper() for t in _WORD.findall(text or '')]
    if not toks:
        return 0.0
    p = sum(t in pos for t in toks); n = sum(t in neg for t in toks)
    return (p - n) / (p + n) if (p + n) else 0.0

# ---- VADER sentiment (reuse the existing analyzer) ----
@lru_cache(maxsize=1)
def _vader():
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        return SentimentIntensityAnalyzer()
    except Exception:
        return None

def vader_sentiment(text: str) -> float:
    a = _vader()
    return float(a.polarity_scores(text or '')['compound']) if a else 0.0

# ---- panel-relative features (PIT: created_at < as_of) ----
def _sym_slice(panel: pd.DataFrame, symbol: str, as_of, lookback_days: int):
    hi = pd.Timestamp(as_of, tz='UTC'); lo = hi - pd.Timedelta(days=lookback_days)
    m = panel['symbols'].apply(lambda ss: symbol in ss) if len(panel) else pd.Series([], dtype=bool)
    sub = panel[m] if len(panel) else panel
    return sub[(sub['created_at'] >= lo) & (sub['created_at'] < hi)]   # strict < as_of

def abn_news_volume(panel, symbol, as_of, window=63):
    """Today's article count for `symbol` vs its trailing-`window`-day daily mean (ratio; 1.0 = normal)."""
    hi = pd.Timestamp(as_of, tz='UTC')
    today = _sym_slice(panel, symbol, hi + pd.Timedelta(days=1), 1)          # articles on the as_of day
    trail = _sym_slice(panel, symbol, as_of, window)
    daily_mean = len(trail) / window if window else 0.0
    return (len(today) / daily_mean) if daily_mean > 1e-9 else (float(len(today)) if len(today) else 0.0)

def novelty(panel, symbol, as_of, window=21):
    """1 − max TF-IDF cosine of the as_of-day articles vs the trailing-`window`-day articles (reuse
    similarity_t237). 1.0 = wholly novel, 0.0 = a repeat. Returns None if no same-day article."""
    hi = pd.Timestamp(as_of, tz='UTC')
    today = _sym_slice(panel, symbol, hi + pd.Timedelta(days=1), 1)
    prior = _sym_slice(panel, symbol, as_of, window)
    if not len(today):
        return None
    if not len(prior):
        return 1.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        docs = list(prior['content'].fillna('')) + list(today['content'].fillna(''))
        X = TfidfVectorizer(stop_words='english', max_features=5000).fit_transform(docs)
        sims = cosine_similarity(X[len(prior):], X[:len(prior)])
        return float(1.0 - sims.max()) if sims.size else 1.0
    except Exception:
        return None
