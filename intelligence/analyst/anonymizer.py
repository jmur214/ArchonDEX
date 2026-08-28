"""intelligence/analyst/anonymizer.py — T-339b entity anonymizer.

T-339 VOIDED at 25/40 leakage because its "anonymizer" replaced only the TICKER;
14/19 texts still carried the company NAME. This module implements what the frozen
T-339b §A actually requires:

  1. entity-name scrubbing (NER: ORG/PERSON/PRODUCT/GPE/FAC) + exact company-name
     variants, all mapped to ONE per-question token;
  2. numeric-date scrubbing (bare years, `Q3 2017`, `fiscal 2019`);
  3. **MANDATORY mechanical verification before any model call** — a text is ADMITTED
     only if zero named-entity spans and zero exact-name matches survive. A text that
     cannot be cleanly scrubbed is **DROPPED, never sent**, and the drop count is
     reported (a high drop rate is itself a finding about the substrate).

The NER backend is INJECTED (`ner_fn`). The non-NER passes here are complete and
tested; the backend is the one piece the frozen spec names (spaCy), which is not in
the lock file — see the outbox blocker. `verify()` is deliberately independent of the
scrubber: it re-checks the OUTPUT, so a weak backend produces DROPS, not leaks.
"""
from __future__ import annotations

import re
from typing import Callable, Iterable, Optional

NerFn = Callable[[str], Iterable[str]]      # text -> entity surface strings

# bare years, quarters, and fiscal-year references (T-339's texts dated themselves)
_DATE_PATTERNS = (
    re.compile(r"\b(?:19|20)\d{2}\b"),
    re.compile(r"\bQ[1-4]\s*(?:of\s*)?(?:19|20)?\d{0,4}\b", re.I),
    re.compile(r"\bfiscal\s+(?:year\s+)?(?:19|20)?\d{2,4}\b", re.I),
    re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|"
               r"October|November|December)\s+\d{1,2}?,?\s*(?:19|20)\d{2}\b", re.I),
)


def name_variants(symbol: str, company: Optional[str] = None) -> list[str]:
    """Exact strings to replace: the ticker plus common company-name forms.
    Longest-first so 'Bristol-Myers Squibb' is replaced before 'Bristol'."""
    out = {symbol, symbol.lower(), symbol.title(), symbol.upper()}
    if company:
        c = company.strip()
        out.add(c)
        # drop corporate suffixes to catch the short form too
        base = re.sub(r"\b(Inc|Corp|Corporation|Co|Company|Ltd|LLC|PLC|Holdings|Group|"
                      r"Incorporated|NV|SA|AG)\b\.?", "", c, flags=re.I).strip(" ,.-")
        if base:
            out.add(base)
            first = base.split()[0]
            if len(first) > 3:
                out.add(first)
        if "-" in base:
            out.update(p for p in base.split("-") if len(p) > 3)
    return sorted({o for o in out if o and len(o) > 1}, key=len, reverse=True)


def scrub(text: str, token: str, symbol: str, company: Optional[str] = None,
          ner_fn: Optional[NerFn] = None) -> str:
    """Replace ticker + name variants + NER entity spans + explicit dates."""
    out = text or ""
    for v in name_variants(symbol, company):
        out = re.sub(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![A-Za-z0-9])", token, out)
    if ner_fn is not None:
        for span in sorted({s for s in ner_fn(out) if s and len(s) > 1},
                           key=len, reverse=True):
            out = re.sub(rf"(?<![A-Za-z0-9]){re.escape(span)}(?![A-Za-z0-9])", token, out)
    for pat in _DATE_PATTERNS:
        out = pat.sub("[DATE]", out)
    return out


def verify(text: str, symbol: str, company: Optional[str] = None,
           ner_fn: Optional[NerFn] = None) -> tuple[bool, list[str]]:
    """MANDATORY pre-call gate. Re-checks the SCRUBBED output independently of the
    scrubber: returns (admitted, surviving_identifiers). Deliberately strict — an
    admitted text must carry ZERO surviving names, tickers, or explicit dates."""
    surviving: list[str] = []
    for v in name_variants(symbol, company):
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![A-Za-z0-9])", text):
            surviving.append(f"name:{v}")
    if ner_fn is not None:
        for span in ner_fn(text):
            if span and len(span) > 1:
                surviving.append(f"ner:{span}")
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            surviving.append(f"date:{m.group(0)}")
    return (not surviving), surviving


def scrub_or_drop(text: str, token: str, symbol: str, company: Optional[str] = None,
                  ner_fn: Optional[NerFn] = None) -> tuple[Optional[str], list[str]]:
    """The only entry point the runner may use: returns (admitted_text | None, reasons).
    None ⇒ DROP the question. A text is never sent partially scrubbed."""
    s = scrub(text, token, symbol, company, ner_fn)
    ok, surviving = verify(s, symbol, company, ner_fn)
    return (s if ok else None), surviving
