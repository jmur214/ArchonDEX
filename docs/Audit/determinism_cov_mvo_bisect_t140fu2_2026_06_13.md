---
task_id: T-2026-06-13-140-followup-2
title: cov()→MVO determinism bisect — site NAMED (active-weight ~5e-9 divergence, not just zero-dust); snap fix shipped but likely INSUFFICIENT; P0 baseline regression found that blocks the proof
date: 2026-06-13
worker: Agent B
branch: feature/determinism-cov-mvo-bisect-t140fu2
outcome: "Site NAMED with per-task capture: the cov()→MVO output diverges across Fargate tasks in BOTH zero-weight dust (BKNG/META/PM: 0.0 vs ~1e-16) AND — the key refinement of A's bounding — the ACTIVE weights at ~5e-9 (MDLZ 0.113032495 vs 0.113032500; PANW 0.0199130439 vs 0.0199130450). Measured lottery at N=5 on the certified image: 3-vs-2 split (p(minority)≈0.4 this batch). Snap-|w|<1e-9→0 fix shipped (d0cdf6e, math-bitwise-safe) — it canonicalizes the zero-weight dust but does NOT touch the ~5e-9 active-weight divergence, so it is necessary-but-probably-INSUFFICIENT; the residue is two genuinely-different SLSQP fixed points born from a ~1e-15 Sigma (cov gemm) difference. PROOF (N≥5 snap-on unanimity) and RE-ANCHOR are BLOCKED by a separately-discovered P0: the current main HEAD (e58f6e9) cloud image produces ZERO TRADES (aborts immediately after the first 'Fetching fundamentals'); controlled A/B vs the known-good sha-5323a3c on the IDENTICAL substrate 553edca7 isolates it to a post-5323a3c merge (not Engine C, not this task's code). Recommend: director fixes/assigns the baseline regression, then a current-main+snap image gets the N≥5 proof + re-anchor; OR authorize cherry-picking the snap onto 5323a3c for an isolated fix-proof now."
---

# cov()→MVO determinism bisect (T-140-fu2)

## TL;DR
1. **Site NAMED** (per-task capture, not inference): the `cov()→MVO` output is where tasks first diverge — and it diverges in the **active weights at ~5e-9**, not merely as sub-ε dust on zero-weight names.
2. **Lottery measured**: N=5 on the certified image `sha-5323a3c` (2022) → **3× `0a62b754`/1.6, 2× `0c6b8811`/1.603 = a 3-vs-2 split.** p(minority)≈0.4 this batch — substantial. This is why T-155's "9/9" was a lucky draw (consistent with, not proof of, determinism).
3. **Fix shipped (`d0cdf6e`), math-safe, but likely INSUFFICIENT**: snap `|w|<1e-9→0` at the Engine-C optimizer output canonicalizes the zero-weight dust (proven math-bitwise-safe: golden master + 359 tests green; `optimize()` 5× bitwise-stable locally). But the captured divergence is in the **active** weights at ~5e-9 — above the snap threshold — so snap alone will probably NOT yield N≥5 unanimity. Honest lean: **irreducibility branch** (the cov gemm on Graviton is alignment-nondeterministic at ~1e-15, SLSQP amplifies it to ~5e-9 in the weights) → resolution is a math-changing quantization (director call) or the **N≥5-per-cell + minority-discard protocol**.
4. **PROOF + RE-ANCHOR BLOCKED by a P0 baseline regression** (separate from this task): current main `e58f6e9`'s cloud image makes **zero trades**.

## The named site — per-task evidence
N=5 on `sha-5323a3c` / 2022, first rebalance bar, `[POLICY] MVO Targets`:

| name | majority `0a62b754` (rep3-5) | minority `0c6b8811` (rep1-2) | class |
|---|---|---|---|
| ABBV | 0.2999999999999999 | 0.29999999999999993 | active, differs ~1 ULP |
| LIN | 0.3 | 0.29999999999999993 | active, differs ~1 ULP |
| **MDLZ** | **0.11303249565806645** | **0.11303250057502304** | **active, differs ~4.9e-9** |
| **PANW** | **0.019913043955624557** | **0.019913045042932842** | **active, differs ~1.1e-9** |
| BKNG | 0.0 | 3.7285218507000016e-17 | zero-name dust |
| META | 0.0 | 1.7562941571615038e-16 | zero-name dust |
| PM | 2.7309768456096386e-16 | 0.0 | zero-name dust |
| BSX | 3.727940267199233e-17 | 1.1421478900755554e-18 | zero-name dust |

**The divergence is the cov()→MVO OUTPUT.** A's bounding (eigh 8/8, SLSQP-on-fixed-QP 6/6, sorted universe) proved the kernels and inputs-order are deterministic; therefore the QP itself must differ across tasks — i.e. the `Sigma = returns_df.cov()*252` matrix differs at ~1e-15 (pandas/BLAS gemm reduction is memory-alignment-sensitive on Graviton, NOT covered by the T-140 thread pins which fixed eigh/SLSQP). SLSQP then converges to two slightly-different fixed points (~5e-9 in active weights), and the trade quantizer (whole-share / min-notional in order construction) tips on a name near a boundary → canon flips → the lottery.

**Refinement of A's characterization:** A reported "real weights agree to ~15 digits, only zero-names carry dust." At the first rebalance the active weights actually disagree at the **8th significant figure (~5e-9)** — so the lottery is NOT purely inactive-residue noise; it is a genuine divergence of the optimizer solution. This is the load-bearing distinction for the fix.

## The fix (shipped d0cdf6e) and why it's probably insufficient
`PortfolioOptimizer.optimize()` now snaps `|w| < ARCHONDEX_MVO_SNAP_EPS (default 1e-9) → 0.0`. Math-bitwise-safe: ε is 7 orders below the smallest economically-real weight (~1e-2) and 8 above the observed zero-dust; active weights are untouched (golden master + 359 targeted tests green; the standalone `optimize()` probe ran 5× bitwise-stable on Mac). An env-gated capture probe (`ARCHONDEX_COV_MVO_PROBE`) hashes returns_df/Sigma/mu/raw-weights for future bisects.

**But:** the captured active-weight divergence (~5e-9 on MDLZ/PANW) is ABOVE the 1e-9 snap threshold, so snap leaves it intact → the two attractors survive → canon likely still splits. Snap is **necessary** (a zero-name dust CAN flip a near-min-notional trade) but **not demonstrably sufficient**. Proving it requires N≥5 snap-on on a trading cloud image — which is blocked (below).

Resolution options (director decision; both exceed "determinism-only, no math change"):
- **(A) Quantize Sigma or weights** to a grid (~1e-6) below economic relevance but above the FP noise — collapses both attractors, but changes weight bits (violates the strict acceptance bar; needs sign-off as a deliberate math change).
- **(B) N≥5-per-cell + minority-canon discard protocol** — accept the cov gemm as irreducible hardware FP; every campaign runs arm0 (and each arm) at N≥5 and takes the majority canon. The launcher already carries the N≥5 arm0 anchor gate; this formalizes minority-discard.

My lean: **(B)** unless a cheap deterministic-cov (pinned-reduction `np.cov` replacement) proves out — that would be the true determinism-only fix and is the recommended follow-up to try before accepting irreducibility.

## P0 BLOCKER (separate finding — escalation)
Building the proof image surfaced a regression bigger than this task:

**The current main HEAD (`e58f6e9`) cloud image produces ZERO TRADES.** Every cell (10 capture + diagnostics, both hermetic modes) returned canon `d41d8cd9…` (md5 of empty) / Sharpe 0.0. The run aborts immediately after the first `DEBUG: <ticker> passed technicals... Fetching fundamentals...` → straight to "Closed logger / Completed run", zero bars.

Controlled isolation:
- **Known-good `sha-5323a3c`** (commit `5323a3c`) on the **identical** substrate `553edca7` → trades fine (the N=5 above, real `0a62b754`/`0c6b8811`).
- **`e58f6e9` LOCALLY** → trades fine (`0145c03a`/0.464, adaptive path).
- **`e58f6e9` cloud** → zero trades, aborts on fundamentals fetch. Hermetic ON and OFF both empty (not the hermetic gate).

→ The regression is in the **post-`5323a3c` merges**, cloud/mean_variance-path-specific, **NOT this task's Engine-C code** (which is downstream of signal generation; local e58f6e9 trades). Candidate culprits (touch signal/universe/fundamentals/allocator): **T-154** (PIT hook — its own audit notes it "overwritten the resolver's `sp500_membership.parquet`"), T-158/T-162 (allocator divergence work), T-159, T-128-CO.

**Blast radius:** blocks this task's fix-proof + re-anchor, **and C's T-118 overlay campaign + every cloud campaign built on current main.** Any fresh-main image is affected.

## Recommendations
1. **Director: triage the baseline regression as P0** (assign or point me at it). Prime suspect: T-154's `sp500_membership.parquet`/PIT change vs the `553edca7` substrate. Quick check: does a current-main cloud cell abort because the universe/fundamentals resolver reads a membership artifact that changed shape or is absent from `553edca7`?
2. Once main trades again: build a **current-main + snap** image, run N≥5 snap-off (reproduce split + capture) vs snap-on (test fix). If snap-on still splits (expected, given the ~5e-9 active divergence) → adopt option (A) quantization (with sign-off) or (B) the N≥5 protocol, and re-anchor.
3. **OR** authorize an isolated fix-proof now: cherry-pick the snap onto `5323a3c` (known-good trading source), build, run N≥5 — proves/refutes the fix on a working substrate without waiting on the baseline fix. (Given the captured ~5e-9 active divergence, I expect this to show snap-alone is insufficient → straight to the protocol decision.)

## Files / evidence
- `engines/engine_c_portfolio/optimizer.py`, `policy.py` — snap fix + capture probe (committed `d0cdf6e`).
- N=5 site cells: S3 `t140fu2site/2022/rep{1..5}/`; diagnostics: `t140fu2diag/`; capture attempt: `t140fu2/{snapoff,snapon}/2022/`.
- Local cov→MVO subprocess probe (`/tmp/t140fu2_probe.py`): 5× bitwise-identical on Mac → lottery is Graviton-specific.
- Image `sha-d0cdf6e` (arm64) in ECR; job def `archondex-backtest-t140fu2`.
