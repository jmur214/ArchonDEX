---
task_id: T-2026-07-07-289c
title: The ONE frozen news-interaction test set (FROZEN 2026-07-07)
date: 2026-07-07
author: Agent D (frozen by the director with T-293 amendments)
type: pre-registration (N_trials = 4; FROZEN — runs authorized, not yet run)
status: FROZEN — director freeze 2026-07-07, T-293 amendments binding. Branch feature/news-lane-t289
---

# T-289c — the frozen news-interaction tests (FROZEN 2026-07-07)

Per `[NN-AI-GATE]`: news is a NEW data modality (text the price vocabulary can't see), tested on a SEPARATE
exploration track with NO live integration. All tests are **interaction/conditional** (fresh-eyes #5) — never
isolated-signal fishing. **Probe gating (T-289a, applied):** `D-deep` (2015-01 floor, ~11yr) → full covered
window at honest-N; `S-clean` → cross-sectional tests use the full universe incl. delisted (NO re-scope);
breadth thins with cap → cross-sectional tests restrict to **large/mid-cap** (small-cap news is data-thin,
median ~4 art/mo).

## Features (frozen defs — `intelligence/news_features.py`)
`lm_sentiment` (Loughran-McDonald pos−neg over word matches), `vader_sentiment` (compound, reused analyzer),
`abn_news_volume` (as_of-day count vs trailing-63d daily mean), `novelty` (1 − max TF-IDF cosine vs trailing
21d, reuses similarity_t237). PIT: every feature reads only `created_at` < decision-time (never `updated_at`).

## The four pre-registered tests (N_trials = 4)
**(a1) news-volume × momentum.** H1: abnormal news volume *conditions* 12-1 momentum — high-`abn_news_volume`
attention amplifies continuation (or flips to reversal). Construction: sort by momentum within
high/low-abn-volume buckets on the large/mid universe; the INTERACTION (not either alone) is the test. Gate:
interaction-portfolio CAR spread `t_HAC ≥ 2.0`, net of FF5+Mom (`core/factor_decomposition`). Window 2015-2026.

**(a2) LM-sentiment × post-8-K drift.** H1: `lm_sentiment` of news in the [-1,+1] day 8-K window conditions the
post-8-K drift. Anchor on `data/edgar/8k/panel_8k_items.parquet` (183k rows — the EVENT set is depth-immune;
the news-sentiment feature exists only on the 2015+ subset, stated). Construction: sentiment-sorted quintiles
of post-8-K CAR[+2,+21], calendar-clustered `t_HAC` (T-265 method). Gate: top−bottom spread `t_HAC ≥ 2.0`.

**(a3) novelty × reversal** (permitted — we are `D-deep`). H1: high-`novelty` news → overreaction → short-horizon
reversal; repeat news → no reaction. Construction: sort next-[+2,+10]d return by novelty × same-day return
sign. Gate: reversal spread `t_HAC ≥ 2.0`, net of short-term-reversal + factors.

**(b1) aggregate news sentiment/volume as a sleeve SIZING tilt** — **T-233-bound: sizing/context role ONLY,
never trend front-running** (restated: the tilt may only SCALE the validated trend sleeve's exposure by an
aggregate news-state percentile, exactly as the breadth tilt did; it must NEVER generate or advance a timing
signal ahead of the price trend). Construction: the T-273 harness — aggregate market news sentiment/volume →
causal percentile → 0.5-1.0 SPY-leg multiplier on the fair-T-255 ensemble sleeve. Gate: paired ΔSortino +
Δwealth ci vs the unconditioned sleeve, AND (the T-268/T-273 lesson) it must beat the trend overlay's own
de-risking, not merely repeat a wealth-costing de-risk. **Causal-lag discipline (T-273 catch): any feature
from `created_at`-day data must be lagged one day before it sizes the next day's return.**

## Honest priors (stated up front)
All **null-to-marginal.** Published news-sentiment/volume effects are small and heavily decayed
(McLean-Pontiff; the ~50% haircut applies), and (b1) is a sizing tilt in the exact family where even-week
(T-268) and breadth (T-273) both NULLED — its prior is the lowest (~10%). (a2) has the best prior (event-anchored,
depth-immune, largest published effect) but still modest. **The panel's durable value is NOT these backtests —
it is (i) forward accrual from the daily append and (ii) the feed to the judgment/analyst layer.** A clean null
here is the expected, honest outcome and still leaves the panel valuable.

## DIRECTOR FREEZE — 2026-07-07, with the T-293 adversarial-review amendments (BINDING)

The four tests above are frozen as specified, with these amendments folded in before any run:

**F1 — article-revision look-ahead (the T-293 review's Lane-1 hole).** The historical backfill returns each
article's CURRENT (post-revision) body keyed to its original `created_at` — so revised articles leak future
text into the past. Rule: every historical feature is computed ONLY on articles with `updated_at ==
created_at` (unrevised). Revised articles are EXCLUDED from historical feature construction, and the
revised-share is reported per year in the results (if any year's exclusion exceeds ~30% of articles, halt and
flag before proceeding — the corpus composition question then outranks the tests). Forward-accrued articles
(captured same-day by `append_today`) are immune by construction and need no exclusion.

**F2 — coverage-drift control.** Benzinga coverage grew over time, so pooled-over-time bucketing turns
secular coverage growth into a pseudo-signal. Rule: (a1)'s high/low `abn_news_volume` buckets are formed
CROSS-SECTIONALLY WITHIN each rebalance date, never pooled across time; (b1)'s aggregate percentile is a
causal rolling percentile (the T-273 harness form). Any feature trending secularly with the corpus must be
demeaned within-date or defined relative to a trailing window (all four frozen features already are — state
the check in the results).

**F3 — delisting-coverage coupling.** `S-clean` was probed at four names; it is not a universal guarantee.
Rule: the cross-sectional tests (a1, a3) report coverage (articles/name-month) for names that later delist vs
survivors within the window; if coverage differentially decays pre-delisting, flag it and state the direction
of the induced bias in the verdict.

**F4 — family-N honesty.** The news family = these 4 trials. Additionally (b1) is ALSO a member of the
sleeve-sizing-tilt family (T-268 even-week, T-273 breadth precede it → tilt-family N = 3); its verdict must
state both family counts, per the T-293 review's Lane-2 finding on family accounting.

**F1 AMENDMENT — 2026-07-08 (director re-freeze after D's HALT-and-report; BINDING).** The literal
`updated_at == created_at` rule tripped the >30% HALT on ~1-second processing-timestamp updates (median
revised-lag 2.4 min; 95% same-calendar-day) — a false alarm against F1's intent. The materiality boundary is
re-frozen as **cross-CALENDAR-DAY revision**: an article is excluded from historical features iff
`updated_at` falls on a later calendar day than `created_at`. Rationale: the b1/T-273 causal-lag discipline
means day-t features are consumed no earlier than day t+1, so a same-day revision's stored body is never
consumed before the revision existed — no look-ahead channel; only cross-day revisions (measured 0.28% of
articles, max 0.7% in any year) leak future text into a consumed feature day. The >30%/yr HALT is RETAINED
on the cross-day measure; per-year cross-day revised-share is still reported. D's corrected loader
(bc3b770) implements exactly this. Re-run authorized under the amendment; all other freeze terms unchanged.

**Authorization:** run a1 → a2 → a3 → b1 exactly as frozen (gates: `t_HAC ≥ 2.0` for a1/a2/a3; paired
ΔSortino + Δwealth ci + beat-the-overlay's-own-de-risking for b1), honest-N, one interaction table with
verdicts. No spec changes after this line; any deviation = a new pre-registration.

---
## RESULTS (run 2026-07-08, corrected causal windows — supersedes any earlier partial output)

**Corpus:** 771,427 articles / 139 monthly parquets / 546 MB / 2015-01→2026-04. F1 (cross-day materiality,
re-frozen): **769,267 unrevised kept = 99.7%**; revised-share **0-1%/yr** (2015:1%, 2016-22:0%, 2023:1%,
2024-26:0%) — clears the 30% HALT. Exploded to 1,632,298 sym-rows across 4,679 priced symbols.

### The interaction table — ALL FOUR NULL
| test | statistic | t_HAC | gate (t≥2.0) |
|---|---|---|---|
| **a1** news-volume × momentum | interaction **+0.0057** (113 months) | **1.34** | FAIL |
| **a2** LM-sentiment × post-8-K drift | top−bot CAR **+0.0007** (3,981 events) | **0.94** | FAIL |
| **a3** novelty × reversal | hi−lo **+0.0049** (4,000 events) | **0.45** | FAIL |
| **b1** aggregate-news sizing tilt | base 4.26× → tilt **2.69×**, **Δwealth −1.566** | — | FAIL (destroys wealth) |

### ⚠️ a1's apparent PASS was a LOOK-AHEAD artifact (caught pre-report)
The first clean run gave a1 = −0.0187, **t_HAC −5.27, "pass"**. It was an artifact: `mom` was computed as
`car(t, d0 − 252 CALENDAR days, 0, 231 TRADING days)`, mixing units so the "12-1 momentum" window ran
`d0−172td .. d0+59td` — **ending ~85 calendar days AFTER the formation date**, overlapping the forward window
`nxt = car(d0, 1, 21)`. Sorting on `mom` therefore partly sorted on `nxt`, mechanically inflating the spread.
Verified on AAPL/2023-01-31: window 2022-05-24 → **2023-04-26**. Corrected to a causal 12-1
(`car(t, d0, -252, -22)`, both legs strictly before `d0`): the interaction **flips sign to +0.0057 and t
collapses to 1.34**. The look-ahead was the entire effect. (Same class as the T-273 breadth-tilt bug.)

### F3 — delisted-vs-survivor coverage: inclusion is clean, coverage INTENSITY is not
| | delisted | survivor |
|---|---|---|
| symbols | 619 | 4,060 |
| articles/ticker | 269.9 | 360.9 |
| pre-delist coverage ratio (last 90d vs own baseline) | **0.65** | — |

**Flag: news coverage DECAYS ~35% in the 90 days before delisting.** The probe verdict `S-clean` (dead tickers
ARE covered) stands for *inclusion*, but coverage *intensity* falls as a name dies. Any future cross-sectional
news test on delisted names must carry this caveat. It does not rescue a1/a3 (both null regardless).

### Verdict — the news lane's backtestable value is H0; its durable value is FORWARD ACCRUAL
Four pre-registered interaction tests, **zero passes**. b1 makes the **third consecutive sizing-tilt failure**
on the sleeve (T-268 even-week, T-273 breadth, T-289 b1) — the sizing-tilt family (N=3) is closed: the trend
overlay's own de-risking is not improved by conditioning on calendar, breadth, or news. This matches the
frozen doc's stated honest prior ("published news effects are small and decayed; expected null-to-marginal;
the panel's durable value = forward accrual + the judgment layer's feed").

**Health warning on the apparatus:** five defects sat in the test path before it produced a number — an OOM
(explode of the 899 MB content column), `novelty`/`abn_news_volume` raising on every call (dead code), an a3
alphabetical-sampling bias, `car()` off-by-one (its `a==b` case always returned `None`, which would have
nulled a3 spuriously), and a tz crash in a2. Two of those (a3's `None`, a1's look-ahead) would have produced
**confidently-reported wrong verdicts**, not visible crashes. The nulls above are the numbers *after* all five
fixes. N_trials: news family = 4 (a1,a2,a3,b1); b1 also counts in the sizing-tilt family (N=3).
