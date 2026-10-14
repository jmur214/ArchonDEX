---
id: merge-rr2-record
status: approved
kind: merge-record
asked_by: director
asked_on: 2026-10-14
---

# Merge record — RR-2 (`3b9e1e2`, health_check fix `71c2d9b`)

**Why this file exists.** The merge commit's message is only the conflict-resolution paragraph: the director's command sequence aborted (on the conflict) before the message file was written, and the later commit used the file that then held only the appended paragraph. The record intended for the commit is here; the commit is not rewritten.

**What merged.** A's `fix/referee-rr2-discovery-verdict` @ 3b6e5c2 (9bc1765, 2263d5b, 654b0e1 + the 10-13 merge of main with R's F2 fixture). Gate 4 can REJECT: the significance test returned the same value every run (a Sharpe-5.2 strategy scored p = 0.973; now p = 0.001). BOTH verdict-overwrite paths closed: the brief's (`mode_controller` recomputing `passed_all_gates` after the gauntlet) and a second copy in `scripts/run_evolution_cycle.py` reachable from the dashboard, which the review never named. Proven by REVERSION: the old code under the new tests logs "Cycle complete: 3 promoted, 0 failed" on three gauntlet-failed candidates and 12 tests fail; restored byte-identical. Seven other callers that passed a missing threshold now pass the real one.

**Independent review (Agent R, `review/agent-r-rr2`): APPROVE.** The reversion reproduced; the execution test asserts the cycle wrote statuses back, so a crash cannot pass vacuously; the sign-flip null is the valid null at the call site (Gate 4 runs on with-minus-base); Gate 7's NameError and Gate 3's phantom threshold confirmed on main. R's F1 (the two anchors): both defect lines are deleted — health_check items (2)+(3) FIXED by RR-2, anchors removed, (16) Gate 7 free pass and (17) Gate 3 phantom added under RR-6. R's F2 (the RR-3 + RR-2 union): fixed on the branch with `_honest_n_fixture` in D's helper shape and two positive-claim tests — RR-3's resolved N IS what every gauntlet call receives and RR-2's verdict binds; with no registry the cycle RAISES before any write.

**Ruling (director, under the user's 2026-10-08 delegation, on R's APPROVE + the director's check): MERGE.** Standing constraint now in force: the gauntlet verdict binds, so NO Discovery promotion cycle runs until RR-6a lands.

**Director's check.** A's full suite on the branch, main's venv, no ignores: 4012 passed, 1 failed, 22 skipped, 12 xfailed (464 s). The one failure is NOT RR-2's — proven on an archive snapshot of main a163f16: `tests/test_contracts.py::test_layer2b_consumer_keys_subset_of_producer_keys` fails identically on main because `scripts/rescore_rr1.py:103-104` (RR-1's driver) consumes `bootstrap_distribution` and `census` — latent since 10-08, invisible to the nightly (which tests origin/main); fixed by C at `56b7a05`. Merge-tree clean; doc_lint exit 0; the RR-2/RR-3 band tests pass on the merged tree. Conflict: `docs/State/health_check.md` only — the merge commit CARRIED THE MARKERS for one commit (the resolution script asserted and aborted before writing); resolved at `71c2d9b` with A's Description and A's RR-2 segment intact, verified by A read-only.
