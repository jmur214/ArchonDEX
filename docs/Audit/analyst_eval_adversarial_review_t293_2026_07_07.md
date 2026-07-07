---
title: "Info-Layer program — adversarial review of the pre-registrations (fresh-eyes)"
task: T-2026-07-07-293
status: review memo (red-team before the director freezes the pre-regs)
---

# T-293 — adversarial review of the Info-Layer pre-registrations

Red-team of the program's frozen-before-run docs. The drafts (T-289c news-features,
T-291 even-week×FOMC) are not yet committed, so I review against the program spec
(`docs/Sources/info_layer_program_2026_07_07.md`) §1.3 / §2 / §3.3 — the frozen docs
MUST resolve each ⚠ below before the freeze.

## 1. D's news-features test (Lane 1, §1.3) — the load-bearing look-ahead is REVISION

⚠ **`created_at` vs `updated_at` is not the whole trap — article REVISION is.**
Benzinga revises articles; the panel schema keeps `content` + both timestamps and
keys features to `created_at`. But `fetch_history_alpaca` pulls each article's
**current (post-revision) body** and stores it against the ORIGINAL `created_at` →
every historical-backfill feature that reads `content`/`headline` leaks later
information into a PIT-stamped row. The daily-forward pulse captures first-seen and
is clean; **the historical panel is not.** → REQUIRE: treat any article with
`updated_at > created_at + ε` as REVISED; for PIT features either use only a
first-seen snapshot or EXCLUDE revised-article content from the historical panel,
and record `content_is_revision` per row. This is the #1 thing the frozen doc must
nail — it silently inflates every historical news backtest otherwise.

⚠ **Coverage/breadth drift = a calendar/size pseudo-signal.** Benzinga coverage
GREW over the sample; `abn_news_volume` (vs trailing 63d) normalizes the level but
not the cross-sectional COVERAGE shift (which names get covered tracks
size/popularity/era). A "news volume" feature can be a market-cap/liquidity proxy =
beta, not news. → REQUIRE: cross-sectional (within-day RANK) normalization, AND an
explicit check that `abn_news_volume` is not proxying market-cap/ADV (regress it on
size; if loaded, it's beta).

⚠ **Delisting-coverage bias couples to survivorship.** Delisted names get elevated,
then truncated coverage near death; a cross-sectional news feature can pick up
"about to delist/distressed" = information already in price + a survivorship coupling.
→ REQUIRE: the T-289 probe must MEASURE delisted-coverage completeness (it gates the
lane); scope every claim to the covered universe; and each cross-sectional test must
show the news feature adds over a distress/price control (not just re-flagging it).

⚠ **N-accounting must count feature×interaction triples, not "4 tests."** 4 features
(lm_sentiment, vader, abn_news_volume, novelty) × interaction partners is a forking
garden. → REQUIRE: pre-register the EXACT 3–4 (feature, interaction, threshold)
triples; any exploratory feature-screening counts toward honest-N; no post-hoc "best
feature" reporting.

⚠ **T-233 role creep.** a1/b1 are sizing/interaction (OK). REQUIRE every test framed
as conditioning/sizing an EXISTING signal and scored vs the unconditioned null
(fresh-eyes #5); flag ANY test where the news feature is the primary return-timer —
that violates the standing T-233 constraint restated in every pre-reg.

## 2. C's even-week × FOMC (Lane 2, T-291) — this is FAMILY trial #3, not N=1

⚠ **Family-N honesty.** T-250 (even-week standalone: real +5.44 bps, marginal) +
T-268 (even-week × sleeve: H0, closed shelf #6) + T-291 (even-week × `is_fomc_week`)
= **three probes of the SAME FOMC-calendar family, already 2/2 null-to-marginal.**
The MBL bar for T-291 must be set at the **accumulated family-N (≥3)**, not N=1. A
marginal result on a 2/2-null family will not clear an honest family-N bar — the doc
must state this and pre-commit the bar. → REQUIRE: family-N ≥ 3 stated; bar set
accordingly.

⚠ **Threshold/definition gameability.** the FOMC-cycle "even week" definition, the
`is_fomc_week` window, and the interaction threshold are forking paths. → REQUIRE:
import B's `macro_calendar` (byte-identical to the T-250 hardcoded list per §2.3),
freeze ONE interaction spec, no sweep.

## 3. The G1 gate (§3.3) — a base-rate-hedging analyst PASSES it as written. Broken.

The gate: "Brier on ≥150 resolved beats climatological baselines + calibration slope
∈ [0.7, 1.3]." **A model that outputs the climatological base rate for every
prediction has PERFECT calibration (slope ≈ 1) and ZERO skill.** Calibration is a
hedger's-pass, not a skill test — it measures reliability, not RESOLUTION
(discrimination). The only skill component is "Brier beats climatological," and
"beats by any ε on 150 noisy predictions" is not a skill bar. **As written, a
base-rate parrot clears G1.** Fixes (all recommended):

1. **Per-category baselines the model must beat — the KEY one is market-implied.**
   Beat, per category: (a) the unconditional base rate (current); (b) a PERSISTENCE
   baseline for price/direction; **(c) the MARKET-IMPLIED prior where it exists** —
   for FOMC/rate-path predictions the model must beat **Kalshi FedWatch odds**; for
   price levels, option-implied. Beating the market-implied prior is real skill;
   beating the unconditional base rate is not.
2. **Add a RESOLUTION/discrimination requirement.** Calibration alone lets a hedger
   pass with zero resolution. Require a positive discrimination metric (Murphy-
   decomposition resolution term, or AUC, or the skill score `1 − Brier/Brier_base`)
   with a threshold — a zero-resolution hedger must FAIL even if perfectly calibrated.
3. **CI on the skill score, not the point estimate** (`[NN-SHARPE-CI]` discipline).
   150 resolved is a thin Brier sample; require the skill-score bootstrap **ci_low >
   0**, per category, not just point > 0.
4. **Exclude gimmes / difficulty-weight.** A model pads its Brier with near-certain
   claims ("SPY won't drop 30% tomorrow" @ 99%). Exclude predictions with base rate
   > 0.9 or < 0.1 from the skill pool, or entropy-weight — so the record can't be
   padded with trivially-true predictions.
5. **Segment by category** so the model can't pass by being skilled only on easy
   categories while noise-trading the hard ones.

The harness (`eval_harness.py`) already emits per-category Brier + base_rate +
calibration deciles; adding the market-implied + persistence baselines and the
skill-score CI is a small extension I'll wire once B's Kalshi settlement + macro
calendar sources land (the resolvers are already stubbed for them, fail-closed).

## Summary
The harness + resolver spec are shipped and verified. The three pre-regs each have a
concrete hole to close before freeze: **Lane 1 = article-revision look-ahead in the
historical panel** (load-bearing); **Lane 2 = family-N ≥ 3, not N=1**; **Lane 3 (G1)
= a base-rate hedger passes as written → add market-implied baselines + a resolution
requirement + a skill-score ci_low, and exclude gimmes.**
