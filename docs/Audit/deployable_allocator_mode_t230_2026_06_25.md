# T-230 — DEPLOYABLE cash-account allocator mode (structural-soundness fix)

**Date:** 2026-06-25
**Agent:** C (branch `feature/deployable-allocator-mode-t230`). Default-OFF addition; canon byte-identical; director merges (no push from me — shared object store).

---

## The bug (D's T-215 diagnosis)
The −47% MaxDD headline is partly a **leverage artifact**: the `mean_variance` allocator runs the book to **~2.32× gross** (borrowing) and the dataclass permits **shorts** (`min_weight = −0.1`). A **$5–15K cash Roth cannot do any of that** — no margin, no borrow, no short. So the allocator models an **un-executable** strategy, which makes the headline numbers dishonest (they bank leverage the account can't use). An allocator with no gross budget cap that levers an un-leverageable account is a structural-soundness bug **independent of any deploy decision** ([NN-ARCHIVE]/[NN-FAIL-CLOSED] hygiene; not the deployable re-run, which is a separate ~30h cloud spend + director call).

**Confirmed on the local 2022 cell (default config):** the **executed book** runs to max `gross_notional/equity` = **2.19×**, **21.1%** of bars > 1.05× (D's full-cycle cell measured 2.32×) — the leverage is real. BUT the dispatch's hypothesized root cause (the allocator's per-name clamp lets weights "freely sum past 1") does **NOT hold on this universe** — see the FINDING below: the allocator target weights sum to ≤1.0; the leverage is a downstream cash-borrow. (The prod `portfolio_settings.json` already sets `min_weight: 0.0` → already long-only at the clamp.)

## The fix — `deployable_cash_account` mode (config-gated, DEFAULT-OFF)
A new `PortfolioPolicy._apply_deployable_constraints(weights)` PROJECTS the allocator's final weights onto the cone a cash Roth can execute, applied at BOTH optimizer return paths (`mean_variance` + `adaptive`):
1. **Long-only** — zero shorts (`w < 0 → 0`).
2. **Per-name** — clamp to `[0, deployable_max_weight]` (0.25).
3. **No leverage** — gross `Σw ≤ deployable_max_gross` (1.0); if over, scale all weights down (the residual `1 − Σw` is uninvested cash). Scaling-down preserves the per-name bound and the relative long proportions.

Gated by `deployable_cash_account` (default **False**) + `deployable_max_weight` (0.25) + `deployable_max_gross` (1.0) in `PortfolioPolicyConfig` + `config/portfolio_settings.json`. **OFF ⇒ the method returns the weights unchanged → the canon is byte-identical** (the same default-OFF-addition contract as the trend overlay / buffering). Parrondo_fixed (a user-set fixed-allocation niche mode, not an optimizer that levers) is intentionally not projected.

## ⚠ FINDING — the measured leverage is DOWNSTREAM of the allocator, not in its weights (the diagnosis layer was off)
The dispatch attributed the 2.32× to the allocator weights "freely summing past 1." On the **local 109-ticker 2022 cell that is NOT what happens** — I parsed all **250 per-bar `mean_variance` target-weight vectors** from the OFF run:
- **max gross Σ|w| = 1.00×, 0 bars with a short** (prod `min_weight: 0.0` ⇒ already long-only; the per-name clamp + the optimizer keep Σw ≤ 1).
Yet the **executed book** runs to **2.19× gross/equity** because **cash goes to −1.19× equity (BORROWING) on 25.1% of bars** (worst bar: positions $177.6K on $80.9K equity = borrow $96.7K). **So the leverage is a downstream EXECUTION/SIZING cash-borrow** (the book buys to target but the rebalance-threshold gates selling, so positions accumulate past 100% and cash goes negative) — **NOT the allocator's target weights.**

**Consequence:** the allocator-level cap I added (the dispatch's requested ~3-5-line change) is **correct and necessary** (a cash-Roth target should never exceed 100% invested; and on the full ~500-name PIT universe more names may hit the clamp and push Σw>1, which the cap then catches) — but it is **NOT SUFFICIENT** to make the book executable. The no-borrow / no-leverage guarantee must ALSO be enforced where the borrow actually happens: the **sizing/rebalance layer** (`portfolio_engine` target-notional + the order-sizing/rebalance path, possibly Engine-B-adjacent) — that is **propose-first** (see below), out of this dispatch's policy.py scope.

## Proofs
- **OFF-canon (load-bearing — D's verdict anchors to the base canon):** 2022 `trades_canon_md5 = 80b501a8ab16206d74bdfc09a7f245aa` == current/baseline — **byte-identical**. The mode OFF disturbs nothing.
- **ON-mode (allocator-target level, on the OFF run's REAL 250 per-bar weight vectors → projected):** Σw cap **ENFORCED** (any vector summing >1 → scaled to exactly 1.0; ≤1 untouched), **shorts → 0**. On the 109-ticker universe the target vectors were already ≤1.0/long-only so the cap is a no-op there — consistent with the finding that the book leverage is downstream. The local ON backtest could not measure the book gross/equity: it **DEADLOCKED** (T-165 in-process harness fragility — 0% CPU, state Ss, log frozen mid-backtest), same as the T-211 composition re-runs; the cloud cell is the only place to measure the de-levered book gross.
- **Tests:** `tests/test_deployable_allocator_t230.py` (8) — OFF no-op; ON zeros shorts / clamps per-name / caps gross at 1.0 / leaves an already-executable book untouched / preserves long proportions on de-lever / empty-safe / Layer-1 config-key contract. Full engine_c suite 370 green (incl. FP-determinism locks); doc_lint green.

## PROPOSE-FIRST (the real fix, not done — out of policy.py scope, possibly Engine-B-adjacent)
A **no-borrow cash budget at the sizing/rebalance layer**: cap the EXECUTED gross at `equity` (cash ≥ 0) — i.e. the rebalance must sell down to keep Σ|position·px| ≤ equity, not just buy to target while holding stale positions. This is where the 2.19×/−1.19%-cash leverage actually originates. It spans `portfolio_engine` target-notional + the order-sizing path → **propose-first** (cross-engine; the deployable mode's allocator cap is the necessary partner, but this is the binding piece). Recommend the director route this with B/T-212 (the risk-sizing levers in flight).

## Honest scope
This makes the allocator MODEL an executable target — it does NOT by itself make the executed book executable (the downstream borrow remains) and does NOT make the strategy good (the flat return, not the leverage, is the killer per D). Default-OFF, canon byte-identical, engine_c lane, no B/E/A crossing. The deployable re-run that re-measures a TRULY de-levered book must wait on the downstream no-borrow fix above.
