"""T-304b — EDGAR 8-K body-text fetch (the second "when it lands" seam, now landed).

The 8-K panel gives item CODE + accession, not the filing BODY. This fetches the primary document's
text for a given (cik, accession), reusing the T-137 SEC etiquette (User-Agent + ≤8 req/s) and the T-237
`html_to_text`. FORWARD-ONLY is the CALLER's contract (the runner fetches bodies only for documents filed
today-forward — never a historical backfill, per `[NN-AI-GATE]`); this function is a plain fetch and does
not itself gate on date.

Chain: submissions/CIK.json → align accession → primaryDocument filename →
Archives/edgar/data/{cik}/{accession-no-dashes}/{primaryDocument} → html_to_text.
"""
from __future__ import annotations

import json
import time
import urllib.error
from typing import Optional

import requests

from core.sec_http import fetch

UA = {"User-Agent": "ArchonDEX research jsm13700@gmail.com"}   # T-137 etiquette
RATE_SLEEP = 0.13                                              # ~7.7 req/s (< 10 req/s ceiling)
_MAX_CHARS = 60_000                                            # cap the body handed to one model call


def _html_to_text(html: str) -> str:
    try:
        from scripts.lazy_prices.similarity_t237 import html_to_text
        return html_to_text(html)
    except Exception:
        import re
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


FETCH_TIMEOUT_S = 15             # per attempt, in TOTAL (core/sec_http.py)
FETCH_ATTEMPTS = 2


def _get(url: str, *, json_: bool = False, session: Optional[requests.Session] = None):
    """GET from sec.gov: text (or JSON), or None. Through core/sec_http: the contact user
    agent never follows a redirect off sec.gov, and the timeout bounds the whole request
    (`requests`' bounds each read, so a trickling server could hold this step — which runs
    before the paper run's main state push — indefinitely). An explicit ``session`` is a
    test seam; it does not follow redirects either."""
    for i in range(FETCH_ATTEMPTS):
        try:
            if session is not None:
                r = session.get(url, headers=UA, timeout=FETCH_TIMEOUT_S, allow_redirects=False)
                if r.status_code == 404:
                    return None
                if r.status_code != 200:
                    raise OSError(f"HTTP {r.status_code}")
                return r.json() if json_ else r.text
            raw = fetch(url, UA, timeout=FETCH_TIMEOUT_S).decode("utf-8", errors="replace")
            return json.loads(raw) if json_ else raw
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            time.sleep(RATE_SLEEP * (i + 1))
        except Exception:
            time.sleep(RATE_SLEEP * (i + 1))
        finally:
            time.sleep(RATE_SLEEP)
    return None


def _primary_document(cik: int, accession: str, *, session=None) -> Optional[str]:
    """Return the primaryDocument filename for `accession` from the company's submissions."""
    sub = _get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", json_=True, session=session)
    if not sub:
        return None
    for block in (sub.get("filings", {}).get("recent", {}),):
        accs = block.get("accessionNumber", []); docs = block.get("primaryDocument", [])
        for a, d in zip(accs, docs):
            if a == accession:
                return d or None
    return None


def fetch_8k_text(cik, accession: str, *, primary_document: Optional[str] = None,
                  session: Optional[requests.Session] = None, max_chars: int = _MAX_CHARS) -> Optional[str]:
    """Fetch + de-HTML the 8-K primary document. Returns None if unavailable (caller treats as no-body).

    `cik`/`accession` from the 8-K panel row; `primary_document` may be supplied to skip the submissions
    lookup. FORWARD-ONLY is enforced by the caller (the runner), not here."""
    if cik is None or not accession:
        return None
    doc = primary_document or _primary_document(cik, accession, session=session)
    if not doc:
        return None
    acc_nodash = str(accession).replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{doc}"
    html = _get(url, session=session)
    if html is None:
        return None
    text = _html_to_text(html)
    return text[:max_chars] if text else None
