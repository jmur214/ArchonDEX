---
task_id: T-2026-08-15-341
title: T-341 — paperswithbacktest Hugging Face datasets: VERDICT = REJECT (survivorship claim is FALSE)
date: 2026-08-15
worker: Agent B
branch: feature/hf-dataset-audit-t341
status: DONE. VERDICT — REJECT as substrate extension and as delisted-name crosscheck. N+=0 (a data audit, not a trial). Nothing canonical touched it.
---

# T-341 — the audit: the "survivorship-aware" claim does not survive contact

Audited: `paperswithbacktest/Stocks-Daily-Price` shard 0 of 4 (**6,454,766 rows, 1,885
symbols, 1962-01-02 → 2026-07-06**, ~131 MB). Alphabetically sharded (A…AACG…).

## VERDICT: **REJECT** — do not adopt as an `[NN-MBL]` substrate extension, and do not use
## as a crosscheck for anything involving delisted names or universe studies.

## The killer: the delisting claim is FALSE, and provably so
The dataset is advertised as survivorship-aware, *"including delisted names"*. Two
independent tests refute that.

**(a) AGGREGATE — nothing ever dies.** Final-observation dates across all 1,885 symbols:
| final date range | symbols |
|---|---|
| 1962–2000 | **0** |
| 2000–2015 | **1** |
| 2015–2024 | **0** |
| 2024–2027 | **1,884** |

**1,884 of 1,885 symbols run to the present.** Over a 64-year window on US equities that
is not merely unlikely — the majority of listed US companies delist, merge, or fail over
such a span. **Zero pre-2024 terminations is the signature of a CURRENTLY-LISTED universe
back-filled to 1962** — i.e. maximally survivorship-BIASED, the exact defect the T-256 /
Stooq paranoia exists to catch. It is the *opposite* of the claim.

**(b) SINGLE-NAME — the mechanism, on the T-271 recycled-ticker case.** `BBBY` (Bed Bath &
Beyond, Chapter 11 April 2023, **equity cancelled September 2023**) is present with
**6,063 continuous bars (max gap 5d) through 2026-07-06**, median 2026 volume **1,919,700**.
A cancelled equity cannot trade. And the series matches the real company at **no point**:

| year | dataset close | real BBBY |
|---|---|---|
| 2013 | 11.29–34.97 | ~$70–80 |
| 2015 | 12.04–25.79 | ~$60–70 |
| 2023 | 13.93–37.86 | **~$0.25 pre-Ch11** |

**There is no seam** — no discontinuity marking a substitution. So it is not a splice of
old-BBBY + successor; the *entire* series belongs to some other security occupying the
ticker. **This is worse than a gap: a gap is detectable, this is not.** Anyone reading
"BBBY rows through 2026" as delisting coverage would be consuming a different company's
prices under a dead company's name.

## What is GENUINELY GOOD (stated so the rejection is not blanket)
**The corporate-action machinery is correct** — this is a well-built dataset for
*currently-listed* names:
- **`close` is SPLIT-adjusted.** AAPL shows no jump across the 4:1 (2020-08-31) or 7:1
  (2014-06-09) splits, and 2014-06-09 close **23.42 = 93.70 / 4** — properly back-adjusted
  to today's basis.
- **`adj_close` is a genuine TOTAL-RETURN series.** `adj_close/close` is a *constant ratio
  within an era that differs across eras* — **0.9700 (2020)** vs **0.8770 (2014)** for AAPL
  — the exact signature of cumulative dividend adjustment. 782/1,885 symbols show a
  non-zero adjustment (the rest are plausibly non-payers).
- Depth genuinely reaches **1962**, and the schema (`symbol,date,ohlc,volume,adj_close`) is
  the right shape.

**So the defect is not sloppiness in corporate actions — it is the absence of POINT-IN-TIME
SYMBOLOGY.** The vendor appears to key on a *current* symbol master and back-fill, which
silently rewrites history for every ticker whose owner changed.

## License — a separate, independent blocker (flagged, NOT resolved by me)
- Both datasets are **`license: "other"`** — not an OSS licence.
- The card carries: `extra_gated_prompt: "To get access to this dataset, you must
  subscribe to Papers With Backtest… Choose Your Plan > Subscribe."`
- Yet **Stocks-Daily-Price is `gated: False`** and its parquet **downloads without auth**
  (verified: HTTP 206, valid `PAR1`, 130,913,071 B). **The card demands a subscription
  while the files are served openly.**
- **ETFs-Daily-Price is `gated: manual`** — genuinely blocked, so the cross-check against
  our `tr_reconciled` 33 ETFs (audit item 4) **could not be performed**.

**"Technically downloadable" is not "licensed for our use."** This needs a human reading of
paperswithbacktest.com's ToS before anything canonical touches it — and that is true
regardless of the data verdict above. I am not resolving it.

## Honest scope of this audit
- **1 of 4 shards** (1,885 of 7,000+ symbols). The other shards are unexamined — but there
  is no plausible mechanism by which alphabetical position changes survivorship handling,
  and the aggregate signature (zero pre-2024 terminations) is a property of the universe
  construction, not of a symbol range.
- **ETFs dataset untested** (gated). Audit item 4 (tr_reconciled byte-for-byte cross-check)
  is therefore **not done**, and I am not claiming it.
- N+=0 — a data audit, not a trial.

## Recommendation
1. **REJECT** for the multi-decade substrate extension. Our T-306 substrate (index-level,
   survivorship-clean by construction) remains strictly better for that purpose.
2. **REJECT** as a crosscheck wherever delisted names or universe composition matter.
3. **The queued intraday probe** should not assume this vendor's `Stocks-1Min-Price` is
   survivorship-aware either — the same universe construction very likely applies, and it
   would need its own audit.
4. If a *currently-listed single-name price* use ever arises where survivorship is
   irrelevant, the corporate-action handling is sound — but the licence question must be
   settled first.
