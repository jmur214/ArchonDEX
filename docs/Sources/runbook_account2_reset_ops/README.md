# Account-2 reset runbook — committed ops scripts, tests, simulations and mutation harness

These are the scripts behind [`../runbook_account2_reset_2026-11-17.md`](../runbook_account2_reset_2026-11-17.md)
§7, their test harnesses, the simulations behind the runbook's §0.1, §7 and §8 expectations, and the
mutation harness that proves the tests can fail.

**Nothing here touches AWS, Alpaca or the network when you run the tests.** The ops scripts act only when
an operator runs them on day D, in the order the runbook gives, on the user's word:
- `step2_snapshot.sh`, `archive.sh`, `restore.sh` and `gate_live_clean.sh` call the `aws` CLI;
- the scheduler updates are fed by `sched_state.py`;
- the two templates run inside account 2's container.

**What is NOT in this folder:**
- no S3 snapshot copies;
- no `data/` content;
- no account identifiers or keys. The fakes use `PLACEHOLDER-ACCT`, the AWS account id
  `000000000000`, and the bucket `fakebucket`.

Run every command from the repo root. Each test exits 0 when every case passes. `C=docs/Sources/runbook_account2_reset_ops`.

## Files

| File | What it is | Command that re-runs its test |
|---|---|---|
| `step2_snapshot.sh` | Runbook step 2. Snapshots the live prefix, md5-lists it, reads the schedule pin and the latest ACTIVE revision and image, and writes `step2.env` (`JD`, `EXPECT`). Refuses a reused OPS dir, a pin that is not the latest revision, and an image that is not `$EXPECT_IMAGE`. | `bash $C/check_step2.sh` |
| `archive.sh` | Step 5. It refuses unless the schedule is DISABLED, refuses an existing manifest, and refuses an occupied archive or aside key. Per key it proves live = snapshot, copies to the archive, and proves the copy (md5 + ETag) before it moves the original aside. `pipefail`. Never deletes, never overwrites. | `bash $C/check_archive.sh` |
| `restore.sh` | The rollback of `archive.sh` (the step-5 rollback, and §7.6). DISABLED-only; refuses an occupied live key; requires aside md5 = archive md5; verifies the live md5 after the move; restores exactly the manifest's keys. A partly finished restore is re-run with `RELS` = the manifest keys still aside (§7.6). | `bash $C/check_restore.sh` |
| `gate_live_clean.sh` | Steps 7, 9.5 and 12: the stray-run gate. Passes only when (1) the schedule is DISABLED, (2) no job on account 2's jobdef (any revision; `list-jobs --filters name=JOB_DEFINITION,values=…`) is anything but SUCCEEDED or FAILED, and (3) the live prefix holds only `data/state/exec_cost_ledger.jsonl`. Fails closed if `list-jobs` errors. | `bash $C/check_gate.sh` |
| `fake_aws.sh` | Test stub for every `aws` call above: `s3 cp` (incl. `--recursive` and `-`), `s3 mv`, `s3 ls`, `s3api head-object` (404 → rc 254, like the real CLI), `scheduler get-schedule`, `batch describe-job-definitions`, `batch list-jobs` (only the JOB_DEFINITION filter on the expected queue, serving `$FAKE_JOBS`). `FAKE_FAIL` injects one fault: `read_live`, `mv`, `corrupt_copy`, `etag_wrong`, `head_denied`, `corrupt_mv` or `list_denied`. | (used by the four `check_*.sh`) |
| `_fake_env.sh` | Sourced by the four `check_*.sh`: builds the synthetic world (one-line objects, a placeholder schedule) and the PASS/FAIL helpers. | — |
| `sched_state.py` | Steps 4 and 12. Turns a FRESH `get-schedule` JSON into an `update-schedule` input that changes only `State`, refusing unless the pin, DLQ and fast-fail retry match. | `python3 $C/check_sched_state.py` |
| `render.py` | Fills `__D__` / `__EXPECT__` / `__ATTEMPT__` / `__EXECUTE__` / `__TICKERS__`, validates each value, and refuses any placeholder left unfilled. | (exercised by `check_reset_a2.py` and `check_postcheck.py`) |
| `reset_a2.tmpl.py` | Steps 9–10, the liquidation body, run ONLY inside account 2's container. It refuses before 10:00 ET or within 30 min of the close (broker clock read in ET), on D = 2026-11-26/27, on a broker date ≠ D, positions ≠ EXPECT, or an open order. Per-order try/except; coids `reset-a2-<D>-<T>-sell-a<ATTEMPT>`. | `python3 $C/check_reset_a2.py` |
| `postcheck_a2.tmpl.py` | Steps 8 and 11 (and 8A–11A). With `TICKERS=[]` it is a flat-check that prints `account_number` and the broker `CLOCK` in ET; with the three tickers it also prints the reset orders' fills. FLAT requires no positions AND no open orders. | `python3 $C/check_postcheck.py` |
| `sim_reset.py` | The first reviewer's simulation: the REAL `scripts/run_paper_cloud_day.main()` for D+1/D+2/D+3 from an empty state against a fake flat broker at the 2026-11-16 closes. Committed with one change: it refuses an existing or in-repo work path instead of `shutil.rmtree`-ing it. | `PY=<checkout>/.venv/bin/python bash $C/run_sims.sh .` |
| `sim_variant.py` | `sim_reset.py` plus an optional `rebase_start_date` argument (applied to the WORK copy of the config): the $10,000 re-base, and option A at $10,000 with and without it. | (run by `run_sims.sh`) |
| `sim_stray.py` | The delta reviewer's stray-run simulation (N1), plus a mode argument: a stray firing after the archive and before the liquidation, then D+1..D+3. `wedge` = no recovery; `recover` = the stray's files moved aside first. | (run by `run_sims.sh`) |
| `run_sims.sh` | Runs the six simulations under a fresh `mktemp` dir, then `check_sims.py`. **Needs the repo's venv interpreter.** It STOPs with exit 2 and names it when `$PY` / `<repo>/.venv/bin/python` is missing or cannot import pandas, python-dotenv and alpaca-py. | itself |
| `check_sims.py` | 38 assertions over the six outputs (exit codes, the contributions line, arrival orders, mirror `tier_equity`, split-feed tickers, the D+1 ledger init, the seeding reason, and the stray wedge vs recovery). | (run by `run_sims.sh`) |
| `mutate.py` | The mutation harness, adapted from the delta reviewer's `run_mut.py`: their 31 mutants (one pattern updated for the ET clock line) plus 33 new ones over every script. Two equivalents are declared with their reasons; every other mutant must be caught. | `PY=… $PY -I $C/mutate.py` (about 4 min) |
| `check_embedded.py` | Proves the runbook's §7.1–7.4 code blocks are byte-identical to `sched_state.py`, `archive.sh`, `reset_a2.tmpl.py` and `postcheck_a2.tmpl.py`. | `python3 $C/check_embedded.py` |

## Results on 2026-11-17 (branch `docs/account2-reset-runbook`, revision 4)

| Check | Result |
|---|---|
| `check_archive.sh` | 14/14 PASS |
| `check_restore.sh` | 11/11 PASS (case 11 = a partial restore, then the §7.6 re-run) |
| `check_gate.sh` | 10/10 PASS (case 6 = the §7.6 "before step 10" recovery, end to end; cases 7–10 = a job still in flight, an unknown status, list-jobs denied, no jobs) |
| `check_step2.sh` | 7/7 PASS |
| `check_sched_state.py` | 7/7 PASS |
| `check_reset_a2.py` | 21/21 PASS |
| `check_postcheck.py` | 9/9 PASS |
| `run_sims.sh` → `check_sims.py` | 38/38 PASS |
| `mutate.py` | 64 mutants: 62 CAUGHT, 2 declared EQUIVALENT, 0 not caught |
| the reviewer's own `run_mut.py`, re-run with only its output dir changed (on revision 3; the four files it mutates are unchanged in revision 4) | 31 mutants: 28 CAUGHT; 2 NOT CAUGHT, both the declared equivalents; 1 NOT APPLIED (its broker-date pattern predates the ET change, and `mutate.py` carries the updated pattern, CAUGHT) |
| `run_sims.sh` with no venv / with `/usr/bin/python3` | exit 2 with the interpreter message (both) |
| `check_embedded.py` | 4/4 IDENTICAL |

**The two equivalent mutants:**
- `archive: drop empty-md5 refusal`: the `[ -s "$SNAP" ]` line before it already refuses an empty
  snapshot. A non-empty file hashing to the empty-file md5 would be an md5 preimage.
- `sched: also rewrite Target pin to expect`: that line runs only after `jd == expect` was enforced, so
  the replacement is the identity.

## Byte-identity: runbook text vs these files

`check_embedded.py`, an exact byte comparison of the first fenced block under each heading:

| Runbook section | File | Result |
|---|---|---|
| §7.1 | `sched_state.py` | IDENTICAL (1,310 bytes) |
| §7.2 | `archive.sh` | IDENTICAL (2,918 bytes) |
| §7.3 | `reset_a2.tmpl.py` | IDENTICAL (2,837 bytes) |
| §7.4 | `postcheck_a2.tmpl.py` | IDENTICAL (1,291 bytes) |

**Not embedded in the runbook (no identity claim applies):**
- the scripts `step2_snapshot.sh`, `restore.sh`, `gate_live_clean.sh` and `render.py`;
- the fakes and every `check_*` file;
- `run_sims.sh`, `mutate.py` and the three simulations.

The runbook names them and points here.

**`sim_reset.py` and `sim_stray.py` versus the reviewers' originals** (`/tmp/runbook_review_fresh/`, ephemeral):
- `sim_reset.py`: only the work-root block differs. The original `shutil.rmtree`-ed it; this copy refuses.
- `sim_stray.py`: the delta reviewer built it on the committed `sim_reset.py`. This copy adds only the docstring, the `wedge|recover` argument and the recovery block.
