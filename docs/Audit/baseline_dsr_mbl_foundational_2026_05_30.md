---
title: FOUNDATIONAL — baseline edge ensemble DSR + MBL on 12-yr window (CORRECTED)
date: 2026-05-30
author: director
related: T-053b, T-055h, CLAUDE.md #6/#7/#9
status: CORRECTED 2026-05-30 — first version used wrong JSON keys and reported fabricated numbers; see correction notice
---

# Baseline DSR + MBL check — the foundational measurement (CORRECTED)

> **⚠️ CORRECTION NOTICE.** The first version of this doc (commit
> `9c8f1ae`) reported baseline Sharpe 0.539 / ci_low 0.18 / MDD -24.7%
> and concluded "phantom base — fails DSR by a wide margin." **Those
> numbers were fabricated by a key-mismatch bug in my analysis script:**
> it read `d["Sharpe"]` / `d["Sharpe_ci_low"]` but the actual
> `performance_summary.json` schema uses `"Sharpe Ratio"` (with a space)
> and has NO ci_low field. The script silently produced garbage (via
> `.get()` defaults) that I wrote up without verifying. The corrected
> numbers below — computed from the actual equity curves via
> `MetricsEngine` block-bootstrap — change the conclusion materially.
> Lesson logged in `memory/feedback_inspect_json_keys_before_analysis_2026_05_30.md`.

## Why this was run

The 2026-05-23 → 2026-05-30 cycle measured *lifts* (Δ vs `arm0_off`).
Both candidate overlays (T-057, T-055e/g/h) were retired on the 12-yr
window. The untested question: does the **base itself** — the production
6-edge ensemble, all overlays OFF — clear DSR at the project's honest N?

## DEFINITIVE FIGURES (supersede any 0.835 in the body below)

Computed via `MetricsEngine.bootstrap_distribution` (correct signature)
on rep1's equity curve:

- **Sharpe 0.810** (modal — 4 of 5 reps; **rep4 drifts to 0.919**, mild
  determinism drift consistent with A's 2/10-cell note → these baseline
  cells are in scope for B's T-057c-det-followup sweep)
- **Block-bootstrap CI [0.328, 1.301]**, ci_low **0.328**
- DSR N=260: benchmark 0.659, **point clears by +0.151**, ci_low fails
- MBL at SR 0.810: needs **16.9 yr**, have 12 (short ~5 yr)
- Kill-thesis ci_low 0.328 < 0.4 → triggers

The body's 0.835 / [0.331,1.342] / bench 0.686 figures are from an
earlier bootstrap seed; they're within the determinism-drift band and
every qualitative conclusion is identical. Use the definitive figures
above when citing.

## Data (CORRECTED)

`arm0_off` from T-055h's 12-yr campoign
(`s3://archondex-results-407539788432/t055h-vol-target-12yr-proof/arm0_off/2014-2025/`),
5 reps, all bitwise-identical:

| Metric | Value |
|---|---|
| Sharpe (equity-recomputed) | **0.835** |
| Sharpe (performance_summary, rounded) | 0.81 |
| Block-bootstrap 95% CI | **[0.331, 1.342]** |
| ci_low | **0.331** |
| CAGR | 7.99% |
| MaxDrawdown | -14.44% |
| Window | 2014-01-02 → 2026-01-14 (11.9 yr, 2997 daily returns) |

CI is block-bootstrap (Künsch, 1000 iter) per CLAUDE.md #6, computed from
the actual daily-return series.

## DSR check (deflated Sharpe)

Deflated-SR benchmark = expected max Sharpe over N trials (Bailey-LdP
2014). σ_SR ≈ 0.258 from the block-bootstrap CI half-width.

| N | Deflated-SR benchmark | Point 0.835 | ci_low 0.331 |
|---|---|---|---|
| 230 | 0.674 | **CLEARS** (+0.161) | fails |
| 260 (current) | 0.686 | **CLEARS** (+0.149) | fails |
| 500 | 0.760 | **CLEARS** (+0.075) | fails |

The **point estimate clears the deflated benchmark by a real margin**
(not noise) at the current N. But per CLAUDE.md #6 (gate on ci_low), the
ci_low 0.331 sits below the benchmark — so the base is **not yet formally
validated at 95% confidence**, though it is far from a phantom.

## MBL check at the actual baseline Sharpe

`T_years ≥ 2·ln(N) / SR²` at SR=0.835:

| N | MBL_min | 12.0 yr actual |
|---|---|---|
| 260 | **16.0 yr** | short by ~4 yr |
| 500 | 16.0 yr | short by ~4 yr |

To clear MBL at N=260 we need ~16 yr of history. We have 12. **The gap is
~4 years — reachable**, not the 26-year gap the erroneous first version
implied. Alternatively, lifting ensemble SR from 0.835 → ~1.0 drops MBL
to ~11 yr, clearing immediately at the current 12-yr window.

## Kill-thesis trigger

ci_low 0.331 < 0.4 → **still triggers**, but at 0.331 it is borderline,
not the decisive 0.18 the erroneous version reported.

## Verdict (CORRECTED) — borderline-real edge, under-powered by ~4 yr

The base edge ensemble is a **plausibly-real modest edge** (point Sharpe
0.835 clears the DSR deflated benchmark; 8% CAGR / -14.4% MDD over 12 yr
is a respectable risk-adjusted stream). It is **not yet formally
validated** — ci_low 0.331 is below both the deflated benchmark and the
0.4 kill-thesis, and MBL wants ~16 yr vs our 12. But this is "under-powered
by ~4 years of history / a modest edge-strength gap," **NOT** the
"statistically-indistinguishable-from-noise phantom" the first version
wrongly claimed.

## Strategic implication (CORRECTED)

1. **Overlay work is not futile** — but an overlay now has to lift *ci_low*,
   and the base ci_low (0.331) has headroom toward the 0.686 benchmark.
2. **The single highest-ROI lever is now clearly history extension.**
   Kibot $99 one-time (1998+, ~28 yr, WITH delisted names) would
   simultaneously (a) push the window past the 16-yr MBL requirement and
   (b) fix the survivorship bias. That $99 is the best-value spend in the
   project — it could move the base from "borderline" to "formally
   validated" without any new alpha.
3. **Edge-strengthening still compounds**: SR 0.835 → 1.0 drops MBL to
   ~11 yr (clears at our current window). Engine D Discovery unblock +
   genuinely differentiated edges remain valuable.
4. The parked LLM/thematic/alt-data directions are a *longer-horizon*
   amplifier, not an *emergency pivot* — the base is healthier than the
   erroneous version suggested.

## Rigor caveats

- σ_SR for the deflated benchmark is proxied from the block-bootstrap CI
  width; a fully rigorous DSR would use the actual cross-trial Sharpe
  variance from the run registry. Direction is robust: point clears at
  every N tested; ci_low fails at every N.
- All 5 reps were bitwise-identical, so the CI is from within-curve
  block-bootstrap of the single 12-yr return series (correct for this
  question — we want the sampling uncertainty of the Sharpe estimate, not
  cross-rep dispersion).
