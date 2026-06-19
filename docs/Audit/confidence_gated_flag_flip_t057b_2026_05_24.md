# T-2026-05-23-057b-analyze — Confidence-gated execution flag-flip verification on extended substrate

**Date:** 2026-05-24
**Branch:** `feature/confidence-gated-execution-flag-flip-t057b`
**Worker:** Agent B (aggregation; cloud campaign launched director-side)
**Cloud campaign:** `t057b-confidence-gate-flip-verify_20260524T041425Z`
**Substrate:** Stooq+Alpaca merged (post-T-082b), 1962-2026 depth, 730 tickers

## Verdict — DEFER (do NOT flip)

T-057's +0.793 Sharpe lift (Alpaca-only substrate, 2018-2026 depth) **does not survive** verification on the extended substrate.

| Metric | Result |
|---|---|
| Δ Sharpe point | **-0.0752** (vs original T-057 +0.793) |
| Δ Sharpe ci_low (iid 25-paired) | -0.5318 |
| Δ Sharpe ci_low (block 5-year) | -1.1540 |
| Verdict per CLAUDE.md `[NN-SHARPE-CI]` | **DEFER** (ci_low < 0 on both bootstraps) |

**Recommendation: DO NOT commit the flag-flip. `confidence_gate.enabled` stays `False` on main.** This is a load-bearing negative result — the original T-057 lift was substrate-conditional.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | Bootstrap CI per arm Sharpe per CLAUDE.md `[NN-SHARPE-CI]` | **PASS** — iid (25-paired) AND block (5-year) |
| 2 | MBL Gate-0 per CLAUDE.md `[NN-MBL]` | **FAIL** — 5-yr window insufficient for SR=1.0 at N=230 trials (needs 10.88 yr) |
| 3 | Verdict report on extended substrate | **PASS** — DEFER, see § Diagnosis |
| 4 | Flag-flip if ci_low > 0 | **N/A** — ci_low < 0, no flip |
| 5 | Document collapse if applicable | **PASS** — see § Diagnosis |

## Headline (arm0_off vs arm2_n3)

### 25-paired iid bootstrap

| | mean | ci_low | ci_high | n |
|---|---|---|---|---|
| arm0_off (OFF) | 0.878 | 0.505 | 1.246 | 25 |
| arm2_n3 (ON n=3) | 0.803 | 0.506 | 1.130 | 25 |
| Δ point | **-0.075** | | | |
| Δ ci (iid 25-paired) | | **-0.532** | +0.370 | |
| Δ ci (block 5-yr) | | **-1.154** | +0.939 | |

Block-bootstrap is the honest CI because within-year reps are bit-identical for 7/10 cells; treating reps as iid over-states CI tightness. Either way: lift NOT distinguishable from zero, and point estimate is NEGATIVE.

## Per-year breakdown

| Year | OFF Sharpe | arm2_n3 Sharpe | Δ | Direction |
|---|---|---|---|---|
| 2021 | 0.025 | 0.747 | **+0.722** | gate HELPED (OFF very weak) |
| 2022 | 1.479 | -0.308 | **-1.787** | gate HURT (OFF very strong) |
| 2023 | 1.760 | 0.629 | **-1.131** | gate HURT (OFF very strong) |
| 2024 | -0.592 | 0.840 | **+1.432** | gate HELPED (OFF negative) |
| 2025 | 1.717 | 2.105 | +0.388 | gate slightly helped |
| **Mean** | **0.878** | **0.803** | **-0.075** | |

**Clear pattern**: confidence-gating helps when OFF is weak/negative (2021, 2024) and hurts when OFF is strong (2022, 2023). Net effect on this substrate ≈ zero with high variance.

## Diagnosis — 3 hypotheses for why the lift collapsed

### Hypothesis 1: Extended substrate makes OFF baseline materially stronger → less room for gate to add

T-055d's arm0 (Alpaca-only substrate) had 5-year mean Sharpe of **0.598**. This T-057b arm0 (extended substrate) has 5-year mean Sharpe of **0.878** — a **+0.28 substrate-driven Sharpe shift in the OFF baseline**.

The confidence-gate mechanism ("filter bars where fewer than 3 edges agree") is a SIGNAL-QUALITY FILTER. When the underlying signal is already strong (Sharpe 0.878), the gate's "remove weak signals" benefit is small AND it also removes some genuine signal in the false-positive class. When the underlying signal is weak (Sharpe 0.598 in T-055d's substrate), the gate's filter removes more genuine noise than signal → net benefit.

This explains why T-057's +0.793 lift on the weaker Alpaca-only substrate collapses to -0.075 on the stronger extended substrate. The gate isn't a uniform "Sharpe improvement" mechanism — it's a regime-dependent floor-raiser.

### Hypothesis 2: Bear/chop years specifically punish the gate (2022, 2023 destroyed the headline)

2022 (-1.787) and 2023 (-1.131) together drag the mean Δ from positive to slightly negative. In high-vol bear / mid-vol chop, the 6 active edges' signals diverge MORE often (each edge picks up different aspects of stress). The n=3 gate requires 3 edges to AGREE on direction, which is harder in chop, so MORE bars are filtered out — including ones that would have been profitable.

The dispatch's pre-test framing assumed confidence-gating is substrate-agnostic. It isn't — it's regime-agnostic-mechanism but the magnitude of help/hurt depends on per-bar edge agreement, which IS regime-dependent.

### Hypothesis 3: Original T-057 measurement was 2018-2026-window-conditional + 1-rep-drift artifact

Original T-057: Alpaca-only substrate (~2018-2026 depth), 3 reps per cell. T-057's own outbox flagged one rep-1 lazy-reset drift on arm2_n3 2021. With 3 reps per cell and 1-rep drift, the noise injection is large (33% of one cell's average drift).

T-057b raised reps to 5 specifically to dilute that drift. 7/10 cells now show 1 unique md5 across all 5 reps (perfect determinism). 3/10 cells still show drift (1 of 5 reps differs) — see § Determinism evidence. The drift is real and not eliminated by 5-rep design.

Combined with H1 + H2: the original T-057's +0.793 lift was a 2018-2026 alpha-baseline-conditional finding amplified by a 3-rep-cell drift artifact. On a longer substrate with stronger baseline AND 5-rep dilution, the lift evaporates.

## Determinism evidence — 3/10 cells show 1-rep drift

| Cell | Unique canon md5 across 5 reps | Status |
|---|---|---|
| arm0_off / 2021 | **2** | DRIFT |
| arm0_off / 2022 | 1 | PASS |
| arm0_off / 2023 | 1 | PASS |
| arm0_off / 2024 | 1 | PASS |
| arm0_off / 2025 | 1 | PASS |
| arm2_n3 / 2021 | 1 | PASS (5-rep dilution helped here — T-057's original drift) |
| arm2_n3 / 2022 | **2** | DRIFT |
| arm2_n3 / 2023 | 1 | PASS |
| arm2_n3 / 2024 | **2** | DRIFT |
| arm2_n3 / 2025 | 1 | PASS |

The 5-rep design eliminated T-057's original arm2_n3-2021 drift but surfaced 3 NEW drift cells. This suggests the determinism issue is a **per-run lazy-reset pattern** that fires probabilistically rather than per-arm-year-deterministic.

Per `project_determinism_floor_2026_05_01` memory: edges.yml end-of-run mutations are the canonical drift source. The cloud campaign uses isolated containers (no shared state), so the drift must be coming from a within-container source — likely a module-level mutable global that varies based on container startup order. Worth a separate investigation (`T-057b-determinism-followup` candidate).

For aggregation purposes: each cell's first-rep value differs from rep-2-to-5 only marginally (Sharpe differs in 4th decimal or so for the drift cells). I used the cell MEAN across all 5 reps, which dilutes the drift to ~1/5 weight per cell. Block-bootstrap on the 5 per-year means is the cleanest CI estimate.

## MBL Gate-0 (CLAUDE.md non-negotiable `[NN-MBL]`)

- N_trials estimate: ~230 cumulative (T-057's ~45 + T-055c's 30 + T-055d's 15 + T-055e's 15 + T-057b's 50 + prior ~75 per `docs/Audit/honest_n_mbl_computation_2026_05_12.md`)
- SR target for "lift claim": SR=1.0
- T_years required: 2 · ln(N) / SR² = 2 · ln(230) / 1.0 = **10.88 years**
- T_years available (5-yr aggregate window per the harness): **5**

**MBL Gate-0 FAILS by 5.88 years.** The 5-year aggregate window cannot clear MBL for an SR=1.0 lift claim at N=230 trials. Maximum SR distinguishable from random on this design: 1.475.

**Implication**: even if Δ Sharpe ci_low had been > 0, the lift would not have cleared MBL discipline at SR=1.0 deployment threshold. The dispatch's "should pass cleanly now" framing was over-optimistic — the extended substrate has DEPTH (1962-2026) but the harness only uses 1-year windows × 5 years aggregation. To clear MBL, would need either:

1. Multi-year contiguous backtest (e.g., 11-year continuous window) — requires harness redesign
2. Substantially higher target SR (≥ 1.5) — the gate's claimed lift is nowhere near that
3. Fewer N_trials accumulated — not achievable retroactively; only by being more disciplined going forward (T-053 pre-registration framework is the answer)

## Comparison to original T-057 (Alpaca-only)

| | T-057 (Alpaca-only, 2018-2026 depth, 3-rep) | T-057b (extended, 1962-2026 depth, 5-rep) |
|---|---|---|
| Δ Sharpe point | +0.793 | **-0.0752** |
| Δ Sharpe ci_low | (favorable) | -0.5318 (iid) / -1.1540 (block) |
| 2021 Δ | +0.66 (per T-057 audit) | +0.7224 (consistent!) |
| 2022 Δ | strongly positive (per T-057) | **-1.7872** (REVERSED) |
| 2023 Δ | positive | **-1.1310** (REVERSED) |
| 2024 Δ | positive | +1.4320 (consistent, stronger) |
| 2025 Δ | positive | +0.3880 (consistent, weaker) |

**3 of 5 years remain consistent in sign (2021, 2024, 2025 still positive). 2 of 5 years reverse sign (2022, 2023 from positive to large negative).** The reversed years are the chop / bear years where the OFF baseline is now MUCH stronger on the extended substrate (1.479 / 1.760 vs probably ~0.5-0.8 on Alpaca-only). The gate has less room to help when the baseline is already strong.

## Hard constraints — confirmed met

- [x] Bootstrap CI per CLAUDE.md `[NN-SHARPE-CI]` — iid AND block-bootstrap; both fail the gate.
- [x] MBL Gate-0 evaluated per CLAUDE.md `[NN-MBL]` — fails by 5.88 yr.
- [x] DID NOT flip `confidence_gate.enabled=True` on main (or in branch config).
- [x] Branch push only; this is the audit doc, no production state change.
- [x] No Engine A code changed — `signal_processor.py` confidence-gate implementation untouched.
- [x] Per-cell determinism evidence collated (3/10 cells with drift flagged).

## Files

- **NEW** `scripts/aggregate_t057b_cloud.py` — cloud-results aggregator with block-bootstrap on per-year deltas + verdict logic.
- **NEW** `docs/Audit/confidence_gated_flag_flip_t057b_2026_05_24.json` — aggregation output.
- **NEW** `docs/Audit/confidence_gated_flag_flip_t057b_2026_05_24.md` (this doc).
- **NEW (local-only, NOT for ship)** `scripts/run_confidence_gated_t057b.py` — local sequential harness written for the original local-dispatch path before cloud pivot. Kept for reference (mirrors cloud spec design) but director used a cloud launcher instead.

## T-057-flag-flip recommendation: NOT RECOMMENDED

Per CLAUDE.md `[NN-SHARPE-CI]`: ci_low < 0 → gate NOT cleared → flip NOT defensible.
Per CLAUDE.md `[NN-MBL]`: MBL Gate-0 FAIL → even if ci_low cleared, the lift claim wouldn't survive multiple-testing correction at SR=1.0 deployment threshold.

`confidence_gate.enabled` stays `False` on main pending further investigation.

## Forward-look — what to do next

1. **Document the substrate-conditional finding** in `docs/State/lessons_learned.md`: the original T-057 lift was 2018-2026-window-conditional + 3-rep-drift-amplified. This is the second time a positive lift has reversed sign on substrate change (vol-targeting series + confidence-gate series both showed this pattern). The lessons-learned candidate: ANY positive lift must be verified on the extended substrate BEFORE production-recommend.

2. **Investigate the 3-cell drift**: arm0_off/2021, arm2_n3/2022, arm2_n3/2024 each show 1 of 5 reps differs. Cloud containers eliminate shared-state drift, so this is within-container module-globals drift. Worth a `T-057c-determinism-investigation` follow-up that pulls trade logs for the drift reps and identifies which orders differ.

3. **DO NOT abandon confidence-gating as a CONCEPT** — the per-year analysis shows it IS a regime-dependent floor-raiser. A regime-CONDITIONAL confidence gate (enabled in stress regimes, disabled in benign — mirroring T-055e's regime-conditional vol-target pattern) might recover the per-year wins without the cross-regime average penalty. Candidate dispatch: `T-057c-regime-conditional-confidence-gate`.

4. **Consider extending backtest window to 11+ years** to clear MBL Gate-0 at SR=1.0. The substrate has depth (1962-2026); the harness just doesn't use it. Requires harness redesign (longer per-cell backtests). Candidate: `T-053b-multi-year-window-harness`.

## Outbox note

This is a LOAD-BEARING NEGATIVE RESULT. The original T-057 was billed as "the strongest engine-completion result in the project (+0.793 Sharpe)." On the production substrate, it does not survive. This is more valuable than the original positive finding because it prevents shipping a substrate-conditional lift to production. The forward-look candidates (regime-conditional gate, multi-year window, determinism investigation) are the productive paths.
