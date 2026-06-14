---
name: hmm-window-mismatch-verify
description: T-103 OOS-AUC 0.914 was measured on a 252-bar trailing window; the live regime engine infers on 60 bars — the validated posterior is NOT the live posterior. Always reconcile inference window before any flag-flip.
metadata:
  type: feedback
---

Before recommending a flag-flip that promotes an offline-validated model
into a live path, confirm the live inference configuration MATCHES the
validation configuration on every load-bearing axis — window length,
feature panel, warmup, causality.

**Why:** T-103 validated the crisis-HMM combined posterior
(`1 - p_benign = p_crisis + p_stressed`) at OOS-AUC@5d 0.914 (ci_low 0.880)
using a **252-bar trailing window** (`validate_hmm_crisis_t103.py`:
`predict_proba(Z[max(0,t-251):t+1])[-1]`). But the LIVE engine path
(`engine_e_regime/regime_detector.py:429` → `hmm_classifier.predict_proba_at`,
hmm_classifier.py:252,286) smooths over a **60-bar window**
(`history_window=60`, `.tail(history_window)`). A 60-bar posterior on the
same model is a DIFFERENT random variable from the 252-bar posterior. The
0.914 number does not transfer to the live path until the windows are
reconciled (either set live to 252, or re-validate AUC at 60).

**How to apply:** Whenever a proposal cites an offline metric as the
justification for a live wiring change, grep the live inference call and
the validation script for window/lookback/feature-set params and diff them
explicitly. If they differ, the live A/B must re-establish the metric — do
NOT carry the offline CI into the live gate. This is a sibling of CLAUDE.md
#9 (re-verify on production substrate) but at the inference-config level,
not the data-substrate level. See [[project-crisis-hmm-repoint]].
