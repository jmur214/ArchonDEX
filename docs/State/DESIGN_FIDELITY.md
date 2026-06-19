# DESIGN_FIDELITY — Intent-vs-Build Registry

**The doc-system fix for the hole that hid the conjunctive selector for 18+ months.** Every other
tracker answers a *present-tense* question (CURRENT_STATE = what's true now, TASK_LEDGER = what
closed, capability_ledger = what's shipped, health_check = what's broken). **None answered "was an
originally-intended central capability ever actually built?"** — so a never-built capability had no
T-ID, no code line, no broken-flag, and fell through every net. This registry owns that question.

**Provenance:** seeded by the intent-vs-reality gap audit (2026-06-18, `wf_d6697848`), which read the
original design (`PROJECT_CONTEXT.md`, archived `GOAL.md`, `engine_charters.md`) against the built
code. **Status legend:** ACTIVE (built + in the live path) · DORMANT (built, not wired/fed/flagged) ·
NEVER-BUILT (intended, no implementation) · DIVERGED (built something different than intended) ·
REFUTED (intended, built/tested, killed by evidence — correctly abandoned).

## The registry

| Capability | Centrality | Status | Intended (doc) | Reality (code) |
|---|---|---|---|---|
| **Conjunctive/conditional "True Edge" selector** (fundamentals/regime AS GATES on technicals; multiplicative AND-logic) | **CORE** | **NEVER-BUILT** | `PROJECT_CONTEXT.md:101-102` "the ultimate goal / holy grail"; `:18` falsely asserts it's already applied | `signal_processor.py:615` weighted_sum ONLY; zero "conjunctive" in engines/; T-156 proved averaging washes it out; T-208 design-only. **→ BUILDING NOW (A/T-216).** |
| Regime-conditional edge gating (per-edge `regime_gate` dicts) | important | DORMANT | `signal_processor.py:585-593` plumbing applies `w *= gate[regime]` | Fed EMPTY dicts (0 `regime_gate` in edges.yml) → silent no-op. Disabled after walk-forward falsification (net-neg 2/3 splits). |
| Regime-conditional weighting / per-regime kill (Governor) | important | DORMANT | producer (regime_tracker, Welford) + consumer both built | `governor_settings.json:13 regime_conditional_enabled:false`. Global weight-update path active; regime-conditional never shipped. |
| `hmm_p_crisis` (validated AUC 0.887) wired to a live sizer/gate | important | PARTIAL/DEAD | Engine E publishes a validated crisis posterior for the live path to consume | Validated (T-087/89) but consumed by NOTHING live. T-178: dynamic sizer doesn't beat always-on 20%. → only as RANK-3 regime input to the selector. |
| 6-engine division of labor + inviolable boundaries | CORE | ACTIVE | `engine_charters.md` formal charters | Built as designed; boundaries enforced. |
| Autonomous discovery + lifecycle + self-learning loop | important | ACTIVE | 4-gate validation, GA, pause/retire/revive, learn-from-fills | Built; fired autonomously (atr_breakout auto-paused 2026-04-24). |
| Institutional backtesting rigor (CI/MBL/census/fail-closed) | CORE | ACTIVE | "bones before paper" | Built; the most mature part of the system. |
| Confidence-gated execution (N≥3 edges agree) | important | REFUTED | a weaker conjunction form | T-057: +0.793→−0.075→−0.128 across substrates. Correctly abandoned. |
| Regime vol-target / de-gross overlay / capital-partition sleeve | important | REFUTED | in-house crisis defense | T-055h/T-118r/T-128r all refuted. Live crisis lever = a BOUGHT MF sleeve. |
| **Intent-vs-build registry (this doc)** | CORE | **NEVER-BUILT → being created now** | implied by "continuously improve / stay faithful to design" | Did not exist; that absence is why the core gap stayed invisible 18 months. |

## How the gap hid (root-cause) — so it can't recur
The doc system is **verdict-and-state-centric, not intent-fidelity-centric** — a structural blind spot,
not a one-off. Three accelerants made it worse: **(1) the charter lied by omission** —
`PROJECT_CONTEXT.md:18` asserts "Applies True Edge combination rules" in the *present indicative*, so it
reads as built; **(2) "CURRENT_STATE wins" + the 2026-06-15 GOAL.md rewrite** evicted the original
conjunctive vision from the active reading path (it now lives unreferenced in `docs/Archive/`);
**(3) the empty-plumbing trap** — `regime_gate` was wired but fed `{}`, so it reads "partially built" to a
code scan and "exists" to the charter.

## The fix (this registry + the proposed rules changes)
1. **This doc exists now** — the standing intent-vs-build registry, code-grounded so a NEVER-BUILT row
   can't be silently asserted-as-built. Re-checked when a core capability's status changes.
2. **PROPOSE-FIRST (needs user go — touches CLAUDE.md / the charter):**
   - Insert `DESIGN_FIDELITY.md` into the CLAUDE.md reading order as step 2.5, with the rule:
     *"CURRENT_STATE wins on what-is-true-now; DESIGN_FIDELITY owns what-was-intended-but-isn't-built.
     Before building anything new, check ABSENT vs WIRED-WRONG."* (operationalizes prefer-repoint-over-rebuild)
   - Re-tag the charter's present-indicative claims (`PROJECT_CONTEXT.md:18,101-102`) with explicit
     build-status (e.g. `[INTENDED — NEVER-BUILT as of 2026-06-18; see DESIGN_FIDELITY / T-208/T-216]`).
   - Add a forwarding pointer from the live GOAL.md to the archived original conjunctive vision.
   - Add a "design-fidelity canary": make capability_ledger's "Wired-to-live?" mandatory + add a
     "Fed-real-data?" column (catches the empty-plumbing trap a code scan misses).
   - On REFUTATION, flip the row to REFUTED so the registry distinguishes wrongly-never-tried from
     correctly-abandoned (not a resurrection backlog of dead ideas).

## Prioritized builds (the never-built/dormant gaps worth closing)
- **RANK 1 — the conjunctive selector** (CORE, never-built, cheap: T-208 design + the regime_gate
  plumbing exist; `conjunctive_score = s_tech × g_fund × g_regime` is a few-line additive default-OFF
  path). **BUILDING NOW (A/T-216).** Caveats: pre-register (every prior conditional attempt reversed on
  extended substrate — it's wrongly-never-tried, NOT guaranteed); multiplicative gating CONCENTRATES
  trades (fewer names clear all gates) → collides with the $5-15K-AUM impact knee → trade-count
  sanity-check first.
- **RANK 2 — regime-conditional edge book activation** (DORMANT; the substrate for RANK 1; re-measure,
  may stay correctly OFF).
- **RANK 3 — `hmm_p_crisis` as the regime input to the selector** (NOT a standalone crash-timer — that
  lane is closed).
- **Do NOT resurrect:** vol-target / confidence-gate / de-gross / sleeve / dynamic sizer (REFUTED).
