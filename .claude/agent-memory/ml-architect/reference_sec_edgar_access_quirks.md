---
name: sec-edgar-access-quirks
description: SEC EDGAR access — UA policy per host (Archives 403s a contact-less UA while data.sec.gov accepts it), rate limits, submissions JSON paging, cost per filing
metadata:
  type: reference
---

- **UA policy differs by host (observed 2026-11-11):** `User-Agent: ArchonDEX-research/1.0`
  (no contact) -> `data.sec.gov/submissions/*.json` 200; `www.sec.gov/Archives/edgar/data/...`
  (every filing DOCUMENT) -> 403 "Your Request Originates from an Undeclared Automated Tool".
  The SEC's documented form is "Company Name contact@domain". Never put the user's personal
  email in a UA without their explicit say. A UA decision is the user's. RULED 2026-11-11 (user,
  via the director, for B-6): the T-237 UA (`scripts/lazy_prices/ingest_filings_t237.py:UA`) is
  approved for SEC EDGAR hosts ONLY — import the constant, never duplicate the literal, and refuse
  any non-SEC host in the fetch function (`b6_edgar.fetch` does). Re-check the ruling's scope
  before using it for a different task.
- Throughput (B-6, 2026-11-11): gzip cuts a 4.5 MB 10-K to ~0.34 MB on the wire; one serial
  process at a 0.45 s floor does ~1.7 docs/s (latency-bound) — two concurrent streams stay <4.5/s.
- Fair access: <= 10 req/s; use <= 4–5/s serial; never parallelize the fetch.
- Submissions JSON: `filings.recent` (~1000 rows) + `filings.files[]` older pages; all forms
  in one array (10-K and 10-Q selection from the same cached JSON). Amendments (10-K/A)
  are separate form strings — exact-match to exclude.
- `acceptanceDateTime` is true UTC.
- Cost: ~0.3–1 s per primary doc (multi-MB 10-Ks); T-237 10-K-only PIT-604 took ~3–4 h cold.
- Loughran-McDonald dictionaries live at Notre Dame SRAF (Drive-hosted), NOT EDGAR — a
  separate external service needing approval; nothing vendored locally as of 2026-11-11.
See [[t237-lazy-prices-parse-similarity]].
