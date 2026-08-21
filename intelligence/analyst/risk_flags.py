"""intelligence/analyst/risk_flags.py — ONE canonical name per condition.

T-331c. The constrained analyst emitted FIVE spellings for one condition across 19
notes (`news_degraded` ×8, `news_panel_degraded` ×5, `news_feed_degraded` ×4,
`degraded_news_feed`, `degraded_news_panel`). Three-plus names for one condition means
**no gate can count it** — the drift is itself the defect, independent of what the flag
was reporting.

THE RULE: grandfather the variants in the READER, NEVER in the writer.
  * READER  — `normalize()` maps every known historical spelling onto one canonical
              token so the existing record becomes countable.
  * WRITER  — new notes emit a canonical token ONLY. This module is the single source
              of truth E's prompt/schema imports (the same import-by-identity pattern
              C used for SLEEVE_INSURANCE_FRAMING); a new spelling is a bug, not a
              synonym to be added here.

HONESTY CONSTRAINT: the legacy variants were written when the bundle could NOT
distinguish "the feed is broken" from "the tape doesn't cover my symbols" (T-331b).
So they normalize to an explicitly AMBIGUOUS legacy token — countable, but never
retroactively re-interpreted as one or the other. We do not know which the model
meant, and inventing that knowledge would be worse than leaving it labelled unknown.
"""
from __future__ import annotations

from typing import Dict, Iterable, List

# ── canonical tokens (the ONLY strings a new note may emit) ───────────────────
NEWS_FEED_DEGRADED = "news_feed_degraded"      # a REAL fault: empty panel / fetch error
NEWS_COVERAGE_THIN = "news_coverage_thin"      # STRUCTURAL: panel healthy, symbols uncovered
# the legacy bucket: countable, deliberately NOT re-interpreted
NEWS_DEGRADED_LEGACY = "news_degraded_legacy_ambiguous"

CANONICAL_FLAGS = frozenset({NEWS_FEED_DEGRADED, NEWS_COVERAGE_THIN})

# Historical spellings observed in the 2026-07-27 → 2026-08-20 record. READER-ONLY.
# Do NOT extend this to bless a new writer spelling — fix the writer instead.
_LEGACY_VARIANTS: Dict[str, str] = {
    "news_degraded": NEWS_DEGRADED_LEGACY,
    "news_panel_degraded": NEWS_DEGRADED_LEGACY,
    "news_feed_degraded": NEWS_DEGRADED_LEGACY,
    "degraded_news_feed": NEWS_DEGRADED_LEGACY,
    "degraded_news_panel": NEWS_DEGRADED_LEGACY,
    "news_degraded_feed": NEWS_DEGRADED_LEGACY,
    "degraded_news": NEWS_DEGRADED_LEGACY,
    # further spellings found in the AGENTIC record (the drift is ~10 names, not 5)
    "empty_news_panel": NEWS_DEGRADED_LEGACY,
    "news_feed_unavailable": NEWS_DEGRADED_LEGACY,
    "no_news_feed": NEWS_DEGRADED_LEGACY,
    "news_unavailable": NEWS_DEGRADED_LEGACY,
}

# DELIBERATELY NOT MAPPED: compound flags that bundle news with another condition
# (e.g. "no_live_prices_or_news", "no_news_or_events_feed"). Folding them into the
# news bucket would silently absorb a PRICE or EVENT fault into a news count. They
# pass through unchanged and stay visible as their own distinct conditions.
COMPOUND_UNMAPPED = frozenset({"no_live_prices_or_news", "no_news_or_events_feed"})


def normalize(flag: str) -> str:
    """READER-side: map a historical spelling onto its canonical token.

    An unknown flag passes through unchanged (this is a normalizer, not a filter —
    swallowing an unrecognized flag would hide exactly the drift we are fixing)."""
    key = str(flag or "").strip().lower()
    return _LEGACY_VARIANTS.get(key, key)


def normalize_all(flags: Iterable[str]) -> List[str]:
    """Normalize a note's risk_flags, de-duplicated, order-stable."""
    out: List[str] = []
    for f in flags or []:
        n = normalize(f)
        if n not in out:
            out.append(n)
    return out


def count_condition(notes: Iterable[dict], condition: str) -> int:
    """Count notes carrying `condition` AFTER normalization — the thing five spellings
    made impossible. This is what a gate calls."""
    n = 0
    for note in notes or []:
        if condition in normalize_all((note or {}).get("risk_flags", [])):
            n += 1
    return n


def is_writer_legal(flag: str) -> bool:
    """True iff a NEW note may emit this flag. Legacy spellings are reader-only:
    grandfathering the writer is how five names became untrackable."""
    return str(flag or "").strip().lower() in CANONICAL_FLAGS
