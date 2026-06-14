---
name: engine-d-doc-drift-gate-accretion
description: Engine D's validate_candidate gauntlet accretes gates over time but the charter/index.md freeze the count at "4-gate"; and MEMORY records refuted VERDICTs while losing the shipped CAPABILITY
metadata:
  type: project
---

Engine D (Discovery) drifts via **capability accretion that the living docs never catch up to**. Two recurring mechanisms:

**1. Gate accretion vs frozen "4-gate" claim.**
`DiscoveryEngine.validate_candidate` (discovery.py) has grown from 4 gates to **Gate 0 through Gate 8** (Gate 0 MBL pre-flight, Gate 5 Universe-B transfer, Gate 6 FF5+Mom factor-alpha, Gate 7 substrate-transfer, Gate 8 DSR multiple-testing), and the *meanings* of Gates 1 and 3 changed (Gate 1 became a contribution-lift gate `with−baseline>0.10`, not standalone "Sharpe>0"; Gate 3 became rolling-window consistency, not OOS/IS WFO degradation). Both `engine_charters.md` Invariant #4 AND `index.md` still say "4-Gate Validation (backtest → PBO → WFO → significance)." Gates 7/8 are wired LIVE in `orchestration/mode_controller.py:~1209-1318` (the production `--discover` path), so they are NOT dead code despite their default-skip signature.
**Where it SHOULD be discoverable but is not:** engine_charters.md Engine D output contract + Invariant #4; index.md "4-Gate Validation" design note.

**2. MEMORY logs the VERDICT, loses the CAPABILITY.** (This is the project-wide gap the C/E crisis-de-gross discovery exposed — confirmed identical in D.)
- MEMORY says "Engine D GA emits only rsi_bounce_v1 mutations" (project_engine_d_gene_encoding_blocker_2026_05_11) — but T-022/T-024/T-052 SHIPPED a far wider vocabulary. `_create_random_gene` (discovery.py:405-657) now emits **macro** (vix_level/yield_curve/unemployment_delta), **behavioral** (panic_score/herding_breadth), **regime** (is bear), **foundry_feature (20%)**, and `direction: short`/`market_neutral` genomes — all resolved by composite_edge.py. So D can ALREADY discover crisis/VIX-gated/short edges. The "gene encoding blocker" memory is the *pre-fix* state; nothing records that the vocabulary expansion landed.
- Pattern: when a feature is built but the headline finding around it is "refuted/blocked," MEMORY captures only the negative verdict. The shipped knob/vocabulary/gate survives in code, invisible to a future planner. **For Path-B / crisis-robustness audits, the highest-value move is to grep the CODE surface for crisis/regime/short/hedge primitives directly, never trust MEMORY's "X is blocked/refuted" as evidence X doesn't exist.**

**Other Engine D capabilities buried from living docs (2026-06-04 audit):** `use_bayesian_opt` flag (skopt GP+EI candidate search, default OFF, no config file exists yet so it's inert); `SyntheticMarketGenerator` regime-switching stress-test data (bull/bear/sideways Markov, charter mentions name only); `generate_cross_section_bootstrap` (correlation-preserving cross-section bootstrap); `WFO.embargo_days` leakage guard. None are in CURRENT_STATE or the charter beyond a one-word module-table entry.

See also [[equity_index_bug_class]] and [[engine_f_evolution_controller_does_d_work]] — Engine D and F both have the "code outran the doc" failure mode.
