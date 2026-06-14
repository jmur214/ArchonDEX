---
name: engine-e-regime-summary-repoint-blast-radius
description: regime_summary has 6 live/latent consumers beyond the exposure cap; repointing its risk_score input (T-103-repoint) silently changes risk_scalar (Engine A brake magnitude) and the vol_target regime multiplier unless scoped explicitly
metadata:
  type: project
---

T-103-repoint proposes substituting the `risk_score` input that feeds `regime_summary` (advisory.py:176) and `suggested_exposure_cap` (advisory.py:179-186) with a graduated map of HMM `1 − p_benign`. Adversarial blast-radius audit (2026-06-05) found the proposal's consumer inventory is INCOMPLETE and its "REPLACE not STACK" guard has one leak.

**Why:** `regime_summary` and `risk_scalar` are BOTH derived from the same `risk_score` local in `AdvisoryEngine.generate` (advisory.py:161 → 176, 179, 195). The proposal names only 176 + 186 as substitution targets, but:

- **`risk_scalar` (advisory.py:195) is `1.2 − risk_score*0.9`.** The Engine A edge-score brake (signal_processor.py:546-549) GATES on `regime_summary ∈ {stressed,crisis}` but the CUT MAGNITUDE is `advisory["risk_scalar"]`. If the repoint substitutes the input to `regime_summary` but leaves `risk_scalar` on 5-axis, then on an HMM-stressed / 5-axis-benign day the gate OPENS (HMM) while the multiplier stays ~1.0 (5-axis benign) → brake fires with no teeth (incoherent). If instead it substitutes `risk_score` wholesale (the only clean way, since it's one variable), then `risk_scalar` ALSO becomes HMM-driven — which is arguably correct but is NOT what Section 2.3 says it does. The proposal must state explicitly that `risk_scalar` moves too, or the Engine A brake is left half-repointed.

- **Latent stacking consumer the map MISSED at the regime_summary level:** vol_target.py:271-275 `_regime_target_multiplier` selects a per-regime vol multiplier KEYED ON `regime_summary`. OFF on prod (portfolio_vol_target_enabled=false in risk_settings.json:20; regime_aware=False default risk_engine.py:112) — but if both flags ever flip on, this is a SECOND cut driven by the same HMM-flipped `regime_summary`, stacking on the exposure cap. The proposal's double-count guard only reasons about the exposure-cap + max-positions consumers; it does not enumerate this one.

- **`correlation_regime` sector-cap branch (risk_engine.py:744-748) is a PRE-EXISTING DEAD branch, NOT a repoint risk:** Engine E emits `correlation_regime` as a `{"state":...}` DICT at the macro_regime level (regime_detector.py:259), but the Engine B consumer does `advisory.get("correlation_regime","normal")` and string-compares to "dispersed" — wrong level + wrong type → always falls to "normal". Repoint doesn't touch it.

**How to apply:** Any future "repoint regime_summary" proposal in this repo must enumerate ALL `regime_summary` consumers via `grep -rln regime_summary engines/ orchestration/`: signal_processor.py (brake+gate), per_ticker_score_logger.py (diag), risk_engine.py (max_pos+gross), vol_target.py (regime multiplier — latent), policy.py (exposure cap), mode_controller.py (diag). And note that `risk_scalar` shares the `risk_score` source so it cannot be excluded from a "substitute risk_score" repoint without explicit branching. See [[doc_gap_pattern_refuted_verdict_buries_shipped_capability]] for the surface-inert-code method.
