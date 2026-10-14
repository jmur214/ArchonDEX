---
task_id: RR-6 (alpha-frontier program §3.1) — BRIEF, written before any code
title: RR-6 brief — gate verdicts that can be trusted, then a gate that measures the goal
date: 2026-10-14
author: Agent D
branch: docs/rr6-brief (docs only)
type: BRIEF — reading only. No referee code until RR-2 is on main (director's ruling).
n_trials: 0
---

# RR-6 brief

**Sources read** (all claims below re-verified on `main` @ `b83a037` on 2026-10-14, by AST or by reading the line,
not taken from the documents): the alpha-frontier program's RR-6 section; A's RR-2 proposal §7
(`fix/referee-rr2-discovery-verdict`); R's RR-2 review (`review/agent-r-rr2`, `docs/Audit/rr2_review_agent_r_2026_10_08.md`);
the 36 T-196 foundry records (`data/observability/rr3b_foundry_t196_2026-10-13/`); `data/research/discovery_log.jsonl`.

## 0. Recommendation first: split RR-6 in two

RR-2 makes the gauntlet's verdict authoritative, and the director has ruled that **no promotion cycle may run between
RR-2's merge and RR-6's**. The original RR-6 bundles two different kinds of work:

| | **RR-6a — the verdicts can be trusted** | **RR-6b — a gate that measures the goal** |
|---|---|---|
| what | the defects: Gate 7's free pass, the two-valued verdict class (§1), Gate 3's dead threshold, Gate 6's RF bias, Gate 5/7 cache contamination, re-queue-forever, R's F3/F4 | terminal-wealth Gate 1′, held-out window, `oos_lock` at cycle start, charter text |
| size | small — mostly one-line and default changes, plus tests | the brief's 3 days, with its own pre-registered refutation criterion |
| blocks | **every promotion cycle** (the ruling) | nothing; a design improvement |

**Recommend: RR-6a first, alone.** Bundled, a three-day redesign holds Discovery hostage to it. RR-6a is what the
"no promotion cycle" ruling actually waits for.

---

## 1. ⭐ The defect class: a verdict that was never rendered reads as a verdict — in opposite directions

Gate results are two-valued booleans with **defaults**, so "not evaluated" cannot be told apart from a verdict. Worse,
**different consumers resolve the same absence in opposite directions:**

| consumer | where (main unless noted) | how it reads an absent verdict |
|---|---|---|
| the **promotion decision** | `discovery.py` final pass check on RR-2's branch: `bool(result.get("gate_7_passed", True))`, same for Gate 8; both initialised `True  # Default True = SKIPPED` (RR-2 branch `:1153`, `:1155`) | **absent = PASS** |
| the **kill attribution** (diagnostic) | `discovery.py:1160-1169`: Gate 7/8 default `True`; Gate 3 excluded "as metric-only" | absent = PASS |
| the **T-195 foundry harness** | `scripts/run_foundry_eval_t195.py:113-115`: `gate_{g}_evaluated` defaults **True**, `gate_{g}_passed` defaults **False** | **absent = FAIL** |

**Evidence that this is not hypothetical:**
- **All 36 T-196 foundry records say `g7: true, g8: true`** — for gates that never ran (no substrate B was passed; the
  candidates died at Gate 1 or Gate 4 before Gate 8).
- **Two of them name Gate 3 as the gate that killed them** (`triple_witching_premium`, `january_effect`). Gate 3 has
  **no pass criterion**: it is evaluated (`gate_3_evaluated = True` when WFO ran) but never gets a `gate_3_passed` key,
  so the harness's `False` default convicts it. Both actually died at the forced Gate 4 (`g4: false`). This is the same
  record RR-7 corrected in the ledger ("2 at gate_3" → "killed by forced Gate 4"); here is the mechanism that wrote it.
- The record is internally inconsistent: `gates.g3` is `null` while `first_failed_gate` is `gate_3`.

**The fix for the class (RR-6a):** one **tri-state verdict per gate** — `PASSED | FAILED | NOT_EVALUATED(reason)` —
written once by `validate_candidate`, read by every consumer, with **no defaults anywhere**. The promotion decision
treats a **required** gate's `NOT_EVALUATED` as a refusal (fail closed); which gates are required is config. Kill
attribution never names a gate that rendered no verdict. Fixing Gate 7's `NameError` (§2) without this leaves the
class open: substrate B can be legitimately unavailable (the fallback path just above `:1315`), and Gate 7 would then
still skip — and still pass.

## 2. Instance A — Gate 7 passes every production candidate (swallowed `NameError`)

Verified by AST on `main`, 2026-10-14:
- `_run_discovery_cycle` (`orchestration/mode_controller.py:1170-1465`) **reads `timeframe` at `:1283` and `:1300`**; the
  name is **never assigned** in the function and is **not an argument**. (R cited `:1270`/`:1287` on 10-08; RR-3's
  insert moved them by 13.)
- `:1315-1316`: `except Exception as _sb_err: print("[DISCOVERY] Gate 7 substrate-B build failed; gate skipped: …")` →
  substrate B `None` → Gate 7 skipped → `True` → a free pass, on every cycle. R saw the message print on every run.
- **The intended value exists:** `self.timeframe` is set at `:547` and again at `:869`, before the cycle is called at
  `:1111`. The minimal fix is `timeframe` → `self.timeframe` at `:1283` and `:1300`.
- **The block must stop catching programmer errors.** A `NameError` swallowed into "gate skipped" is the 2026-09-14
  lesson exactly (53 green tests passed on a broken line because none executed it) and the "fail-open block is a
  phantom factory" pattern. The build may degrade on *data* unavailability, with a named reason that becomes
  `NOT_EVALUATED`; it may never absorb `NameError`, `TypeError`, `AttributeError`.

**Why it did not matter until now:** before RR-2 the production overwrite ignored the gauntlet's verdict entirely
(N-2). RR-2 is what makes Gate 7's default decide promotions.

## 3. Instance B — Gate 3's threshold is declared and never checked

`gate3_consistency_threshold: float = 0.40` (`engines/engine_d_discovery/discovery.py:958`) has **exactly one
occurrence: its declaration**. `wfo_consistency` is computed (`:1478-1489`) and recorded, and compared to nothing. A
caller passing `gate3_consistency_threshold=0.9` changes nothing — **a parameter that silently does nothing is a false
statement in the interface.**

**RR-6a makes the interface honest; RR-6b decides whether Gate 3 should bind.** Binding Gate 3 is a new condition on
future Discovery — a design question, not a defect. Until that is ruled, RR-6a should either remove the parameter, or
raise if a caller passes a non-default value ("Gate 3 is recorded, not a promotion condition"). Gate 3 then renders
`NOT_EVALUATED`-style output for promotion purposes and is never named a killer (§1).

## 4. Instance C — Gate 8 defaults to `True` when skipped

After RR-3, Gate 8's N resolves fail-closed and is ≥ 2, so production always evaluates it. The default remains
reachable through an explicit `n_trials_for_dsr ≤ 1`, and through any short-circuit before Gate 8. Same fix: §1.

## 5. Carried into RR-6a from the original brief and the reviews
- **Gate 6 RF bias** (original brief): `regress_returns_on_factors(..., already_excess=True)` for attribution spreads;
  a missing factor cache HALTS in measured runs. Xfail `test_gate6_alpha_of_a_factor_neutral_spread_is_not_shifted_by_rf`
  flips.
- **Gate 5/7 cache contamination** (original brief): the with-arms reuse the Universe-A signal cache; build from fresh
  baseline edges on the alternate data_map, or key the cache on `(data_map_id, now)`.
- **Re-queue forever** (A §7.3, R's F6): in `run_evolution_cycle` a WFO failure leaves the candidate at `"candidate"`,
  so it is re-queued on every cycle. It must leave the queue with a recorded reason.
- **R's F3:** move the two threshold readers out of `orchestration/mode_controller.py` (imported by five engine-side
  scripts — an inverted dependency) to `engines/engine_d_discovery/thresholds.py`.
- **R's F4:** one size test of Gate 4's sign-flip null on a **skewed** zero-mean H0 stream (centred lognormal or
  GARCH-shaped). If the size drifts, the stationary bootstrap centred at zero is the drop-in replacement. This is a
  measurement, not a reversion test.

## 6. Proof-by-reversion plan — each lock fails when only its fix is reverted

Every test DRIVES the real entrypoint. A text assertion cannot catch a `NameError` (2026-09-14).

| defect | the test | revert → |
|---|---|---|
| Gate 7 `NameError` | drive the cycle's substrate-B build in a temp root with a stub historical cache; assert substrate B is built, and that an injected `NameError` **propagates** | bare `timeframe` restored → "gate skipped", test fails |
| absent = PASS (decision) | `validate_candidate` with no substrate B → Gate 7 is `NOT_EVALUATED`, and `passed_all_gates` is **False** when Gate 7 is required | `True` default restored → passes |
| absent = FAIL (attribution) | a candidate killed at Gate 4 with Gate 3 evaluated → `first_failed_gate == "gate_4"`, in both the diagnostic and the harness | old harness logic → `"gate_3"` |
| Gate 3 dead parameter | a non-default `gate3_consistency_threshold` raises (or the parameter is gone) | parameter restored silently → passes |
| Gate 8 skipped | explicit `n_trials_for_dsr=1` → Gate 8 `NOT_EVALUATED`, not a pass | default `True` → passes |
| Gate 6 RF | the existing xfail flips | `already_excess` removed → fails |
| Gate 5/7 cache | pure-noise candidate on the alternate data_map → contribution ≈ 0, not Universe-A's | shared cache → Universe-A value |
| re-queue forever | WFO failure → status leaves `"candidate"` with a reason | old behaviour → stays queued |

## 7. Which records it touches

**No historical verdict flips — verified, not assumed.** Before RR-2 the overwrite ignored the gauntlet, and **no
candidate ever passed all gates**: 0 of 36 foundry records, 0 of 88 `discovery_log.jsonl` rows, 0 promotions. The free
pass never decided anything. RR-2 is what would have let it.

- **36 S3 foundry records** state `g7/g8: true` for gates that never ran; **2** name Gate 3 as their killer when Gate 4
  was. These are evidence — **annotate, never rewrite** (a sidecar note beside the records, cross-referenced from RR-7's
  T-196 correction).
- **`discovery_log.jsonl`** (88 rows) carries no Gate 7/8 fields — unaffected.
- **Schema:** the tri-state verdict changes the result dict, `discovery_log` rows going forward, and harness records.
  **15 files consume gate verdicts:** 2 production (`discovery.py`, `mode_controller.py`), 9 scripts (`run_foundry_eval_t195.py`,
  `run_phase0b_foundry_discover_t193.py`, `run_spinoff_gauntlet_t041b.py`, `run_vrp_gauntlet_t122.py`,
  `run_bab_gauntlet_t123.py`, `run_falsifiable_spec.py`, `run_discovery_diagnostic_standalone.py`,
  `analyze_discovery_diagnostic.py`, `discovery_diag_analytics.py`), 4 tests. The T-041b/T-122/T-123 verdicts were
  Gate-1 kills (T-346's graveyard) — evaluated gates — so the absent-verdict reading never touched them.
- **`health_check.md` anchors:** RR-6a edits the cycle (`:1283`, `:1300`, `:1315`) and `discovery.py`, which will shift
  code anchors on the open HIGH row. Re-point them in the merge commit, after confirming each still witnesses its
  defect — R's F1 pattern on RR-2 and RR-3.
- **Charter** (`docs/Core/engine_charters.md`, Discovery): proposal text only (charter language is propose-first).
- **Config:** `config/discovery_settings.json` gains a required-gates list.

## 8. RR-6b in one paragraph (unchanged from the original brief)

Gate 1′ on `ci_low(Δ log terminal wealth vs SPY-TR)` at deployable weight ≤ 0.25 AND `ci_low(Δ Sortino) > −0.05`, with
ΔSharpe as a diagnostic; `hunt()` and GA fitness on `[start, T−24mo]` with Gate 1′ also on the held-out
`[T−24mo, T]`; `oos_lock` consulted at cycle start, refusing on overlap. **Pre-registered refutation, kept:** if Gate
1′ passes a zero-α candidate in more than 10% of 50 seeded noise candidates on the golden fixture, tighten before
proposing.

## 9. Sequencing
RR-2 merges → my pin branch (`1bae7eb`) merges → one full suite on main → **RR-6a** (code begins here) → only then any
promotion cycle → RR-6b separately. N_trials 0 throughout: these are corrections, and any historical cell re-run under
them is a RE-SCORE.

---
**BRIEF — docs only, no referee code.** Everything in §§1–4 was re-verified on `main` @ `b83a037`.
