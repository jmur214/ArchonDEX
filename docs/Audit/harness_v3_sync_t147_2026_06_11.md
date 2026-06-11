---
task_id: T-2026-06-11-147
title: Crisis-replay harness → ADDENDUM v3 sync + concurrent-suite flake isolation
date: 2026-06-11
substrate: n/a (constants transcription + test isolation; fixture-only; zero N_trials; zero campaign-artifact contact)
scope: scripts/crisis_replay_t118b.py constants/tests (Part A — pure transcription of the FINAL v3) + two test files (Part B — real isolation, no skips/retries)
outcome: **Both parts delivered.** (A) Harness == v3 exactly: 7 enumerated actionable episodes (+2010 Apr→Jul, +2025 Feb→Apr), splits 4 in-sample / 3 OOS, ALL-3-OOS clause, sign ≥6/7, median over 7, everything else standing; 26 fixture tests green incl. the NEW 2-of-3-OOS regression (sign passes at its 6/7 boundary, only the OOS clause fails ⇒ FAIL, not PARTIAL — the clause demonstrably bites alone); real-data pinning reproduces v3's stated figures (2010 −16.1%, 2025 −18.8%). (B) Two tests properly isolated — the pairs-registration test read the LIVE data/governor/edges.yml (anchor-restore/lifecycle-write races), and test_collector_integration called yf.download() LIVE in the test body (network-flaky, masquerading as concurrency). **Reproduction proof: full suite during a concurrent run_isolated cell = exactly the known pre-existing 5 failures, zero flakes, 2223 passed**; the concurrent cell itself stayed canonical (5d88e1a0).
---

# T-147 — v3 sync + flake isolation

## Part A — harness → ADDENDUM v3 (transcription, no interpretation)

The transcription diff, in full (everything else untouched):

| Constant / structure | v2 (was) | v3 (now) |
|---|---|---|
| `LOCKED_EPISODES` actionable | 5: {GFC, 2011, 2018Q4, COVID, 2022} | **7**: + `us2010` (2010-04→2010-07) + `y2025` (2025-02→2025-04); dotcom unchanged (disclosed-blind, never gated) |
| Splits | in-sample {GFC, 2011, 2018Q4} / OOS {COVID, 2022} | in-sample {GFC, **2010**, 2011, 2018Q4} / OOS {COVID, 2022, **2025**} |
| OOS criterion | `oos_both_improve` (2 of 2) | `oos_all_improve` (**3 of 3**, each ΔMaxDD > +0.5pp) |
| `SIGN_REQUIRED/SIGN_N` | 4/5 | **6/7** |
| Median | over 5 | over **7** |
| GFC floor, calm-drag, terminal-wealth, 3× ratio, single-episode, primary-config, PARTIAL/FAIL logic | — | unchanged (v3: "ALL STAND") |
| Docstring | v2 criteria | v3 criteria + v3 §4 finality note (derivation disputes → run BOTH readings, report both, never edit) |

Month-anchored day-pinning (the T-143 procedure v3 adopted) verified on
real data (Stooq SPY TR-proxy): all 7 actionable pin cleanly — 2010
−16.1% and 2025 −18.8% match v3's stated figures exactly; dotcom
remains uncoverable locally (series floor 2005-02; flagged in T-143 —
the ^SP500TR caching decision still pending). The divergence checker
now reports against the v3 enumeration: `alltime_high` matches 5/8
(missing dotcom/2010/2011, extras 0 — 2025 now matched), `local_peak`
7/8 (missing dotcom, extras 3 = the GFC/2022 spell-splits) — reported,
never patched, per v3 §4.

### The new regression: 2-of-3-OOS must NOT pass

`TestScenarioTwoOfThreeOOS`: every episode treated EXCEPT 2025 (one OOS
left identical to the OFF arm ⇒ ΔMaxDD ≈ 0). Asserts: sign test passes
AT ITS 6/7 BOUNDARY, median/GFC/calm/terminal/ratio/single all pass,
ONLY `oos_all_improve` fails ⇒ **verdict FAIL** (co-equal v3 criterion
is structural — must not escape to PARTIAL). Same spirit as the v1-hole
regression: the clause demonstrably bites alone. 26/26 fixture tests
green (PARTIAL scenario updated to treat all three OOS so its only
failure remains the trigger-tunable sign test; pinning/derivation/
sensitivity counts updated to 7/8).

## Part B — the concurrent-suite flake (diagnose + real isolation)

### Diagnosis — what actually shares mutable state with a live run_isolated

| Test | Shared state | Failure mode | Action |
|---|---|---|---|
| `test_pairs_trading_edges::test_all_pairs_register_at_paused_feature` | **live `data/governor/edges.yml`** (module import-side-effect `EdgeRegistry().ensure()` + default-path registry read) | run_isolated's anchor restore rewrites edges.yml between runs; the backtest's end-of-run lifecycle/tier writes can stomp status/tier; mid-write reads | **FIXED** — test now exercises the same `_load_survivor_specs` → `_build_pair_spec` → `ensure()` mechanism against a `tmp_path` registry, plus a fresh-instance re-read proving the YAML round-trip. Zero shared state. |
| `test_collector_integration::test_collector_normalization` | **the network** — `yf.download()` live in the test body | yfinance rate-limit/outage ⇒ empty frames ⇒ zero scores; masqueraded as a concurrency flake (it also violates the project's yfinance-contamination discipline) | **FIXED** — deterministic synthetic OHLCV bars (250 bars, seeded); + a new determinism companion test. |
| `test_validate_candidate_v2` ×2 | live `data/governor/edges.yml` + `data/processed` (reads both at module scope) | shared-state-dependent by construction — but fails PERSISTENTLY on quiet systems too (pre-existing on main since ≥2026-06-10) | **NOT fixed here** (pre-existing failure, not a concurrency flake; named for the standing triage dispatch — its live-registry dependency makes it BOTH broken AND concurrency-fragile) |
| `test_cockpit_metrics_alignment`, `test_discovery_gate1_caching`, `test_oos_validation_isolation_default` | tmp dirs / script source (no live mutable state) | persistent pre-existing failures, NOT concurrency | triage dispatch (unchanged) |

No serial/isolation markers were needed — both flaking tests' contracts
are fully expressible against isolated state.

### Reproduction proof

The reproduction case (full pytest suite while a `run_isolated --runs 1
--year 2024` cell runs concurrently, same worktree):

- Before fixes (2026-06-10/11): 7–8 failures (known-5 + pairs and/or
  collector + transient extras whose names the first run didn't
  capture).
- **After fixes: exactly the known pre-existing 5, zero concurrency
  flakes, 2223 passed.** The concurrent cell completed normally and
  stayed canonical (`trades_canon_md5 5d88e1a0…`).

Caveat stated honestly: the first 8-failure run included 2 uncaptured
names beyond the collector test; they did not reproduce in the
post-fix concurrent run. If a rare-timing flake survives in some other
shared-state test, this proof's timing didn't hit it — the two
identified root causes are closed, and the diagnosis table above is the
map for any future appearance.

## Files

- `scripts/crisis_replay_t118b.py` — v3 constants/criterion/docstring (transcription only)
- `tests/test_crisis_replay_t143.py` — v3 fixtures + `TestScenarioTwoOfThreeOOS`
- `tests/test_pairs_trading_edges.py` — tmp_path registry isolation
- `tests/test_collector_integration.py` — synthetic bars replace live yfinance
- this audit

## NOT done

- The 5 pre-existing failures (standing triage dispatch; validate_candidate's live-registry read belongs in it)
- ^SP500TR caching (still the director's substrate decision, pre-relaunch)
- Any registration edit (v3 is FINAL; this task transcribed)
