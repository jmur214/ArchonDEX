---
name: text-section-parse-classify-not-regex-match
description: When extracting named sections from filing/document text, CLASSIFY each candidate heading, REQUIRE a terminating heading, and audit "ok" rows with end-of-document markers
metadata:
  type: feedback
---

When extracting named sections (Item 1A, Item 7, MD&A, etc.) from SEC filing text or
similar structured-prose documents, a bare heading regex (`\bItem\s*1A\b`) is a latent
parse bug — it produces silently-truncated or wrong-span sections that LOOK parsed.

**Why:** real filings saturate the same token across (a) table-of-contents lines,
(b) inline cross-references ("see Item 7 of this Form 10-K"), (c) repeated running
page-headers, and (d) intra-word-space artifacts from inline-XBRL ("I TEM 7",
"RIS K FACTORS"). On T-237 this produced the WORST failure: a cross-ref "Item 1A. Risk
Factors" (title included, so the title-lookahead classifier accepted it) inside MD&A's
forward-looking-statements paragraph, no terminating heading after it, carve ran to EOF,
and "longest span wins" SELECTED the runaway — 40% of "parse_ok" Item 1A rows were
MD&A tail + financial statements (found 2026-11-11 by B-6, months after "validation").

**How to apply:**
1. Enumerate every candidate heading token; classify with local context on BOTH sides
   (veto connectors after: of/under/see/in Part/comma/bullet; veto quote/see/refer-to/in
   BEFORE the token — a title after the token is NOT sufficient).
2. Carve to the next genuine heading of ANY later item in canonical order; if the carve
   hits end-of-document it is UNTERMINATED -> fail closed, never "longest span wins" on
   an unterminated span.
3. Audit the "ok" rows, not just the failures: unambiguous end-of-document markers inside a
   section (signature boilerplate "Pursuant to the requirements of Section 13 or 15(d)",
   "Report of Independent Registered Public Accounting Firm") and a length distribution
   vs the marker-free population. A failure census that reads only skip_reason certifies
   nothing about the successes.
4. Minimum-length guards pass stubs ("incorporated by reference" ~400 chars) — classify
   incorporation-by-reference explicitly (NOT_COVERED or follow EX-13), don't length-gate.
5. Validate on a broad random sample across years/sectors, not 2 mega-caps.
6. (B-6 review F4, 2026-11-12) A FALLBACK carve is still a carve: my title-located MD&A fallback
   accepted end-of-document "when clean" and 52/52 such sections ran through Part II to the 10-Q
   signatures. Causes: heading lines keyed on letters only ("Item 3. Quantitative" -> ITEMQUANT…
   never matched a terminator) and a contamination check that knew only the 10-K signature
   sentence. Strip "PART II"/"Item N." from the RAW line before matching (an item letter counts only
   standing alone), never accept end-of-document, cut at /s/, both signature sentences and
   auditor-report headings. Never write "cannot occur by construction" for anything with a fallback.
See [[t237-lazy-prices-parse-similarity]].
