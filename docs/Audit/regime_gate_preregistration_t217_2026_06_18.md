# `g_regime` Gate — PRE-REGISTRATION (T-217, 2026-06-18)

**Written BEFORE measurement** (CLAUDE.md #7). Builds the regime half of the
conjunctive selector (`conjunctive_score = s_tech × g_fund × g_regime`,
T-208/A-T-216). Engine E. **Repoints existing plumbing** (the `regime_gate`
multiplicative hook + the validated HMM + `regime_tracker`); no new engine,
no boundary cross. Default-OFF, canon-safe.

## The thing being fixed
RANK 2 (`DESIGN_FIDELITY.md`): the per-edge `regime_gate` dicts
(`signal_processor.py` L585-593, `w *= gate.get(current_regime, 1.0)`) are
fed EMPTY `{}` → silent no-op. They were disabled after a walk-forward
falsification (net-negative 2/3 splits) — but on the **5-axis advisory
regime** (`advisory["regime_summary"]`), which is the regime label that
FAILED. RANK 3: the validated `hmm_p_crisis` (AUC 0.887, T-087/089) is
consumed by NOTHING live. This task re-measures the gate on the **HMM** label
the prior attempt never used.

## The regime label (HMM, causal — NOT the advisory)
- Source: `regime_meta["hmm_regime"]["probabilities"]["crisis"]` — the
  causal forward-filter posterior (`predict_proba_at` with a trailing
  history window; T-089's lookahead-clean path, NOT
  `predict_proba_sequence`). Already produced per-bar during a backtest.
- **3-state label from p_crisis (pre-registered thresholds, no sweep):**
  - `calm` : p_crisis < 0.30
  - `cautious` : 0.30 ≤ p_crisis < 0.60
  - `crisis` : p_crisis ≥ 0.60
  Chosen a-priori (T-172 found the HMM is regime-grade, generalizing to
  fast/credit crises ~p>0.5). NOT the 5-axis `regime_summary`.
- Off-cloud / HMM-absent fallback: label = `calm` (a missing regime never
  suppresses an edge — fail-safe to no-op).

## The gate mapping (per-edge-per-regime → multiplier ∈ [0,1])
`g_regime[edge][regime]` derived from MEASURED per-edge-per-regime
performance (not theory-picked), reusing `regime_tracker`'s Sharpe→weight
shape:
```
if trade_count < MIN_TRADES (=20):  gate = 1.0   # insufficient data → no gate (default)
elif sharpe <= DISABLE_SR (=-0.25): gate = 0.0   # kill the edge in this regime
else: gate = clip(FLOOR + (CEIL-FLOOR)*clip(sharpe,0,1), FLOOR, CEIL)
       FLOOR=0.25, CEIL=1.0
```
A missing `edge` or `regime` key → 1.0 (unconditional pass-through). All
constants pre-registered here; **no sweep** (sweeping them is the overfit).

## Measurement (does HMM-regime-conditioning clear where the advisory failed?)
1. Compute the **causal HMM regime series** over the canonical substrate
   (the same HMM/feature path the backtest uses; lookahead-clean).
2. Re-derive **per-(edge, HMM-regime) performance** — re-label each edge's
   contribution by the HMM regime at the bar, accumulate Welford
   Sharpe/mean/count per (edge, regime).
3. Build the gates from (2) via the mapping above.
4. **Honest read (the deliverable, NOT a deploy decision):** is the
   per-edge-per-HMM-regime structure (a) DIFFERENTIATED (edges genuinely
   perform differently across calm/cautious/crisis — non-trivial gates), and
   (b) STABLE across a time split (the IS-derived per-regime ranking holds on
   a held-out span — the property the advisory LACKED, which is why it
   net-negatived OOS)? If not stable, the gate **stays correctly OFF** and
   that is the reported result.

## What's IN scope vs deferred
- **IN (this task):** the composable `g_regime` gate (HMM-labelled, gates
  populated from measured data), pre-registration, unit tests, canon-safety
  (OFF → bitwise-unchanged prod), and the honest IS + split-stability read.
- **DEFERRED to the director's COMPOSITION step** (per the task): the full
  portfolio walk-forward OOS measurement of the COMPOSED selector
  (`s_tech × g_fund × g_regime`) vs the robo scorecard, after-tax. The gate
  is a default-OFF INPUT; A's selector + C's robo gate measure it. I do NOT
  wire it into live sizing standalone.

## N_trials + discipline
- ONE pre-registered structure (HMM 3-state + the fixed Sharpe-map). The
  gates are DERIVED from measured data, not searched → **N_trials += 1** (the
  structure). No threshold/label sweep.
- A clean null ("the HMM gate is not differentiated/stable → stays OFF") is
  an explicitly valid, pre-registered outcome.

## Contract for A's T-216 selector (proposed — no on-disk contract existed)
```python
# Engine E delivers (default-OFF):
from engines.engine_e_regime.regime_gate import RegimeGate, hmm_regime_label
rg = RegimeGate.from_file(path) | RegimeGate(gates={})   # {} == OFF == all 1.0
# A's selector, per (edge, bar):
g = rg.gate(edge_name, regime_meta)        # float in [0,1]; 1.0 when OFF / missing
conjunctive_score = s_tech * g_fund * g          # A composes; E does not
```
`regime_meta` is the existing per-bar dict (carries `hmm_regime`). The gate
reads the HMM label, NOT `advisory["regime_summary"]`. A consumes; E does not
fork A's selector.
