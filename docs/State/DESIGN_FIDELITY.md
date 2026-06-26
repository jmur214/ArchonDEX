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

> **⚠️ STRATEGIC REALITY UPDATE (T-242 currency pass, 2026-06-26) — the CENTRAL intent shifted.**
> The original "True Edge" vision (the conjunctive selector gating a stacked-alpha EQUITY BOOK) is
> BUILT (T-216) but now gates a book measured **H0** — no alpha on the honest PIT × realistic-cost
> substrate, on Sharpe AND Sortino (T-215; composition H0 on tail too, T-234). **The realized
> robo-beater is NOT the equity book — it's the TREND-OVERLAY SLEEVE** (T-204/T-236: Sortino 1.085,
> MaxDD −12%, survives dotcom — the first validated robo-beater on the TAIL yardstick, → paper
> E/T-238). **The win is the SLEEVE, not the equity book.** The measure is now **Sortino + tail**
> (2026-06-25 directive), not Sharpe (which buried the convex sleeve). So the conjunctive-selector
> row below, while correctly BUILT+DORMANT, is no longer the live CORE prize — it would refine an
> H0 book. In-flight: C1 concentration moonshot probe (T-241), trend-sleeve paper validation
> (T-238), EDGAR Lazy-Prices (T-237, leaning H0).

## The registry

| Capability | Centrality | Status | Intended (doc) | Reality (code) |
|---|---|---|---|---|
| **Conjunctive/conditional "True Edge" selector** (fundamentals/regime AS GATES on technicals; multiplicative AND-logic) | **CORE** | **BUILT + DORMANT** (default-OFF `mode=conjunctive`; composition verdict pending the deep-window measure) | `PROJECT_CONTEXT.md:101-102` "the ultimate goal / holy grail"; `:18` asserts it's already applied | **BUILT (T-216, merged).** `_conjunctive_aggregate` at `signal_processor.py:510` (s_tech × g_fund × g_regime), dispatched at `:693` under `mode='conjunctive'`; default prod path is still weighted_sum so canon-md5 is unchanged (DORMANT). g_regime consumes E/T-217 `hmm_regime_label` (`signal_processor.py:546-547`). Prior status was a one-merge-wave lag (registry said NEVER-BUILT; was already built). |
| **Trend-overlay SLEEVE** (long/flat 5mo absolute-momentum on SPY/AGG/GLD — the asymmetric-upside / tail-protection sleeve, [[project_retail_capital_constraint_2026_05_01]]) | **CORE (the realized robo-beater)** | **VALIDATED (offline) — heading to PAPER; code DORMANT** | asymmetric-upside / crisis-defense objective | **VALIDATED T-236** (full-cycle incl dotcom: Sortino 1.085/ci_low 0.536 > both robos, MaxDD −12%, clears MBL @ honest-N) — the FIRST validated robo-beater on the tail yardstick. Code: `core/trend_overlay.py` (pure module) + consumed by Engine-C `phase1_composition.py` (DORMANT, default-OFF). Standalone-sleeve DEPLOY is the live forward path (paper proposal E/T-238). **Distinct from the REFUTED in-house sleeves below** (vol-target/de-gross/spot-sleeve) — this is the long/flat absolute-momentum overlay, a DIFFERENT mechanism, and it WORKS on the tail measure. NOT a free win: ~1%/yr less terminal wealth for the smoother ride (the give-up the T-241 moonshot probe aims to close). |
| Regime-conditional edge gating (per-edge `regime_gate` dicts) | important | DORMANT | `signal_processor.py:585-593` plumbing applies `w *= gate[regime]` | Fed EMPTY dicts (0 `regime_gate` in edges.yml) → silent no-op. Disabled after walk-forward falsification (net-neg 2/3 splits). |
| Regime-conditional weighting / per-regime kill (Governor) | important | DORMANT | producer (regime_tracker, Welford) + consumer both built | `governor_settings.json:13 regime_conditional_enabled:false`. Global weight-update path active; regime-conditional never shipped. |
| `hmm_p_crisis` (validated AUC 0.887) wired to a live sizer/gate | important | PARTIAL/DORMANT | Engine E publishes a validated crisis posterior for the live path to consume | Validated (T-087/89). As a standalone SIZER still DEAD (T-178: dynamic sizer doesn't beat always-on 20%). The RANK-3 use has now SHIPPED: E/T-217 `hmm_regime_label` (regime_gate.py:63) derives the calm/cautious/crisis label that feeds the conjunctive selector's g_regime gate (signal_processor.py:546-547) — reachable only under the default-OFF `mode=conjunctive` (DORMANT). |
| 6-engine division of labor + inviolable boundaries | CORE | ACTIVE | `engine_charters.md` formal charters | Built as designed; boundaries enforced. |
| Autonomous discovery + lifecycle + self-learning loop | important | ACTIVE | 4-gate validation, GA, pause/retire/revive, learn-from-fills | Built; fired autonomously (atr_breakout auto-paused 2026-04-24). |
| Institutional backtesting rigor (CI/MBL/census/fail-closed) | CORE | ACTIVE | "bones before paper" | Built; the most mature part of the system. |
| Confidence-gated execution (N≥3 edges agree) | important | REFUTED | a weaker conjunction form | T-057: +0.793→−0.075→−0.128 across substrates. Correctly abandoned. |
| Regime vol-target / de-gross overlay / capital-partition sleeve | important | REFUTED (thesis) — CODE STILL SHIPS WIRED + DORMANT | in-house crisis defense | THESIS refuted: T-055h (vol-target) / T-118r (de-gross) / T-128r (sleeve). **NB: these are the OLD in-house crisis sleeves — DISTINCT from the T-204/T-236 trend-overlay sleeve above, which is VALIDATED (the long/flat absolute-momentum overlay is a different mechanism + works on the tail measure).** Live crisis lever = the trend-overlay sleeve (T-236) and/or a BOUGHT MF sleeve. **"Refuted" ≠ "removed": the code still ships, wired + inert, default-OFF.** SpotETFTrendSleeve is constructed in PortfolioEngine init (capital partition) + snapshot equity (PnL) behind `spot_etf_trend_sleeve_enabled=False` (portfolio_engine.py:79-85, 322-331); B's regime_transition_overlay (T-118, risk_engine.py) ships Path-A-LIVE behind `regime_transition_overlay_enabled=False`. See capability_ledger Engine-B / Engine-C rows. |
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
