---
name: engine-e-buried-defensive-capabilities
description: Engine E (Regime) ships a large crisis/de-gross/tail-warning surface that the living docs (CURRENT_STATE.md, MEMORY index) almost entirely omit — relevant to T-092 Path B
metadata:
  type: project
---

Engine E carries far more shipped defensive capability than the living docs surface. Audited 2026-06-04 for T-092 Path B (crisis-regime robustness pivot).

**Fact:** CURRENT_STATE.md mentions only the *validated verdict* `hmm_p_crisis AUC 0.887` (T-087). It surfaces ZERO of the actual code-level defensive knobs. The MEMORY index records only negative VERDICTS (T-055 refuted, HMM-5yr refuted) — never the shipped CAPABILITY.

**Why:** Capabilities get buried when the experiment that touched them is REFUTED. The doc records the negative measurement and drops the mechanism. This is the same burial mode that hid the Engine B `crisis_target_multiplier=0.40` de-gross path.

**How to apply (Path B inventory — the forgotten defensive surface in Engine E):**
- `advisory.py` ships a full crisis de-gross chain that IS LIVE in prod (risk_advisory_enabled=true): regime_summary=='crisis' floors suggested_max_positions to crisis_max_positions=5 (advisory.py:228), exposure cap tightens to 0.3 (advisory.py:179-186), risk_scalar floors to 0.3 (advisory.py:195). Consumed by Engine B risk_engine.py:727-748, Engine C policy.py:380, Engine A signal_processor.py:546.
- `AXIS_RISK` + `STRESS_WEIGHTS` (advisory.py:70-86): when vol is high/shock the risk-score reweights toward forward_stress+vol+correlation — an automatic regime-stress amplifier. Active, undocumented.
- `UNSTABLE_COMBOS` (advisory.py:92-119): "Walking on Ice" pre-crisis fragility detector forces exposure_cap_max=0.65 + momentum 0.5. ACTIVE coherence override. The single most Path-B-relevant forgotten tool — a *pre*-crisis (not coincident) tightener. Totally undocumented.
- HMM crisis posterior (hmm_classifier.py): the validated AUC-0.887 signal. SHIPPED but GATED OFF — hmm_enabled=false in config/regime_settings.json. Models on disk: hmm_minimal_C_v1.pkl is the RECOMMENDED 7-feature artifact (feature_set="minimal_c", AUC 0.594/0.636 20d/60d, benign-state forward-DD -2.4% vs -7.4% unconditional) but config still points at legacy 4-feature hmm_3state_v1.pkl. THIS IS THE PATH-B KILL-SWITCH SIGNAL and it is one flag flip + one feature_set change away.
- ForwardStressDetector (forward_stress_detector.py): VIX-term-structure 3-tier panic/stressed detector. ACTIVE (5th axis), Lai-2022 forward-looking. Tier3 synthetic fallback works offline. Undocumented in CURRENT_STATE.
- TransitionWarningDetector (transition_warning.py): fires ≥48hr ahead of regime flips via HMM entropy+KL. SHIPPED, GATED OFF (transition_warning_enabled=false), observability-only (no Engine B consumer wired). Pure Path-B early-warning tool.
- MultiResolutionHMM (multires_hmm.py): daily/weekly/monthly crisis classifiers. SHIPPED, GATED OFF (multires_enabled=false). monthly cadence designed for slow de-gross.
- Leading-indicator features (macro_features.py): hyg_ig_oas (credit), copper_gold_ratio, xlp_xly_ratio (defensive rotation). Built but only wired when feature_set in minimal_b/minimal_c.

**Dead consumer found:** Engine B risk_engine.py:744 reads `advisory.get("correlation_regime")` for dynamic sector caps, but Engine E puts `correlation_regime` at the TOP LEVEL of output, NOT inside `advisory`. So B's dispersed/elevated sector-cap branch never fires. Sibling of the silent-mismatch bug family.

See also [[engine_d_drift_patterns]] (bare-except silent-default is endemic; same pattern fills Engine E's HMM/multires/transition init with try/except → silent None).
