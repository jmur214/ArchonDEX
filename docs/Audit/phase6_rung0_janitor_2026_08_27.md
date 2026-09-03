# Phase-6 rung 0 — the nightly janitor: first artifacts, and what its first run caught

**Date:** 2026-08-27 · **Agent:** B · Branch `feature/phase6-janitor` · **0 N_trials** (infra)
Implements rung 0 of `docs/Core/autonomous_development_prestatement.md`.

## 1. The load-bearing piece is the GUARD, not the orchestrator

The constitution names things an autonomous session may never modify: the **referee**
(the measurement stack), the **gates themselves**, and the standing **propose-first list**.
Those exclusions cannot live only in the janitor's prompt. A prompt is a request; a model
that misreads it — or is steered by something it reads mid-run — produces a diff nobody
vetted. `scripts/janitor_guard.py` therefore checks the **actual diff**, after the session
and before anything is offered for merge.

| property | why |
|---|---|
| allowlist **and** denylist, **deny wins** | `core/` is broadly allowed; `core/census.py` never is |
| **deny by default** | an unfamiliar path is refused, not waved through |
| **all-or-nothing** | one forbidden path refuses the WHOLE branch — partial acceptance would launder exactly the judgment we distrust |
| the guard is on **its own** denylist | otherwise the first "mechanical cleanup" could widen it; `doc_lint.py` too, a gate the janitor is checked **by** |
| a test asserts the **constitution still says what the guard enforces** | a rewritten pre-statement forces re-derivation instead of silent drift |

**The fix phase is OFF by default.** The pilot's first nights establish a checks-only
record; the director switches autonomous editing on with that record in hand — authority
by record, exactly as the ladder specifies.

## 2. What the first run caught — in my own code

`[NN-FIRST-ARTIFACT]`: 22 guard tests green, module imports clean, **integration dead on
first contact**. The wrapper was PATH-hardened against bare-`python` (my own 2026-07-08
bug); `janitor_nightly.py` then computed its **own** `ROOT/.venv/bin/python`, which does
not exist in a worktree. The wrapper's fallback launched it correctly and the module died
immediately — *the same interpreter-resolution class, reintroduced one layer down.*

Fixed with `sys.executable` (correct by construction in every worktree, venv and launchd
context) and pinned by a test that forbids a hardcoded venv path returning.

**The alarm chain proved itself on a real fault rather than a drill** — the failure
published to SNS with a MessageId from the wrapper's loud-failure path.

## 3. First artifacts (the constitution's rung-0 requirement) — OBSERVED

```
| check          | result | detail                                                    |
| worktree_canon | FAIL   | 2 uncommitted path(s); 0 commit(s) behind origin/main     |
| doc_lint       | PASS   | all doc-lint checks pass                                  |
| census_review  | PASS   | 23 clocks registered                                      |
| suite          | FAIL   | 3 failed, 3605 passed ... in 249.72s                      |
```
`data/state/autonomy_ledger.jsonl` row 1: `session/rung/trigger/checks/diff_summary/outcome`,
`outcome=checks_only`. The ledger's shape is what makes the autonomy stream **scoreable** —
and a bad class **demotable**, symmetrically.

**The designed failure behaviour held:** a failing check produced a record rather than
crashing the janitor. A red suite is the janitor doing its job; non-zero rc is reserved for
the janitor itself failing, which is the only thing worth paging for.

`janitor_ran_nightly` is registered in the clock census over the report surface (budget 2d)
— the census watches the watchmen. A test asserts the report is written to *the path the
clock actually watches*, since a report written elsewhere is an unwatched promise.

## 4. Six red tests on origin/main — three fixed, three escalated

**Fixed (mechanical, the janitor's chartered class):** three cadence tests hardcoded
`news_202608.parquet` while the clock correctly asked for September. **They went red on
2026-09-01 and the clock was right throughout.** The filename now derives from today's
month while `rows_stamp` independently controls row **content** — that separation is the
whole point of the frozen-feed test.

**NOT fixed, escalated — and one needs eyes:**
`test_firewall_breach_surfaces_loud_and_files_nothing` now returns **`ok` instead of
`FIREWALL_BREACH`**, because the drill-week `MIN_SCAN_DOCUMENTS` evidence floor
short-circuits **before** the firewall check. Either the fixture needs more documents, or
**a firewall breach can be masked by a clean-skip.** Two sibling failures in
`test_intel_pulse_t310` / `test_thesis_scan_runner_t325` are the same clean-skip class.
The firewall family is constitutionally off-limits to autonomous modification — the
guard's line, demonstrated on day one rather than in theory.

## 5. Suite tiering — the premise did not reproduce
Measured: **4:15 and 5:13** across two runs of ~3,590 tests, already under the ~5min bar;
the "20+ min" report did not reproduce here (machine load explains the spread).
`pytest-randomly` and `pytest-xdist` are **not installed** — so `-p no:randomly` in our
commands was a no-op, and **xdist would be a new dependency, i.e. propose-first.**

Built the tier regardless, because the janitor is its consumer: `pytest.ini` registers
`slow`, four expensive replay/perf tests carry it (95s of work isolated to the nightly
run). **Determinism pins deliberately stay in the fast tier** — a determinism regression
that waits for the next nightly is a measurement-integrity gap the seconds do not buy back.
**Measured after the split:** the fast tier runs **3:00** (3,611 passed, 4 deselected)
against 4:15-5:13 for the full suite — so the tier earns its keep even though this branch
ADDS 28 tests. Machine load still moves these numbers by ~20%, so read the direction, not
the decimal.

## 6. Not done here
- `ops/com.archondex.janitor.plist` is written but **NOT loaded** — installing a schedule
  is deploy-shaped, therefore propose-first. Install steps are in the file, including the
  reminder to verify on the **next scheduled firing**, never a manual run (the gap behind
  the 2026-07-13 silent outage).
- The **scheduled director/worker passes** — the constitution sequences them second.
