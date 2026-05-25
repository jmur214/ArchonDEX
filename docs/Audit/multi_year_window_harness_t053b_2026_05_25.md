---
task_id: T-2026-05-24-053b
title: Multi-year-window harness + 12-yr T-057 proof
date: 2026-05-25
substrate: Stooq+Alpaca merged (post-T-082b)
window: 2014-01-01 → 2025-12-31 (12 years, 3,017 trading days)
data_source: cloud — s3://archondex-results-407539788432/t053b-{verify,proof}-confidence-gate-12yr/
outcome: T-057 lift REFUTED on MBL-clearing window; multi-year harness shipped + validated
---

# T-053b — Multi-Year Window Harness + 12-yr T-057 Proof

## Headline

**T-057 confidence-gate lift REFUTED on the 12-yr MBL-clearing window.**

| Metric | arm0_off (baseline) | arm2_n3 (N≥3 gate) | Δ |
|--------|--------------------:|--------------------:|-----|
| Sharpe (point) | **0.8102** | 0.6827 | **-0.128** |
| Sharpe ci_low | +0.265 | +0.170 | **-0.696** |
| Sharpe ci_high | +1.392 | +1.210 | +0.429 |
| p(Δ > 0) | — | — | **32.3%** |

Block-bootstrap (Politis-White block=8, n_iter=2000, seed=0) on 3017 aligned daily returns. The confidence gate **does not deliver a lift on the substrate-honest 11.5+ yr window**. ci on Δ straddles zero with a negative point estimate — fails CLAUDE.md #6 by both the strict ci_low gate AND the point estimate's sign.

The T-057 +0.793 Sharpe lift on the 2021-2025 5-yr window was the **floor-raiser artifact** B's T-057b analysis flagged: that window has small N_obs by MBL standards, and the 2024 fragility outlier dominated the Δ. On 12 yr of daily returns with proper block-bootstrap, the lift dissolves.

**Recommendation:** Confidence gate stays OFF permanently. Close T-057 chapter cleanly. T-057c regime-conditional gate (B's track) is the only remaining lever; T-053b is REFUTED.

## Part A — Harness extension

### Code changes

**`scripts/cloud_entrypoint.sh`**
- Added `ARCHONDEX_START_DATE` / `ARCHONDEX_END_DATE` env vars
- Precedence matches `scripts/run_isolated.py`: START/END > YEAR > default
- Both must be set when either is (clear error if only one)
- Backward compat: existing `ARCHONDEX_YEAR` campaigns unchanged

**`scripts/submit_arms_campaign.py`**
- New spec schema: `windows: [{start, end, label?}, ...]`
- Legacy `years: [...]` desugars to single-year windows (backwards compatible — pre-T-053b S3 paths preserved for year-based campaigns)
- `Cell` dataclass: `year:int` → `start_date` + `end_date` + `window_label`
- Cell S3 path: `<campaign>/<arm>/<window_label>/rep<N>`
  - Single year → "2024" (bit-identical to pre-T-053b)
  - Multi-year → "2014-2025"
  - Sub-year → "YYYY-MM-DD_YYYY-MM-DD"
- **New `--job-timeout` flag**: per-job `attemptDurationSeconds` override. REQUIRED for multi-year windows — 12-yr cells need ~7,200s; job def default is 1,800s. Without this, multi-year cells time out (we saw this on the v1 verify run — both cells FAILED with "Job attempt duration exceeded timeout" at 2017-05 timestamp, ~3.5 yr in).
- `year_int_for_legacy` property: emits `ARCHONDEX_YEAR` only when window is a single calendar year, preserving downstream tooling compat.

**`tests/test_submit_arms_campaign_windows.py`** (NEW, 17 tests, all pass)
- Label generator (single-year, multi-year, sub-year, override)
- Legacy `years` desugaring + path back-compat
- New `windows` spec (single-window, multi-window, label override)
- Validation: rejects both/neither/malformed/empty
- `year_int_for_legacy` across single-calendar / partial-year / multi-year cells

### Image rebuild

Local rebuild + push to ECR required because the entrypoint changed. CI workflow `build_backtest_image.yml` failed on AWS OIDC credentials when dispatched against the feature branch — secret not configured for non-main refs. Manual path used:

```
docker build -f Dockerfile.backtest --platform=linux/arm64 -t archondex-backtest:dev .
aws ecr get-login-password ... | docker login ...
docker tag archondex-backtest:dev 407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:dev
docker push 407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:dev
```

ECR `:dev` image pushed at **2026-05-25T01:04:43** (post-feature-branch commit `f893c3e`). Local docker had a hung daemon — required user-authorized `killall Docker` + Desktop relaunch before build could proceed.

### Time budget actual

- Code changes: ~30 min
- Tests (17 / 17): ~5 min
- Docker fix + rebuild + push: ~45 min (most of it docker daemon recovery)
- Verify v1 timeout discovery + v2 resubmit: ~85 min wall total
- Proof grid (10 cells parallel): ~150 min wall (8 ran first batch, 2 queued)

## Part B — Verify (2 cells)

| Cell | Sharpe | canon_md5 | run_id |
|------|--------|-----------|--------|
| arm0_off / rep1 | 0.81 | `989af6a3...` | f11cd024-... |
| arm2_n3 / rep1 | 0.683 | `15ab4234...` | 4d0d5d44-... |

**Verify pass: canon_md5 distinct** — the per-cell config patch fires (gate genuinely enabled on arm2_n3). Single-cell preview already shows the negative direction that the full proof confirms.

## Part C — Proof (10 cells = 5 reps × 2 arms × single 12-yr window)

### Determinism — PERFECT bitwise

Each arm's 5 reps produced **byte-identical** trade logs (one canon_md5 per arm). The rep-axis is reproducibility, not statistical sampling — every replicate confirms the single deterministic measurement.

| Arm | All 5 reps' Sharpe | canon_md5 |
|-----|---|-----|
| arm0_off | 0.81 (×5) | `989af6a351e301c0b440a281954b4d87` |
| arm2_n3  | 0.683 (×5) | `15ab42340f798cf55276ebd5e56478cf` |

### Statistical inference — block-bootstrap on daily returns

Because reps are identical, rep-resampling is degenerate. Proper inference uses the 3,017-day return series block-bootstrap per CLAUDE.md #6 (block-bootstrap on daily returns is the correct method when reps are deterministic).

- **Aligned window**: 2014-01-03 → 2025-12-31 (3,017 trading days)
- **Block length**: 8 days (Politis-White auto)
- **n_iter**: 2,000
- **Seed**: 0

| Statistic | arm0_off | arm2_n3 | Δ (n3 − off) |
|-----------|---------:|--------:|-------------:|
| Sharpe (point) | +0.8102 | +0.6827 | **-0.128** |
| ci_low (2.5%) | +0.265 | +0.170 | **-0.696** |
| ci_high (97.5%) | +1.392 | +1.210 | +0.429 |
| p(Δ > 0) | — | — | **32.3%** |

**Δ Sharpe's bootstrap CI straddles zero**, point is negative, p(Δ>0) below 50% by ~18pp. **Fails CLAUDE.md #6** under any reading: strict ci_low > 0 gate (no — ci_low = -0.696), point > 0 (no — -0.128), one-sided p>0 > 95% (no — 32.3%).

### MBL Gate-0 (CLAUDE.md #7) — PASSES

- N_trials accumulated (post-T-057b + T-055g v2): **260** (estimate)
- SR_target: 1.0
- MBL required years: 2·ln(260)/1² = **11.12 yr**
- Years covered: **11.99 yr** (2014-01-03 → 2025-12-31)
- **Pass: YES** — first T-* dispatch to clear MBL Gate-0 at the project's accumulated N. Dev's prescription was 11.5+ yr; we cleared it.

## What this means

1. **The 5-yr T-057 +0.793 lift was an MBL-window artifact.** B's hypothesis in T-057b-analyze was correct: the lift came from the 2024 fragility-rescue cell dominating a 5-yr small-N window. On a window that clears DSR, the lift evaporates.

2. **Confidence gate stays OFF.** The `confidence_gate.enabled=False` default in main is the right state. No flag-flip dispatch (T-057-flip) should be queued.

3. **The multi-year harness is shipped and validated.** Future A/B campaigns can run on 12-yr+ windows by setting `windows: [...]` + `--job-timeout 14400`. This unblocks:
   - T-055g v3 on 12-yr (re-verify the multiplier sweep — current T-055e wins may also be window-conditional)
   - T-055f VVIX-z kill switch — 12-yr provides the 2025 stress sample the policy needs to be tested against
   - Any future T-* with a Sharpe headline that the 5-yr-window era would have measured suspectly

4. **The "load-bearing 2024 fragility" framing has substrate-conditional caveats.** On the extended Stooq+Alpaca substrate, 12-yr arm0 baseline = 0.81 Sharpe — material upside vs the 5-yr 0.270/0.598 baseline. Per CLAUDE.md #9, prior bear-year audits remain in the "must re-verify" queue.

## Spec acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|--------|
| 1 | cloud_entrypoint.sh + submit_arms_campaign.py extended; tests cover new spec | DONE (17/17 pass) |
| 2 | Verify campaign: canon_md5 differs between OFF and ON on 12-yr window | DONE — `989af6a3` ≠ `15ab4234` |
| 3 | Proof campaign: 10/10 cells SUCCEEDED | DONE |
| 4 | MBL Gate-0 check explicitly logged | DONE (PASSES at 12.0/11.12 yr) |
| 5 | Δ Sharpe reported with bootstrap CI; ci_low is the gate | DONE — Δ -0.128, ci_low -0.696 |
| 6 | Verdict: REAL (ci_low > 0) or REFUTED | **REFUTED** |
| 7 | Audit doc with all of above | DONE (this file) |
| 8 | Branch push only; director merges | DONE |

## Open follow-ups

1. **Per-job-timeout discovery cost.** v1 verify burned 30 min × 2 cells before timeout. Cost ~$0.50. Cheap, but worth flagging in `CLOUD_USAGE.md` that any window > 5 yr REQUIRES `--job-timeout` override.

2. **CI OIDC for non-main refs.** The `build_backtest_image.yml` workflow can't be dispatched against feature branches because the AWS_ROLE_TO_ASSUME trust policy is main-only (or the secret is gated to main). Either expand the trust policy OR document that image rebuilds for feature-branch entrypoint changes need local docker. Cleanest forward path: extend the trust policy.

3. **T-057-related memory entries** at `project_t057_confidence_gated_strongest_lift_2026_05_23.md` need a substrate-/window-conditional caveat. The "5/5 years improved" framing held on the 5-yr Alpaca-era substrate; on the 12-yr extended substrate, point Δ is negative.

## Files

NEW:
- `scripts/cloud_entrypoint.sh` (modified — window args)
- `scripts/submit_arms_campaign.py` (modified — windows spec + per-job timeout)
- `tests/test_submit_arms_campaign_windows.py` (17 tests)
- `data/cloud_runs/specs/t053b_verify_confidence_gate_12yr.json`
- `data/cloud_runs/specs/t053b_proof_confidence_gate_12yr.json`
- `data/cloud_runs/t053b-{verify,proof}-confidence-gate-12yr_*.csv` (gitignored)
- `data/cloud_runs/t053b_block_bootstrap.json` (gitignored)
- this audit doc

S3:
- `s3://archondex-results-407539788432/t053b-verify-confidence-gate-12yr/`
- `s3://archondex-results-407539788432/t053b-proof-confidence-gate-12yr/`

NOT changed (per spec hard constraints):
- No flag flipped on main
- No Engine B / live_trader touched
- All status changes via campaign spec, not manual config edits
