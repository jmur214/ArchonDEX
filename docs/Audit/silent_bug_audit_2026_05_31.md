---
title: Silent-bug audit — systematic hunt for the mismatch/lookahead/wiring bug family
date: 2026-05-31
author: director (multi-agent workflow: 6 hunters + per-finding adversarial verify + synth)
method: 21 agents, 14 candidates, 9 confirmed (5 refuted by adversarial pass)
---

# Silent-bug audit — 9 confirmed defects

Motivated by the recurring silent-mismatch bug family (cockpit peak_equity
slot, hunt() ticker=, env-suffixed config, T-055g v1 patch keys, director
'Sharpe' vs 'Sharpe Ratio', predict_proba_sequence lookahead). One hunter
per bug-class; every candidate adversarially verified (refute-by-default)
before confirmation. 5 of 14 candidates were refuted as benign — so the
list below survived active refutation.

## Ranked punch list

### HIGH — lookahead (could contaminate any regime-conditional backtest)

**H1. `engines/engine_e_regime/hmm_classifier.py::predict_proba_sequence`
— non-causal smoothing.** Uses Baum-Welch forward-backward; posterior at
bar t depends on bars t+1..T. Any backtest/live decision path consuming
it sees the future. A flagged this in T-087 (where the diagnosis correctly
used the causal filter). **Fix:** add `predict_proba_filtered` (forward-only),
route all decision-path callers to it; keep smoothed for offline labeling only.
**Blast radius:** any backtest that reads regime probabilities for sizing/gating.
Note: T-055e/g/h still FAILED, so lookahead there (if present) wasn't enough
to manufacture a passing lift — but it could have understated OFF-baseline
or distorted per-year attribution.

**H2. `engines/engine_e_regime/regime_detector.py` — full-series
normalization.** The feature panel feeding the HMM is normalized with
mean/std/quantile over the ENTIRE window, so early-window regime calls use
end-of-window statistics. **Fix:** expanding/rolling causal normalization
(data ≤ t only) in backtest. **Blast radius:** same as H1 — regime calls
are contaminated independent of the smoothing issue. These two are likely
the reason the 2026-05-06 5-yr AUC was 0.49 while the T-087 causal-path
12-yr AUC was 0.887: production may have been running the leaky path.

### MEDIUM

**M1. `core/observability/run_registry.py:118` — Sortino key mismatch.**
Reads `'Sortino Ratio'`; producers write `'Sortino'`. Registry sortino
column is NULL for every run. **Fix:** one-char-class change to `"Sortino"`.
Blast: forensic queries that sort/filter on sortino silently see all-NULL.

**M2. `orchestration/mode_controller.py` — env-suffixed config (recurrence).**
Loader prefers `risk_settings.{env}.json` but some scripts patch the plain
`risk_settings.json`; with env set, the patch is silently ignored. Same
family as T-055c + T-055g v1. **Fix:** patch helper resolves the same
env-suffixed path the loader uses; warn if both exist + diverge.

**M3. `engines/engine_a_alpha/alpha_engine.py` — cross_asset_confirm
dead-letter.** Computed + threaded in the advisory dict but never gates a
trade (matches the WS-C observability-only memo). **Fix:** either wire it
into its intended gate or annotate it observability-only to stop
re-discovery. (Likely intended-dormant; confirm.)

**M4. `engines/engine_b_risk/risk_engine.py` — slippage_bps double-scale.**
[PROPOSE-FIRST — Engine B, flagged not edited.] Primary fill path correct;
a SECONDARY cost-estimate path applies bps without /10000. **Fix:** /10000
in the secondary path + unit test (5bps→0.0005). Needs user approval.

**M5. `engines/engine_b_risk/risk_engine.py` — regime_meta.advisory contract.**
[PROPOSE-FIRST — Engine B.] Reads `regime_meta.get('advisory')`; some
callers pass advisory flattened at top level → advisory-driven sizing
silently no-ops. **Fix:** accept both shapes or assert; test. Needs approval.

**M6. `engines/engine_d_discovery/discovery.py` — stale gate-result key.**
A gauntlet gate reads a candidate-result key a refactor renamed; stale read
falls back to pass-through default → that gate silently weakened. **Fix:**
align reader key to current producer; regression test asserting the gate
fires on a known-fail candidate. Blast: Discovery may be passing candidates
a gate should kill.

### LOW

**L1. 13 harnesses — `summary.get('Total Trades')` always None.**
`ModeController.run_backtest` returns `summary()` whose keys have no trade
count; the count lives under `'Trades'` in the unused `summary_metrics()`.
13 measurement/A-B scripts record `total_trades: null`. **Fix:** readers →
`summary.get("Trades")` + wire `summary_metrics()`, or add `"Total Trades"`
to `_compute_summary()`. Not a gate input — purely a nulled diagnostic.

## Did any of these contaminate the T-053b/T-055h/T-057b cycle?

- **H1/H2 (regime lookahead):** Potentially yes for the regime-conditional
  arms (T-055e/g/h read the advisory). But those arms FAILED — lookahead
  can't have manufactured a passing result. Worst case it distorted per-year
  attribution. The T-057 confidence-gate arms don't read regime, so T-057b/
  T-053b verdicts are clean.
- **L1 (total_trades null):** The turnover/trade-count columns in those
  audits were null — any "turnover reduced X%" claim sourced from these
  JSONs is unsupported. Sharpe/CAGR/MDD/ci_low verdicts are unaffected
  (those keys match).
- **M1 (sortino null):** registry sortino was unusable; no verdict keyed
  on it.
- Everything else: no impact on the cycle's headline verdicts.

**Bottom line:** the cycle's Sharpe-based verdicts (T-057 refuted, T-055
closed, baseline borderline) stand. The lookahead pair (H1/H2) is the real
prize — it must be fixed before ANY new regime-conditional work, and it
explains the 2026-05-06-vs-T-087 AUC swing.

## Coverage (refuted/benign candidates prove the search was real)
5 candidates refuted across key-field-mismatch, unit-scale, and
wiring-deadletter classes (false alarms the adversarial pass caught —
e.g. EDGE_CATEGORY_MAP benign by Python source-order guarantee).
