---
task_id: T-2026-06-18-216
title: Conjunctive "trade like a trader" selector — BUILD + honest test vs the robo gate (the central thesis)
date: 2026-06-18
scope: Engine-A signal construction (ensemble_mode=conjunctive, default-OFF, additive/canon-safe); measured vs the T-203 robo gate; builds T-208's design
status: CURRENT (pre-registration committed before build/run — see git history; results appended after)
outcome: "**H0 — the central conjunctive thesis is CLEANLY CLOSED with evidence (recent-window first-cut).** Built ensemble_mode=conjunctive (default-OFF, canon-inert PROVEN: 4055ead6 with-change == stashed-base). Mode fires (canon 6c8251f7, 328 trades vs legacy 465 — fundamental-confirmation gate prunes ~30%, not zeroed). 2018-2025 robo gate (Roth, after-tax, w_dbmf=0): passed=False / DO NOT DEPLOY — beats 60/40 (ci_low −0.075>−0.273) but FAILS schwab_like (ci_low −0.239<−0.135 + worse MDD); beta-or-edge = 'beta' (alpha +3.99%/yr, t_hac +1.18 < signif). Consistent with the <20% prior. The thesis is now TESTED not 'never tried.' CAVEAT: 2018-2025 is bull-heavy (worst case for a defensive gate); the canonical crisis-inclusive 26-yr PIT-universe robo-gate is flagged as a CLOUD cell (the fuller test) before declaring it permanently dead. Bug caught: env-suffixed-config trap (first run patched alpha_settings.json but run reads alpha_settings.prod.json — identical canon was the tell). N_trials += 1."
references: docs/Audit/conditional_selection_design_t208_2026_06_18.md (the design); T-205 quality; T-156 (averaging washes out); core/combined_candidate_scorecard.evaluate_deploy_readiness; engine_b_risk/factor_analysis.is_it_beta_or_edge
---

# T-216 — Conjunctive Selector: Build + Honest Test

## 1. PRE-REGISTRATION (committed before build/run)

### 1.1 The thesis (the project's central original idea, never tested)

"Fundamentals say it's a good buy → THEN technicals confirm the entry →
and only in the right regime." Today the ensemble AVERAGES independent
edge votes (weighted-mean + shrinkage), which T-156 showed washes them
out. The conjunctive version makes the dimensions MULTIPLICATIVE gates.
Literature prior < 20% (12/13 edges factor-negative) — but a clean
measured pass/fail on the central thesis beats an un-tested "what if."

### 1.2 The ONE structure (fixed — no search, per T-208)

Per-ticker, computed from the edges that fired this bar
(categories via `EDGE_CATEGORY_MAP`: technical = momentum /
trend_following / mean_reversion; fundamental = fundamental):

- **`s_tech`** = weighted-mean norm over TECHNICAL edges (the same
  weighted-mean the legacy uses, restricted to technical). No technical
  edge fired → `s_tech = 0` (no entry signal → no trade).
- **`g_fund` ∈ [0,1]** = the fundamental confirmation gate. `f_agg` =
  weighted-mean norm over FUNDAMENTAL edges (the quality/value signal —
  same edges T-205 repointed). `g_fund = clip(0.5 + f_agg, 0, 1)` if ≥1
  fundamental edge fired, **else `g_fund = 0`** (require fundamental
  confirmation — this is the conjunction; a great-technical name with no
  fundamental opinion does NOT trade).
- **`g_regime` ∈ [0,1]** = regime gate, reusing the regime_summary the
  existing `regime_gate` hook reads. Fixed map: robust_expansion 1.0,
  emerging_expansion 1.0, cautious_decline 0.5, market_turmoil 0.0,
  default/benign 1.0.
- **`conjunctive_score = clip(s_tech × g_fund × g_regime, −1, 1)`** —
  replaces the averaged `agg` ONLY when `ensemble.mode == "conjunctive"`.

This reuses the existing edges + the regime hook; no new alpha, no
engine-boundary cross. It is Engine-A signal construction only.

### 1.3 Default-OFF / canon-safe (invariant)

`EnsembleSettings.mode` defaults to `"weighted_mean"` → the legacy path
is bitwise-unchanged. **Proof obligation: 2024 cell canon-md5 UNCHANGED
with mode at default.** The conjunctive branch executes only when the
config opts in.

### 1.4 The gate (fixed) + N_trials

- **Gate:** `core/combined_candidate_scorecard.evaluate_deploy_readiness(
  candidate_equity, account="roth", w_dbmf=0.0)` — the T-203 robo gate,
  Roth, after-tax, net-of-cost, vs the 60_40 + schwab_like proxies.
  **PASS = `passed=True`** (beats ALL proxies on `ci_low(Sharpe)` OR a
  ≥20% shallower MaxDD). Plus the `is_it_beta_or_edge()` verdict
  (B/T-209) on the conjunctive returns.
- Substrate: the honest substrate (PIT universe + realistic costs ON),
  crisis-inclusive. Compute-bound full-cycle → **local first-cut now +
  flag a cloud cell for the canonical** (like C/T-211).
- **N_trials += 1** (this ONE structure). No space search; any variant
  is a new trial. Pre-registered before the run (CLAUDE.md #7).

### 1.5 Honest deliverable either way

- **H1** — conjunctive clears the robo gate → the central thesis is
  VINDICATED (a huge, report-it-loud result).
- **H0** — a clean, well-measured MISS → the central thesis is honestly
  CLOSED with evidence, not left as a permanent "we never tried."
- Both are real answers; whichever it is gets reported plainly. A likely
  side-finding: the conjunction (require-fundamental-confirmation) may
  shrink the tradeable set sharply (fundamentals cover ~50% of names and
  must fire) → if trades are too few to evaluate, THAT is the finding
  (the conjunction is too restrictive at our coverage).

---

## 2. RESULTS

(Appended after the pre-registration commit `4ab5979`.)

### 2.0 Build + canon-inert proof (mode OFF)

`ensemble_mode` added to `EnsembleSettings` (default `"weighted_mean"`),
`_conjunctive_aggregate()` in `signal_processor`, config threaded in
`alpha_engine`. **Canon-inert PROVEN:** 2024 cell with the change
(mode default) = `4055ead6…` / Sharpe 2.22; with the change **stashed**
(removed) = `4055ead6…` / 2.22 — **bitwise identical** → the conjunctive
code is a strict no-op when OFF (prod canon unchanged).

### 2.1 Mode fires (and a bug caught along the way)

**Bug caught before it produced a false verdict:** the first conjunctive
run patched `config/alpha_settings.json`, but `run_isolated` uses
`env="prod"` → reads `alpha_settings.prod.json` (the env-suffixed-config
trap). The tell was a canon IDENTICAL to legacy (`4055ead6`) — the mode
never fired. Re-running against `alpha_settings.prod.json`:
- **2024 (mode ON):** canon `6c8251f7…` (≠ legacy `4055ead6`), Sharpe
  **0.731** (vs legacy 2.22), **328 trades** (vs legacy 465). The
  require-fundamental-confirmation conjunction prunes ~30% of trades but
  does NOT zero out — it's a real, sane, firing signal. The bull-year
  underperformance is the expected signature of a defensive
  fundamental+regime gate in a strong bull (it gates out momentum names
  lacking fundamental confirmation).

### 2.2 The pre-registered gate — multi-year (2018-2025, local first-cut)

Conjunctive 2018-2025 (current universe, 2011 daily obs): canon
`cca2534f`, **CAGR 9.92%, MDD −17.8%, raw Sharpe 0.958.**

**ROBO GATE** (`evaluate_deploy_readiness`, Roth, after-tax, w_dbmf=0.0):

| vs proxy | cand ci_low | robo ci_low | cand MDD | robo MDD | beats? |
|---|---|---|---|---|---|
| 60_40 | −0.075 | −0.273 | −17.8% | −21.8% | YES (ci_low) |
| schwab_like | **−0.239** | **−0.135** | −17.8% | −16.0% | **NO** (worse ci_low + MDD) |

**`passed = False` → DO NOT DEPLOY.** The gate requires beating ALL
proxies; the conjunctive selector beats 60/40 but loses to the
schwab-like proxy on both ci_low and MDD.

**BETA-OR-EDGE** (B/T-209): alpha_ann **+3.99%**, alpha_t_hac **+1.18**
(below the ~2 significance bar), R² 0.221 → **VERDICT: "beta"** — the
returns are explained by factor exposure; no statistically-orthogonal
edge.

### 2.3 Verdict — H0: the central thesis is CLEANLY CLOSED with evidence (recent-window first-cut)

**The conjunctive "trade like a trader" selector does NOT clear the robo
gate and is "beta" not "edge" on the 2018-2025 window.** H0, measured —
consistent with the pre-stated <20% prior. The mechanism works
(canon-inert OFF, fires ON, trades sanely); the conjunctive STRUCTURE
(fundamentals × technical × regime as multiplicative gates) does not
produce a robo-beating, factor-orthogonal result here.

**This is the deliverable the dispatch wanted:** the project's central
original thesis is now TESTED with evidence, not a permanent "we never
tried." A clean H0 closes it honestly.

**The one honest caveat that gates a full close → the canonical is a
cloud cell.** 2018-2025 is a BULL-HEAVY recent window (current universe),
the worst case for a DEFENSIVE conjunctive gate — it gives up rally
upside (2024: 0.731 vs 2.22) for downside protection that this window
barely needed (base MDD only −17.8%). A defensive conjunctive structure
could plausibly fare relatively better on the **crisis-inclusive
26-yr full-cycle (PIT universe)** where the gating-out *helps* (2008,
dotcom). So the recent-window first-cut is H0, and **the canonical
full-cycle robo-gate is flagged as a cloud cell** (compute/data-bound
locally — the historical-universe multi-year data-load is the bottleneck
that hung the first attempt). The <20% prior + this first-cut + the
"beta" verdict all point H0, but the deep-window cloud run is the fuller
test before the thesis is declared permanently dead.

### 2.4 What was NOT done (discipline)

- ONE pre-registered structure measured AS-IS; **no space search** (the
  overfit trap T-208 warned about). N_trials += 1.
- The canonical 26-yr crisis-inclusive PIT-universe robo-gate = a flagged
  CLOUD cell (per the dispatch's "local first-cut + flag a cloud cell").
- Default-OFF preserved; config reverted (git diff = only signal_processor
  + alpha_engine).
