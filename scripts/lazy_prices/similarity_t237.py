"""Lazy Prices (Cohen-Malloy-Nguyen, J.Finance 2020) — parse + YoY similarity (T-237).

FALSIFICATION research pilot, Engine D (Discovery) offline track. Nothing here is
wired into any engine; this is exploration permitted under CLAUDE.md [NN-AI-GATE]
(separate track, no live integration). The hypothesis under test: firms that do NOT
change their 10-K language year-over-year ("non-changers") modestly outperform firms
that do. This module produces the *similarity panel* that a downstream backtest stage
consumes; it makes no trading decision.

Two stages, one CLI module:

  Stage 1 (`parse`)      Strip cached filing HTML to text and extract Item 1A
                         (Risk Factors) and Item 7 (MD&A). Section-boundary detection
                         is robust to table-of-contents false positives (the real
                         section is the later/longer occurrence) and to
                         case/whitespace/&#160; variants. Fails CLOSED per
                         [NN-FAIL-CLOSED]: a filing where a target section cannot be
                         located is marked parse_ok=False with a skip_reason — it is
                         NEVER emitted as a parsed-but-empty section masquerading as
                         real text.

  Stage 2 (`similarity`) For each (ticker, form), order filings by acceptance_dt and
                         pair each with the SAME firm's immediately-prior same-form
                         filing. YoY similarity is computed on the concatenated
                         (Item 1A + Item 7) text:
                           - PRIMARY:  cosine similarity of TF-IDF vectors, fit
                             PER-PAIR (the two docs are the corpus), so cosine in
                             [0,1] is the document-pair similarity. This matches the
                             CMN pairwise-similarity construction.
                           - SECONDARY (reported, not gated): Jaccard on word sets.
                         decision_date = the next business day STRICTLY AFTER
                         acceptance_dt (filings are frequently accepted post-close, so
                         the same calendar day would be look-ahead). A simple pandas
                         BDay roll is used here; exact NYSE-calendar alignment is the
                         backtest stage's job.

PIT-discipline (no future leakage):
  - acceptance_dt (the SEC acceptance timestamp) is the only point-in-time key used.
    period_end / filingDate are NOT used for sequencing or decision timing.
  - The decision_date is strictly AFTER acceptance_dt; a filing accepted at 16:42 ET
    can only be acted on the next business day, never the same session.
  - Similarity for filing T uses only filing T and the prior same-firm filing (T-1);
    no information from T+1 enters the score.

Stop words:
  Loughran-McDonald "StopWords_Generic" (Notre Dame SRAF) is the field-standard
  financial stop-word list. It is, however, distributed only as a Drive-hosted XLSX
  behind an unstable file id — not a reliable pipeline dependency. So the DEFAULT is
  sklearn's English stop-word list, and the LM list is used ONLY if a plain-text copy
  has been vendored locally at data/edgar/lazy_prices/lm/StopWords_Generic.txt (one
  token per line, '|'-or-comment-tolerant). Whichever list was actually used is
  recorded per row in the `stopwords_source` column so the provenance travels with
  the data. No network access is performed by this module.

No new dependencies: requests/bs4/lxml/sklearn/pandas/pyarrow are already locked.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity

# --------------------------------------------------------------------------- #
# Paths (all relative to repo root; resolved against this file's location)
# --------------------------------------------------------------------------- #
_REPO_ROOT = Path(__file__).resolve().parents[2]
_LAZY_DIR = _REPO_ROOT / "data" / "edgar" / "lazy_prices"
DEFAULT_INDEX_PATH = _LAZY_DIR / "filing_index.parquet"
SECTIONS_PATH = _LAZY_DIR / "sections.parquet"
SIMILARITY_PATH = _LAZY_DIR / "similarity_panel.parquet"
LM_STOPWORDS_PATH = _LAZY_DIR / "lm" / "StopWords_Generic.txt"

# A section shorter than this many characters is treated as a parse failure, not a
# real (tiny) section — guards against grabbing a stub heading. CMN Item 1A/Item 7
# bodies run tens of thousands of characters; a few hundred chars is a mis-parse.
_MIN_SECTION_CHARS = 400


# --------------------------------------------------------------------------- #
# Stage 1 — HTML -> text -> Item 1A / Item 7 extraction
# --------------------------------------------------------------------------- #
def load_stopwords() -> tuple[frozenset[str], str]:
    """Return (stopword_set, source_label).

    Prefer a locally-vendored Loughran-McDonald StopWords_Generic list; otherwise
    fall back to sklearn English stop words. No network access. The source label is
    persisted per row so similarity provenance is auditable.
    """
    if LM_STOPWORDS_PATH.is_file():
        words: set[str] = set()
        for raw in LM_STOPWORDS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            tok = raw.split("|", 1)[0].strip().lower()
            if tok and not tok.startswith("#"):
                words.add(tok)
        if words:
            return frozenset(words), "loughran_mcdonald_generic_vendored"
    return frozenset(ENGLISH_STOP_WORDS), "sklearn_english"


def html_to_text(html: str) -> str:
    """Strip tags to plain text using the lxml parser.

    Normalises &#160;/&nbsp; and other whitespace to single spaces. Drops script /
    style nodes. Post-2019 10-Ks carry inline-XBRL (<ix:...>) tags; bs4 treats them
    as ordinary elements, so .get_text() already discards the tag markup and keeps
    the visible text. We additionally strip XBRL-only namespaced nodes that carry no
    display text to reduce token noise.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    # inline-XBRL hidden facts carry no human-visible text; drop them so they don't
    # inject numeric/context noise into the TF-IDF vocabulary.
    for tag in soup.find_all(lambda t: t.name and ":" in t.name and not t.get_text(strip=True)):
        tag.decompose()
    text = soup.get_text(separator=" ")
    # &#160; (non-breaking space) -> normal space, collapse runs of whitespace.
    text = text.replace("\xa0", " ").replace(" ", " ").replace("​", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# Heading detection. A bare "Item 1A" / "Item 7" regex is NOT enough — 10-K text is
# saturated with non-heading occurrences of the same token, of three kinds (all
# observed on the AAPL/MSFT validation set):
#
#   1. TABLE-OF-CONTENTS lines:   "Item 1A. Risk Factors 8 Item 1B. ..."   (top of doc)
#   2. INLINE CROSS-REFERENCES:   'Item 1A of this Form 10-K under the heading ...'
#                                 'see Item 7, "Management\'s Discussion..."'
#                                 'in Part II, Item 8 ...'
#   3. RUNNING PAGE-HEADERS:      "Item 7 • Microsoft Dynamics ..." repeated per page.
#
# Naive title-anchoring is ALSO brittle: MSFT FY2017's heading reads "ITEM 1A. RIS K
# FACTORS" / "MANAGEMENT'S DISCUSSION" with intra-word spaces injected by inline-XBRL
# formatting, so requiring "Risk\s+Factors" as clean tokens drops a real section.
#
# Robust approach: enumerate EVERY "Item <n><letter>" token, classify each as a
# genuine section HEADING vs noise using local context, then carve sections between
# consecutive genuine headings. A token is a HEADING when, looking at the ~60 chars
# that follow it, the canonical section TITLE appears with intra-word spaces removed
# (so "RIS K FACTORS" -> "RISKFACTORS" still matches) AND it is not an inline
# cross-reference. Cross-references are recognised by the connector words that
# immediately follow the item token ("of", "of this", "under", "see", "in Part",
# "and", a bullet "•", or a comma+quote) — a real heading is followed by its title or
# a period, never by "of this Form".
# The word "Item" itself can be split by inline-XBRL formatting, e.g. MSFT FY2016's
# real MD&A heading reads "I TEM 7. MANAGEMENT'S DISCUSSION" (a space injected inside
# "ITEM"). Allow at most one internal space inside the word so the genuine heading is
# not lost. \b before "I" still anchors the token at a word boundary.
_ITEM_TOKEN_RE = re.compile(r"\bI\s?TEM\s*(\d{1,2})\s*([A-Z]?)\b", re.IGNORECASE)

# Connector words that mark an "Item N" token as an inline reference, not a heading.
_XREF_AFTER_RE = re.compile(
    r"^\s*(?:of\b|under\b|see\b|in\s+Part\b|and\b|or\b|,\s*[\"“'‘]|•|•)",
    re.IGNORECASE,
)

# Canonical section titles, matched after stripping ALL non-letters from the lookahead
# window (defeats "RIS K FACTORS", "&#160;", punctuation, casing). Keyed by item id.
_SECTION_TITLE_KEY = {
    "1A": "RISKFACTORS",
    "1B": "UNRESOLVEDSTAFFCOMMENTS",
    "2": "PROPERTIES",
    "7": "MANAGEMENTSDISCUSSION",
    "7A": "QUANTITATIVE",          # "Quantitative and Qualitative Disclosures..."
    "8": "FINANCIALSTATEMENTS",
}
_TITLE_LOOKAHEAD = 90  # chars after the item token to scan for the title


def _item_id(num: str, letter: str) -> str:
    return f"{num}{letter.upper()}" if letter else num


def _is_heading(text: str, m: re.Match[str]) -> str | None:
    """Classify an 'Item N[L]' token match. Return the item id (e.g. '1A', '7') if it
    is a genuine section heading, else None.

    Heading test: the canonical title for that item id must appear in the lookahead
    window once all non-letters are stripped (tolerant of intra-word spaces, &#160;,
    punctuation, and casing). Cross-reference connectors immediately after the token
    veto the match even if a title word happens to appear later.
    """
    item_id = _item_id(m.group(1), m.group(2))
    title_key = _SECTION_TITLE_KEY.get(item_id)
    if title_key is None:
        return None
    after = text[m.end():m.end() + _TITLE_LOOKAHEAD]
    if _XREF_AFTER_RE.match(after):
        return None  # inline cross-reference, not a heading
    letters_only = re.sub(r"[^A-Za-z]", "", after).upper()
    if letters_only.startswith(title_key):
        return item_id
    return None


def _section_headings(text: str) -> list[tuple[int, int, str]]:
    """Return genuine section headings as (start_pos, end_pos, item_id), in order.

    end_pos is the offset just past the matched 'Item N[L]' token (the body begins
    there). Multiple genuine headings for the same id can survive (e.g. ToC line +
    real body); the caller resolves which span is the real section.
    """
    out: list[tuple[int, int, str]] = []
    for m in _ITEM_TOKEN_RE.finditer(text):
        hid = _is_heading(text, m)
        if hid is not None:
            out.append((m.start(), m.end(), hid))
    return out


def _carve(headings: list[tuple[int, int, str]], text: str,
           start_id: str, end_ids: set[str]) -> str:
    """Carve the body of `start_id` running to the next genuine heading whose id is in
    `end_ids`. Among multiple `start_id` headings (ToC + body), return the LONGEST
    resulting body — the ToC entry's body is tiny (next heading is the adjacent ToC
    line), the real section's body is long. This is the "longest span wins" CMN
    replication heuristic, now applied over CLASSIFIED headings so cross-references
    and running page-headers can no longer create spurious boundaries.
    """
    best = ""
    for i, (hs, he, hid) in enumerate(headings):
        if hid != start_id:
            continue
        end_pos = len(text)
        for js in range(i + 1, len(headings)):
            njs_start, _, njs_id = headings[js]
            if njs_id in end_ids and njs_start > he:
                end_pos = njs_start
                break
        body = text[he:end_pos].strip()
        if len(body) > len(best):
            best = body
    return best


def extract_sections(text: str) -> tuple[str, str]:
    """Return (item_1a_text, item_7_text). Empty string means 'not located'."""
    headings = _section_headings(text)
    item_1a = _carve(headings, text, "1A", {"1B", "2"})
    item_7 = _carve(headings, text, "7", {"7A", "8"})
    return item_1a, item_7


@dataclass(frozen=True)
class SectionResult:
    item_1a_text: str
    item_7_text: str
    parse_ok: bool
    skip_reason: str


def parse_filing(raw_abs_path: Path) -> SectionResult:
    """Parse one cached filing HTML into Item 1A / Item 7. Fails closed."""
    if not raw_abs_path.is_file():
        return SectionResult("", "", False, f"raw_html_missing:{raw_abs_path}")
    try:
        html = raw_abs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return SectionResult("", "", False, f"read_error:{exc}")
    if len(html) < 1000:
        return SectionResult("", "", False, "raw_html_too_small")

    text = html_to_text(html)
    item_1a, item_7 = extract_sections(text)

    missing: list[str] = []
    if len(item_1a) < _MIN_SECTION_CHARS:
        missing.append("item_1a")
    if len(item_7) < _MIN_SECTION_CHARS:
        missing.append("item_7")
    if missing:
        # [NN-FAIL-CLOSED]: do NOT emit a parsed-but-empty section. Report the
        # specific section(s) that could not be located.
        return SectionResult("", "", False, "section_not_located:" + ",".join(missing))

    return SectionResult(item_1a, item_7, True, "")


def run_parse(index_path: Path, limit: int | None) -> pd.DataFrame:
    """Stage 1: parse every fetched filing in the index into sections.parquet."""
    if not index_path.is_file():
        # [NN-FAIL-CLOSED]: required input absent -> halt, do not emit an empty panel.
        raise SystemExit(f"FATAL: filing index not found: {index_path}")
    idx = pd.read_parquet(index_path)
    required = {
        "ticker", "cik", "form", "accession", "acceptance_dt",
        "primary_doc", "raw_path", "fetch_ok", "skip_reason",
    }
    missing_cols = required - set(idx.columns)
    if missing_cols:
        raise SystemExit(f"FATAL: filing index missing columns: {sorted(missing_cols)}")

    if limit is not None:
        idx = idx.head(limit)

    rows: list[dict[str, object]] = []
    for _, r in idx.iterrows():
        if not bool(r["fetch_ok"]):
            rows.append({
                "accession": r["accession"], "cik": int(r["cik"]), "ticker": r["ticker"],
                "acceptance_dt": r["acceptance_dt"], "item_1a_text": "", "item_7_text": "",
                "parse_ok": False,
                "skip_reason": f"upstream_fetch_failed:{r.get('skip_reason', '')}",
            })
            continue
        raw_abs = _REPO_ROOT / str(r["raw_path"])
        res = parse_filing(raw_abs)
        rows.append({
            "accession": r["accession"], "cik": int(r["cik"]), "ticker": r["ticker"],
            "acceptance_dt": r["acceptance_dt"],
            "item_1a_text": res.item_1a_text, "item_7_text": res.item_7_text,
            "parse_ok": res.parse_ok, "skip_reason": res.skip_reason,
        })

    out = pd.DataFrame(rows, columns=[
        "accession", "cik", "ticker", "acceptance_dt",
        "item_1a_text", "item_7_text", "parse_ok", "skip_reason",
    ])
    out = out.astype({
        "accession": "string", "cik": "int64", "ticker": "string",
        "acceptance_dt": "string", "item_1a_text": "string", "item_7_text": "string",
        "parse_ok": "bool", "skip_reason": "string",
    })
    SECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(SECTIONS_PATH, index=False)
    return out


# --------------------------------------------------------------------------- #
# Stage 2 — YoY cosine-TF-IDF similarity
# --------------------------------------------------------------------------- #
_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def _word_set(text: str, stopwords: frozenset[str]) -> frozenset[str]:
    return frozenset(
        w for w in (m.group(0).lower() for m in _WORD_RE.finditer(text))
        if w not in stopwords
    )


def jaccard(text_a: str, text_b: str, stopwords: frozenset[str]) -> float:
    sa = _word_set(text_a, stopwords)
    sb = _word_set(text_b, stopwords)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    if union == 0:
        return 0.0
    return inter / union


def cosine_tfidf(text_a: str, text_b: str, stopwords: frozenset[str]) -> float:
    """Cosine similarity of TF-IDF vectors, vectorizer fit PER-PAIR.

    The corpus is exactly the two documents, so cosine in [0,1] is the document-pair
    similarity (CMN construction). A degenerate empty-vocabulary pair returns 0.0.
    """
    vec = TfidfVectorizer(
        stop_words=list(stopwords),
        token_pattern=r"(?u)\b[A-Za-z]{2,}\b",
        lowercase=True,
        sublinear_tf=True,
    )
    try:
        mat = vec.fit_transform([text_a, text_b])
    except ValueError:
        # empty vocabulary after stop-word removal
        return 0.0
    if mat.shape[1] == 0:
        return 0.0
    sim = cosine_similarity(mat[0], mat[1])[0, 0]
    # clamp tiny FP excursions outside [0,1]
    return float(min(1.0, max(0.0, sim)))


def next_business_day(acceptance_dt: str) -> str:
    """Next business day STRICTLY AFTER the acceptance timestamp (ISO date string).

    Filings are frequently accepted post-close, so the decision can only be acted on
    a later session. We roll to the next pandas business day after the acceptance
    calendar date; exact NYSE-calendar/holiday alignment is the backtest stage's job.
    """
    ts = pd.Timestamp(acceptance_dt)
    # normalise to the calendar date, then add one business day. BDay always lands on
    # a strictly-later day, so even a same-day pre-close acceptance cannot be acted on
    # in its own session.
    decision = (ts.normalize() + pd.offsets.BDay(1)).normalize()
    return decision.date().isoformat()


def run_similarity(limit: int | None) -> pd.DataFrame:
    """Stage 2: build similarity_panel.parquet from sections.parquet."""
    if not SECTIONS_PATH.is_file():
        raise SystemExit(
            f"FATAL: sections panel not found ({SECTIONS_PATH}); run the 'parse' stage first."
        )
    sec = pd.read_parquet(SECTIONS_PATH)
    stopwords, sw_source = load_stopwords()

    # Need form for the (ticker, form) grouping; re-attach from the index.
    if SECTIONS_PATH.with_name("filing_index.parquet").is_file():
        idx = pd.read_parquet(DEFAULT_INDEX_PATH)[["accession", "form"]]
        sec = sec.merge(idx, on="accession", how="left")
    else:
        sec["form"] = "10-K"
    sec["form"] = sec["form"].fillna("10-K")

    # Order each firm's same-form filings chronologically by the PIT key.
    sec["_acc_ts"] = pd.to_datetime(sec["acceptance_dt"], utc=True, errors="coerce")
    sec = sec.sort_values(["ticker", "form", "_acc_ts"]).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for (ticker, form), grp in sec.groupby(["ticker", "form"], sort=False):
        grp = grp.sort_values("_acc_ts")
        prev = None
        for _, cur in grp.iterrows():
            if prev is None:
                prev = cur
                continue  # first filing for the firm has no prior; emit nothing
            cur_doc = f"{cur['item_1a_text']} {cur['item_7_text']}".strip()
            prev_doc = f"{prev['item_1a_text']} {prev['item_7_text']}".strip()

            ok = bool(cur["parse_ok"]) and bool(prev["parse_ok"])
            skip = ""
            sim_cos = float("nan")
            sim_jac = float("nan")
            if not ok:
                bad = []
                if not bool(cur["parse_ok"]):
                    bad.append("current")
                if not bool(prev["parse_ok"]):
                    bad.append("prior")
                skip = "parse_failed:" + ",".join(bad)
            else:
                sim_cos = cosine_tfidf(cur_doc, prev_doc, stopwords)
                sim_jac = jaccard(cur_doc, prev_doc, stopwords)

            rows.append({
                "ticker": ticker, "cik": int(cur["cik"]), "form": form,
                "acceptance_dt": cur["acceptance_dt"],
                "decision_date": next_business_day(str(cur["acceptance_dt"])),
                "prior_accession": prev["accession"],
                "sim_cosine_tfidf": sim_cos, "sim_jaccard": sim_jac,
                "stopwords_source": sw_source, "ok": ok, "skip_reason": skip,
            })
            prev = cur

    out = pd.DataFrame(rows, columns=[
        "ticker", "cik", "form", "acceptance_dt", "decision_date", "prior_accession",
        "sim_cosine_tfidf", "sim_jaccard", "stopwords_source", "ok", "skip_reason",
    ])
    if not out.empty:
        out = out.astype({
            "ticker": "string", "cik": "int64", "form": "string",
            "acceptance_dt": "string", "decision_date": "string",
            "prior_accession": "string", "sim_cosine_tfidf": "float64",
            "sim_jaccard": "float64", "stopwords_source": "string",
            "ok": "bool", "skip_reason": "string",
        })
    if limit is not None:
        out = out.head(limit)
    SIMILARITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(SIMILARITY_PATH, index=False)
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="similarity_t237",
        description="Lazy Prices (T-237): parse 10-K sections + YoY TF-IDF similarity.",
    )
    sub = p.add_subparsers(dest="stage", required=True)

    pp = sub.add_parser("parse", help="Stage 1: extract Item 1A / Item 7 -> sections.parquet")
    pp.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH,
                    help="filing_index.parquet (input)")
    pp.add_argument("--limit", type=int, default=None, help="max filings to parse")

    ps = sub.add_parser("similarity", help="Stage 2: YoY similarity -> similarity_panel.parquet")
    ps.add_argument("--limit", type=int, default=None, help="max pairs to emit")

    pa = sub.add_parser("all", help="Run parse then similarity")
    pa.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    pa.add_argument("--limit", type=int, default=None)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.stage == "parse":
        df = run_parse(args.index, args.limit)
        ok = int(df["parse_ok"].sum())
        print(f"parse: {len(df)} filings, {ok} parse_ok -> {SECTIONS_PATH}")
    elif args.stage == "similarity":
        df = run_similarity(args.limit)
        ok = int(df["ok"].sum()) if not df.empty else 0
        print(f"similarity: {len(df)} pairs, {ok} ok -> {SIMILARITY_PATH}")
    elif args.stage == "all":
        run_parse(args.index, args.limit)
        df = run_similarity(args.limit)
        ok = int(df["ok"].sum()) if not df.empty else 0
        print(f"all: {len(df)} pairs, {ok} ok -> {SIMILARITY_PATH}")
    else:  # pragma: no cover
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
