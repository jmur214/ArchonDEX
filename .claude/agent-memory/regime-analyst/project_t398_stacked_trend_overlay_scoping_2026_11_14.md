---
name: project-t398-stacked-trend-overlay-scoping-2026-11-14
description: T-398 scoping (2026-11-14) of a buy-and-hold stacked trend overlay (RSST structure) on investable returns — the overlay's fixed cost hurdle, the break-even haircuts on B-5's AQR arm, and why no investable record can decide it
metadata:
  type: project
---

T-398 Phase 1 (census + prereg, no returns computed) for "100% equity + trend overlay vs 1× equity on
terminal wealth, with INVESTABLE trend returns". Prereg:
`docs/Sources/prereg_t398_stacked_trend_overlay_2026-11-14.md`; census beside it. Status at writing:
DRAFT awaiting the director's rulings — check the TASK_LEDGER row before quoting any of this as a result.

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
