---
name: t103-crisis-hmm-repoint-review-2026-06-05
description: Adversarial review of the T-103 repoint proposal (live crisis de-gross to crisis-trained HMM via 1-p_benign). Records the signal verdict, the validation-vs-live window-mismatch class of bug, and the persistence gap that AUC cannot answer.
metadata:
  type: project
---
Reviewed T-103-repoint proposal (repoint live crisis de-gross from 5-axis to crisis-trained HMM `hmm_3state_crisis_v1.pkl`). Verdict NEEDS_FIX, high confidence.

**Why:** The signal-choice is empirically airtight but the proposal carried an offline CI onto a production path that uses a different inference window, and left the persistence axis unmeasured.

**How to apply (load-bearing for any future Engine E -> Engine B repoint):**

1. **`1 - p_benign` (= p_crisis + p_stressed) is the correct crisis signal on the crisis-trained HMM, NOT `p_crisis`.** Confirmed in `docs/Audit/hmm_crisis_retrain_t103_2026_06_04.md`: p_crisis alone is OOS coin-flip (AUC 0.497); 1-p_benign is OOS AUC 0.914 ci_low 0.880, fires 3/3 held-out crises (COVID 28d / 2022 58d / 2025 43d lead). Reason: the crisis-trained model concentrates the literal `crisis` label into the 2008-magnitude tail only (210/3459 = 6.1% of train bars); everything else incl. all of COVID lands in `stressed` (37.8%). On held-out COVID, p_crisis=0.000 throughout while p_stressed pins at 1.000 from 2020-03-02. State labels are training-distribution-dependent; the INVARIANT signal is `1 - p_benign`. This vindicates and upgrades [[project_macro_signal_lead_coincident_classification_2026_05_06]]: yield_curve_spread + credit_spread (my "candidate-leading via interaction, 1 OOS event") are now validated on 3 independent OOS drawdowns -> promote to LEADING.

2. **VALIDATION-VS-LIVE WINDOW MISMATCH is a recurring bug class — always check it on any HMM repoint.** T-103's 0.914 AUC was measured at `window=252` (scripts/validate_hmm_crisis_t103.py:50,62,194). The LIVE engine infers at `history_window=60` (hmm_classifier.py:252 default; regime_detector.py:429-431 calls predict_proba_at with no override). A 60-bar filtered posterior is a different random variable from a 252-bar posterior on the same Gaussian HMM. The headline number does NOT describe the production signal until reconciled. Sibling of CLAUDE.md #9 at the inference-config level. Before trusting ANY offline regime-detector CI in a live gate: confirm validation inference window == live inference window, or re-measure at the live window.

3. **PERSISTENCE / RUN-LENGTH is the axis AUC cannot answer — it was missing from both the audit and the proposal.** Hard project rule (from [[feedback_hmm_lag_characteristics_2026_05_06]]): a de-gross signal needs median run-length <= 20 trading days OR must be a transition trigger, not a state-label level. The slice-1 stress-or-crisis state was ON 67% of days, median run-length >100 bars -> "operationally useless for de-grossing even when AUC is OK." The T-103 graduated map feeds the posterior as a LEVEL = exactly that disqualified form. The crisis-trained model's 1-p_benign mass is ~44% of train days (6.1% + 37.8%, NOT the 38% the proposal repeatedly stated). Graduated-tighten-only-regime-conditional is genuinely different from the failed unconditional vol-target, but shares the SAME persistence failure mode unless run-length is measured short.

4. **Horizon decay of the crisis AUC matters for the MaxDD KPI.** 0.914 @5d -> 0.864 @10d -> 0.661 (ci_low 0.589) @20d. De-gross acts over days-to-weeks, so the operative horizon is ~10-20d where the edge is much weaker. Pre-register the MaxDD-reduction claim at the operative horizon, not the strongest 5d cell.

5. **Current 5-axis crisis de-gross is near-inert, so the REPLACE-not-STACK double-count guard protects against a smaller live risk than the proposal claims.** T-100 (`docs/Audit/crisis_path_diagnostic_t100_2026_06_04.json`): delta_gross_crisis_vs_benign = -0.012, mean_gross_crisis = 0.438, and 2020 had n_live_crisis=0 (5-axis flagged ZERO crisis bars in COVID year). The repoint is well-motivated; the guard's REPLACE/min()-not-product design is sound; but "single most dangerous failure mode" is miscalibrated — window-mismatch and persistence-unknown are the dangerous ones.

The A/B plan itself is structurally excellent (default-OFF, canon-md5-OFF==main, 16+26yr MBL windows, MaxDD-primary + Sharpe-ci_low-not-down secondary, calibrate-16/verify-OOS-26 per CLAUDE.md #9, T-099 + cloud-OFF determinism gate, pre-registration). The fixes are about measuring the live signal, not about the experiment design.
