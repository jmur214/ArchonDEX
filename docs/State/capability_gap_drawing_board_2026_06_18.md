# ArchonDEX — Drawing-Board Capability & Blind-Spot Map (2026-06-18)

Commissioned by the user after the T-196 H0 verdict ("go back to the drawing board, be
honest about what our machine lacks, research the blind spots"). Built by a 6-lens
read-only research pass over the actual code/data/ledger (`wf_e2ec7cf8`). This is the
honest assessment, not a pep talk.

## The brutal honest state

**The system cannot currently "perform like a quant desk" or "significantly outperform
the market." It is far from both.** Worse than "no validated edge":

- **The measured 0.751 Sharpe is probably NOT edge-alpha.** All 13 dense edges are
  closet-beta (negative factor-α, T-117). The 3 "active" behavioral-flow edges that carry
  **~94% of PnL** (volume_anomaly, gap_fill, herding) are uniformly factor-negative — their
  dollars are Mkt+Mom **beta**, not alpha. So the base Sharpe is **risk-management +
  survivorship + beta**, not stacked edge alpha. We have never proven otherwise.
- **8+ edges explicitly REFUTED** with strong methods: VRP (T-174), BAB (T-123/129),
  overnight-intraday (T-135, priced out 4-5×), Form-4 insider clustering (T-144, StepM zero
  survivors), 8-K reactions (T-137), HMM de-gross overlay (T-118r), metalearner (T-149),
  and the 35-cell single-gene Foundry sweep (T-196 H0).
- **The risk model is a stub.** `factor_analysis.py` (beta/momentum/size) is never called by
  `risk_engine.py` — no factor-neutrality, no VaR/ES, no correlation-break detection. A quant
  desk constrains factor exposures; we only cap gross/sector notional. `low_vol_factor` sits
  at weight 0.0.
- **Execution flatters the tail.** Backtest assumes 0bps slippage + t+1 Open fills — fine for
  mega-caps, optimistic for the book's 50-100 small names. Any borderline Sharpe is partly a
  cost-modeling artifact.

**What IS genuinely quant-desk-grade: the measurement apparatus.** Bootstrap CI, the
execution census, cov-pin determinism, the fail-closed non-negotiables, loader-HALT. That
discipline — the ability to say "there's no edge here" without fooling ourselves — is the
real deliverable of the last arc, and it's rare. It's why we can now do the honest thing.

## What's DEAD — stop scoping these (the kill list)

- **Dealer gamma, options flow, prime-broker positioning, alt-data (satellite/credit-card):**
  INSTITUTIONAL-ONLY data (paid Cboe/Bloomberg feeds, prime-broker $50M-AUM minimums).
  **Not retail-accessible. Stop scoping them** — repeatedly desired, structurally unavailable.
- **Cross-asset tradeable sleeves** (rate steepeners, commodity/FX carry, bond sleeves):
  broker-infra-blocked — the Alpaca paper account is equity-only. Macro data is fine as a
  regime *input* (already used); it just can't be *traded* until the broker changes.
- **Refuted edges:** VRP, BAB, 8-K, insider-cluster *directional*, metalearner — closed with
  bulletproof methods. Do not retest in equity space.
- **Single-gene UNIVERSAL Foundry discovery** — exhausted (T-196). Only regime-stratified /
  multi-gene composites remain untested.
- **Uniform vol-target / confidence-gate / in-house crisis-timing** — refuted; always-on 20%
  bought-MF is the proven crisis ceiling (T-178).

## What's genuinely OPEN — untested, NOT refuted (the doors)

**Every closure verdict above is on UNIVERSAL, single-gene, equity-cross-sectional forms.**
The conditional / multi-gene / positioning forms were never run. The user's "we've been too
narrow" is correct here:

1. **REGIME-CONDITIONAL edge book — the single biggest open door.** The base is provably
   bull-conditional (16yr 1.105 ≫ 26yr 0.751), the HMM crisis posterior is validated (AUC
   0.887 causal, T-089), and `signal_processor.py` (585-596) **already has regime_gate
   plumbing — but it's fed empty dicts**; every edge has `regime_gate=None`;
   `regime_conditional_enabled=false` since Apr 2026; Discovery has zero regime-stratification.
   The system has **never forked the book by regime.** This is the user's own "decompose,
   don't require all-weather" directive, never actually executed. **Critical nuance:** it WAS
   tried net-negative in Apr 2026 — but with the COARSE 5-axis advisory regime, NOT the
   validated HMM p_crisis. The diagnosis was input-quality, not mechanism. Re-run with the HMM.
2. **Positioning/flow data — cached, ZERO code consumers.** 5 parquets (FINRA short-interest,
   margin-debt, RegSHO short-volume, NAAIM exposure, SEC FTD) + 641 insider files on disk,
   wired to nothing. User explicitly requested this. Orthogonal to price/macro. **Honest prior:
   modest** (insider clustering already refuted; short-interest is biweekly/stale) → realistic
   lift 0.05-0.15 Sharpe IF anything. But a clean falsification is cheap and closes the branch.
3. **Multi-gene / regime-stratified Discovery** — T-196 closed single-gene universal; composites
   (macro+price, positioning+momentum, regime-gated genes) with state-specific DSR thresholds
   were never reached. LOW prior, but a literal untested branch.

## The honest first move (cheap truth before any spend)

**Edge-by-edge alpha attribution on the canonical 26yr cell** (leave-one-out / each-edge-zeroed
ΔSharpe). ~$20, low effort. It tells us whether 0.751 is alpha, beta, or risk-management
*before* we spend a dollar on any other lever. T-117/T-036 strongly imply "mostly beta" —
confirming that reframes the whole goal honestly and informs every downstream decision.

## Prioritized plan (repoint-first)

| # | Lever | Kind | Leverage / Effort | Note |
|---|---|---|---|---|
| 1 | Edge alpha attribution (26yr leave-one-out) | activate-untested | high / low | Cheap truth first — is 0.751 alpha or beta? |
| 2 | Paper machine + base-vs-robo scorecard | the deploy GATE | high / med | The spine; "beat the robo net-of-cost" is the real bar |
| 3 | **Regime-conditional book reconstruction (HMM)** | repoint-dormant | high / med | The one genuine high-leverage research push; plumbing exists |
| 4 | Positioning-data falsification (short-interest micro-edge) | repoint-dormant | med / med | User-requested; cheap; modest prior; closes the branch honestly |
| 5 | Multi-gene / regime-stratified Discovery | activate-untested | low / high | Completes the alpha hunt before declaring closed |
| 6 | LLM-analyst narrative checkpoint (T-190) | build-new | high / high | Last; forward-only validation (6-12mo); only truly-different modality |

**The single hard gate for ALL of it:** beat the Schwab robo net-of-cost/after-tax,
paper-confirmed. Any lever whose best-case modeled lift still leaves the base under the robo
gets killed. "Money stays in the robo" remains an acceptable honest outcome — but the doors
above (esp. #1, #3) are real and unopened, so we are NOT yet at "concede."
