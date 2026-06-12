# T-158 — Engine C reachability map under prod config: the override nobody knew was live

**Date:** 2026-06-11
**Agent:** C (branch `feature/engine-c-reachability-t158`, off origin/main `5d8cfdd`)
**Status:** READ-MOSTLY diagnostic. Zero engine edits (all instrumentation = runtime monkeypatching in `scripts/probe_engine_c_reachability_t158.py`); canon guard run post-work.
**Probe:** prod config, env=prod, window 2022-01-01→2022-03-31 under `run_isolated` governor isolation; counters on `allocate` / `optimize` / `_apply_vol_target` / `_apply_exposure_cap` / `_apply_regime_overrides`; 3 captured real allocate inputs replayed offline for the cancellation experiment. Artifact: `data/research/t158_reachability/probe_results.json`.

---

## 0. The headline — the dev's claim 2 is wrong at runtime, and the truth is bigger

**Local prod runs do not execute `mean_variance` at all.** The probe's live window: **61/61 allocate calls ran the ADAPTIVE branch; the optimizer was called 0 times; `_apply_vol_target` and `_apply_exposure_cap` ran on every bar.** Mechanism: `policy.allocate:170` calls `_apply_regime_overrides`, whose disk fallback loads `data/research/allocation_recommendations.json` — a **learned artifact written by the AllocationEvaluator on 2026-04-23** that carries `"mode": "adaptive"` (plus `max_weight: 0.15`, `target_volatility: 0.10`, `rebalance_threshold: 0.08`) for `_global` and every regime label. `"mode"` is in the safe-override keys list (`policy.py:138`), so **every call flips the config's `mean_variance` to `adaptive` before the branch executes.** The config's `mode: "mean_variance"` (on disk since 2026-01-27) has been dead-on-arrival since 2026-04-23.

**And the cloud canonical substrate is the opposite.** `data/research/` is untracked and NOT staged by `build_backtest_image.sh` (which stages only `processed/raw/governor`), so the rec file is **absent in the container** → `load_recommendations` no-ops → `get_config_for_regime` returns None → no override → **cloud canonical cells run `mean_variance` with the overlays dead** (the optimizer's `Σw=1` branch returns at `policy.py:252` before `:295/:299`). The governor re-writes the rec file only at END of run (`governor.py:520 save_recommendations`) — inside the container that write is discarded; locally it persists, which is exactly why the two substrates diverged silently.

> **LOCAL-vs-CLOUD ALLOCATOR DIVERGENCE (the finding of this task):** every local measurement since 2026-04-23 (the April verdicts, the T-101/T-111/T-116/T-118 2022 canon `0145c03a` lineage, every local exploratory Sharpe) ran **adaptive + live overlays + max_weight 0.15 + target_vol 0.10**. Every cloud canonical number (26yr `529e5520`/0.237, 16yr `9153ff15`/0.945, every campaign cell) ran **mean_variance with the Engine-C overlays dead and max_weight 0.30**. These are materially different trading systems. Local→cloud transfer of any Engine-C-sensitive finding is not substrate-conditional, it is *allocator*-conditional.

## 1. The reachability table (prod config, empirically probed)

| Engine C lever | Where | LOCAL substrate (rec file present) | CLOUD canonical (rec file absent) |
|---|---|---|---|
| `_apply_regime_overrides` (incl. **mode flip**) | `policy.py:170→100` | **LIVE — fires every call**, overrides mode/max_weight/target_vol/rebal from the Apr-23 learned file | Reachable but inert (no rec source) |
| mean_variance optimizer branch (`Σw=1`, clip 0.30) | `:184-252` | **DEAD** (0 live calls in probe) | **LIVE** (the canonical allocator) |
| adaptive inverse-vol branch | `:254-292` | **LIVE** (61/61) | dead (only via `<5-rows` fallthrough, below) |
| `_apply_vol_target` overlay (`vol_target_enabled: true`) | `:295` | **LIVE every bar** — and it *levers up* (replays: gross ×1.35–1.44 at target_vol 0.15; live path uses overridden 0.10) | dead |
| `_apply_exposure_cap` overlay (`exposure_cap_enabled: true`) | `:299` | **LIVE every bar** | dead |
| `len(returns_df) < 5` fallthrough (`:204 pass` → adaptive+overlays) | `:204` | n/a (already adaptive) | real but degenerate-only (full trailing frames make it unreachable in practice; 0 unambiguous occurrences in probe) |
| `parrondo_fixed` | `:175` | dead | dead |
| Dynamic optimization (T-139, `dynamic_optimization_enabled: false`) | `portfolio_engine.py:430` — applies AFTER allocate | dormant-by-flag, **mode-independent** | dormant-by-flag, mode-independent |
| Position buffering (T-148, `position_buffering_enabled: false`) | `portfolio_engine.py:439` | dormant-by-flag, mode-independent | dormant-by-flag, mode-independent |
| HRP/turnover (`portfolio_optimizer` block) | Engine A `signal_processor` (method `weighted_sum` default) | dormant (method default) | dormant |
| Governor auto-apply of allocation recs | `governor.py:698` → writes **`config/portfolio_policy.json`** | **DEAD WIRE** — the loader reads `portfolio_settings.json` (`mode_controller.py:523`); `portfolio_policy.json` is never read by anything. (`auto_apply_allocation` default False anyway.) | same |

Probe counters (live window): `allocate=61, optimize=0 live (9 total − 9 from my replays), vol_target_overlay=61 live, exposure_cap_overlay=61 live, mode_flips=1` (call 1 entry-mode mean_variance→adaptive; calls 2–61 enter already-adaptive since the override persists on the policy instance until reset-and-reapplied each call). Honest note: my "fallthrough" counter (1) is the call-1 override event, not a `<5-rows` fallthrough — the two are indistinguishable to the counter; the `<5-rows` path needs frames shorter than 5 rows, which the controller never supplies after warmup.

## 2. The cancellation quantification (both modes, real captured inputs, deterministic replays ×2)

Uniform ×0.5 on all signal strengths, 3 real capture points, 27 names each:

| Mode | gross(S) vs gross(0.5S) | max abs weight diff | Verdict |
|---|---|---|---|
| **adaptive** (the LIVE local path) | 1.4395 vs 1.4395 / 1.3980 vs 1.3980 / 1.3515 vs 1.3515 | **0.000000** | **EXACT algebraic cancellation** — `(iv/Σiv)` is scale-invariant; the dev's claim 1 confirmed end-to-end. (Gross >1 here = `_apply_vol_target` levering up in the replays — the April "2× leverage in disguise" mechanism, observed live.) |
| **mean_variance** (the cloud canonical path) | **1.000000 vs 1.000000** (×3) | up to **0.1386** | **Gross-invariant but NOT allocation-invariant**: the `Σw=1` budget constraint pins total gross regardless of μ scale, but μ-vs-risk/cost trade-offs reshuffle relative weights by up to 14 weight-points. |

**Refinement of the dev's claim (and of my own T-116 §4a):** the scale-invariance is *exact* only in adaptive. In mean_variance the cancellation is of **gross** (by budget constraint), not of allocation — a uniform de-gross signal cannot de-gross, but it is not a pure no-op; it rotates the book. Either way, **the de-grossing INTENT of any uniform signal-level multiplier is architecturally cancelled in both allocators** — confirming and sharpening the T-122 washout mechanism and T-116 §4a.

## 3. The April-verdicts re-dating

Timeline (git): config `mode: mean_variance` since 2026-01-27 (`cb61f4f`); overlay flags added 2026-04-24 (`19add81`, the measurement commit); the rec file written 2026-04-23.

- **"Advisory exposure cap contributes +Sharpe (0.98→0.817 when disabled)" (2026-04-24): STANDS for the path it measured, with a substrate qualifier.** It ran adaptive (the Apr-23 override was already live), so it measured the genuinely-live local `_apply_exposure_cap`. It does NOT transfer to the cloud canonical substrate, where that overlay is dead and the live exposure-cap mechanism is **Engine B's** `suggested_exposure_cap` gross gate (`risk_engine.py:1191`) — a different code path. The standing record conflates these two same-named mechanisms (the brief's option (b)) — the April claim is about Engine C's overlay; today's canonical defense is Engine B's gate.
- **"Vol targeting = always-2× leverage in disguise" (2026-04-24): STANDS, mechanism directly re-observed** — my adaptive replays show `_apply_vol_target` multiplying gross ×1.35–1.44 (target_vol/realized ratcheting up in calm tape; same family as the T-153 finding that σ-dividers lever up). Live locally on every bar; dead on cloud canonical.
- **Bonus re-dating:** any LOCAL measurement dated **before 2026-04-23** ran true mean_variance; anything after runs adaptive. April-era results straddle an allocator change that nobody recorded.

## 4. De-grossing levers inventory (the fork input)

| Lever | Engine | Reachable TODAY (canonical/cloud) | Reachable locally | Evidence status |
|---|---|---|---|---|
| `suggested_exposure_cap` → gross gate | B (`:1191`) | **LIVE** | LIVE | T-100/T-116-mapped; min()-ceiling semantics |
| `suggested_max_positions` count cap | B (`:763`) | **LIVE** | LIVE | T-100; count×size co-fire flagged in T-116 |
| `advisory_risk_scalar` → Path A mult | B (T-116 flag) | dormant (default-OFF) | dormant | canon-proven inert; A/B pending |
| Drawdown kill-switch → Path A | B (T-111 flags) | dormant | dormant | canon-proven; A/B pending |
| **HMM transition overlay → Path A mult** | B (T-118 flag) | dormant (campaign holds for T-140) | dormant | canon-proven; THE pre-registered experiment |
| σ-floor / YZ vol-target estimator | B (T-153 flags) | dormant | dormant | canon-proven; A/B queued post-T-140 |
| Engine C `_apply_exposure_cap` | C | **DEAD** (mode=mv returns first) | LIVE every bar | April +Sharpe claim attaches HERE (local only) |
| Engine C `_apply_vol_target` | C | **DEAD** | LIVE every bar — **levers UP, not down** | April 2×-leverage claim attaches here |
| Uniform signal-level de-gross (any engine upstream) | A/E→C | **CANCELLED** (gross pinned by Σw=1) | **CANCELLED** (exact, sum-norm) | T-122 washout + this probe; do not build de-gross as a signal multiplier |
| Engine A stressed/crisis `risk_scalar` brake (`signal_processor:549`) | A | cancelled (uniform-shrink washout) | cancelled | T-116 §4a, now empirically backed |
| Regime-override `target_volatility`/`max_weight` | C (`:138`) | inert (no rec file) | LIVE (0.10/0.15 since Apr-23) | nobody pre-registered this |

**Punchline:** on the canonical substrate where all deployment evidence lives, **the only live de-grossing levers are Engine B's two advisory caps — everything in Engine C is either dead (mode), cancelled (normalization), or dormant (flags)** — and every proposed new de-gross correctly targets Engine B's Path-A `target_notional` (T-111/T-116/T-118), *after* the allocator, which is the only placement the cancellation cannot wash out. The T-118 overlay design is retroactively validated by this map.

## 5. Recommendations (propose-first; no changes made)

1. **Resolve the allocator divergence deliberately** (director decision): either (a) delete/retire the Apr-23 rec file (Archive, never delete) so local == cloud == mean_variance, or (b) commit the recommendation into config intent. Until then, every local exploratory number carries an invisible allocator override from a 2026-04-23 learned artifact whose own metrics say `_global` Sharpe 0.396.
2. **Guard `mode` out of the override safe-keys** (1-line propose-first): letting a learned artifact silently flip the allocator violates the "no silent prod behavior change" discipline (silent-mismatch family).
3. Retire/redirect the governor auto-apply dead wire (`portfolio_policy.json`).
4. Add the `PortfolioPolicyConfig` unknown-key warning (T-088 parity — it currently silently drops).

## 6. Proofs & files
- Canon guard post-work: 2022 cell canon `0145c03a6496d9d823bc8e50b0635ec2` (== baseline; my probe/script work perturbed nothing). Probe replays deterministic ×2 each.
- **NEW (this branch):** `scripts/probe_engine_c_reachability_t158.py`, this audit. Engine files untouched. Artifacts in `data/research/t158_reachability/` (gitignored).
