---
name: project-live-path-a-degross-map
description: The LIVE Path A crisis de-gross controls depend EXCLUSIVELY on the 5-axis regime_summary, not the HMM. Exact file:lines of every consumer; HMM currently dead-ends in risk_scalar sizing (Path B).
metadata:
  type: project
---

The live crisis de-gross chain in production reads `advisory["regime_summary"]`,
which is 100% derived from the 5-axis `risk_score`
(`advisory.py:176` `_risk_to_summary(risk_score)`; risk_score from
`_compute_risk_score` axis-weighted average at advisory.py:161). The HMM
has ZERO input to regime_summary today.

**Why:** Needed for the T-103-repoint proposal — to inject the crisis-HMM
`1 - p_benign` into the live de-gross, you must reach `regime_summary` (or
the cap/max-positions it gates), NOT `risk_scalar`. The HMM's only current
wire (advisory.py:204-209) damps `risk_scalar` by entropy-confidence, and
`risk_scalar` only feeds `risk_engine.py:915` ATR sizing = DEAD Path B per
T-088/T-100 (prod sizes via Path A target_weight).

**How to apply:** When proposing or reviewing any regime-driven exposure
change, the live Path A consumers (verified 2026-06-05 against current code) are:
- `engine_a_alpha/signal_processor.py:545-551` — risk_scalar brake on edge
  scores when regime_summary in (stressed, crisis), BEFORE alpha aggregation.
- `engine_a_alpha/signal_processor.py:588-593` — per-edge regime_gate weight
  multiplier indexed by regime_summary.
- `engine_c_portfolio/policy.py:246-247` — `_apply_exposure_cap` consumes
  `suggested_exposure_cap` (gated by exposure_cap_enabled, default True).
- `engine_b_risk/risk_engine.py:729-736` — effective_max_positions +
  effective_max_gross from advisory; hard gates at 751-752 and gross at ~1117
  (risk_advisory_enabled default True).
- `advisory.py:228-235` — regime_summary applies crisis_max_positions=5 /
  stressed_max_positions=7 FLOOR (regime_config.py:105-106).
Diagnostics-only (do NOT affect trades): per_ticker_score_logger.py:87,
mode_controller.py. Secondary overlay (both flags default False):
vol_target.py:271-275. Dead/unpopulated: advisory["correlation_regime"]
(risk_engine.py:744 always falls back to "normal"). See
[[project-crisis-hmm-repoint]] and [[hmm-window-mismatch-verify]].
