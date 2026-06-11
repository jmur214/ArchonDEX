---
task_id: T-2026-06-10-146
title: OPG/CLS auction execution — backtest-side fill modeling (+ live-side design only)
date: 2026-06-10
substrate: n/a (execution-convention wiring + cost ACCOUNTING on an existing book; no backtest measurement; zero N_trials)
scope: backtester/execution_simulator + config plumbing (autonomous); live_trader UNTOUCHED (design one-pager below)
outcome: **Delivered.** `auction_execution: off|moo|moc|moo_moc` (default off = legacy bitwise) in ExecutionSimulator; auction fills take the official auction print + adverse safety bps and skip the spread/impact model; fees path (SEC §31 + TAF via AlpacaFees) reused unchanged; intrabar stops stay slippage-priced in every mode. 36 unit tests green. OFF canon-bitwise vs fresh same-day baseline (`5d88e1a0…`, det 3/3) + ON smoke fires. **Headline: at the 2024 6-edge book's turnover (26× equity/yr, 76% mega / 24% mid bucket), auction execution is worth ≈$306/yr = 29.7 bps of equity/yr vs the PROD realistic slippage model (2.14 → 1.00 bps of turnover) — and ≈$2,418/yr = 235 bps/yr vs the legacy fixed-10bp convention.** The honest framing: the realistic model already prices mega-caps at ~1bp half-spread ≈ the auction safety margin, so the per-cost win is modest; the primary value is killing the live-vs-backtest fill-mechanism divergence class (blind-spots Q8.5) before it exists.
---

# T-146 — Auction execution (OPG/CLS)

## What was built (backtest side, autonomous scope)

`backtester/execution_simulator.py`:

- `ExecParams.auction_execution ∈ {off, moo, moc, moo_moc}` (default
  **off** — the legacy next-Open + slippage-model path runs bitwise) and
  `auction_safety_bps` (default 1.0).
- **moo**: every signal fill at the next bar's OPEN auction print.
  **moc**: every signal fill at the next bar's CLOSE auction print.
  **moo_moc**: entries (long/short) at the open auction, signal exits
  (exit/cover) at the close auction.
- **Price convention documented**: on US-equity daily bars the Open and
  Close columns ARE the official opening/closing auction prints
  (primary-listing official prices). Caveat stated in code: thin names
  can have small/crossed opening auctions where the print is less
  representative — our liquid large-cap universe at <0.001% ADV is the
  good case (the 2024 book is 76% mega- / 24% mid-bucket by notional,
  0% small).
- **Cost model**: no spread, no impact (a marketable auction order at
  our size receives the print); `auction_safety_bps` applied ADVERSELY
  per side (buys pay up — long/cover; sells receive less — short/exit)
  as the imbalance/thin-auction buffer; regulatory fees unchanged —
  the existing `AlpacaFees` (SEC §31 ≈0.278bp + FINRA TAF on sells,
  enabled in prod config) applies identically in auction and legacy
  modes (reused, not rebuilt).
- **Intrabar stop/take-profit fills are NOT auction orders** — they
  keep the legacy level+slippage path in every mode (tested).
- Missing-print fallbacks mirror `prefer_close_fallback` semantics
  (moo falls back to Close, moc to Open).
- Plumbing: `backtest_settings.json` top-level keys →
  `mode_controller.exec_params` → `BacktestController` →
  `ExecutionSimulator`. Invalid mode raises at construction.

Timing semantics note (documented, not hidden): `moo` is the
cost-honest match to the current convention (same price point, auction-
priced). `moc`/`moo_moc` move signal fills to the close auction —
that's a TIMING change (one extra day of drift on affected fills), not
just a cost change; any enable decision should treat mode choice as a
strategy-semantics decision, with `moo` the conservative default.

## Proofs

### OFF inertness (canon-bitwise + determinism)

Fresh same-day baseline on current main (3bdc0b7) vs post-change OFF,
2024 cell, `PYTHONHASHSEED=0 python -m scripts.run_isolated --runs 3
--year 2024`:

| State | Sharpe | trades canon md5 | Det |
|---|---:|---|---|
| Pre-change baseline (main 3bdc0b7) | 0.991 | `5d88e1a0f70f0cd052a7813a6e40b1a9` | 3/3 |
| Post-change, `auction_execution: off` | 0.991 | `5d88e1a0f70f0cd052a7813a6e40b1a9` | 3/3 |

(The hash equals the T-139-era baseline — the interim T-141/T-143/doc
merges were trade-inert, independently confirmed here.)

### ON fires (functional smoke) — and the wiring bug it caught

The FIRST ON smoke returned the baseline canon unchanged — the flag
never reached the simulator. Root cause: `mode_controller.run_backtest`
builds a **local** `exec_params` dict (line ~980) rather than using the
`self.exec_params` built in `__init__` (line ~536); the auction keys had
been added to the latter only. **The silent-mismatch family
(T-088/T-090) again: a config key read at one site but not the
consuming site.** The 36 unit tests could not catch this (they construct
the simulator directly); only the end-to-end canon smoke could. Fixed by
adding the keys to the consuming local dict with a sync-warning comment;
both proofs below are on final code.

`auction_execution: moo_moc` for one 2024 run, then reverted (config
diff vs HEAD zero afterward):

| State | Sharpe | trades canon md5 |
|---|---:|---|
| OFF (default, final code) | 0.991 | `5d88e1a0f70f0cd052a7813a6e40b1a9` |
| ON moo_moc (2024 cell) | 0.456 | `a85ebc8238dcbd16096baf8dce7a8f99` |

The convention changes fills end-to-end. **The large single-cell Sharpe
delta is dominated by `moo_moc`'s exit-TIMING change (signal exits move
from next-open to next-close — a full day of drift on every exit), not
by costs** — exactly the documented timing-semantics caveat, and why
`moo` (timing-identical, cost-honest) is the conservative enable
choice. Single-cell deltas are NOT performance evidence (zero N_trials
posture; any enable decision needs its own gate).

### Tests — 36 green (`tests/test_auction_execution_t146.py`)

OFF-mode fill dict identical to a pre-T-146-constructed simulator for
all four sides (the unit-level bitwise check); price selection per
mode×side (moo/moc/moo_moc routing matrix); no-slippage-model-applied
assertion; adverse safety arithmetic per side; SEC+TAF on sells / none
on buys (prod fee config), fee path identical on/off; missing-print
fallbacks both directions; **stop/TP fills identical across all four
modes**; invalid mode raises; repeat-fill determinism; `exit_position`
inherits the convention. Full suite: **2219 passed**, same 5
pre-existing-on-main failures as the morning runs (stash-verified),
zero new.

## The Δcost headline (accounting, not a backtest)

`python -m scripts.demo_auction_execution_t146 <run_dir>` — per-fill
re-pricing of the canonical 2024 6-edge book (run `93965dbf…`, the
fresh baseline) under both conventions, ADV-bucketed per fill from the
same daily bars the backtest used (prod `slippage_extra` parameters:
mega ≥$500M ADV → 1bp, mid ≥$100M → 5bp, small → 15bp, + Almgren-Chriss
`0.5·σ·√(qty/ADV)` impact). Auction re-pricing applies only to the
1,093 signal fills (entry/exit); 204 stop/TP fills are unaffected in
both worlds. Fees identical both sides, excluded from Δ.

| convention | cost $ (year) | bps of turnover |
|---|---:|---:|
| current (realistic model) | $571 | 2.14 |
| auction moo_moc (+1.0bp safety) | $267 | 1.00 |
| legacy fixed 10bp (scenario) | $2,670 | 10.00 |

**Δ vs prod realistic model: ≈$306/yr = 29.7 bps of equity/yr.**
**Δ vs legacy fixed-10bp: ≈$2,418/yr = 235 bps of equity/yr.**
(Turnover 26.1× equity/yr on $103K avg equity; eligible notional $2.67M.)

Honest reading: the realistic slippage model already prices our
mega-cap-dominated book near auction reality (1bp half-spread vs 1bp
auction safety — Δ≈0 on 76% of notional by construction). The cost win
concentrates in the mid bucket (5bp → 1bp on 24% of notional) and the
impact term. ~30bps/yr of equity is still real at a ~5.7%-CAGR
baseline (~5% of returns), and the convention's primary value is
structural: **the backtest now fills by the same mechanism the live
system will actually use**, pre-emptively closing a known
live-vs-backtest divergence class.

## Live-side design (ONE-PAGER — live_trader untouched, propose-first)

**Alpaca order mechanics.**
- MOO/LOO: `time_in_force="opg"`, submit before **9:28 ET** (orders
  after 9:28 are rejected for same-day OPG; queue next-day). MOC/LOC:
  `time_in_force="cls"`, submit before **3:50 ET** (NYSE cutoff; NASDAQ
  imbalance-only after 3:55). Order type `market` (MOO/MOC) or `limit`
  (LOO/LOC — a later refinement for thin names).
- **Whole-share constraint: auction orders (OPG/CLS) cannot be
  fractional.** This is exactly why T-139's dynamic optimization
  exists — the integer-position layer chooses the whole-share book, so
  every order the auction path submits is already integer. The two
  features are designed to enable together: dyn-opt produces integer
  deltas → OPG/CLS executes them at the auction print the backtest
  models. Enabling auction-live WITHOUT dyn-opt at small capital
  re-opens the naive-rounding tracking-error problem (T-139 fixture:
  2.87% annualized TE at $5K).
- **The constraint most likely to bite live: the 9:28 ET OPG cutoff.**
  The daily pipeline computes signals from the prior close; the order
  batch must be built, routed through pre-trade checks (risk caps,
  T-141 router/blackout, buying power), and submitted in the
  pre-market window WELL before 9:28 — a hard scheduling dependency the
  current loop doesn't have. A missed cutoff must degrade explicitly
  (skip-and-log or fall back to a regular market order at open — a
  DIFFERENT fill mechanism that must be tagged as such in the fill log,
  or live-vs-backtest attribution silently degrades again).
- **Order-state handling the live path needs**: OPG/CLS orders sit
  queued for hours → the order-state machine needs `accepted → queued →
  filled-at-auction | rejected | expired-unfilled` transitions, an
  explicit reconciliation pass after the auction print (compare fill vs
  expected auction price; alert on deviation > safety bps), and
  idempotent resubmission rules (never blind-retry an OPG after 9:28).
  Partial fills are not a concern for market-on-auction at our size,
  but rejected-for-fractional and rejected-after-cutoff are.
- **T-141 router implications**: the router decides WHICH ACCOUNT
  submits each sleeve's orders (taxable vs Roth). The auction batch
  builder must therefore be account-aware: two order batches, two
  Alpaca accounts, with the cross-account wash-sale blackout checker
  (T-141's `CrossAccountWashSaleChecker`) consulted pre-submission —
  a Roth buy inside the 31-day window after a taxable loss in the same
  ticker must be blocked/deferred, which can only happen at the batch
  layer (the per-account submitters can't see each other).

**What enabling requires (user-gated path).** (1) Backtest side: flip
`auction_execution` to `moo` (conservative, timing-identical) in
`backtest_settings.json` — one key; an A/B vs OFF under the standard
gate if the decision is performance-motivated (it shouldn't be — this
is a fidelity change; zero N_trials posture says enable on engineering
grounds when live uses auctions). (2) Live side: an Engine
B/live_trader proposal implementing the one-pager above — propose-first
per the hard rule, sequenced with the paper-trading milestone.

## Files

- `backtester/execution_simulator.py` — ExecParams + auction price/safety helpers + fill-path branch
- `backtester/backtest_controller.py`, `orchestration/mode_controller.py` — config plumbing
- `config/backtest_settings.json` — `auction_execution: "off"`, `auction_safety_bps: 1.0`
- `tests/test_auction_execution_t146.py` — NEW; 36 tests
- `scripts/demo_auction_execution_t146.py` — NEW; the Δcost accounting
- this audit

## NOT done (out of scope)

- Any live_trader code (design one-pager only; propose-first)
- Enabling any auction mode (default off; user-gated)
- LOO/LOC limit-priced auction variants (refinement noted for thin names)
- Paper-mode (`PaperTradeController`) plumbing — paper constructs its
  own simulator with defaults (off = unchanged); wiring paper to the
  convention belongs to the paper-trading milestone
