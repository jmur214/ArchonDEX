# T-2026-06-10-138 — Agent-code safety gate: golden master + property suite + forbidden-pattern lint (+ suite green-up)

**Date:** 2026-06-11
**Branch:** `feature/agent-code-safety-gate-t138`
**Worker:** Agent B
**Spec source:** `docs/Sources/Research_2026_06_10_blindspots/RESULTS_single_pass_no_research_mode.md` §AREA 1
**Status:** DONE — all parts shipped + verified; full suite **2,237 passed / 0 failed** (60 skipped, 3 xfailed); the sign-flip kill demonstration went RED exactly as designed.

## TL;DR

| Part | Deliverable | Verified |
|---|---|---|
| A — golden master | `tests/test_golden_master.py` + frozen `tests/golden/` fixtures: replay of the production-equivalent pipeline (`run_backtest_pure`) on a 12-ticker × 1-yr pinned-substrate window; 3-tier comparison (signals → trades → P&L vector, rtol=1e-9) + input-hash drift guard + shadow-diff summary + documented regen procedure | green ×3 consecutive runs (~15 s each) |
| A — kill demo | one-line sign flip in `momentum_12_1_v1` score → gate **RED**: "SIGNALS changed: 9 differing rows" + shadow-diff **ΔSharpe +1.164, Δtrades −269**; mutation reverted; gate green again | the headline scenario is caught, with a reviewer-readable report |
| B — property suite | `tests/test_invariants_property.py` (hypothesis): 6 invariants on REAL production units | **all pass on current main → no findings** |
| C — forbidden-pattern lint | `tests/test_forbidden_patterns.py`: 4 calibrated patterns over signal/feature/risk paths + justified allowlist + stale-allowlist self-check | green; 1 allowlisted entry (ML label construction) |
| D — suite green-up | 5 pre-existing failures fixed + 2 enrichment items (tmp_path registry; tests/ network sweep) | **full suite 2,237/0** |
| CI | gates appended to `.github/workflows/contract_tests.yml` (same job, cheapest-first) | YAML valid; ~1 s added on CI (golden auto-skips without data); ~16 s locally |

## Part A — golden master

**Fixture (frozen):** `TICKERS` = 12 liquid names + SPY; warmup 2019-06-01, run 2021-01-04 → 2021-12-31; `initial_capital` 100k; slippage 5 bps. Inputs come from the PINNED substrate (manifest `147e9d0e…`, T-127/T-131) and are additionally sha256-hashed by the test itself — **input drift fails loudly before any behavioral comparison** (and points at the substrate manifest if it ever fires).

**Edge set is registry-independent by design:** momentum_12_1 + rsi_bounce + short_term_reversal with pinned params/weights. The live registry is mutable governor state; a golden master that moved with edge lifecycle would conflate code drift with governance activity.

**Three comparison tiers, most-localized first** — signals at 3 sampled dates (value-based at rtol; dtype-tolerant), the full trade log (categoricals exact, numerics rtol), the daily P&L vector (rtol=1e-9). Each tier fails with a human-readable report: which dates, which symbols, what magnitude, how many rows.

**Shadow-backtest-diff tier:** every run prints `ΔSharpe / Δn_trades / Δturnover / Δmax-position` vs the stored summary — the dispatch's "nonzero diff must be justified in the PR" hook (director enforces at merge).

**Snapshot-update procedure (in the test docstring):** `ARCHONDEX_REGEN_GOLDEN=1 pytest tests/test_golden_master.py` → commit `tests/golden/` SEPARATELY with a justification → director merges. Never regen to silence a diff.

### The kill demonstration (acceptance criterion #1)

Mutation: `momentum_12_1_v1.py` line 114, `out[ticker] = long_score …` → `-long_score …` — the literal "single sign error introduced by an agent into a live signal."

Result: **RED.** `GOLDEN DIFF — SIGNALS changed: 9 differing signal rows`, and the shadow summary showed **ΔSharpe +1.164** (the mutation *improved* the fixture Sharpe — the exact reason "it looks better" can never be auto-accepted) and **Δtrades −269**. Mutation reverted (verified zero markers + clean git status); gate green again.

**Fixture-stability engineering worth recording:** two artifacts made the first verify-after-regen fail and were fixed: (1) CSV float round-trip perturbs the last ULP → snapshots are written `%.17g` and numeric columns compare at rtol while categorical columns compare exact; (2) `assert_frame_equal` dtype-checks false-positive on int-vs-float CSV reads → the signals tier is value-based. Neither artifact weakened the gate (the kill demo proves sensitivity at 1e-9 while ULP noise stays green).

## Part B — property suite (hypothesis 6.155.2 — NEW DEV DEPENDENCY, flagged)

All six properties target REAL production units, not synthetic stand-ins:

| Property | Production subject | Result |
|---|---|---|
| NO-LOOKAHEAD | the EXACT production slicer (`backtest_controller` `iloc[:idx+1]`) composed with real edges (momentum, rsi_bounce): future rows must not move signals at ≤ T | PASS |
| P&L CONSERVATION | `PortfolioEngine`: `equity == cash + Σ(qty·px)` in every snapshot under arbitrary fill streams | PASS |
| SIGN ANTISYMMETRY | mirror-image fill streams negate realized P&L exactly. *Spec deviation, documented:* the research spec's literal form (negate forecast → negate position) presumes linear sleeves; this codebase's signal path is gated/long-only-scored by design, so the antisymmetry invariant is asserted at the accounting layer where it genuinely holds | PASS |
| UNITS | `compute_realized_vol_from_history` invariant to the equity unit (cents/dollars/2×; binary factors compared EXACTLY) | PASS |
| SCALE INVARIANCE | 2× capital + 2× quantities ⇒ exactly 2× cash/MV/equity (binary doubling is FP-exact — no tolerance) | PASS |
| IDEMPOTENCY | identical fill streams into fresh engines ⇒ identical snapshot sequences | PASS |

**No findings on current main** — the accounting engine, the production slicer, and the vol estimator all hold their invariants. (Per the dispatch: a failure would have been reported as a finding, not "fixed" to pass.)

`hypothesis>=6.130` added to `requirements.txt` (dev/CI file) — **deliberately NOT in `requirements.lock.txt`**, so the cloud image is unchanged (no new package in the backtest container). New-dep rule: flagged in the outbox for director sign-off.

## Part C — forbidden-pattern lint

`tests/test_forbidden_patterns.py` — pytest-collectable (zero extra CI plumbing), scoped to `engine_a_alpha`, `engine_b_risk`, `engine_c_portfolio`, `engine_e_regime`, `core/feature_foundry` (NOT tests/scripts/research — lookahead is legitimate in validators and fixtures).

| Pattern | Hits at introduction | Disposition |
|---|---|---|
| `.shift(-` (future leak) | 1 | allowlisted: `ml_predictor.py` label construction (the future IS the training target) — justification inline |
| forward positional `iloc[ident + N]` | 0 | calibrated to exclude backward idioms (`iloc[-(lookback+1)]`, slice-ends `idx+1`) — zero false positives |
| wall-clock `now()/utcnow()` in signal code | 0 | tree was clean — invariant now locked |
| bare `fillna(` on return series | 0 | tree was clean — locked (weight-reindex fills excluded by pattern precision) |

Second test guards the allowlist itself: a stale entry (code moved/changed) fails until pruned — the allowlist can only ever be an exact, reviewed set.

## Part D — suite green-up (director-triaged 5 + enrichment)

1. **`SNAPSHOT_COLUMNS` desync — fixed, with a real find:** the keyed reindex in `cockpit/logger._append_to_csv` was **silently DROPPING `sleeve_equity`** (emitted by `snapshot()` since T-120 but never added to the column list) — sleeve campaigns were losing per-bar sleeve attribution from snapshot CSVs. Column added in writer-dict order; T-034 invariant test re-synced.
2. **Sweep lifecycle list** + `ga_population.yml` (lockstep with `ISOLATED_FILES`; the contract test enforces set-equality).
3. **Gate1 cache "non-invalidating fingerprint" — reclassified:** Gate-0 MBL correctly short-circuits the sub-year fixture BEFORE the caching block, so the fingerprint was never set (None != None). With the documented `enable_mbl_gate=False` escape hatch the mechanism is exercised — **and it is CORRECT** (fingerprint = window + edge-set; changes invalidate). The director triage's "real latent bug" was Gate-0 test-staleness, same family as #4-5.
4-5. **`test_falsifiable_spec_*`:** now assert the **Gate-0 refusal first** (`gate_0_passed is False`, no `contribution_sharpe` — no backtest may fire on a sub-MBL window, CLAUDE.md #7), then exercise the original gauntlet-correctness spec via the escape hatch. Product right; tests predated Gate-0.

**Enrichment (E's T-147):** (a) `test_validate_candidate_v2` now uses a **tmp_path snapshot of `edges.yml`** per test (live governor never opened — concurrency-stable, kills the live-state dependency); (b) tests/ network sweep found **one live `yfinance` call** (`test_earnings_vol_cached_dates_are_tz_naive` — "trigger the cache load via a real call") → converted to a synthetic tz-AWARE fake-Ticker via monkeypatch (the exact input shape of the 2026-05-08 regression; invariant unchanged, now deterministic). No other live network calls found.

## Acceptance

| Criterion | Status |
|---|---|
| Golden master green on main + RED on deliberate sign-flip (reverted) | DONE — green ×3; kill demo RED with readable report (9 signal rows, ΔSharpe +1.164, Δtrades −269); reverted + re-verified |
| Property suite green or findings reported | DONE — 6/6 PASS on main (no findings) |
| Forbidden-pattern lint wired with documented scope/allowlist | DONE — 4 patterns, 1 justified allowlist entry, stale-allowlist self-check |
| Snapshot-update procedure documented | DONE — test docstring + this audit |
| Suite fully green incl. the 2 stale tests asserting current behavior | DONE — **2,237 passed / 0 failed** (60 skipped, 3 xfailed) — exceeds the 2,129 target (suite grew) |
| Audit + ledger row in outbox | DONE |

## Hard constraints — confirmed

- [x] ADDITIVE only — zero engine-behavior changes (the one engine-adjacent edit, `SNAPSHOT_COLUMNS`, is CSV-schema only; canon untouched). The kill-demo mutation was reverted and verified gone.
- [x] Fixture from the pinned substrate; no new data.
- [x] No TASK_LEDGER write (row in outbox). Branch push only.
- [x] New dependency (hypothesis) flagged; NOT in the image lock file.

## CI wall-time added

- On GitHub CI: **~1 s** (lint 0.07 s + properties 0.65 s; golden auto-skips — no `data/processed` on the runner).
- Locally / data-enabled CI: **~16 s** (golden replay 15 s).

## Deferred (per dispatch)

- Mutation testing (mutmut/cosmic-ray) — weekly-scoped job, explicitly out of scope.
- OAP-style pre-action layer; pandera data contracts; mypy --strict tier — later phases of the stack.
- Golden master on a data-enabled CI runner (today it gates local suite runs; CI gains it the day substrate is available there, e.g. via the S3 snapshot).

## Files

- **NEW** `tests/test_golden_master.py`, `tests/golden/{golden_equity.csv,golden_trades.csv,golden_signals.csv,golden_input.sha256,golden_summary.txt}`
- **NEW** `tests/test_invariants_property.py`, `tests/test_forbidden_patterns.py`
- **MOD** `.github/workflows/contract_tests.yml` (gate steps + trigger paths), `requirements.txt` (hypothesis)
- **MOD (Part D)** `cockpit/logger.py`, `scripts/sweep_cap_recalibration.py`, `tests/test_cockpit_metrics_alignment.py`, `tests/test_discovery_gate1_caching.py`, `tests/test_validate_candidate_v2.py`, `tests/test_earnings_vol_tz_regression.py`
