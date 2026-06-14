---
name: engine-a-drift-patterns
description: How Engine A (Alpha) drifts from its charter — risk-protective logic leaking into the forecast layer, and refuted-experiment capabilities left shipped-but-undocumented
metadata:
  type: project
---

Engine A's charter (engine_charters.md:28-89) is emphatic that A is the loose, opinionated Researcher: "opinionated about direction but NOT protective about risk." The dominant A drift pattern is RISK-PROTECTIVE LOGIC LEAKING INTO THE FORECAST LAYER.

**Why:** B's job is risk; A's job is direction. But because A's SignalProcessor sits in the hot path and has `regime_meta` available, it's the path of least resistance to bolt de-gross logic onto edge norms rather than route it through B.

**How to apply:** When auditing A, grep `signal_processor.py` for any multiplication of `norm` / `agg` by a regime- or advisory-derived scalar. Each one is a candidate charter violation (it makes A "protective about risk"). Cross-check against the Double-Counting Matrix (engine_charters.md:546-557) — if the same regime fact is consumed by B too, it's a double-count.

Confirmed leak sites in `signal_processor.py` (process loop):
- Macro brake: `norm *= risk_scalar` on stressed/crisis (543-551) — double-counts with B.
- Legacy binary cuts: bear→`*0.5`, high-vol→`*0.75` (552-559) — fallback when advisory absent.
- Learned-affinity multiplier 0.3-1.5x (561-576) — this one IS charter-sanctioned (matrix row "Learned Affinity" → A applies multiplier).
- Per-edge regime_gate weight multiplier (584-593).
- Micro-regime per-ticker trend/vol shrink_off (531-536) — A self-detecting trend/vol per ticker; arguably legitimate "ticker-level vol/trend penalty" (charter design note line 79) but it's A computing its own regime, adjacent to E's authority.

Second A drift pattern: REFUTED-EXPERIMENT CAPABILITIES LEFT SHIPPED-BUT-UNDOCUMENTED. confidence_gate (T-057 refuted), vol-target couplings (T-055 refuted) — the negative verdict is in MEMORY/CURRENT_STATE, the shipped knob is not. See [[engine-a-buried-defensive-paths]].

Engine A is NOT the fastest-drifting engine (that's D — bare-except + silent-default, see [[engine_d_drift_patterns]]). A's narrow-catch discipline is actually strong: `_PROGRAMMER_ERRORS` re-raise pattern is applied consistently across alpha_engine.py + signal_collector.py + signal_processor.py after the 2026-05-08 zero-trade regression. A's drift is architectural-boundary (risk logic in forecast), not silent-failure.
