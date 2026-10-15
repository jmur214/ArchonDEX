# Session Summary: 2026-10-15 (Agent B) — the substrate's rails: the level identity, the stale/holed guard, the fundamentals miss-refusal, the direct-readers contract

Agent B's side of the day. The director's summary (`2026-10-15_session_env_fix_substrate_findings.md`)
covers the rulings and the merge record. Every unit below was R-approved by hash and merged by the
director after the full suite ran on the staged merge.

## What was worked on

- **The level rail's split-window fix** (`db8c110` → main `dad8786`).
  - The bug: `level_identity` multiplied back the splits after a file's LAST bar. It must use the
    splits after its ADJUSTMENT date W.
  - Who it hit: a stale file split in between (NVDA, which ends 2024-05-10, then split 10:1 on
    2024-06-10) read 0.0999 and would have been refused at cutover as a ÷10 defect.
  - How it was found: by B's own 652-file sweep, after R's approval. The director held the merge.
- **The 652-file identity record** (`bcb07c8`).
  - 651 files measured. Over tolerance, exactly AZO, MTD, NVR and SLE (at 0.1) and CPWR (at 2.0).
  - All 55 stale files are explained.
  - New finding: the LEGACY adjustment date (04-25) is an upper bound, not the real write date.
    Five files carry an unapplied dividend, CVS's being the largest at 0.0087, all inside the
    tolerance. Ruled accepted on the closed set.
- **The stale/holed-files guard** (`73b421c` → `69506bc`).
  - It counts BARS, never file presence.
  - The END test runs per name, against the earlier of the window end and the name's exit
    (R's correction).
  - The trading calendar is proven against SPY in BOTH directions. On the real cache, 244 of 248
    files lack 1999-11-16, a day SPY traded, and the majority calendar had hidden it.
  - With no SPY to prove the calendar against, the run fails.
  - `data_gaps` declarations come in two kinds, each excusing exactly what it declares. The set
    is 46: the 45 files no provider can fill, plus FISV's one-day provider gap. FISV traded that
    day: Alpaca's SIP volume was 6.2M.
  - Formation coverage counts every member on the date: 0.38 / 0.70 / 208 of 312.
  - Results: the post-write copy reads green over 2018–2025; the real cache stays red until
    cutover day.
- **The fundamentals miss-refusal** (`55e1325` → `a4c6f89`).
  - A canonical run refuses a per-ticker fundamentals cache miss, using the same switch as the
    price fallback.
  - A miss fetched mid-run fails the gate as an unpinned input entered mid-run.
  - Blind names count only when a DECLARED consumer is loaded (`READS_TICKER_FUNDAMENTALS`). Gate 1
    reads the same count, and an AST lock covers every class that reaches the cache.
- **The direct-readers contract** (`a38db0b`).
  - An AST check over the scripts that read the processed cache directly. The 63 are frozen; 16
    more are exempted by R's ruling.
  - The real bypass it found: the dashboard-launched `run_evolution_cycle.py` read every cached
    file, ÷10 names included. Fixed.

## What was decided

- **LEGACY W = 2026-04-25 is accepted on the closed set.** No per-file W is read from a file's own
  content: picking the hypothesis with the smaller residual is tuning.
- **A run with no SPY fails** ([NN-FAIL-CLOSED]). 19 Discovery test fixtures had no SPY. They were
  fixed additively; the rule was not relaxed.
- **The declaration set is 46, not 33.** Tolerance is 0 over each file's full span. The 10
  later-entity files are class (i), beside SLE and POM.
- **The 5 single-day holes left on the copy** (JPM/KDP/TDC/WMT/WU, all span refusals) wait on the
  user's class (iii)/(iv) ruling. They are not declared.
- **The fundamentals rulings.**
  - (A) A fetched miss is non-canonical.
  - (B) Consumers are declared, never inferred from edge ids. The old id-hint list matched
    value_trap_v1 alone.
  - One switch covers both prices and fundamentals.

## What was learned

- **Plant a lock's event in EVERY interval the formula distinguishes**, with the cache in the basis
  a real file would have. The split lock only placed its split after W, so it could not see the
  defect. A sweep over the real population is a lock's own check.
- **A data-derived reference needs proving in both directions.** A majority vote cannot see a mass
  hole.
- **Witness an absence before naming its cause.** "No provider series" for FISV would have been
  false.
- **A detector needs a positive control against the known population.** The globber detector first
  missed the §5.1 harnesses' own idiom, `glob(str(ROOT / "processed" / "*_1d.csv"))`. Measuring
  it against the 63 caught that.
- **A denominator taken from the files present is file-presence in disguise.** The formation
  number moved with whichever files were in the map.
- **A new fail-closed rule breaks fixtures that never modelled production.** Run the full suite
  before posting. A contract test can also fail on the census's own new keys, so read WHY a test
  fails in the restored state.

## Pick up next time

- **The verify-stamp module** (`core/substrate_stamp.py`; the interface is agreed on
  `docs/verify-stamp-agreed-interface`). Blocked until D's registry unit ships; not on main as of
  9f9ec13.
- **Re-pin #1**, with:
  - the honest-N re-bake (after the registry);
  - `data/external/base_curve/` into `SUBSTRATE_DIRS`;
  - the T-219 shares snapshot;
  - the fundamentals re-bake step. **No CLI exists for that step yet.** A small script is a
    follow-up, to be added to `execution_manual.md` when it exists.
- **For the user's batch:** the class (iii)/(iv) span rulings that would bring the copy's last 5
  single-day holes to green over 2000–2025.

## Files touched

```
engines/data_manager/tr_writer.py            engines/data_manager/coverage.py (new)
engines/data_manager/data_manager.py         core/census.py
backtester/backtest_controller.py            engines/engine_d_discovery/discovery.py
orchestration/mode_controller.py             scripts/run_evolution_cycle.py
engines/engine_a_alpha/edges/{fundamental_value,fundamental_ratio,composite_edge}.py
config/data_gaps.json (new)
tests/test_level_rail_2026_10_15.py          tests/test_stale_holed_guard_2026_10_15.py (new)
tests/test_fundamentals_miss_refusal_2026_10_15.py (new)
tests/test_processed_globbers_2026_10_15.py (new)
tests/test_contracts.py  tests/test_census_fail_closed.py  tests/test_gate1_candidate_census_t347.py
tests/test_discovery_gates_7_8.py  tests/test_rr6a_gate_verdicts.py  tests/test_discovery_gate_remediation.py
docs/Sources/proposal_level_rail_last_bar_identity_2026-10-15.md
docs/Sources/proposal_stale_and_holed_files_guard_2026-10-15.md
docs/Sources/proposal_substrate_cutover_exact_tr_2026-10-15.md
docs/Sources/proposal_observability_shipping_2026_10_13.md
docs/State/health_check.md
```

## Subagents invoked

- None. Every unit was built and measured directly. Reviews were by Agent R (cross-session), and
  merges by the director.
