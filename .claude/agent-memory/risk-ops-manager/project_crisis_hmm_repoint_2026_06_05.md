---
name: project-crisis-hmm-repoint
description: T-103-repoint design — graduated (not binary) de-gross from crisis-HMM 1-p_benign into the live Path-A regime_summary. Default-OFF, REPLACE-not-STACK with 5-axis, A/B-gated. Propose-first Engine E/B.
metadata:
  type: project
---

Proposal authored 2026-06-05 (propose-first, NO code) to repoint the live
crisis de-gross from the 5-axis detector (MISSED COVID per T-100: 0 crisis
bars May-Dec 2020) to the T-103 crisis-trained HMM combined posterior
`1 - p_benign = p_crisis + p_stressed` (OOS-AUC@5d 0.914 ci_low 0.880;
p_crisis-alone is coin-flip OOS 0.497). Model artifact
`hmm_3state_crisis_v1.pkl` exists; live config still points at baseline
`hmm_3state_v1.pkl`.

**Why:** The crisis signal is ON ~38% of days (the crisis-trained HMM dumps
non-2008 stress into the 37.8% `stressed` bucket; COVID rode p_stressed=1.000
for the whole Mar-May 2020 span). 38%-on means a BINARY kill would over-cut
in calm-but-stressed periods — so the design maps 1-p_benign to a CONTINUOUS
exposure scalar (graduated de-gross), not a switch.

**How to apply (key design constraints carried forward):**
- Inject at advisory.py:176 — a new `_risk_to_summary_hmm` consuming a
  synthetic risk_score = `1 - p_benign` so ALL existing Path A consumers
  pivot with zero downstream edits (Option A / Minimal in the map).
- DOUBLE-COUNT GUARD: the new HMM-derived regime_summary must REPLACE the
  5-axis-derived one, never stack. Engine E owns the single cut; Engine A/B/C
  consumers stay as-is. Do not let both the 5-axis and HMM brakes multiply.
- DEFAULT-OFF: new `regime_settings.json` flag (e.g. hmm_repoint_enabled=false)
  + canon-md5 must be bitwise-identical to head when OFF.
- A/B arms: (1) current 5-axis, (2) HMM-repoint, (3) combined/max-conservative.
  16-yr + 26-yr windows. PRIMARY KPI = MaxDD reduction; secondary = Sharpe
  ci_low must-not-go-down (block-bootstrap, CLAUDE.md). Calibrate scalar on
  one window, verify OOS on the other (CLAUDE.md #9).
- NEAR-MISS flagged: live infers on 60-bar window, T-103 AUC was 252-bar —
  see [[hmm-window-mismatch-verify]]. Must reconcile before flag-flip.
- Risks: regime_summary blast radius (signal_processor + policy + risk_engine
  all consume it); crisis model train ends 2019 (no post-2020 in train);
  38%-on may over-de-gross. See [[project-live-path-a-degross-map]].
- Gated on T-099 (determinism) — MERGED 253a96f, single-container PASS;
  cross-container cloud verify still DEFERRED, so the cloud A/B must
  canon-md5 the OFF arm vs head before trusting deltas.
