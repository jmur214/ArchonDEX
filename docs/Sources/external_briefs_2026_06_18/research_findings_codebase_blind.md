# Codebase-Blind Domain Research — Findings (2026-06-18)

**Provenance:** external research agent, NO codebase access, evidence-grounded (academic +
practitioner, cross-checked, replication-weighted). Commissioned via `research_brief_codebase_blind.md`.
The complement to the fresh-eyes code audit (`docs/Audit/external_fresh_eyes_assessment_2026_06_18.md`):
the audit assessed OUR system; this assesses the OUTSIDE world (is there retail-reachable alpha,
and where).

## TL;DR
- **The honest ceiling is risk-managed beta with a modest defensive/structural tilt — not
  "quant-desk" alpha.** The replication literature is brutal: Hou-Xue-Zhang (2020) — 65% of 452
  anomalies fail t≥1.96 (82% at t≥2.78); McLean-Pontiff (2016) — survivors −26% OOS, −58%
  post-publication; Harvey-Liu-Zhu (2016) — need t>3.0. **Our empty GA search + null edge book are
  consistent with the evidence, not a personal failure.**
- **Our unused positioning/macro data is mostly stale, aggregate, non-orthogonal, or untradeable on
  daily bars.** The genuinely price-LEADING positioning data (dealer gamma, prime-broker) is
  institutional/options-only. Aggregate short interest is the one strongly-documented predictor —
  but for INDEX-level market timing, not stock selection.
- **The biggest wins are NOT alpha — they're capability builds that add value OVER the robo:**
  systematic trend-following / managed-futures-style crisis-alpha on liquid equity ETFs (POSITIVE
  SKEW — our stated preference), volatility targeting, defensive factor tilts (profitability/quality,
  low-beta), and disciplined portfolio construction.

## The single most important reframe (Q7)
> **We've been hunting cross-sectional stock-selection signals (where retail evidence is bleakest)
> while under-weighting time-series risk management + positive-skew construction (where the evidence
> is strongest AND our skew preference is satisfied). Pivot from "what stock to buy" to "how to size
> and de-risk a beta portfolio with a convex overlay."**

## Ranked directions (filtered to retail-N / cost / daily-bar / Alpaca-equity-only)

**Tier 1 — robust, tradeable, match constraints + skew preference:**
1. **Systematic trend / absolute-momentum overlay on liquid equity ETFs (long/flat).** Positive
   skew, crisis-alpha, daily-bar, equity-only — the single best fit for our constraints + skew
   preference (AQR "A Century of Evidence on Trend-Following": positively skewed, crisis alpha;
   skew grows over horizon). Implement as long/flat on SPY vs its 200-day/10-month trend. Near-term,
   low-moderate effort. *Caveats:* equity-only trend lacks the cross-asset diversification of true
   managed futures; whipsaws are the cost of convexity; protects best in the slow grind, not the
   first sharp drop.
2. **Volatility targeting of overall equity exposure.** Robust Sharpe + tail improvement for risk
   assets (Harvey et al. 2018: US-equity Sharpe ~0.40→0.48-0.51, left-tail less severe). 6-12mo.
3. **Defensive tilt: profitability/quality (Novy-Marx) + high-IVOL/lottery exclusion screen.**
   Robust, low-turnover. Near-term, low effort.
4. **Homegrown Barra-lite multi-factor risk model** (mkt/size/value/mom/quality/low-vol betas) — to
   CONTROL exposures and confirm what's beta vs edge before risking capital. 6-12mo.

**Tier 2 — worth testing with strict deflated-Sharpe / walk-forward discipline:**
5. **Industry momentum on sector ETFs, sector-neutral** (Moskowitz-Grinblatt 1999 — robust,
   internationally replicated). Watch multiple-testing across sectors. Near-term.
6. **Aggregate short-interest as a market-timing overlay** (Rapach-Ringgenberg-Zhou 2016: OOS R²
   ~13%, ~300bps/yr utility gain). Index-level only, monthly cadence.

**Tier 3 — do NOT pursue as alpha (folklore / overfit / untradeable at our scale):**
PEAD + short-term reversal (BOTH cost-killed at retail — drift is near-zero in liquid stocks, 70-100%
cost-consumed in illiquid; STR is a liquidity-provision strategy); COT / NAAIM / margin debt / RegSHO
/ FTDs as stock-selection signals; dealer gamma/GEX + 13F cloning (institutional / options / stale);
**3-state HMM for SIGNAL selection** (overfit trap) + free-form sector-conditional search;
incremental tax harvesting vs the robo (the robo already does TLH).

## Key nuances that refine OUR plan
- **Regime (Q2):** HMM to PICK signals = overfit trap (a cited study: OOS Sharpe −1.65 frozen-params).
  Volatility STATE to SIZE risk = worth pursuing — **BUT a continuous vol-target likely DOMINATES the
  3-state HMM on a degrees-of-freedom-adjusted basis** (Nystrup: gradual prob-weighted ≈ discrete
  switching). → The "wire the HMM as risk-control" idea should probably be a continuous vol-target,
  not the 3-state HMM.
- **"Quant desk" at retail (Q6) = portfolio-construction + risk discipline, NOT proprietary alpha.**
  Realistic target: match the equity risk premium with materially better risk-adjusted + after-tax +
  tail outcomes (cut MDD via vol-target + trend overlay; Sharpe ~0.40→0.50; defensive tilt).
- **The deploy bar is correctly set and HARD.** Most directions struggle to clear "beat the robo
  net-of-cost AND after-tax" on RAW return; the realistic path clears it on RISK-ADJUSTED + TAIL
  terms (trend + vol-target + defensive tilt), even if raw return merely matches. **If after honest
  paper trading none of Tier 1 beats the robo after-tax/after-drawdown, leaving the money in the robo
  is a valid, evidence-based outcome — not a failure.**
- At $5K-$50K, most cross-sectional strategies are **un-validatable at our own sample size** (the
  deflated-Sharpe minimum-track-record problem) — itself the strongest argument for low-turnover beta
  engineering over signal trading.
