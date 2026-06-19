# Regime-Conditional Trend Overlay — VERDICT (T-220, 2026-06-19)

Reads against the pre-registration (`regime_conditional_overlay_preregistration_t220`,
locked `86b883a` BEFORE measurement). Branch `feature/regime-conditional-overlay-t220`.
md5-deterministic. Reproduce: `python -m scripts.regime_conditional_overlay_t220`.

## VERDICT (for C/T-211): KEEP THE OVERLAY ALWAYS-ON — do NOT regime-condition it.
The HMM regime gate does not help; it **hurts**. Always-on is the best form
on every shape axis. This is the expected null (the honest prior), and it is
a clean decision input for C: wire the overlay always-on.

## The arms (3-asset EW SPY/AGG/GLD sleeve, 5-month lookback, 2005-2026)
Regime-label census (causal frozen-HMM, train 2000-2012): calm 93.2% /
cautious 0.2% / crisis 6.6%; mean p_crisis 0.237 in known crises vs 0.051
calm (crisis-grade — passes `[NN-CENSUS]`).

| arm | CAGR | Sharpe (ci_low) | MDD | skew_m | GFC / COVID / 2022 DD |
|---|---|---|---|---|---|
| (a) no overlay (buy-hold) | +8.20% | 0.88 (0.47) | −24.3% | −0.43 | −24.3 / −15.1 / −16.0% |
| **(b) always-on** | +5.88% | **0.91 (0.48)** | **−10.6%** | **+0.13** | **−10.6 / −6.6 / −6.8%** |
| (c) regime-gated | +7.08% | 0.87 (0.45) | −17.7% | −0.17 | −12.0 / −10.5 / −17.0% |
| (d) inverse-gated (control) | +7.01% | 0.89 (0.45) | −23.1% | −0.25 | −23.1 / −11.5 / −5.6% |

## Why regime-gating loses (the mechanism — not just the number)
1. **The trend signal self-times better than the HMM gate.** Absolute
   momentum already goes flat when an asset's own trend rolls over — that IS
   a regime response, and it's faster/asset-specific. Always-on (b) beats
   regime-gated (c) on MDD (−10.6% vs −17.7%), skew (+0.13 vs −0.17), and
   every crisis window.
2. **The HMM gate is BLIND to the slow grind (2022).** 2022 was a slow
   valuation bear, not a vol spike, so p_crisis stayed in `calm` most of the
   year (consistent with T-172: the HMM is weak on slow valuation bears). The
   regime-gated arm therefore stayed FULLY INVESTED through 2022 and took
   −17.0% — vs always-on's −6.8%, where the trend signal cut equity as SPY
   rolled below its 5-month average. Gating to "only fire in crisis regimes"
   removes the protection exactly when a slow bear needs it.
3. **The inverse control proves protection lives in the crisis bars.** (d)
   turns the overlay OFF in cautious/crisis (on in calm) → its MDD collapses
   to −23.1% (near buy-hold). So the overlay's value is concentrated in the
   stress bars; the regime gate's job — deciding when stress is here — is done
   better by the price trend itself than by the lagging HMM posterior.

## The decision rule (pre-registered) → result
Regime-gating would "win" only if (c) beat (b) on shape AND the inverse
control (d) were clearly worse than (c) (gate carries information). Result:
(c) is WORSE than (b) on MDD/skew/2022 — the first condition already fails.
**→ KEEP ALWAYS-ON.**

## Scope / integrity
- E-lane standalone sleeve diagnostic; **C wires the portfolio composition**
  (the overlay enters always-on). No beat-the-robo measurement here.
- Reused `core/trend_overlay.py` (T-204) + `regime_gate.py` thresholds
  (T-217) + `regime_oos_loco_t172.py` causal forward-filter (T-089-clean) —
  **forked nothing.** Causal labels only (regime_{t-1}, signal_{t-1}).
- `[NN-SHARPE-CI]` block-bootstrap ci_low; `[NN-CENSUS]` + `[NN-FAIL-CLOSED]`
  guards (HALT on a degenerate/non-crisis-grade label); md5-deterministic.
- **Canon untouched** (a new measurement script + reuse of OFF-default
  modules; no prod path imports any of it). **N_trials += 2** (the two new
  gated structures; (a)/(b) are T-204 re-measurements).

## Note for A/T-216
This confirms the HMM regime label is a *lagging* timer for a *self-timing*
trend signal — a different use than A's conjunctive `g_regime` (T-217), which
gates per-edge SELECTION (where stock-selection edges work by regime), not
the timing of an already-self-timing momentum overlay. T-220 does not bear on
T-217's still-pending composition measurement; it only answers the overlay's
form (always-on). g_regime stands ready for A's selector.
