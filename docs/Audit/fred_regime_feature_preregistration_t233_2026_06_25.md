# FRED Credit-Spread / VIX-Term Regime Feature — PRE-REGISTRATION (T-233, 2026-06-25)

**Written BEFORE measurement** (`[NN-MBL]`). **FEASIBILITY ONLY** — measure
whether a free FRED credit / VIX-term signal would have de-grossed *earlier*
(or, on the slow bears, *at all*) vs the validated always-on trend overlay at
the T-221 crisis onsets. **NO integration, NO canon change, OFF-default.** If
it leads → propose a pre-registered A/B (don't build). Reuses the T-221
crisis-onset + overlay de-gross dates ([[project_t221_regime_ground_truth_2026_06_19]]);
canonical regime path per T-222.

## The pre-registered question
At each T-221 crisis (dotcom, GFC, COVID, 2022), does a simple threshold on a
FRED credit / VIX-term signal trigger a de-gross BEFORE the trend overlay's
first de-gross — measured by trading-day lead AND the SPY drawdown-from-peak
already incurred at the trigger (smaller = earlier)? Honest focus: the **slow
bears (dotcom, 2022)** where the HMM is structurally weak (T-172) — does
**credit stress** help *there*?

## Data (deterministic, on-disk; PIT-clean) + the HY-OAS caveat
- **Credit (deep, all crises):** `BAA10Y − AAA10Y` (Moody's Baa−Aaa, FRED, on
  disk 2000-2026) — the deep credit-stress proxy.
- **HY OAS (`BAMLH0A0HYM2`) — DATA GAP, flagged:** the live FRED series is
  restricted to a ~3yr rolling window (on disk only 2023-04→); the ALFRED
  vintage query returned HTTP 400. Deep PIT HY OAS is **not readily
  obtainable** this session → BAA−AAA is the deep stand-in. HY OAS is *more*
  sensitive than Baa−Aaa, so a BAA−AAA lead is a **conservative lower bound**
  on the credit-signal's lead; a deep HY OAS (ALFRED/Wayback) is the
  production-data step IF the feasibility leads.
- **VIX term structure (`VIX/VIX3M` ratio):** on disk 2020-01→ → covers
  **COVID + 2022 only** (no dotcom/GFC term structure available). Ratio ≥ 1.0
  = backwardation = stress.
- **VIX level (deep):** `data/research/vix_deep_t172.csv` (1995+, all crises)
  — vol-stress reference.
- **Dollar (`DTWEXBGS`):** on disk 2006+ → GFC/COVID/2022 (no dotcom).
- SPY price for drawdown-at-trigger: `build_deep_panel().spy_close` (T-172/221
  — the SAME source as the T-221 dates, so apples-to-apples).

## The pre-registered de-gross rule (ONE rule, causal, no sweep)
Each signal "de-grosses" on the first date its **z-score > +1.0 over a
trailing 252-trading-day window, sustained ≥ 3 consecutive days** (causal —
the window ends at t; no lookahead). For `VIX/VIX3M` ALSO report the natural
absolute onset (**ratio ≥ 1.0**, sustained 3d). Constants fixed here; NO sweep
(sweeping the threshold is the overfit).

## The measurement (per T-221 crisis, per signal)
1. First de-gross date inside the crisis window (peak→trough).
2. SPY drawdown-from-peak at that date.
3. **Lead/lag vs the overlay** (trading days; − = the signal led the overlay):
   overlay first de-gross from T-221 — dotcom 2000-07-31 (+3.8%), GFC
   2007-10-22 (−3.8%), COVID 2020-02-26 (−7.9%), 2022 2022-01-20 (−6.5%).

## Decision rule (fixed now)
- **LEADS** (→ propose a pre-registered A/B) iff a credit/VIX signal de-grosses
  with a **materially smaller drawdown-at-trigger than the overlay (≥ ~5pp
  earlier)** in **≥ 2 crises INCLUDING ≥ 1 slow bear (dotcom or 2022)** — i.e.
  it adds protection where the overlay/HMM are weakest.
- **REFUTED** (→ "no lead; FRED regime feature is not an overlay-timing
  improvement") if the signals fire at-or-after the overlay's drawdown
  everywhere, or only marginally earlier in the fast crises (where the overlay
  already de-grosses early).
- A signal with NO data for a crisis is reported as `n/a` (not a fail) —
  `[NN-FAIL-CLOSED]`: HALT only on a degenerate/all-constant series, never
  fabricate a trigger.

## Out of scope
- Integration / canon change / live sizing — none (feasibility).
- Any Sharpe/return claim is out of scope here (timing-lead analysis only); if
  the A/B is proposed it carries `[NN-SHARPE-CI]` block-bootstrap then.
