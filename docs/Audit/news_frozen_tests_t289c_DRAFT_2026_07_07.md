---
task_id: T-2026-07-07-289c
title: The ONE frozen news-interaction test set (DRAFT — director freezes before any run)
date: 2026-07-07
author: Agent D
type: pre-registration DRAFT (N_trials = 4; NOT yet run — awaiting director freeze)
status: DRAFT — do NOT run until the director freezes. Branch feature/news-lane-t289
---

# T-289c — the frozen news-interaction tests (DRAFT)

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

## Process
DRAFT only — the director FREEZES this doc (thresholds + specs) before ANY run. On freeze: run a1→a2→a3→b1,
each pre-registered, honest-N (news family = these 4 trials), report as an interaction table with the verdicts.
No test runs until the freeze.
