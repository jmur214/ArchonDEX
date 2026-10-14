# Session Summary: 2026-10-14 (Agent D) — the push record, a pin-composition fix, the T-196 kill table, RR-6a (+2 fixups), the edges.yml unit

## What was worked on

- **The push record.** A full suite on clean `72485f7`, run from the agent-d worktree with the two worktree-name
  tests deselected, gave **4 failed / 4065 passed**. All four were R's F2 cycle-harness tests, broken by a
  merge-composition defect between that fixture and **my honest-N pin**. Fixed test-only at `4793b2d`, merged at
  `18fa3f4`.
- **T-196 per-gate kill table**, the input to the gap report's §2g reconciliation. `1539e17`, merged at `16c000f`.
  - Of the 36 records, 34 name Gate 1 as the killer. Four of those are exact-zero contributions (blind or
    absorbed), so they are not verdicts.
  - `triple_witching_premium` failed no gate that rendered a verdict.
- **RR-6a** (referee, propose-only) on `fix/referee-rr6a-gate-verdicts`: `c982114` → fixup `413dcee` (the director's
  rulings: (a) `run_evolution_cycle` passes the production window; (b) the per-candidate handler catches only the
  diagnostic `TimeoutError`; (c) the cycle fails loudly with the stage named and a `cycle_failure` row) → fixup 2
  `85508785b1e012ec8be1f0582307f4b102dfb0ca` (the regime step refuses instead of hunting context-free). 18 of 18
  reversion cases bite; with R.
- **The edges.yml unit** (`fix/engine-d-registry-write-fail-closed` @ `6e207904c3449b5936e40ace2c58549d6488c03d`).
  An unreadable registry refuses and is left byte-untouched, and writes are atomic. With the old write, a dump
  error left the registry at the empty-file sha. With R; it merges clean with RR-6a.
- **News-panel tests** compare against the repo root (`8cd65ea`). The suite now passes from any worktree.

## What was decided

- **One fix for the class, not per-gate patches.** Each gate gets a tri-state verdict: PASSED | FAILED |
  NOT_EVALUATED(reason).
  - There are no defaults; a missing gate is a `KeyError`.
  - The decision happens in one place.
  - A required gate that rendered no verdict refuses promotion.
  - The required set lives in config (`required_gates` = gates 0, 1, 2, 4, 5, 7, 8) and is validated against
    `factor_gate_mode`.
- **Legacy `gate_N_passed` flags stay, derived from the verdicts and written for every gate.** No unconverted
  reader can fall through to a default, and the historical gauntlet scripts keep working.
- **Kept out of RR-6a, as rulings:**
  - the per-candidate and outer exception handlers in `_run_discovery_cycle`;
  - `run_evolution_cycle` passing no validation window, so it can no longer promote;
  - `save_candidates` wiping `edges.yml` when it fails to parse.
- **F4 was pre-registered and committed (`d15846b`) before it ran.** Reading 2: **SIZE DRIFTS.** On left-skewed
  zero-mean streams, Gate 4 rejects at 1.5–2.3× its nominal 5%. The replacement null is its own unit.

## What was learned

- **Read WHY a reverted lock failed.** One of 13 locks bit on a `ModuleNotFoundError`, which means it bit
  vacuously. The reversion script now prints each failure's first assertion line.
- **A refusal lock needs a positive control.** Gate 0 with no window refuses everything, so without a control
  where every other gate passes, a Gate-7 refusal lock holds on buggy code too.
- **A swallow-all block hides fixture defects as well as code defects.** The F2 fixture never had `timeframe`
  and passed only because the substrate-B catch-all absorbed the error.
- **A merge can break a test file nobody re-runs.** The pin changed what the F2 fixture needed. Run every file
  that touches a module after each merge, not only before it.
- **First artifact.** The fixed Gate 7 build resolves a **469-ticker** substrate B locally. Gate 7 has never run
  in production, so the first post-merge `--discover` cycle costs two extra backtests over 469 tickers per
  candidate. Cloud availability is unverified.

## Pick up next time

- **Hold until R reports** on RR-6a (`8550878`) and the edges.yml unit (`6e20790`). Then:
  - apply R's notes as fixups and give the director the exact hashes;
  - after both merge, run `scripts/sync_docs.py` once. The `engine_d_discovery/index.md` regeneration was
    deliberately left out of both branches;
  - build the **Engine F registry-write unit** from the outbox brief, after one ruling: does a failed save raise
    out of the production backtest's post-run path, or route to the journal?
  - **The constraint:** no Discovery promotion cycle until RR-6a AND the edges.yml fix are both on main.

- When R's verdict on RR-6a (`c982114`) arrives: apply notes as pre-merge fixups and give the director the
  **exact** new hash.
- **Test-only follow-up** (the director's request): `tests/test_pulse_news_wiring_t290b.py::TestRepoRelativeRoot`.
  Its two tests should compare against the repo root, not the literal `trading_machine-agent-d`, so the suite
  passes from any worktree.
- **R1:** after the first post-push 03:00 run proves IAM write on `ops/observability/`, hash and copy the RR-3B
  mirror and the 36 foundry records to `s3://…/ops/observability/mirror_2026-10-13/` with a sha256 manifest. The
  sidecar `docs/Measurements/2026-10/t196_foundry_records_SIDECAR.md` goes beside the S3 records.
- Proposal-ready follow-ups, each its own unit:
  - the Gate-4 replacement null (F4);
  - the `save_candidates` destructive fail-open;
  - the T-195 harness taking the honest N.

## Files touched

- `fix/pin-cycle-harness-fixture` (merged): `tests/test_referee_repairs_proposed.py`.
- `docs/t196-per-gate-kill-table` (merged): `docs/Measurements/2026-10/t196_foundry_per_gate_kill_table.md`.
- `fix/referee-rr6a-gate-verdicts` (proposed): `config/discovery_settings.json`, `core/factor_decomposition.py`,
  `engines/engine_d_discovery/{discovery,discovery_logger,gate_verdicts,thresholds}.py`, its `index.md`,
  `orchestration/mode_controller.py`, six `scripts/` imports, `scripts/rr6a_gate4_size_skewed.py`,
  `scripts/rr6a_reversion_proof.py`, four test files plus `tests/test_rr6a_gate_verdicts.py`, the proposal, the
  F4 record, the sidecar, and `docs/Core/execution_manual.md`.
