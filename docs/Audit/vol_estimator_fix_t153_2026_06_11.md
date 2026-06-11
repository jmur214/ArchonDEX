# T-153 — Engine B vol-estimator collapse fixes: σ-floor guard + Yang-Zhang option (PROPOSE-FIRST)

**Date:** 2026-06-11
**Agent:** C (worktree `trading_machine-agent-c`, branch `feature/vol-estimator-fix-t153`, off origin/main `a027a7a`)
**Status:** PROPOSE-FIRST. Risk assessment + two default-inert fixes + canon/determinism proofs + pre-registered enable-A/B spec (**NOT run**). No prod-default change; no enables.
**Evidence base:** D's T-150 (`docs/Audit/intraday_features_t150_2026_06_11.md`) — YZ beats the production-spec EWMA(0.94) at next-day vol forecasting (SPA p=0.013–0.024, ci_low>0 both targets, 60–97% of names) AND the EWMA has a structural collapse-to-near-zero state on quiet stretches.

---

## 1. The risk assessment (the headline number)

Script: `scripts/assess_vol_collapse_t153.py` (deterministic, pure replay; artifact `data/research/t153_assessment/assessment.json`). Two sweeps:

### 1a. Portfolio-level — canonical 26-yr arm0 equity history (T-118 pre-flight, canon `529e5520`)

Replaying BOTH `vol_target.py` estimators bar-by-bar exactly as `compute_portfolio_vol_scale` would (production params: target 10%, floor 0.5, ceiling 2.0, warmup 60):

| | EWMA(0.94) | rolling-60 |
|---|---|---|
| live bars | 6,478 | 6,478 |
| **near-zero σ bars (<2% ann)** | **928 (14.3%)**, 7 episodes | **918 (14.2%)**, 4 episodes |
| deep-collapse bars (<0.5% ann) | 534 | 584 |
| min σ observed | **3e-06** (passes the `<=0` guard) | 0.0 (guarded) |
| ceiling-pinned bars (2.0× requested) | 1,448 | 1,396 |
| …of which off a near-zero σ | **928 (100% of near-zero)** | 918 |
| max over-lever vs sanity-floored σ | **1.574×** | 1.574× |

**Headline:** *IF the vol-targeter were enabled, BOTH production estimators request the 2.0× ceiling off a garbage (<2% annualized) σ on ~14% of canonical 26-yr bars — up to 1.57× more leverage than a sanity-floored estimate, concentrated in 4–7 multi-month episodes (the early sparse-trading years' near-flat-equity stretches).* The collapse is therefore NOT EWMA-specific at the portfolio level — the rolling default has the same consumer-side hole, which is why Fix A floors at the consumer.

### 1b. Per-name — full processed substrate (696 names) vs D's YZ panel

Same EWMA recursion per name (pandas `ewm(alpha=1−λ, adjust=False)` on r², σ²₀=r²₀ — identical math): near-zero state on **394 bars across 5 sparse/halted names (0.0094% of 4.2M bars)** — rare, but where it happens, on the 355 bars with a YZ match the **median YZ/EWMA σ ratio is 6,533× (p90 331,689×)**; YZ reads ≥5% sane vol on 196 of them. This is D's QLIKE-explosion mechanism counted directly: the estimator is wrong by 3–5 orders of magnitude in the collapse state, and a range-based estimator cannot enter it (daily ranges are never all-zero).

### 1c. Honest today-risk framing

The on-main production defaults are `portfolio_vol_target_enabled=False` **and** `estimator_type="rolling"` — the collapse risk is **conditional on two flag-flips** (the T-055 enable + the T-055d EWMA opt-in). Nothing is over-levering in production *today*. The defect is in shipped, armed-by-config code in the live sizing path, on the exact knobs every vol-target A/B (T-055 family) exercises — and the `min σ = 3e-06` finding shows the existing `<= 0` guard family does NOT protect it. This is the estimator-level instance of the CLAUDE.md std-tolerance non-negotiable.

---

## 2. Fix A — σ-floor guard (consumer-side; protects ALL estimators)

`vol_target.py`: new `apply_vol_floor(realized_vol, cfg, history)` applied after estimator dispatch, before the `target/σ` divide.

- Config (all default-inert): `vol_floor_enabled: bool = False`, `vol_floor_annual: float = 0.02`, `vol_floor_full_sample_frac: float = 0.0`.
- Effective floor = `max(vol_floor_annual, frac × full-sample σ(history))` — the relative component (recommended arm: frac=0.5) is stateless + causal (computed from the same history at call time) and adapts to the book's own vol scale.
- **Never invents an estimate**: `None` (estimator unavailable) stays `None` → 1.0 no-op. The floor only catches *collapsed-but-positive* σ — exactly the `3e-06` hole.
- RiskConfig keys: `portfolio_vol_target_floor_enabled` / `_floor_annual` / `_floor_full_sample_frac`.

## 3. Fix B — `estimator_type="yang_zhang"` (D's T-150 winner; collapse-immune)

- New module `engines/engine_b_risk/yz_vol.py` — the YZ math **ported verbatim** from D's `scripts/build_ohlc_features_t150.py::_features_one` (r_on/r_id decomposition, `k = 0.34/(1.34+(W+1)/(W−1))`, `var_on + k·var_oc + (1−k)·RS`, ×252), **including the mandatory T-135 corrupt-opens snap-back repair** (open := prev close when |r_on|>25% ∧ |r_id|>25% ∧ opposite signs) on every call.
- Selected via the **existing** `portfolio_vol_target_estimator_type` key (the T-055d mechanism) — default stays `"rolling"`.
- **Portfolio aggregation semantics (stated honestly):** gross-weighted average of per-name YZ vols over open positions — ignores correlations, hence an **upper bound** on portfolio vol → conservative leverage requests. Correct bias for an over-levering defect; whether it costs Sharpe is an A/B question (§5).
- **Data plumbing without canon risk:** YZ needs OHLC, which `compute_portfolio_vol_scale` never had. Threading `price_data` into `prepare_order` is NOT canon-inert (the sector-check block at `risk_engine.py:~1297` reads it when present). Instead, `manage_positions` — which already receives `data_map` every bar — caches the reference (`self._last_data_map`), and the vol-scalar passes it through. A reference assignment with no reader on the default path; zero behavioral change until `yang_zhang` is selected. Missing data → `None` → 1.0 no-op (live path degrades gracefully).
- New RiskConfig key: `portfolio_vol_target_yz_window_days: int = 21`.

## 4. Proofs

- **Canon-bitwise default path:** pre-change baseline re-measured on current main (`a027a7a`): 2022 cell canon `0145c03a6496d9d823bc8e50b0635ec2`, Sharpe 0.464. Post-change `--runs 2`: [see §4-result below].
- **Unit tests:** `tests/test_vol_estimator_fix_t153.py` — **12/12**, including the load-bearing collapse fixture (30 normal + 250 quiet days → EWMA σ ~1e-4 annualized, tiny-but-positive, ceiling-pinned without the guard; relative floor restores a sane request), floor-never-invents, default-passthrough equality, YZ-sane-on-flat-close/live-range tape, corrupt-opens repair exactness, gross-weighted aggregation + all fail-safes, unknown-estimator fallback.
- **Regression:** 58 passed (vol-target + contract suites), 1 known xfail, 0 regressions. New config keys pass the T-090/T-091 contract suite (Layer-1 key⊆dataclass).

### §4-result (filled after the run)
Post-change `--runs 2` on default config: canon `0145c03a6496d9d823bc8e50b0635ec2` ×2, Sharpe range 0.0000 — **bitwise-identical to the pre-change baseline; T-099 floor preserved.**

---

## 5. Pre-registered enable-A/B spec (NOT run — queued for the post-T-140 batch)

**Hypothesis (H1):** with vol-targeting enabled, a collapse-protected estimator (floored rolling / floored EWMA / YZ) does not degrade Sharpe vs the unprotected estimator and reduces the ceiling-pinned-off-garbage-σ bar count to ~0; YZ additionally improves realized risk-targeting accuracy (per T-150's forecast superiority).
**H0:** no ci_low-resolvable Sharpe difference; the floor only matters in states the backtest never monetizes.

| Arm | Config patch (all on `config/risk_settings.prod.json`) |
|---|---|
| arm0_off | `{}` (vol-target OFF — production baseline) |
| arm1_rolling | `portfolio_vol_target_enabled=true` (rolling, no floor — the T-055h arm re-run on the fixed substrate) |
| arm2_rolling_floor | arm1 + `portfolio_vol_target_floor_enabled=true, _floor_annual=0.02, _floor_full_sample_frac=0.5` |
| arm3_ewma_floor | arm2 + `portfolio_vol_target_estimator_type="ewma"` |
| arm4_yang_zhang | arm1 + `portfolio_vol_target_estimator_type="yang_zhang"` |

Windows: **12yr (2014-01-01→2025-12-31) + 26yr (2000-01-01→2025-12-31)** = 10 cells. Decision: block-bootstrap **ci_low on the Sharpe DIFFERENCE** vs arm1 (and vs arm0 for the enable question), plus per-cell counts of near-zero-σ bars and ceiling-pinned-off-garbage bars (from snapshots replay) as the mechanism check. N_trials += 5 configs. **Gated on the post-T-140 deterministic substrate + fresh anchors** (cross-task incomparability makes any earlier run unreadable — same reason the T-118 campaign holds). Joins the director's pre-registration batch; do NOT run before the substrate fix lands.

---

## 6. Acceptance checklist

- [x] Risk-assessment headline (over-lever frequency × magnitude on canonical history) — §1
- [x] Guard option (Fix A) + YZ estimator option (Fix B), both default-inert
- [x] Canon-bitwise default + det ×2 + collapse-case tests (12/12)
- [x] Pre-registered A/B spec (not run) for the post-T-140 batch — §5
- [x] This audit doc + proposed ledger row in OUTBOX
- [x] NO enables; NO prod-default change; branch pushed NOT merged

## 7. Files
- **MOD** `engines/engine_b_risk/vol_target.py` — `apply_vol_floor` + `_full_sample_sigma_ann` + 4 config fields + `yang_zhang` dispatch branch (+2 optional kwargs, default None).
- **NEW** `engines/engine_b_risk/yz_vol.py` — ported YZ + corrupt-opens repair + gross-weighted portfolio aggregation.
- **MOD** `engines/engine_b_risk/risk_engine.py` — 4 RiskConfig keys + `_last_data_map` cache (manage_positions) + pass-through in `_compute_portfolio_vol_scalar`.
- **NEW** `scripts/assess_vol_collapse_t153.py` + artifact `data/research/t153_assessment/assessment.json` (gitignored data).
- **NEW** `tests/test_vol_estimator_fix_t153.py` (12 tests).
