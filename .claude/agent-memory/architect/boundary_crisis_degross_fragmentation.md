---
name: finding-crisis-degross-fragmented
description: The single market fact "crisis regime" is independently de-grossed in FOUR engines (A forecast, B sizing, C allocation, F edge-weights) — the Double-Counting Matrix's own anti-triple-count rule is violated in code
metadata:
  type: project
---

ArchonDEX's most important architectural risk for T-092 Path B: crisis-regime
de-grossing is FRAGMENTED across four engines, all keying on the same Engine E
crisis posterior, none of them aware of the others. The charter's Double-Counting
Matrix (engine_charters.md:541-557) exists precisely to prevent this and its own
rule is "each regime fact affects at most 2 engines, never both as 'reduce
aggressiveness'." Verified-in-code reality (2026-06-04):

- **A (forecast):** signal_processor.py:546-549 multiplies every edge norm by
  `advisory.risk_scalar` when regime_summary in (stressed,crisis). Default-ON.
  This VIOLATES the matrix — the Risk-Off row gives A a dash; B is the only
  authorized consumer. A "reduces aggressiveness," which the matrix forbids.
- **B (sizing):** risk_engine.py:739-741 applies the SAME risk_scalar to ATR
  sizing (authorized). Plus advisory crisis floor on max_positions
  (risk_engine.py:729 ← advisory.py:228, crisis→5). Default-ON.
- **C (allocation):** policy.py:334-352 regime-aware vol-target ceiling (1.0x = no
  leverage in crisis) + 0.3x downside FLOOR + exposure-cap consumption that
  DOUBLE-CONSUMES the same suggested_exposure_cap B also consumes. Gated behind
  adaptive-mode (reachable via the mode-flip, see [[pattern-flag-vs-path-disconnect]]).
- **F (edge-weights):** regime_tracker get_regime_weight kills edges whose
  per-regime Sharpe <= 0. Gated off (regime_conditional_enabled=false).

**Path B implication:** a new HMM crisis kill-switch gating on the same crisis
posterior would be the FIFTH de-gross on one fact. Before building it, the live
de-gross stack must be inventoried and the kill-switch must either replace or
explicitly compose with A's risk_scalar brake + B's max_positions floor (both
default-ON) — otherwise crisis de-gross is triple/quadruple-applied.

**How to apply:** when reviewing any new exposure/de-gross/regime change, ask
"how many engines already cut on this same E field?" The matrix is the contract;
check code against it, because A already breaks it.

Related: [[pattern-verdict-buries-capability]], [[pattern-advisory-key-mismatch]].
