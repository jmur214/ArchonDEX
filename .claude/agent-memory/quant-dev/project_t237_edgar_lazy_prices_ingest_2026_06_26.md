---
name: t237-edgar-lazy-prices-ingest
description: T-237 Lazy-Prices EDGAR 10-K/10-Q document ingest — built, validated, and the full-universe cost numbers + EDGAR doc-format gotchas
metadata:
  type: project
---

T-237 "Lazy Prices" (Cohen-Malloy-Nguyen) FALSIFICATION pilot. Built the EDGAR
10-K/10-Q DOCUMENT ingest at `scripts/lazy_prices/ingest_filings_t237.py`
(reuses the access layer from `scripts/fetch_8k_edgar_t137.py`). Output panel:
`data/edgar/lazy_prices/filing_index.parquet`; raw docs cached under
`data/edgar/lazy_prices/raw/CIK{cik:010d}/{accession}.html`. Only the .py is
committed (data/ is gitignored at line 28 of .gitignore — whole `data/` tree).

**Why:** test whether YoY change in filing TEXT predicts returns on our
substrate. PIT key is `acceptance_dt` = `acceptanceDateTime` (full ISO with
time + Z, e.g. "2005-12-01T02:22:48.000Z"), NOT filingDate (date-only) nor
reportDate (period end, months earlier). Per `[NN-AI-GATE]` the prior on text
finding alpha is the open question — this is a NEW-DATA modality the price
vocabulary can't see, so it's a legitimate exploration (separate track, no
live integration).

**How to apply (cost estimate for the full PIT-691 ingest):**
- 5-ticker (AAPL,MSFT,JPM,XOM,KO) 10-K-only, since 2005: 108 filings, all
  fetch_ok, ~21-22 consecutive years each (clean YoY pairing). In-loop
  wall-time 519s for ~190 requests (108 docs + ~82 submissions json/pages).
- Per company ≈ 38 requests (1 recent + ~15 older submission pages + ~21
  docs) and ≈ 104s when fully cold. At RATE_SLEEP=0.13 the floor is req×0.13;
  observed is ~2-3x that because EDGAR doc fetches themselves are slow (some
  multi-MB 10-Ks). For PIT-691 names: ~26k requests, raw ≈ 56 min at the rate
  floor but realistically ~3-4 HOURS cold (network-bound, not CPU). 10-K only.
  Adding 10-Q roughly 4x's the doc count (4 quarterlies/yr, but Q4 is the K) →
  budget a ~half-day cold ingest. Re-runs are OFFLINE: 108 docs replayed in
  0.8s with network blocked.
- This is a campaign candidate for cloud per CLAUDE.md (>2h, parallelizable by
  ticker) but ingest is I/O to SEC, not CPU — local overnight is fine and
  avoids hammering SEC from many cloud IPs (fair-access). Single-process at
  7.7 req/s is the polite ceiling; do NOT parallelize the fetch.

**EDGAR doc-format gotchas (downstream similarity parser must handle):**
- Older filings' primaryDocument (e.g. JPM CIK19617 2009) is an SGML-WRAPPED
  .htm: the body is real HTML but wrapped in SEC `<DOCUMENT><TYPE>10-K
  <SEQUENCE><FILENAME>...<TEXT><HTML>...` tags. Strip the wrapper before
  bs4/text extraction.
- Pre-2001 filings are often plain-text .txt with NO HTML and frequently no
  primaryDocument in the submissions arrays at all → those rows come back
  fetch_ok=False / skip_reason="missing_primary_document". Since-2005 default
  (Item 1A risk-factor mandate) sidesteps most of this; for the 5-ticker
  large-cap sample 0 were missing.
- `[NN-FAIL-CLOSED]` is enforced: a missing primaryDocument or a failed fetch
  is written as a fully-populated row with fetch_ok=False + non-empty
  skip_reason ("missing_primary_document" / "fetch_error:<ExcType>"), NEVER
  dropped, NEVER a silent zero. Verified by direct unit exercise of
  ingest_filing on both paths.
- Documents stored as raw BYTES (write_bytes), not decoded text — the
  similarity step needs verbatim bytes and old filings have mixed encodings.

See [[feedback_prefer_repoint_over_rebuild_2026_06_04]] — reused the t137
access layer wholesale rather than rebuilding.
