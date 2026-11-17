# Account-2 reset runbook — committed ops scripts, tests and simulations

These are the scripts behind [`../runbook_account2_reset_2026-11-17.md`](../runbook_account2_reset_2026-11-17.md)
§7, their test harnesses, and the simulations behind the runbook's §0.1 and §8 expectations.

**Nothing here touches AWS, Alpaca or the network when you run the tests.** The scripts that do touch AWS
(`archive.sh`, the `aws scheduler` commands fed by `sched_state.py`) and the broker (the two templates)
act only when an operator runs them on day D, in the order the runbook gives, on the user's word.

**What is NOT in this folder:**
- no S3 snapshot copies;
- no `data/` content;
- no account identifiers or keys. The fakes use `PLACEHOLDER-ACCT`, the AWS account id
  `000000000000`, and the bucket `fakebucket`.

Run every command from the repo root. Each test exits 0 when every case passes.

## Files

| File | What it is | Command that re-runs its test |
|---|---|---|
| `archive.sh` | Step 5. Per key: proves the live object equals the step-1 snapshot, copies it to the archive prefix, proves the copy (md5 + ETag), then moves the original aside. `pipefail`; refuses the empty-file md5. Never deletes. | `bash docs/Sources/runbook_account2_reset_ops/check_archive.sh` |
| `fake_aws.sh` | Test stub for `archive.sh`. It maps `s3://bucket/key` to a local directory; `FAKE_FAIL=read_live\|mv` injects a denial. | (used by `check_archive.sh`) |
| `check_archive.sh` | 5 scenarios on SYNTHETIC fixtures: happy path, live read denied, move denied, live changed since the snapshot, live key missing. | itself (see above) |
| `sched_state.py` | Steps 4 and 12. Turns a FRESH `get-schedule` JSON into an `update-schedule` input that changes only `State`, refusing unless the pin, DLQ and fast-fail retry match. | `python3 docs/Sources/runbook_account2_reset_ops/check_sched_state.py` |
| `check_sched_state.py` | 7 cases on a synthetic schedule (account id `000000000000`). | itself |
| `render.py` | Fills `__D__` / `__EXPECT__` / `__ATTEMPT__` / `__EXECUTE__` / `__TICKERS__` in a template, validates each value, and refuses any placeholder left unfilled. | (exercised by `check_reset_a2.py` and `check_postcheck.py`) |
| `reset_a2.tmpl.py` | Steps 9–10. The liquidation body, run ONLY inside account 2's container through `aws batch submit-job` command overrides. | `python3 docs/Sources/runbook_account2_reset_ops/check_reset_a2.py` |
| `check_reset_a2.py` | 12 cases against a fake broker module: renders, dry run, execute, a per-order failure, six refusals. | itself |
| `postcheck_a2.tmpl.py` | Steps 8 and 11 (and 8A–11A). With `TICKERS=[]` it is a flat-check that prints `account_number`; with the three tickers it also prints the fills of the reset orders. | `python3 docs/Sources/runbook_account2_reset_ops/check_postcheck.py` |
| `check_postcheck.py` | 5 cases against a fake broker module. | itself |
| `sim_reset.py` | The independent reviewer's simulation. It drives the REAL `scripts/run_paper_cloud_day.main()` for D+1/D+2/D+3 from an empty state against a fake flat broker at the 2026-11-16 closes. **One change from the reviewer's copy:** it refuses an existing or in-repo work path instead of `shutil.rmtree`-ing it. | `bash docs/Sources/runbook_account2_reset_ops/run_sims.sh .` |
| `sim_variant.py` | `sim_reset.py` plus an optional 4th argument that re-bases `contributions.start_date` in the WORK copy of the config. It covers my three variants: $10,000 re-base; option A at $10,000; option A at $10,000 with the re-base. | (run by `run_sims.sh`) |
| `run_sims.sh` | Runs the base simulation and the three variants under a fresh `mktemp` directory, then calls `check_sims.py`. | itself |
| `check_sims.py` | 28 assertions over the four outputs: exit codes 70/0/0, the contributions line, the arrival orders, mirror `tier_equity` on D+1/D+2/D+3, split-feed tickers, the D+1 ledger init row, the seeding reason. | (run by `run_sims.sh`) |
| `check_embedded.py` | Proves the runbook's §7.1–7.4 code blocks are byte-identical to the four committed scripts. | `python3 docs/Sources/runbook_account2_reset_ops/check_embedded.py` |

The simulations need the repo's Python environment (pandas, alpaca-py, python-dotenv). `run_sims.sh`
uses `<repo>/.venv/bin/python` when it exists, else `python`.

## Results on 2026-11-17 (branch `docs/account2-reset-runbook`)

| Check | Result |
|---|---|
| `check_archive.sh` | 5/5 PASS |
| `check_sched_state.py` | 7/7 PASS |
| `check_reset_a2.py` | 12/12 PASS |
| `check_postcheck.py` | 5/5 PASS |
| `run_sims.sh` → `check_sims.py` | 28/28 PASS |
| `sim_reset.py` safety refusals | REFUSE on an existing path; REFUSE on a path inside the repo |

## Byte-identity: runbook text vs these files

Checked with `check_embedded.py` (an exact byte comparison of the first fenced block under each heading):

| Runbook section | File | Result |
|---|---|---|
| §7.1 | `sched_state.py` | **IDENTICAL** (1,310 bytes) |
| §7.2 | `archive.sh` | **IDENTICAL** (1,857 bytes) |
| §7.3 | `reset_a2.tmpl.py` | **IDENTICAL** (2,551 bytes) |
| §7.4 | `postcheck_a2.tmpl.py` | **IDENTICAL** (942 bytes) |

**Before this commit, §7.1 and §7.2 were NOT identical.** Revision 2 embedded hand-compacted copies:
- §7.1 had the docstring reduced to one line and several statements joined onto one line;
- §7.2 had the 4-line header comment dropped and two assignments joined onto one line.

The executable statements were the same, but the text was not the tested file. Both blocks were replaced
with the committed files' exact bytes, and the check now exits 0. §7.3 and §7.4 were already identical.

**Not embedded in the runbook (no identity claim applies):** `render.py`, `fake_aws.sh`, every `check_*`
file, `run_sims.sh` and both simulations. The runbook names them and points here.

**`sim_reset.py` versus the reviewer's original** (`/tmp/runbook_review_fresh/sim_reset.py`, ephemeral):
the only difference is the work-root block. The original ran `shutil.rmtree(work, ignore_errors=True)`;
the committed copy refuses an existing or in-repo path instead. Confirmed with `diff` on 2026-11-17.
