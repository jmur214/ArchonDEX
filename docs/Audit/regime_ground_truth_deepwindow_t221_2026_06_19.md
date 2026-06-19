# Regime Ground-Truth + Defensive-Behavior PRE-SPEC for the deep-window cells (T-221, 2026-06-19)

The verification layer A/T-216 (conjunctive selector) and C/T-211 (composition)
consume when they run their crisis-inclusive **deep-window (2000-2025) cloud
cells**. LABELING + SPEC ONLY — **0 N_trials**, no new strategy arms. Reuses
the frozen causal HMM (T-172) + the always-on overlay (T-204/T-220); forks
nothing. Causal labels only. md5-deterministic. Reproduce:
`python -m scripts.regime_ground_truth_deepwindow_t221`.

## 1. Regime ground-truth (2000-02 → 2026-04)
Causal frozen-HMM (train 2000-2012) forward-filter label. Census: calm 93.2%
/ cautious 0.2% / crisis 6.6%; mean p_crisis 0.182 in known crises vs 0.041
calm (crisis-grade — passes `[NN-CENSUS]`).

| crisis | type | HMM first sustained fire (SPY dd from peak) | overlay first de-gross (SPY dd) | tail protection |
|---|---|---|---|---|
| dotcom 2000 | slow valuation | 2001-09-17 (**−23%**) | 2000-07-31 (**+4%**) | OVERLAY (HMM blind to the grind) |
| GFC 2008 | fast credit | 2008-09-17 (**−24%**) | 2007-10-22 (**−4%**) | OVERLAY early; HMM late confirmer |
| COVID 2020 | fast vol | 2020-03-09 (**−19%**) | 2020-02-26 (**−8%**) | OVERLAY early; HMM late confirmer |
| 2022 bear | slow valuation | 2022-06-14 (**−22%**) | 2022-01-20 (**−6%**) | OVERLAY (HMM blind to the grind) |

**The load-bearing fact (stronger than the fast/slow dichotomy):** the HMM
fires LATE for tail-AVOIDANCE in **every** crisis — its first sustained
`p_crisis ≥ 0.50` only after SPY has already fallen **−19% to −24%** from the
peak. It is a regime *confirmer*, not an early de-gross trigger. The always-on
overlay de-grosses **early in every crisis** (first flat at SPY **+4% to
−8%**), i.e. it is the front line of tail protection across the board.

**The T-172 fast/slow nuance (preserved):** the HMM stays `calm` during the
SLOW-grind phases (dotcom 2000-2001, 2022 H1) and only fires on the eventual
vol legs (9/11; mid-2022). For the FAST crises (GFC late-2008, COVID) it fires
nearer the decline and still has lead to the *trough*. Either way, for
**avoiding** drawdown the overlay leads everywhere; the HMM is regime-grade,
not timing-grade ([[T-172]]/[[T-220]]).

## 2. Expected-defensive-behavior PRE-SPEC (the cloud cells must reproduce this)
The always-on overlay (long/flat 5-month absolute momentum) SHOULD be FLAT
(de-grossed) for the bulk of each crisis. Expected de-gross windows + share of
the crisis spent flat (from the causal overlay signal on SPY):

| crisis | expected de-gross window | ≈ % of crisis flat |
|---|---|---|
| dotcom 2000 | 2000-07-31 → 2002-10-09 | ~73% |
| GFC 2008 | 2007-10-22 → 2009-03-09 | ~82% |
| COVID 2020 | 2020-02-26 → 2020-03-23 | ~79% |
| 2022 bear | 2022-01-20 → 2022-10-12 | ~79% |

A deep-window cell whose defensive structure does NOT show the overlay flat
across ~75-80% of each crisis window (starting EARLY — within a few % of the
peak) is NOT exercising the tail protection and its crisis-drawdown number
should be distrusted.

## 3. Regime-sanity checklist for the deep-window cells (A/T-216, C/T-211)
Run alongside the existing census; FAIL the cell (`[NN-FAIL-CLOSED]`) on any:

- [ ] **(label present)** regime is NOT 100% `unknown` and NOT degenerate
  (≥2 regimes; no single regime ≥99% of bars) — `[NN-CENSUS]`.
- [ ] **(crisis-grade)** mean `p_crisis` is higher inside the known crisis
  windows than in calm (else the label is blind/inverted — HALT).
- [ ] **(overlay de-grossed)** the always-on overlay is FLAT across ~75-80% of
  EACH crisis window (table §2), with the first de-gross EARLY (SPY within a
  few % of the peak), NOT only after −20%.
- [ ] **(slow bears carried by the overlay)** for dotcom + 2022 specifically,
  the overlay de-grosses in H1 of the decline even though the HMM regime label
  stays `calm` there — do NOT expect the regime label to read `crisis` early
  in a slow bear; expect the OVERLAY to carry it.
- [ ] **(crisis DD actually cut)** the defensive arm's per-crisis drawdown is
  materially smaller than the no-overlay arm's (the protection fired), and the
  cut concentrates in the crisis windows above.
- [ ] **(no HMM-gating regression)** the composition uses the overlay
  ALWAYS-ON, not regime-gated — regime-gating the overlay HURTS (T-220:
  gated −17.7% MDD vs always-on −10.6%; it drops protection in the slow 2022
  bear the HMM labels calm).

## 4. Interpretation for the two H0/H1 re-opens
- **A/T-216 (conjunctive selector) was H0 on bull-heavy 2018-2025.** The deep
  window adds the crises above. But note: the selector gates per-edge
  SELECTION via `g_regime` (T-217) — and the HMM regime label is LATE/blind
  exactly where the slow bears bite. So a deep-window H0 for the *regime-gated
  selector* is the expected outcome; the crisis VALUE in the deep window comes
  from the always-on overlay + the bought-MF floor, not from the regime gate.
- **C/T-211 (composition) halved the GFC drawdown first-cut.** Expect the
  always-on overlay to be the source of that on the full cycle; verify it
  de-grossed per §2/§3. The honest H1 bar is whether the bull-chop cost
  (the overlay gives up CAGR in calm — T-204) is repaid by the crisis
  protection over 2000-2025, after-tax, vs the robo (C's measurement).

## Scope / constraints
- E lane (regime INTERPRETATION). The cells are run by A/D; this is the
  ground-truth + sanity layer they consume. 0 N_trials; causal labels only;
  forked nothing; canon untouched (new measurement script).
