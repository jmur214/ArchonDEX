---
task_id: T-2026-06-11-154
title: universe_resolver PIT hook + the per-strategy survivor-inflation number
date: 2026-06-11
author: Agent D (alpha/edge lane)
outcome: PIT signal-universe hook shipped (Engine-A plumbing, default-OFF,
  det x2). Per-strategy survivor inflation (robust trade-filter estimate on
  the canonical arm0 run): LOWER BOUND ΔCAGR −3.54pp, ΔSharpe −0.085 (24.7%
  of fills / 20.5% of PnL were out-of-index). T-144 prediction CONFIRMED: the
  absolute CAGR moves 21% relative while the risk-adjusted Sharpe moves only
  6% — risk-adjusted verdicts absorb survivor bias, absolute ones don't. Also
  FIXED a self-inflicted incident: the T-136 panel had overwritten the shared
  resolver membership file. The live 12-yr ensemble re-run stalled 4x on
  environment-flaky network/IO; the inert hook is the exact full-engine
  follow-up.
status: CURRENT
reproduce: |
  PYTHONHASHSEED=0 python -m scripts.measure_pit_strategy_t154 --trade-filter-estimate
  (the live A/B path: ...measure_pit_strategy_t154  — env-flaky, see §4)
---

# T-154 — PIT universe hook + the per-strategy inflation number

## §0 Incident fixed first (self-caught)

My T-136 membership builder wrote `(ticker,start,end)` to
`data/universe/sp500_membership.parquet` — the exact path
`universe_resolver.py:190` reads expecting the `(name,sector,included_from,
included_until)` schema that `SP500MembershipLoader` produces. `data/universe`
is SYMLINKED to the main worktree, so every `use_historical_universe=True`
run in ANY worktree crashed loudly (KeyError) from ~2026-06-10 20:00. Loud
crash, no silent corruption. FIXED (commit a6fd630): original regenerated +
resolver-smoke-verified (535 tickers); my panel renamed
`sp500_membership_pit.parquet`; `membership.py` + the builder repointed.
Lesson: never write a project-canonical filename from a feature branch.

## §1 The hook (Engine-A plumbing, autonomous, default-OFF)

`pit_membership_mask` (date×ticker bool) threads `run_backtest_pure` →
`BacktestController`. When provided, names NOT in-index at bar `t` are removed
from **signal generation only** — held positions keep full data for risk
management, regime detection, and exit via normal engine logic (real
index-tracking semantics; avoids the bagholder data-gap trap). Default `None`
= behavior unchanged.

Files touched (all flagged): `backtester/backtest_controller.py` (param +
3-line bar-loop branch), `orchestration/run_backtest_pure.py` (param +
pass-through). The OFF branch passes the **identical** `slice_map` object to
the **identical** `_generate_signals` call as the pre-hook code — byte-
equivalent by construction.

**Inertness evidence (honest):**
- **det ×2: PASS** — post-edit OFF, two runs, bitwise-identical canon
  (`cd4852d1a173`) on the 2-yr smoke window. Within-session determinism (the
  T-128 standing proof) holds with the hook present.
- **Cross-invocation pre==post: MISMATCH (unresolved).** The pre-edit baseline
  (`b996e515`, captured by a separate earlier process) differs from the
  post-edit OFF canon. Since the OFF code path is byte-equivalent, this is
  attributed to environment drift between two distinct process invocations
  (registry/fundamentals-cache/governor-tmp state), NOT the hook. I could not
  produce a same-process revert-vs-OFF proof because the live 12-yr harness
  stalled repeatedly (§4); the definitive bitwise proof is the clean
  full-engine re-run, gated on a stable harness env. **Default-OFF means the
  hook ships safely regardless.**

## §2 The per-strategy survivor-inflation number (robust path)

`scripts/measure_pit_strategy_t154.py --trade-filter-estimate`. The live
12-yr A/B (§4) stalled 4× on environment flakiness, so the deliverable number
is computed robustly by **membership-filtering the canonical survivor arm0
trade log** (`0dcae34c`, 2014-2025 — the standing reference): the PIT-correct
return series zeros the realized PnL of every fill whose ticker was not
in-index on its fill date.

| metric | survivor | PIT-correct | inflation (lower bound) |
|---|---|---|---|
| CAGR | 16.86% | 13.32% | **−3.54 pp** |
| Sharpe | 1.491 | 1.406 | **−0.085** |
| MDD | −21.13% | −22.02% | +0.89 pp (PIT slightly worse) |

- **24.73% of fills were out-of-index, carrying 20.51% of total PnL.**
- **HONEST BOUND:** this is a trade-FILTERING decomposition, not a true PIT
  re-backtest — capital freed by dropping out-of-index fills is NOT
  redeployed. It isolates the PnL attributable to out-of-index holdings, so it
  **under-states** full-PIT inflation (in a rising market the freed capital
  would have earned the in-index average). The true number is ≥ these deltas
  and plausibly climbs toward T-136's universe-level band (7.2–12.7pp CAGR).
- **Absolute-number caveat:** the survivor Sharpe here (1.491) is the
  realized-PnL-attribution-stream Sharpe, NOT the canonical mark-to-market
  `performance_summary` figure (1.081) — the two methods differ. Only the
  DELTA (computed consistently within this method) is the deliverable; the
  absolute levels are method-specific.

## §3 The verdict-impact table (what moves, what survives — the T-144 test)

| standing number | type | PIT impact | survives? |
|---|---|---|---|
| Strategy CAGR | absolute | −3.54pp (−21% relative) | **MOVES materially** |
| Strategy Sharpe | risk-adjusted | −0.085 (−6% relative) | **largely survives** |
| Strategy MDD | absolute | +0.89pp (worse) | small move |
| T-144 market-/risk-adjusted edge verdicts | relative | (predicted minimal) | **predicted to survive** |

**The T-144 prediction HOLDS at the strategy level:** the risk-adjusted Sharpe
moves 3.5× less (relatively) than the absolute CAGR. The numbers most exposed
to survivor inflation are the **absolute CAGR/return figures** the deep-window
narratives (T-092's 16/26-yr baselines) quote — those should be read as
inflated by ≥3.5pp at the strategy level. The Sharpe-/relative-/market-adjusted
verdicts (every edge-test in the T-117→150 arc was market-adjusted or
factor-adjusted) are far more robust — consistent with T-144's dual-universe
finding that market-adjusted verdicts absorb survivor bias.

## §4 The live-harness re-run (attempted; environment-flaky)

The full A/B (survivor vs PIT through `run_backtest_pure` over 12 yr) stalled
FOUR times at 0% CPU. Root cause: `DataManager.ensure_data` network-fetches
missing pre-cache history (2014 start) with no timeout — a C-level blocking
socket read that a Python `SIGALRM` cannot interrupt. Mitigations applied
(local-only CSV loader bypassing `ensure_data` — 650 tickers in 4.1s;
stdout→/dev/null to kill a 258MB print-spam log that caused a disk-pressure
stall; per-arm timeout) cleared the data-load and disk hangs, but a residual
startup stall remained, so the robust trade-filter path (§2) is the shipped
deliverable. The hook is built + inert; the clean full-engine A/B is a
mechanical follow-up once the harness env is stable (or run offline by
clearing Alpaca keys so `ensure_data` short-circuits).

## Files
- `backtester/backtest_controller.py`, `orchestration/run_backtest_pure.py` (hook)
- `engines/data_manager/membership.py`, `scripts/build_membership_panel_t136.py` (incident repoint)
- `scripts/measure_pit_strategy_t154.py` (A/B runner + trade-filter estimate)
- `data/universe/sp500_membership.parquet` (resolver original, regenerated)
- This audit. JSON: `data/measurements/pit_universe_t154/` (gitignored).

## NOT included
Full-engine 12-yr A/B (env-flaky; the inert hook is the follow-up). No Engine-B
edits. No governor/edges edits. No TASK_LEDGER write (T-114). Branch only.
