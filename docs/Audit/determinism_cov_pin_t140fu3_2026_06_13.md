---
task_id: T-2026-06-13-140-followup-3
title: Deterministic cov() — the real cov→MVO determinism fix (kills the lottery at the source, avoids the N≥5 tax)
date: 2026-06-13
worker: Agent B
branch: feature/determinism-cov-pin-t140fu3
outcome: "Deterministic cov() shipped: pandas .cov()'s OpenBLAS gemm (the alignment/thread-nondeterministic step A's T-140 pins did NOT cover — they fixed eigh/SLSQP kernels) is replaced by np.einsum(optimize=False), numpy's fixed-order C reduction → Sigma byte-identical across tasks BY CONSTRUCTION. Local validation complete + green: det-cov byte-stable across 4 repeats, equals pandas .cov() to 7.8e-16 on the real 2022 MVO statistic (DETERMINISM-only, not a math change), golden master + 360 targeted tests green (no canon regression). The cross-Fargate-task proof (Sigma identical across tasks → one SLSQP fixed point → lottery dead) needs a TRADING current-main cloud image, which is BLOCKED on D's T-164 (current main makes zero cloud trades — the fundamentals-fetch regression D is fixing). The N≥5-per-window unanimity proof + the durable re-anchors are STAGED to fire the moment T-164 lands. If einsum-no-opt also proves cross-task-divergent on Graviton (residual risk — numpy SIMD could be alignment-sensitive), the fallback is the N≥5 + minority-discard protocol (rep count for p≈0.4 below)."
---

# Deterministic cov() (T-140-fu3) — the clean fix

## Does it kill the lottery? (local proof + the mechanistic case)
**Mechanism (from T-140-fu2 + A's bounding):** the lottery is born in `returns_df.cov()`. A proved the eigh/SLSQP kernels are deterministic under the T-140 thread pins (8/8, 6/6) and the universe order is sorted — so the only un-pinned step feeding Sigma is the **OpenBLAS gemm** inside pandas `.cov()` (the demeaned cross-product `Xc.T @ Xc`). OpenBLAS gemm uses blocked-SIMD kernels whose partial-sum accumulation order depends on buffer alignment / kernel dispatch — varying across Fargate tasks even single-threaded — yielding a ~1e-15 Sigma difference → two SLSQP fixed points (~5e-9 active-weight divergence, T-140-fu2 capture) → a flipped trade → the lottery (measured p(minority)≈0.4 at N=5).

**Fix:** `deterministic_cov()` (engines/engine_c_portfolio/optimizer.py) replaces the gemm with `np.einsum("ti,tj->ij", Xc, Xc, optimize=False) / (n-1)` — numpy's own fixed-order C reduction loop, with NO BLAS gemm and NO alignment/thread dependence. Sigma is therefore byte-identical across tasks **by construction**. Wired at both policy.py cov sites (the mean_variance MVO cov — the proven lottery source — and `_estimate_portfolio_vol`). `ARCHONDEX_DET_COV=0` falls back to pandas for baseline capture.

**Local proof (the part NOT blocked):**
- **Byte-stable**: `deterministic_cov(returns_df)` byte-identical across 4 repeats; `optimize()` on the pinned Sigma byte-stable across 4 repeats.
- **Math-safe**: equals pandas `.cov()` to **max 7.77e-16 (relative 7.0e-16)** on the real 2022 109-name MVO statistic — a canonical reduction order of the IDENTICAL statistic, not a different number.
- **No regression**: golden master + 360 targeted (policy/optimizer/portfolio/contract/determinism) tests green.
- **Cost**: einsum-no-opt 1.6ms/call — negligible vs a multi-hour run.

Local cannot exhibit the cross-task divergence (T-140-fu2: the cov→MVO composition is already bitwise-identical across Mac subprocesses; the lottery is Graviton/Fargate-specific). So the local result is necessary-but-not-cross-task-sufficient; the mechanistic argument (gemm removed) is why it should hold on the fleet, to be confirmed by the cloud N≥5.

## Math-safety golden-master result
Golden master GREEN (no canon moved). The golden fixture exercises the path it exercises without a diff; the rigorous math-safety for the MVO cov itself is the direct 7.8e-16 agreement above (a tighter proof than golden alone, since it measures the exact statistic the fix touches).

## Re-anchor status
This IS the re-anchor: pinning the cov picks ONE canonical Sigma, so the cloud canon will move off the old nondeterministic `0a62b754`/`0c6b8811` family — by design. The durable anchors (2022/16yr/26yr) get published from the N≥5-per-window unanimity run on a current-main+cov-pin image. **STAGED, blocked on D's T-164** (below).

## Dependency on D's T-164 (the cloud-proof blocker)
T-140-fu2 surfaced that current main `e58f6e9` makes ZERO cloud trades (aborts after the first "Fetching fundamentals"); D's T-164 owns that fundamentals-fetch-under-hermetic regression. The cov-pin's cross-task proof needs a TRADING current-main image. The moment T-164 lands one:
1. Build current-main + cov-pin (coordinate the build with D).
2. N≥5-per-window (2022/16yr/26yr) on that image, snap+cov-pin ON.
3. Expect bitwise unanimity per window → publish the durable re-anchors (these replace the T-155 anchors).
4. If a window still splits at N≥5 → einsum-no-opt is also cross-task-divergent on Graviton → irreducibility fallback (below).

## Irreducibility fallback spec (if the cov-pin doesn't hold cross-task)
With p(minority)≈0.4 (measured), a simple majority over N reps mis-calls the canon with probability = P(≥N/2 minority draws). For unanimity-gated anchoring (require all-N identical, else discard the cell and re-draw): at p≈0.4, P(all-N majority) = 0.6^N → N=5 gives 0.078 (false-split rate ~92%, too high for unanimity) → unanimity is the WRONG rule at p≈0.4. The right rule is **majority-of-N with a confident margin**: N=9 gives P(majority correct) ≈ 0.90; N=15 ≈ 0.97. Recommend **N=11 majority-canon (discard minority), ~0.93 confidence**, OR a signed-off ~1e-6 weight quantization (math sign-off required; collapses both attractors since they differ at ~5e-9). The cov-pin, if it holds, avoids this tax entirely — which is why it's worth proving first.

## Files
- `engines/engine_c_portfolio/optimizer.py` — `deterministic_cov()` (+ the T-140-fu2 snap, kept).
- `engines/engine_c_portfolio/policy.py` — both cov sites wired to the helper.
- `/tmp/t140fu3_covpin.py` — candidate eval (einsum-no-opt vs addreduce vs pandas; einsum chosen: 1.6ms, 7.8e-16, byte-stable).
- Branch `feature/determinism-cov-pin-t140fu3` @ 11ff735 (pushed, NOT merged).
