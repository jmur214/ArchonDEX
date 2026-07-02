---
name: t237-lazy-prices-parse-similarity
description: T-237 Lazy Prices pilot — 10-K Item 1A/Item 7 parser + YoY TF-IDF cosine stage; EDGAR HTML parsing gotchas and PIT keys
metadata:
  type: project
---

T-237 is a FALSIFICATION research pilot (Cohen-Malloy-Nguyen, J.Finance 2020): firms
that DON'T change their 10-K language YoY ("non-changers") modestly outperform. Engine
D (Discovery) offline track, research-only, NOT wired to any engine — permitted under
[[feedback_plateau_before_ai_2026_05_01]] / `[NN-AI-GATE]` (separate track, NEW-DATA
text modality the exhausted price vocabulary can't see).

**Why:** the price vocabulary is H0-exhausted (T-196); value, if any, is in new data
modalities like filing text. This is the first such pilot.

**How to apply:** if asked to extend/backtest this, the parse + similarity stage lives
at `scripts/lazy_prices/similarity_t237.py` (worktree agent-a, branch
feature/lazy-prices-pilot-t237). Outputs land under `data/edgar/lazy_prices/`
(gitignored, NOT in the pinned substrate). The DOWNSTREAM backtest stage (event-study
on decision_date forward returns, non-changer long leg) is the user's job, not built here.

## EDGAR 10-K HTML parsing gotchas (load-bearing — these cost the most iterations)
Section extraction (Item 1A Risk Factors, Item 7 MD&A) by bare `\bItem\s*1A\b` regex
FAILS badly. Three classes of non-heading noise, ALL seen on AAPL/MSFT FY2015-2017:
1. **Inline cross-references** — "Item 1A of this Form 10-K under the heading ...",
   "see Item 7, ...", "in Part II, Item 8 ...". AAPL FY2015 had 7 "Item 1A" matches,
   only 2 real headings. Veto by connector word immediately after the token
   (of/under/see/in Part/and/or/comma-quote/bullet).
2. **Running page-headers** — MSFT repeats "Item 7 • <text>" on every MD&A page.
3. **Intra-word spaces injected by inline-XBRL formatting** — MSFT FY2017 heading reads
   "ITEM 1A. RIS K FACTORS" and "MANAGEMENT'S DISCUSSION"; MSFT FY2016's MD&A heading
   reads "I TEM 7." (the word ITEM itself is split). This is the nastiest one.

**Winning approach (in the module):** enumerate every `Item N[L]` token (regex tolerant
of one space inside ITEM: `\bI\s?TEM\s*(\d{1,2})\s*([A-Z]?)\b`), CLASSIFY each as a
genuine heading by (a) NOT being followed by a cross-ref connector AND (b) the canonical
section TITLE appearing in the ~90-char lookahead AFTER stripping all non-letters
(defeats "RIS K FACTORS" -> "RISKFACTORS"). Then carve body between consecutive genuine
headings, "longest span wins" to drop the ToC entry. Min-section guard 400 chars.
Curly apostrophe U+2019 in "Management's" must be matched as wildcard (`.`).

## PIT key (no future leakage)
`acceptance_dt` (SEC acceptance timestamp, e.g. "2016-10-26T16:42:14.000Z") is the ONLY
PIT key — NOT filingDate, NOT period_end. Filings are often accepted POST-CLOSE
(16:00-22:00 ET seen), so decision_date = next business day STRICTLY AFTER acceptance
(pandas BDay(1) on normalized date — always lands strictly later, so a same-day pre-close
acceptance still can't be acted on its own session). Exact NYSE-calendar alignment is the
backtest stage's job.

## Validated cosine numbers (sanity, sklearn english stopwords, per-pair TF-IDF, sublinear_tf)
- AAPL 2015->2016 cosine 0.964, jaccard 0.925 (AAPL rarely overhauls language — HIGH is correct)
- MSFT 2015->2016 cosine 0.954; 2016->2017 cosine 0.956
- identical docs -> 1.0; unrelated -> 0.046. Discriminator works.

## Stop-word provenance
Loughran-McDonald StopWords_Generic (Notre Dame SRAF) is the field standard BUT only
distributed as a Drive-hosted XLSX behind an unstable file id (sraf.nd.edu/.../resources/
404s; GitHub mirrors I tried 404). NOT a reliable pipeline dependency. DEFAULT =
sklearn english (318 words); LM used only if a plain-text copy is vendored locally at
`data/edgar/lazy_prices/lm/StopWords_Generic.txt`. Which list was used is recorded
per-row in the `stopwords_source` column so provenance travels with the data. If the user
wants LM, they drop the txt file in and re-run — no code change.

## SEC fetch mechanics (for the ingest stage / future EDGAR work)
- User-Agent "ArchonDEX research jsm13700@gmail.com" required, <=7 req/s (used ~2 req/s).
- `https://data.sec.gov/submissions/CIK##########.json` "recent" block only ~last 5-7yr;
  older filings are in `filings.files[].name` pages (e.g. CIK..-submissions-001.json).
- AAPL FY2015/2016 fell in the gap between older-page (ends 2015-05) and recent (~2018);
  got them via `browse-edgar?action=getcompany&type=10-K&output=atom`, then the
  per-accession `index.json` for the primary document filename.
- AAPL CIK 320193, MSFT CIK 789019.
