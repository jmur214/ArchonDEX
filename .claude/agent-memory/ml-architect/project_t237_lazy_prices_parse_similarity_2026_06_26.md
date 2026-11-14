---
name: t237-lazy-prices-parse-similarity
description: T-237 Lazy Prices 10-K panel (Item 1A/7 + YoY cosine) — INVALID as built (B-6 audit 2026-11-11: 40% of "ok" Item 1A run into Item 8/signatures; recycled-ticker CIKs; 604/970 members); EDGAR gotchas, PIT key
metadata:
  type: project
---

T-237 = Cohen-Malloy-Nguyen (J.Finance 2020) "Lazy Prices" falsification pilot, Engine D
offline research track, never wired to an engine (`[NN-AI-GATE]` separate track — filing
text is a NEW-DATA modality). B-6 (T-383, 2026-11-11) is its repair + 10-Q + two-universe
re-run; branch `research/lazy-prices-repair-b6`.

**Where the data really is:** the shared main tree `data/edgar/` (NOT `data/edgar/lazy_prices/`
as the code's constants say): `sections.parquet` (11,464 10-Ks, 604 tickers, 1.1 GB snappy,
ONE row group — pyarrow decompresses a whole text column, ~1.5–2.2 GB RSS even when
streaming), `similarity_panel.parquet` (10,860 pairs), `raw/` = submissions JSONs ONLY
(1,562, through ~2026-05; NO raw HTML anywhere — the ingest parsed-and-discarded).
`data/edgar/lm/` is EMPTY: no Loughran-McDonald dictionary or stopword list exists on disk.

**B-6 audit findings (2026-11-11) — the T-237 panel is NOT evidence either way:**
- 40.1% of parse_ok Item 1A (3,942/9,841) contain the signature-page boilerplate
  ("Pursuant to the requirements of Section 13 or 15(d)") and/or the auditor's report —
  they run into Item 8 / end of document. Marker-free median 54K chars vs marker-present
  273K. Mechanism: a cross-ref to "Item 1A. Risk Factors" inside MD&A's forward-looking-
  statements paragraph is classified as the heading; no 1B/2 heading follows, so the carve
  runs to EOF and "longest span wins" PICKS the runaway (ATI 2023, AAL 2025 seen). The
  real 1A text precedes the stored chunk -> not repairable offline; needs refetch.
- Stub sections pass the 400-char guard (ETR Item 7 = 408 chars, "incorporated by ref").
- Universe: 970 S&P PIT tickers since 2005 vs 604 with sections; 13 are wrong-company
  maps from the LIVE company_tickers.json (S->SentinelOne not Sprint, STI, NE, ADT, MMI,
  BEAM, DYN, KG, LIFE, SGP, TE, APC, ADCT).
- T-341b's diagnosis (15.1% failures, pre-2006 1A reclass, 15 mega-cap Item-7 tickers) is
  correct but INCOMPLETE — it read only `skip_reason`, never the "ok" rows' contents.
- Upper bound on usable rows: 5,786/11,464 (50.5%) ok+marker-free; pairs need both ends.

**How to apply:** never reuse T-237 sections/similarity; re-parse everything with ONE parser
version (mixed-parser pairs manufacture "change"). Build a date-conditional ticker->CIK map
from the local Form 3/4/5 datasets (`data/edgar/insider_zips/`, 2006Q1–2026Q1,
ISSUERTRADINGSYMBOL+ISSUERCIK). See [[text-section-parse-classify-not-regex-match]] for
the carve rules and [[sec-edgar-access-quirks]] for fetch mechanics.

## PIT key (no future leakage)
`acceptanceDateTime` is TRUE UTC (verified: ETN 10-K `2023-02-23T21:22:19Z` has filingDate
2023-02-23; were it ET it would roll to the next day after 17:30). Conservative decision
date = first NYSE session strictly AFTER the literal date in the string (safe under either
reading). Never filingDate / reportDate for sequencing.

## Similarity construction notes
T-237 used per-pair TF-IDF sublinear cosine — NOT CMN's construction (CMN: term-frequency
cosine + Jaccard etc.). sklearn english stopwords (318) since LM StopWords_Generic is not
vendored. Validation on AAPL/MSFT only (cos 0.964/0.954) MISSED the runaway-carve class —
a 2-firm validation set is not a parser test.
