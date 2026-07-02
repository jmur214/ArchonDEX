---
name: text-section-parse-classify-not-regex-match
description: When extracting named sections from filing/document text, CLASSIFY each candidate heading; don't trust a bare heading regex
metadata:
  type: feedback
---

When extracting named sections (Item 1A, Item 7, MD&A, etc.) from SEC filing text or
similar structured-prose documents, a bare heading regex (`\bItem\s*1A\b`) is a latent
parse bug — it produces silently-truncated or wrong-span sections that LOOK parsed.

**Why:** real filings saturate the same token across (a) table-of-contents lines,
(b) inline cross-references ("see Item 7 of this Form 10-K"), (c) repeated running
page-headers, and (d) intra-word-space artifacts from inline-XBRL ("I TEM 7",
"RIS K FACTORS"). On the T-237 AAPL/MSFT validation set this caused Item 7 to truncate
to ~1.2K chars (grabbed a cross-ref span) and a whole filing to fail to parse — both
would have been WRONG NUMBERS that look right, exactly the [NN-FAIL-CLOSED] failure mode.

**How to apply:** enumerate every candidate heading token, then CLASSIFY each (genuine
heading vs cross-ref vs running-header) using local context — veto on connector words
immediately after the token, confirm the canonical section title in a short lookahead
AFTER stripping non-letters (so intra-word spaces don't defeat it), then carve bodies
between consecutive genuine headings with "longest span wins" to drop the ToC entry.
And ALWAYS fail closed: a section that can't be located is parse_ok=False + skip_reason,
never an empty string masquerading as a parsed-but-empty section.
See [[t237-lazy-prices-parse-similarity]] for the worked patterns and the exact filings
that broke each naive approach.
