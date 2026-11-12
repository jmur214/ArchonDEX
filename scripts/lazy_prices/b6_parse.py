"""scripts/lazy_prices/b6_parse.py
=================================
T-383 (B-6) step 2 — the REPAIRED 10-K / 10-Q section parser (Risk Factors + MD&A).

Replaces T-237's carve (`similarity_t237.extract_sections`), which the B-6 audit (2026-11-11)
found INVALID on 40% of its "parse_ok" rows: a cross-reference to "Item 1A. Risk Factors" inside
MD&A was classified as the heading, no terminating heading followed, the carve ran to the end of
the document, and "longest span wins" selected the runaway (3,942 of 9,841 "ok" Item 1A sections
contain the signature-page boilerplate or the auditor's report).

The four rules that fix it (each locked by a test in tests/test_b6_lazy_prices_parse.py):

1. BLOCK STRUCTURE IS KEPT. HTML is flattened with block tags (p, div, br, tr, td, li, h1-6,
   table) -> "\\n" and inline tags (span, font, b, ix:*) -> "" (inline-XBRL splits words with
   spans: "RIS<span>K</span>"), raw source newlines -> " " (they carry no rendering meaning).
   Plain-text / <pre> filings keep their own line breaks.
2. A HEADING STARTS A LINE. Tier 1 accepts an "Item N[L]" token only at the start of a line
   (optionally after "PART I..IV"), with its canonical title right after it. A cross-reference
   is mid-sentence. Tier 2 (used only when tier 1 finds no candidate for that section, recorded
   in `*_tier`) relaxes the line-start rule but vetoes connector words on BOTH sides of the
   token ("see Item 1A", 'in "Item 7.', "Item 7 of this").
3. A SECTION MUST BE TERMINATED BY ITS STRUCTURAL SUCCESSOR. The body runs from the heading to
   the next genuine heading of a DIFFERENT item; that item must be in the allowed successor set
   (10-K 1A -> 1B/1C/2/3; 10-K 7 -> 7A/8; 10-Q MD&A -> I-3/I-4/II-1/II-1A; 10-Q 1A ->
   II-2..II-6). Anything else — or the end of the document — rejects the candidate. Among valid
   candidates the longest wins (drops the table-of-contents entry).
4. FAIL CLOSED, CLASSIFY ABSENCE. Every section gets a status, never an empty string posing as
   text: OK | NOT_COVERED:<reason> (pre_rule, incorporated_by_reference, not_required) |
   NOT_LOCATED | TOO_SHORT | CONTAMINATED (an end-of-document marker inside an accepted body —
   impossible under rule 3, asserted anyway).

No network, no disk. Pure functions over a decoded document.
"""
from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# 1. document -> text with block structure
# --------------------------------------------------------------------------- #
_DROP_BLOCKS = re.compile(
    r"<!--.*?-->|<script\b.*?</script\s*>|<style\b.*?</style\s*>|<head\b.*?</head\s*>"
    r"|<ix:header\b.*?</ix:header\s*>|<xbrl\b.*?</xbrl\s*>",
    re.IGNORECASE | re.DOTALL)
_HIDDEN_DIV = re.compile(r"<div[^>]*display\s*:\s*none[^>]*>.*?</div\s*>", re.IGNORECASE | re.DOTALL)
_BLOCK_TAG = re.compile(
    r"<\s*/?\s*(?:p|div|br|tr|td|th|li|ul|ol|table|tbody|thead|tfoot|h[1-6]|hr|center|"
    r"blockquote|title|section|article|dd|dt|dl|caption|page|body|html)\b[^>]*>",
    re.IGNORECASE)
_PRE_BLOCK = re.compile(r"<pre\b[^>]*>(.*?)</pre\s*>", re.IGNORECASE | re.DOTALL)
_ANY_TAG = re.compile(r"<[^>]{0,2000}>", re.DOTALL)
_SGML_HEAD = re.compile(r"^.*?<TEXT>", re.IGNORECASE | re.DOTALL)
_WS_INLINE = re.compile(r"[ \t\f\v  -​  　]+")
_MULTI_NL = re.compile(r"\s*\n\s*")


def decode(blob: bytes) -> str:
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob.decode("latin-1")


def _looks_html(raw: str) -> bool:
    head = raw[:20000].lower()
    return any(t in head for t in ("<html", "<body", "<div", "<p>", "<p ", "<table", "<font", "<br"))


def doc_to_text(raw: str) -> str:
    """Flatten a filing document to text, one block per line (rule 1)."""
    raw = _SGML_HEAD.sub("", raw, count=1) if "<TEXT>" in raw[:5000].upper() else raw
    if _looks_html(raw):
        pres: list[str] = []

        def _keep_pre(m: re.Match[str]) -> str:
            pres.append(m.group(1))
            return f"\x00PRE{len(pres) - 1}\x00"

        s = _DROP_BLOCKS.sub(" ", raw)
        s = _HIDDEN_DIV.sub(" ", s)
        s = _PRE_BLOCK.sub(_keep_pre, s)
        s = s.replace("\r", " ").replace("\n", " ")
        s = _BLOCK_TAG.sub("\n", s)
        s = _ANY_TAG.sub("", s)
        for i, p in enumerate(pres):
            s = s.replace(f"\x00PRE{i}\x00", "\n" + _ANY_TAG.sub("", p) + "\n")
        s = _html.unescape(s)
    else:
        s = _ANY_TAG.sub(" ", raw.replace("\r", ""))
        s = _html.unescape(s)
    s = _WS_INLINE.sub(" ", s)
    s = _MULTI_NL.sub("\n", s)
    return s.strip()


# --------------------------------------------------------------------------- #
# 2. heading classification
# --------------------------------------------------------------------------- #
# Section classes. 10-K classes are the item ids; 10-Q classes carry the part because item
# numbers repeat across Part I / Part II and only the TITLE tells them apart.
TITLES_10K: dict[str, tuple[str, ...]] = {
    "1": ("BUSINESS",),
    "1A": ("RISKFACTORS",),
    "1B": ("UNRESOLVEDSTAFFCOMMENTS", "UNRESOLVEDSECSTAFFCOMMENTS"),
    "1C": ("CYBERSECURITY",),
    "2": ("PROPERTIES", "PROPERTY", "DESCRIPTIONOFPROPERT"),
    "3": ("LEGALPROCEEDINGS",),
    "4": ("MINESAFETY", "SUBMISSIONOFMATTERS", "REMOVEDANDRESERVED", "RESERVED"),
    "5": ("MARKETFOR", "MARKETSFOR"),
    "6": ("SELECTEDFINANCIAL", "SELECTEDCONSOLIDATEDFINANCIAL", "RESERVED", "REMOVEDANDRESERVED"),
    "7": ("MANAGEMENTSDISCUSSION", "MANAGEMENTDISCUSSION"),
    "7A": ("QUANTITATIVEANDQUALITATIVE", "QUALITATIVEANDQUANTITATIVE"),
    "8": ("FINANCIALSTATEMENTS", "CONSOLIDATEDFINANCIALSTATEMENTS"),
    "9": ("CHANGESINANDDISAGREEMENTS", "CHANGESINDISAGREEMENTS"),
    "9A": ("CONTROLSANDPROCEDURES",),
    "9B": ("OTHERINFORMATION",),
    "9C": ("DISCLOSUREREGARDINGFOREIGN",),
    "10": ("DIRECTORS",),
    "11": ("EXECUTIVECOMPENSATION",),
    "12": ("SECURITYOWNERSHIP",),
    "13": ("CERTAINRELATIONSHIPS",),
    "14": ("PRINCIPALACCOUNT",),
    "15": ("EXHIBITS", "EXHIBIT"),
    "16": ("FORMKSUMMARY",),
}
# 10-Q: (item id, title keys) -> class
TITLES_10Q: dict[str, tuple[str, tuple[str, ...]]] = {
    "I1": ("1", ("FINANCIALSTATEMENTS", "CONDENSEDCONSOLIDATED", "CONSOLIDATEDFINANCIAL",
                 "CONSOLIDATEDCONDENSED", "UNAUDITED", "INTERIMFINANCIAL", "CONDENSEDFINANCIAL")),
    "I2": ("2", ("MANAGEMENTSDISCUSSION", "MANAGEMENTDISCUSSION")),
    "I3": ("3", ("QUANTITATIVEANDQUALITATIVE", "QUALITATIVEANDQUANTITATIVE")),
    "I4": ("4", ("CONTROLSANDPROCEDURES",)),
    "II1": ("1", ("LEGALPROCEEDINGS",)),
    "II1A": ("1A", ("RISKFACTORS",)),
    "II2": ("2", ("UNREGISTEREDSALES", "CHANGESINSECURITIES", "ISSUERPURCHASES",
                  "PURCHASESOFEQUITY", "SALESOFUNREGISTERED", "REPURCHASES")),
    "II3": ("3", ("DEFAULTSUPON", "DEFAULTS")),
    "II4": ("4", ("MINESAFETY", "SUBMISSIONOFMATTERS", "REMOVEDANDRESERVED", "RESERVED")),
    "II5": ("5", ("OTHERINFORMATION",)),
    "II6": ("6", ("EXHIBITS", "EXHIBIT")),
}
ORDER_10K = list(TITLES_10K)
ORDER_10Q = list(TITLES_10Q)

# target section -> (form, class, allowed structural successors)
TARGETS: dict[str, dict[str, tuple[str, frozenset[str]]]] = {
    "10-K": {"risk": ("1A", frozenset({"1B", "1C", "2", "3"})),
             "mda": ("7", frozenset({"7A", "8"}))},
    "10-Q": {"risk": ("II1A", frozenset({"II2", "II3", "II4", "II5", "II6"})),
             "mda": ("I2", frozenset({"I3", "I4", "II1", "II1A"}))},
}

_ITEM_TOKEN = re.compile(r"\bI\s?TEMS?\s*(\d{1,2})\s*([A-Z])?(?:\s*\(\s*T\s*\))?(?![A-Za-z0-9])",
                         re.IGNORECASE)
_LINE_PREFIX_OK = re.compile(r"^[\s\W]*(?:PART\s+(?:I{1,3}|IV)\b[\s\W]*)?$", re.IGNORECASE)
_XREF_AFTER = re.compile(
    r"^\s*(?:of\b|under\b|in\s+(?:Part|this|our|the)\b|and\b(?!\s*\d)|or\b|to\b|herein\b|"
    r"above\b|below\b|hereof\b|thereof\b|,\s*[\"“'‘(]|[\"”’]|•|·|•|\)|is\b|are\b|was\b|"
    r"which\b|that\b|contains\b|included\b)",
    re.IGNORECASE)
_XREF_BEFORE = re.compile(
    r"(?:\bsee|\bin|\bunder|\bto|\band|\bor|\balso|\bof|\bwithin|\bfrom|\bat|\bby|\brefer|"
    r"\bdescribed|\bdiscussed|\bincluded|\bcontained|\bforth|\bcaptioned|\bentitled|\bheaded|"
    r"\btitled|\bthis|\bour|\bthe|\bits|\bper|\bwith|\bfollowing|\bpreceding|\babove|\bbelow|"
    r"\bcaption|\bsection|\bsections|\bitems?|[\"“'‘(])\s*(?:Part\s+(?:I{1,3}|IV)[\s,.:\-–—]*)?$",
    re.IGNORECASE)
_TITLE_LOOKAHEAD = 140
_AND_ITEM = re.compile(r"^AND(?:ITEM)?\d{1,2}[A-Z]?")


def _title_key(text: str, end: int) -> str:
    """Upper-case alnum-only lookahead after the token: defeats 'RIS K FACTORS', '&#160;',
    curly apostrophes, a leading '(T)', and the 'Items 7 and 7A.' combined heading."""
    ahead = re.sub(r"[^A-Za-z0-9]", "", text[end:end + _TITLE_LOOKAHEAD]).upper()
    ahead = _AND_ITEM.sub("", ahead)
    ahead = re.sub(r"^\d+", "", ahead)
    return ahead


def _classify(form: str, num: str, letter: str, key: str) -> str | None:
    item = f"{int(num)}{letter.upper()}" if letter else str(int(num))
    if form == "10-K":
        titles = TITLES_10K.get(item)
        if titles and any(key.startswith(t) for t in titles):
            return item
        return None
    for cls, (iid, titles) in TITLES_10Q.items():
        if iid == item and any(key.startswith(t) for t in titles):
            return cls
    return None


@dataclass(frozen=True)
class Heading:
    start: int
    end: int
    cls: str
    tier: int


_BARE_NUM = re.compile(r"(?m)^[ \t]*(\d{1,2})[ \t]*([A-Z])?[ \t]*[.:][ \t]+")


def find_headings(text: str, form: str) -> list[Heading]:
    """All genuine headings: tier 1 = line-start "Item N[L]" (or a line-start bare "N[L]." with
    its exact title — older plain-text filings drop the word "Item"), tier 2 = mid-line "Item N[L]"
    surviving the two-sided cross-reference veto."""
    out: list[Heading] = []
    for m in _BARE_NUM.finditer(text):
        cls = _classify(form, m.group(1), m.group(2) or "", _title_key(text, m.end()))
        if cls is not None:
            out.append(Heading(m.start(), m.end(), cls, 1))
    for m in _ITEM_TOKEN.finditer(text):
        cls = _classify(form, m.group(1), m.group(2) or "", _title_key(text, m.end()))
        if cls is None:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        prefix = text[line_start:m.start()]
        if len(prefix) <= 40 and _LINE_PREFIX_OK.match(prefix):
            out.append(Heading(m.start(), m.end(), cls, 1))
            continue
        before = text[max(0, m.start() - 60):m.start()]
        after = text[m.end():m.end() + 40]
        if _XREF_AFTER.match(after) or _XREF_BEFORE.search(before):
            continue
        out.append(Heading(m.start(), m.end(), cls, 2))
    out.sort(key=lambda h: h.start)
    dedup: list[Heading] = []
    for h in out:
        if dedup and h.start < dedup[-1].end:
            continue
        dedup.append(h)
    return dedup


# --------------------------------------------------------------------------- #
# 3. structural carve
# --------------------------------------------------------------------------- #
# End-of-document markers. `_END_MARKERS` (both phrases anywhere) is the B-6 AUDIT's test on
# T-237's whitespace-collapsed text and stays as defined there (census continuity).
# `_CONTAMINATION` is the parser's own assertion on a carved body that still has its line
# breaks: the signature boilerplate anywhere, the auditor's report only as a LINE-START heading
# (MD&A legitimately MENTIONS "the Report of Independent Registered Public Accounting Firm").
_END_MARKERS = re.compile(
    r"pursuant\s+to\s+the\s+requirements\s+of\s+section\s+13\s+or\s+15\s*\(\s*d\s*\)"
    r"|report\s+of\s+independent\s+registered\s+public\s+accounting\s+firm",
    re.IGNORECASE)
# b6_parse/2 (review F4, 2026-11-12): the 10-K signature sentence was the ONLY signature wording
# known; 10-Qs sign with "Pursuant to the requirements of the Securities Exchange Act of 1934, the
# registrant has duly caused this report to be signed", and electronic signatures read "/s/".
# Every pattern is whitespace-insensitive so the same test runs on raw and on stored (collapsed) text.
_SIG_SENTENCE = (r"pursuant\s+to\s+the\s+requirements\s+of\s+section\s+13\s+or\s+15\s*\(\s*d\s*\)"
                 r"|pursuant\s+to\s+the\s+requirements\s+of\s+the\s+securities\s+exchange\s+act"
                 r"\s+of\s+1934\s*,?\s+the\s+registrant\s+has\s+duly\s+caused")
_SLASH_S = r"(?<![A-Za-z0-9])/s/"
_AUDITOR_SALUTATION = (r"reports?\s+of\s+independent\s+registered\s+public\s+accounting\s+firm\s*"
                       r"(?:\W{0,3})\s*to\s+the\s+(?:board|shareholders|stockholders|members)")
_CONTAMINATION = re.compile(
    _SIG_SENTENCE + "|" + _SLASH_S + "|" + _AUDITOR_SALUTATION
    + r"|(?m:^[ \t]*reports?\s+of\s+independent\s+registered\s+public\s+accounting\s+firm)",
    re.IGNORECASE)
# Document-end markers that CUT a title-located body (b6_parse/2): a SIGNATURES heading line, either
# signature sentence, a "/s/" line, an auditor-report heading, an exhibit-index heading.
_DOC_END = re.compile(
    r"(?m:^[ \t]*signatures?[ \t]*$)|(?m:^[ \t]*exhibit\s+index[ \t]*$)|"
    + _SIG_SENTENCE + "|" + _SLASH_S + "|" + _AUDITOR_SALUTATION
    + r"|(?m:^[ \t]*reports?\s+of\s+independent\s+registered\s+public\s+accounting\s+firm)",
    re.IGNORECASE)
_INCORP = re.compile(
    r"incorporated\s+(?:[\w-]+\s+){0,4}by\s+reference|reference\s+is\s+(?:hereby\s+)?made\s+to"
    r"|can\s+be\s+found\s+(?:in|under|on)\b|annual\s+report\s+to\s+(?:stock|share)holders"
    r"|exhibit\s+13\b"
    r"|is\s+(?:included|contained|presented|set\s+forth)\s+(?:in|on|under)\b"
    r"|appears?\s+(?:in|on|under)\b",
    re.IGNORECASE)
# Some filers (Boston Scientific) put management's ICFR report and the auditor's ICFR report at the
# END of Item 7, before Item 7A. Inside a structurally terminated MD&A those line-start headings end
# the MD&A (recorded as source 'item_trimmed_icfr', so pairs stay like-for-like).
_ICFR_HEAD = re.compile(
    r"(?m)^[ \t]*(?:management.?s\s+(?:annual\s+)?report\s+on\s+internal\s+control"
    r"|reports?\s+of\s+independent\s+registered\s+public\s+accounting\s+firm)",
    re.IGNORECASE)
_NOT_REQ = re.compile(r"not\s+applicable|not\s+required|smaller\s+reporting\s+compan", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z]{2,}")


@dataclass
class Section:
    status: str = "NOT_LOCATED"
    text: str = ""
    tier: int = 0
    terminator: str = ""
    n_candidates: int = 0
    n_valid: int = 0
    n_words: int = 0
    detail: dict = field(default_factory=dict)


def _carve(text: str, heads: list[Heading], target: str, succ: frozenset[str],
           tier: int) -> tuple[str, str, int, int]:
    """Longest VALID body for `target` starting at a heading of `tier`. A tier-1 (line-start)
    start terminates only at tier-1 headings — a mid-sentence tier-2 match inside a genuine
    section is far more likely an un-vetoed cross-reference than a real boundary; a tier-2
    start may terminate at either tier. Returns (body, terminator_cls, n_candidates, n_valid)."""
    best, best_term, n_cand, n_valid = "", "", 0, 0
    for i, h in enumerate(heads):
        if h.cls != target or h.tier != tier:
            continue
        n_cand += 1
        term = None
        for nxt in heads[i + 1:]:
            if nxt.cls == target:          # running header / "(continued)" — skip
                continue
            if tier == 1 and nxt.tier != 1:
                continue
            term = nxt
            break
        if term is None or term.cls not in succ:
            continue                        # unterminated or structure violated -> reject
        n_valid += 1
        body = text[h.end:term.start].strip()
        if len(body) > len(best):
            best, best_term = body, term.cls
    return best, best_term, n_cand, n_valid


def _strip_title(body: str) -> str:
    """Drop the heading's own title line (first line) before counting words."""
    nl = body.find("\n")
    return body[nl + 1:] if 0 <= nl < 200 else body


def extract_section(text: str, form: str, section: str, heads: list[Heading] | None = None,
                    pre_rule: bool = False) -> Section:
    """Carve one target section ('risk' or 'mda') and classify it (rule 4)."""
    target, succ = TARGETS[form][section]
    heads = find_headings(text, form) if heads is None else heads
    out = Section()
    min_words = 8 if (form == "10-Q" and section == "risk") else 150
    body, term, n_c, n_v = _carve(text, heads, target, succ, tier=1)
    out.tier = 1
    if len(_WORD.findall(_strip_title(body))) < min_words:
        # tier 1 found nothing, or only a table-of-contents stub: try the relaxed tier
        body2, term2, n_c2, n_v2 = _carve(text, heads, target, succ, tier=2)
        n_c, n_v = n_c + n_c2, n_v + n_v2
        if len(body2) > len(body):
            body, term, out.tier = body2, term2, 2
    out.n_candidates, out.n_valid, out.terminator = n_c, n_v, term
    if not body:
        out.tier = 0
        if pre_rule and section == "risk":
            out.status = "NOT_COVERED:pre_rule"
        else:
            out.status = "NOT_LOCATED" if n_c == 0 else "NOT_LOCATED:unterminated"
        return out
    if section == "mda":
        cut = _ICFR_HEAD.search(body)
        if cut is not None and len(_WORD.findall(body[:cut.start()])) >= min_words:
            body = body[:cut.start()].rstrip()
            out.detail["trimmed_icfr"] = True
    content = _strip_title(body)
    words = len(_WORD.findall(content))
    out.n_words = words
    if _CONTAMINATION.search(body):
        out.status = "CONTAMINATED"
        return out
    if words < min_words:
        if _INCORP.search(content):
            out.status = "NOT_COVERED:incorporated_by_reference"
        elif _NOT_REQ.search(content):
            out.status = "NOT_COVERED:not_required"
        elif pre_rule and section == "risk":
            out.status = "NOT_COVERED:pre_rule"
        else:
            out.status = "TOO_SHORT"
        return out
    if section == "mda" and words < 400 and _INCORP.search(content[:2000]):
        out.status = "NOT_COVERED:incorporated_by_reference"
        return out
    out.status = "OK"
    out.text = re.sub(r"\s+", " ", body).strip()
    return out


# MD&A located by TITLE (no "Item 7"), for filers whose Item 7 is a pointer into another part of
# the same document (the "Form 10-K cross-reference index" format: ETN, IBM, XOM, WFC, C, USB ...).
_MDA_TITLE = re.compile(r"^(?:MANAGEMENTSDISCUSSIONANDANALYSIS|FINANCIALREVIEW$)")
_MDA_ENDS = ("QUANTITATIVEANDQUALITATIVE", "QUALITATIVEANDQUANTITATIVE", "MARKETRISKDISCLOSURE",
             "SIGNATURE", "EXHIBITINDEX", "OTHERINFORMATION", "UNREGISTEREDSALES", "EXHIBITS",
             "RISKFACTORS", "CONTROLSANDPROCEDURES", "LEGALPROCEEDINGS", "PARTIIOTHERINFORMATION",
             "REPORTOFINDEPENDENTREGISTERED",
             "MANAGEMENTSREPORTONINTERNALCONTROL", "MANAGEMENTSRESPONSIBILITY",
             "CONSOLIDATEDSTATEMENTSOF", "CONSOLIDATEDSTATEMENTOF", "CONSOLIDATEDBALANCESHEET",
             "STATEMENTOFCONSOLIDATED", "STATEMENTSOFCONSOLIDATED", "FINANCIALSTATEMENTSAND",
             "REPORTSOFINDEPENDENT")
_MAX_HEADING_LINE = 220


# Leading "PART II -" and/or "Item 3." / "Items 7 and 7A." stripped from the RAW line: an item letter
# only counts when it stands alone ("1A." yes; "3. Quantitative" must not lose its "Q").
_ITEM_PART_PREFIX = re.compile(
    r"^[\s\W]*(?:PART\s+(?:IV|I{1,3})\b[\s\W]*)?"
    r"(?:ITEMS?\s*\d{1,2}(?:\s*[A-Z](?![A-Za-z]))?"
    r"(?:\s*(?:AND|&)\s*\d{1,2}(?:\s*[A-Z](?![A-Za-z]))?)?[\s\W]*)?",
    re.IGNORECASE)


def _line_keys(text: str) -> list[tuple[int, int, str]]:
    """(start, end, key) of every short line — heading-like lines only. The key is the upper-case
    alphanumeric line with a leading "PART II" / "Item 3." stripped, then letters only: b6_parse/1
    keyed on letters only, so "Item 3. Quantitative and Qualitative ..." became "ITEMQUANTITATIVE..."
    and never matched a terminator — the cause of the 52 runaway MD&A sections (review F4). A line
    that is only "PART II" keys as "PARTII"."""
    out, pos = [], 0
    for line in text.split("\n"):
        end = pos + len(line)
        if 0 < len(line.strip()) <= _MAX_HEADING_LINE:
            stripped = _ITEM_PART_PREFIX.sub("", line, count=1)
            key = re.sub(r"[^A-Za-z]", "", stripped).upper()
            if not key:
                key = re.sub(r"[^A-Za-z]", "", line).upper()      # a bare "PART II" -> PARTII
            out.append((pos, end, key))
        pos = end + 1
    return out


def mda_by_title(text: str, min_words: int = 1000) -> tuple[str, str]:
    """Longest MD&A body that starts at a short title line and ends at the next short line opening
    a known post-MD&A section (prefix-stripped keys: "Item 3. Quantitative ...", "PART II", ...) ->
    (body, 'title_fallback'). b6_parse/2: END-OF-DOCUMENT IS NEVER A TERMINATOR. With no terminating
    heading, the body is cut at the earliest document-end marker (signature block, either signature
    sentence, "/s/", an auditor-report heading, an exhibit-index heading) -> 'title_fallback_docend';
    with no marker either -> rejected. b6_parse/1 accepted end-of-document when it looked clean and
    52 of 52 such S&P sections ran through Part II to the 10-Q signatures (review F4).
    Every accepted body must also pass `_CONTAMINATION`. Nothing acceptable -> ('', '')."""
    lines = _line_keys(text)
    best, best_src = "", ""
    for i, (s0, e0, k0) in enumerate(lines):
        if not _MDA_TITLE.match(k0):
            continue
        end, src = None, ""
        for s1, _e1, k1 in lines[i + 1:]:
            if _MDA_TITLE.match(k1):
                continue
            if k1 == "PARTII" or k1.startswith(_MDA_ENDS):
                end, src = s1, "title_fallback"
                break
        if end is None:
            cut = _DOC_END.search(text, e0)
            if cut is None:
                continue
            end, src = cut.start(), "title_fallback_docend"
        else:
            cut = _DOC_END.search(text, e0, end)
            if cut is not None:
                end, src = cut.start(), "title_fallback_docend"
        body = text[e0:end].strip()
        if len(_WORD.findall(body)) >= min_words and not _CONTAMINATION.search(body) \
                and len(body) > len(best):
            best, best_src = body, src
    return best, best_src


def is_pre_rule(form: str, period_end: str | None) -> bool:
    """Item 1A was required for fiscal years ending on/after 2005-12-01 (10-K); the first 10-Qs
    carrying Part II Item 1A cover quarters after that 10-K (period ends from ~2006-03)."""
    if not period_end:
        return False
    cutoff = "2005-12-01" if form == "10-K" else "2006-03-01"
    return str(period_end)[:10] < cutoff


def parse_document(raw: str, form: str, period_end: str | None = None) -> dict[str, object]:
    """Parse one decoded filing document into the B-6 section record."""
    if form not in TARGETS:
        raise ValueError(f"unsupported form {form!r}")
    text = doc_to_text(raw)
    heads = find_headings(text, form)
    pre = is_pre_rule(form, period_end)
    rec: dict[str, object] = {"doc_chars": len(text), "n_headings": len(heads)}
    for sec in ("risk", "mda"):
        s = extract_section(text, form, sec, heads=heads, pre_rule=pre)
        source = ("item_trimmed_icfr" if s.detail.get("trimmed_icfr") else "item") \
            if s.status == "OK" else ""
        if sec == "mda" and s.status != "OK" and not s.status.startswith("CONTAMINATED"):
            # the item carve failed: a title-located MD&A in the same document (the
            # cross-reference-index / integrated-report layouts: ETN, XOM, GHC, USB, C ...)
            body, src = mda_by_title(text, min_words=1000 if form == "10-K" else 300)
            if body:
                s.status, s.text, source = "OK", re.sub(r"\s+", " ", body).strip(), src
                s.n_words = len(_WORD.findall(body))
            elif s.status == "NOT_COVERED:incorporated_by_reference":
                s.status = "NOT_COVERED:incorporated_by_reference_external"
        if (sec == "risk" and form == "10-Q" and s.status == "NOT_LOCATED"
                and len({h.cls for h in heads if h.cls.startswith("II")}) >= 2):
            # Part II exists but carries no Item 1A at all (e.g. Merck's 10-Qs list Items 1, 2, 6)
            s.status = "NOT_COVERED:item_absent"
        rec[f"{sec}_source"] = source
        rec[f"{sec}_status"] = s.status
        rec[f"{sec}_text"] = s.text
        rec[f"{sec}_tier"] = s.tier
        rec[f"{sec}_terminator"] = s.terminator
        rec[f"{sec}_n_cand"] = s.n_candidates
        rec[f"{sec}_n_valid"] = s.n_valid
        rec[f"{sec}_words"] = s.n_words
    return rec
