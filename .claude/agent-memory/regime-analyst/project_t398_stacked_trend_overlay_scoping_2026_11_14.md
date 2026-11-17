---
name: project-t398-stacked-trend-overlay-scoping-2026-11-14
description: T-398 (2026-11-14) stacked trend overlay (RSST structure) on investable fund returns — H1 NOT MET, +0.37 %/yr [−3.89, +4.17] on 2010-09→2025-12; the overlay's cost hurdle, how trend behaves across equity regimes, AQR break-even haircuts, and why no investable record can decide it
metadata:
  type: project
---

T-398: "100% equity + trend overlay vs 1× equity on terminal wealth, with INVESTABLE trend returns".
Prereg `docs/Sources/prereg_t398_stacked_trend_overlay_2026-11-14.md`; verdict
`docs/Audit/t398_stacked_trend_overlay_verdict_2026-11-14.md`. Independent review by execution
(2026-11-14) confirmed every number; review round 1 corrected the write-up (below). Check the
TASK_LEDGER row before quoting.

**RESULT (run as an estimate by the director's ruling; H1 scored as frozen):** +100% overlay on a
14-fund live composite, 15.3 yr: Δ log wealth **+0.37 %/yr, CI [−3.89, +4.17]**, active IR 0.05, CI
[−0.48, +0.55] (MBL needs 0.76 at the gate in force, N_eff 372.28). NOT MET, straddles zero. Regime facts measured, reusable:
- Composite net excess over cash +1.9 %/yr at 7.9% vol; Sharpe 0.24, CI [−0.29, +0.73] (21-day
  blocks) — not distinguishable from zero. Daily corr with equity +0.07.
- **Any single large year moves the sign:** the +5.7 log-point total is the small difference of big
  years. Dropping 2022 (+15.8), 2014 (+10.9) or Sep–Dec 2010 (+7.0) each flips it negative; dropping
  2018, 2023, 2011 or 2012 each more than doubles it.
- **Keep two frames apart (the review's MAJOR-1).** *Since the start (2010-09):* behind SPY on 39% of
  days, at worst −8.8%, longest stretch behind 2.6 yr; −3.7% at end-2019; +5.9% at end-2025.
  *Below its own earlier relative high:* 6.9 yr (2015-04→2022-03), during which it was still AHEAD
  since the start on 58% of days; worst 3-yr fall −25.1% (from +30.9% to −2.0% since the start).
  "−10% over 2011–2019" is a January-2011 starter. Never state a below-own-high figure as "behind SPY".
- **In 7 equity falls ≥10% the arm lost MORE than SPY in 5.** Pooled corr −0.14 [−0.31, −0.02], but
  the exclusion of zero rests on 2015–16 and 2022 (leave either out and the CI spans 0). +0.61 (Feb
  2018) and +0.51 (Feb–Apr 2025): long equity after a rally, hit at the onset. Helped only in the slow
  falls (2015–16, 2022). Slow-bear hedge, not a crash hedge.
- **On point estimates the paper factor's edge is era-bound:** AQR +50% overlay is +5.11 on
  1985–2025 but +1.40 [−1.59, +4.38] (6-month blocks) on 2010–2025. The factor's own mean (post-hoc
  eras): +16.6 %/yr [+12.7, +20.8] before 2010-09, +4.3 [−1.8, +10.5] after. Measured live over-capture
  h_L = +1.1 %/yr [−4.2, +5.8] (seed 0 is the lowest of 50 seeds) — still unpinned, and it says nothing
  about pre-2010 fees. **"Era, not fees" is NOT established** (the review's MINOR-7): don't repeat it.
- Sign of the point flips with the survivorship haircut (0 → +1.37; 2% → −0.62) and with the fee
  gross-up (none → −0.94). Pre-data forecast (±4 CI around ~0) was right: run the power line first.

**Durable facts worth reusing:**
- **A stacked overlay has a fixed hurdle**: per 100% of overlay, ER increment 0.91 + financing spread
  0.1–0.5 + variance cost σ²/2 (0.4–0.8) + correlation cost ≈ **1.5–2.3 %/yr of trend excess return,
  gross of the trend fund's own fee**, before it adds anything. Compare with a net trend premium of
  roughly 1–3 %/yr over cash since 2000 and about zero over 2011–2019 (from memory, unverified).
- **Break-even haircut on B-5's AQR arm, read from B-5's on-disk spread curve** (a haircut on the trend
  leg enters exactly where the spread does, so `h* = s*_ci − 50 bp`): 6.56 %/yr (1985–2025) and
  2.00 %/yr (2000–2025) at a 50% overlay. Measured over-captures: 2.9 (B-5) and 5.3 (T-296), each on
  ~2.5 years with SE ≈ 6 %/yr. At N ≈ 371 the MBL line on 1985–2025 is lost at 4.46 %/yr — between the two.
- **Power, not data, is the wall.** A true active IR of 0.2–0.3 needs 43–96 years for a 50% chance of
  ci_low > 0. Live trend funds give ~15 years (3 funds from 2010), SG Trend 26. Pre-data prior that H1
  is met: 6%. B-8 was closed unrun on a weaker power gap.
- **Live-fund composites from yfinance are survivor-only** (dead mutual funds are delisted on Yahoo).
  Pre-declare a survivorship haircut and say it is a judgment.
- **Regime shape of trend vs equity:** helps in slow bears (2008, 2022), is long equity and loses at the
  onset of fast crashes (early 2018, March 2020, April 2025). Not a crash hedge; a slow-bear hedge.
  It is the complement of the bond stack, which fails in ρ(stock, bond) > 0 inflation regimes
  ([[project-b5-route-c-closed-correlation-regime-bet-2026-11-11]]).

**Process lessons from the review (2026-11-14):** tests must DRIVE the harness's own composite/panel
on a synthetic snapshot and be proven by single-line reversion (7 reversions survived 28 green tests);
FP-guard tests need a tiny NON-zero std (np.full gives exactly 0); gate/integrity files must be bound
to the manifest md5; a monthly 1-block bootstrap is iid — print the auto block beside it; every Sharpe
and IR needs its interval; commit before any network step runs.

**Data-source facts learned in Phase 2 (2026-11-14, before any return was computed):**
- Yahoo Adj Close DOES neutralize trend mutual funds' big December distributions (70 of 70 raw falls
  ≥ 3% with a recorded distribution were neutral; e.g. ASFYX 2022-12-29 raw −24%, adjusted +0.05%).
  The real defects are different: one-day bad prints that reverse (RYMFX 2017-04-21/24), stale NAVs
  that catch up a day later, and thin-ETF close noise (FMF carries 17 of 45 integrity flags).
- yfinance `info["category"]` is empty for mutual funds; the fund overview's `categoryName` has it.
  `netExpenseRatio` is in percent (SPY 0.0945). AQMIX's reads 3.09% (annual-report ratio) — cap it.
  `fundInceptionDate` is unreliable; `firstTradeDateMilliseconds` matches the first price.
- CSAIX (Credit Suisse Managed Futures) is gone from Yahoo — survivorship, witnessed.
- BarclayHedge's BTOP50 page serves only the last five years without a login; history is gated.
  SG Trend/CTA are registration-gated. No free long net CTA index exists.

**Why:** B-5 left the overlay "neither closed nor opened"; the owner asked about futures and options
with constraints relaxed.

**How to apply:** Before proposing any managed-futures or return-stacking test again, run the power
line first and price the hurdle. Read a haircut off an existing spread curve instead of re-running.
Earlier managed-futures results each tested a different use (T-296 gated sleeve leg, T-253/T-170
displacement, T-311/T-333 equity timing, T-316 5% shadow) — do not cite them as verdicts on the overlay.
See also [[project-b5-financing-inputs-census-2026-11-11]].

**Corrected in review round 1 (2026-11-14), was → now:** "Sharpe 0.24" bare → with CI [−0.29, +0.73];
"IR 0.05" bare → with CI; "payoff is one year (2022)" → any of several big years flips the sign;
"−10% relative over 2011–2019; 6.9 years below peak" read as a standing → two frames stated apart;
"the gap is the era, not fees" → not established, point estimates only.
