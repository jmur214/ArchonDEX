---
task_id: T-2026-06-18-215
title: Cloud canonical beat-the-robo measurement — PREP + pre-registration (PIT × realistic-cost)
date: 2026-06-18
author: Agent D (substrate + cloud lane)
type: prep + pre-registration (the RUN is gated on C's T-211 harness)
outcome: Cloud path VERIFIED ready for the honest beat-the-robo cell (PIT ×
  realistic-cost, census-gated, cov-pin deterministic, measured-mode). Closed the
  one substrate gap: market_cap_tiers.json (the realistic-cost cap join) was NOT
  baked → realistic_retail_costs would be SILENTLY INERT on the cloud (all-ADV
  fallback); now baked + manifest-pinned. The canonical RUN (base vs composition)
  is GATED on C's T-211 phase1_composition harness landing (only T-203 is in C's
  outbox so far) + an image built off that commit. Pre-registration + the exact
  cell spec are here so the run fires the moment T-211 lands.
status: PREP DONE — run pending C/T-211 + the image build
---

# T-215 — cloud canonical beat-the-robo measurement: prep

## 1. Cloud path — VERIFIED ready
- **Both modes flip via the cell config patch.** `cloud_entrypoint.sh` applies
  `ARCHONDEX_CONFIG_PATCH_B64` (base64 JSON) BEFORE the run. The cell sets:
  - `use_historical_universe: true` → `mode_controller:774-778` →
    `resolve_universe(use_historical=True)` → PIT universe (T-207/T-154).
  - `slippage_extra.realistic_retail_costs: true` → `get_slippage_model` →
    cap-tier half-spreads (T-210). **NB:** the patch must MERGE into the existing
    `slippage_extra` (preserve the ADV keys + add the flag), not replace it.
- **Measured-mode ON:** `cloud_entrypoint.sh:46` sets `ARCHONDEX_MEASURED=1` → the
  T-189/T-194 loader HALTs if a load-bearing input is missing (simfin / membership)
  → no silent survivorship/simfin-blind cell.
- **Census + cov-pin:** `core/census.py` (T-181) gates the cell (`fundamentals_blind
  =0`, `regime_unknown~0`, `n_trades>floor`); `deterministic_cov` (T-140-fu3) is on
  the mean_variance path → cross-task bitwise determinism.
- **Image provenance:** an image built off CURRENT origin/main carries T-207 (PIT)
  AND T-210 (realistic-cost) — both are merged (verified). It MUST also carry C's
  **T-211 phase1_composition** (not yet landed) → the canonical image is built off
  the commit that merges T-211.

## 2. Substrate baking — the gap I closed (load-bearing)
`market_cap_tiers.json` (the T-210 realistic-cost cap join) was **NOT** in
`Dockerfile.backtest` or the manifest. Without it the cap cache loads EMPTY on the
cloud → every ticker silently falls back to the ADV bucket → **realistic_retail_costs
=true would be INERT** (the honest cell would under-cost — a silent fail-open).
**Fixed:** `Dockerfile.backtest` now `COPY`s it; `gen_substrate_manifest.SUBSTRATE_FILES`
pins it; manifest regenerated (diff = the cap-json line only, no foreign drift).
- **Cap coverage:** built for the static-109 (107/109) AND extended to the PIT
  universe (676 names) — 340 entries, **300 resolved** (51 mega / 205 large / 33 mid / 7 small / 4 micro), ~40 delisted-miss.
- **LIMITATION (carried from T-210):** delisted PIT names have no current cap →
  ADV-fallback (15 bps) → the realistic cell UNDER-counts friction on exactly the
  survivorship cohort. The number is a CONSERVATIVE lower bound; true PIT cost needs
  survivorship-free cap history (Norgate/FMP). The other baked legs (simfin T-180,
  macro T-164, full SPY T-167, membership T-167) are present.

## 3. Harness contract with C (don't fork — single source of truth)
Per C's T-211 inbox: C builds a default-OFF `phase1_composition` Engine-C mode
(base + trend-overlay E/T-204 + defensive tilt A/T-205 + T-148 lower-turnover;
vol-target EXCLUDED, B/T-212). The cloud cell INVOKES that mode + the base through
C's gate — it does NOT reimplement composition. The verdict path:
`run backtest → candidate_equity → core.combined_candidate_scorecard.
evaluate_deploy_readiness(candidate_equity, account="roth", robo=("60_40",
"schwab_like"), w_dbmf=0.20, mdd_improve_threshold=0.20, n_boot=1000) →` pass iff
`ci_low(Sharpe_cand) > ci_low(Sharpe_robo)` OR ≥20% shallower MDD, after-tax,
crisis-tail-verified; + `FactorRiskModel.is_it_beta_or_edge()` (Engine-B/T-209) on
the composition returns (we EXPECT "beta" — the win is better-shaped beta).

## 4. PRE-REGISTRATION (the canonical cells — written before the run)
- **Hypothesis H1:** the Phase-1 composition clears `evaluate_deploy_readiness`
  (beats the robo on after-tax ci_low Sharpe OR ≥20% shallower MDD, Roth) on the
  HONEST substrate (PIT × realistic-cost) over a CRISIS-INCLUSIVE full-cycle window,
  where the BASE does not. **H0:** it does not clear (the honest, decision-grade
  null — closes the high-belief front with evidence).
- **Substrate:** PIT universe (`use_historical_universe=true`) × realistic-cost
  (`realistic_retail_costs=true`).
- **Window:** **2000-01-01 → 2024-12-31** (full-cycle, crisis-inclusive: dotcom
  2000-02, GFC 2008, COVID 2020, 2022). Required: `full_cycle_tail_verified=True`
  (the gate discounts a bull-window MDD).
- **Cells:** 2 configs (BASE, COMPOSITION) × **N≥3 reps** each (the standing
  reproducibility rule; cov-pin → expect bitwise-unanimous) = 6 cells. Block-
  bootstrap CI (1000 iter). Census-gated (a non-canonical cell is void).
- **N_trials:** this is the composition deploy-decision, n_trials per the honest-N
  registry at run time (`compute_n_effective`), DSR-aware where applicable.
- **Decision rule:** `evaluate_deploy_readiness` verdict + `is_it_beta_or_edge`
  classification. Promote NOTHING; the verdict goes to the director.
- **Cost:** ~6 cells (Fargate); a 26yr PIT cell ≈ B's T-180 ~9h each → modest $ but
  LOG it; **flag before any larger fan-out.**

## 5. RUN status — GATED
The run fires once: (a) C's **T-211 phase1_composition** lands on main; (b) B builds
the canonical image off that commit (carries T-207+T-210+T-211 + the now-baked cap
join + membership + simfin + macro + SPY) and census-pre-flights one cell; (c) I
submit the 6 cells with the config patch above. The PREP (path + substrate +
contract + pre-registration) is done; nothing else blocks D's side.

## Files
- `Dockerfile.backtest` — bake `market_cap_tiers.json` (realistic-cost cap join)
- `scripts/gen_substrate_manifest.py` — pin `market_cap_tiers.json` (SUBSTRATE_FILES)
- `config/substrate_manifest.sha256` — regenerated (cap-json pinned; no foreign drift)
- `data/universe/market_cap_tiers.json` — static-109 + PIT cap snapshot (gitignored)

## NOT done (per constraints)
The realistic-cost + PIT modes are turned ON only IN THE MEASUREMENT CELL config
patch — NOT a prod default flip (the config defaults stay OFF; canon unchanged).
Promote nothing. The RUN waits on C/T-211. Branch only; director reviews the verdict.
