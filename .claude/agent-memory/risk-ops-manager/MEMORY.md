# Risk & Ops Manager — Memory Index

- [Crisis-HMM repoint design map (T-103-repoint)](project_crisis_hmm_repoint_2026_06_05.md) — where 1-p_benign injects to reach live Path-A de-gross; the 60-vs-252 window mismatch near-miss; the double-count guard.
- [Live Path A de-gross depends EXCLUSIVELY on 5-axis regime_summary](project_live_path_a_degross_map_2026_06_05.md) — exact file:lines of every regime_summary consumer; HMM currently dead-ends at risk_scalar sizing (Path B).
- [Near-miss: T-103 OOS-AUC measured on 252-bar window, live infers on 60](feedback_hmm_window_mismatch_verify_2026_06_05.md) — the validated posterior is not the live posterior. Always reconcile inference window before flag-flip.
- [Deployment posture on the borderline base (2026-06-15)](project_deployment_posture_2026_06_15.md) — paper-NOW; small-live OK Roth-only with deep-window safe_f cap (expect <1) + armed kills; ci_low 0.382 forbids SIZE not observation; both crisis-defense levers dead.
- [safe_f is record-conditional — never quote a benign-year number](feedback_safef_is_record_conditional_2026_06_15.md) — 1.602 is the calm-2024 artifact; deep-window 26yr safe_f likely <1; cap sizing min(1, deepwindow), no leverage on an unhedged equity book.
