# T-199 — signal_collector swallowed-crash: census-detectable + measured-HALT. The T-180 anchors STAND.

**Date:** 2026-06-17/18
**Agent:** C (branch `feature/signal-collector-swallow-census-t199`)
**Status:** DONE — propose-first (canon path). Blast-radius assessment is CLEAN → the T-180 anchors stand; the structural fix is in with a bitwise canon-invariance proof. Director re-verifies the diff + canon before merge.

---

## 0. The flag (D's T-197)
D's T-197 made the Discovery `gate1_signal_cache` distinguish a crashing edge from a legitimate no-signal, then found the **same swallow class in the SHARED PRODUCTION BACKTEST path** (`signal_collector`, the one that produced the T-180 anchors) and correctly did NOT touch it (canon-moving) — flagging it for this census/HALT lane.

## 1. The swallow, located + characterized
`engines/engine_a_alpha/signal_collector.py:collect()` has **two** swallow sites:
- **Outer except (≈line 390):** a non-programmer exception (KeyError / ValueError / IndexError / ZeroDivisionError / pandas errors — the **data-shaped** crash class) is caught; the edge contributes no signal on that bar; the loop continues. Programmer errors (TypeError/AttributeError/NameError/AssertionError/ImportError) already re-raise (the 2026-05-07 narrow-catch).
- **Inner dict-loc retry (≈line 261):** if the `'dict' object has no attribute 'loc'` retry also fails → `signals = None` (swallowed).

**Why `edges_blind` misses it:** the T-181 census flags an edge with **0** non-zero signals over the whole window. A **partial** crash — an edge that dies on *some* bars (a specific regime, a missing column on certain dates, a degenerate data shape) but fires on others — has `signal_counts > 0`, so it is NOT in `edges_blind` and the run reads census-canonical while silently degraded on the crash bars. This is the exact silent-fail-open disease (T-088/T-167/T-175/T-189), here in the canon path.

## 2. BLAST-RADIUS ASSESSMENT (the gate — run BEFORE any fix)
Instrumented the swallow to record every caught crash per edge (`_edge_errors`), emitted it as `census.edges_errored`, and re-ran **all three T-180 anchor windows locally** on the full **22-edge book** (6 active + 15 paused + news_sentiment — ≥ the 21-edge anchor book):

| window | bars | trades | `edges_errored` |
|---|---|---|---|
| 2022 | 250 | 450 | **{}** |
| 16yr (2010–25) | 4,023 | 11,472 | **{}** |
| 26yr (2000–25, dotcom+GFC+COVID) | 6,538 | 14,994 | **{}** |

**ZERO swallowed crashes on every anchor window → THE T-180 ANCHORS STAND.** The partial-crash gap was a **latent hazard, not an active corruption**. The swallow is data-deterministic (a crash is a function of edge code × data shape), so zero crashes locally over these exact windows ⇒ zero on the cloud anchor runs (same edges, same baked data). *Caveat:* the exact anchor image was `sha-fc5a69e` (21-edge book); this assessment ran the current branch's 22-edge book over the same windows/substrate — a superset, so the conclusion holds.

## 3. The structural fix (mirrors D's gate1)
- **Record** every swallowed crash at both sites — `_edge_errors{edge:count}` + `_edge_error_samples{edge:last_error}`. A genuine no-signal NEVER appears here → a swallowed crash is now **distinguishable** from a legitimate no-signal.
- **Emit** `census.edges_errored = {edge:{crash_bars,last_error}}` in `_build_census`.
- **Gate:** `assert_census` treats a non-empty `edges_errored` as **NON-CANONICAL** — and unlike `edges_blind` there is **NO allowlist** (a swallowed exception is never a legitimate no-signal; a partial crash → cannot publish/certify).
- **Measured-mode HALT:** the recorder routes through B's `core.measured.halt_or_degrade(site, load_bearing=True, active=True, reason=...)` (T-194) — in a measured run (cloud / anchor / hermetic-strict) a real crash in the canon path raises `MeasurementHalt` and fails LOUD at the load site; outside measured mode it records-and-continues (still census-visible at the publish gate). Imported at call-time so a clean run (never crashes → never calls it) is bit-for-bit unaffected.

## 4. Canon-invariance proof (the high bar for a canon-path change)
A clean run (no crashing edge) must be byte-identical, because the recorder is only ever called from inside an `except` that catches a real crash. Proven:

| build | 2022 trades_canon_md5 |
|---|---|
| origin/main (trade-path files checked out) | `80b501a8ab16206d74bdfc09a7f245aa` |
| this branch (T-199 fix) | `80b501a8ab16206d74bdfc09a7f245aa` |

**Bitwise identical** → not one trade moved. Cross-process determinism on this branch: 2022 reproduced unanimous across **3 independent processes** (`80b501a8` ×3). The ONLY behaviour change is: a swallowed crash that used to vanish now FAILs the census / HALTs in measured mode.

## 5. Sibling sweep (the shared signal path)
- `engines/engine_a_alpha/signal_processor.py:347` — already a **disciplined narrow-catch** (only `ValueError` on `float(raw)` coercion of a single feature value; programmer errors re-raise). NOT the per-edge crash-as-no-signal class. Safe.
- `engines/engine_c_portfolio/policy.py:246` — a missing-optional-config (`sector_map.json`) degrade-to-`{}` (drops the diversification constraint). A **different class** (config load, not an edge crash); a candidate for a future measured-mode HALT on a missing baked config, but out of scope here.
- `composer.py` has `continue`/`return None` control-flow worth a later look, but none is the per-edge crash swallow.
The correctly-scoped target was `signal_collector`; the immediate siblings are either already-disciplined or a different class.

## 6. Tests
- `tests/test_signal_collector_silent_failure.py` — T-199: swallowed ValueError is recorded (crash ≠ no-signal); a partial-crash edge is visible though not blind; a clean run records nothing (unit canon-invariance); measured-mode HALTs (`MeasurementHalt`).
- `tests/test_census.py` — `edges_errored` non-empty → NON-CANONICAL (parametrized invariant).
- `tests/test_contracts.py` — `edges_errored` added to the Layer 2d CENSUS_GATING_KEYS producer/consumer contract.
45 green (+1 xfail).

## 7. Files / propose-first
`engines/engine_a_alpha/signal_collector.py` (recorder + both sites + measured-HALT), `backtester/backtest_controller.py` (`census.edges_errored`), `core/census.py` (gate), the 3 test files. No Engine-B-risk / `live_trader/` touched. **Canon-moving → director reviews the diff line-by-line and re-verifies canon-md5 invariance before merge.** Only behaviour change = a real swallowed crash now fails/halts; clean runs are bitwise-identical.
