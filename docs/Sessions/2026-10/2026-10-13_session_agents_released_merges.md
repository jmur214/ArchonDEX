# Session Summary: 2026-10-13 → 2026-10-14 — director: the agents released, nine merges, the verifier gap

## What was worked on

- **Five idle windows identified (A/B/C/D/E, one each, no duplicates) and released** after sitting five days waiting on an ownership confirmation that depended on a message nobody sent. The director's protocol, not the agents, cost the week.
- **C's RR-1 RE-SCORE finished (8/8, 10-14 12:35)** after two defects in C's own campaign were found and fixed: the feature ids in the cell list did not match the foundry registry (`triple_witching` → `triple_witching_premium`, `january` → `january_effect`), and a feature cell's record was labelled canonical on a harness rc that is always 0. The T195 harness FAILS OPEN on unknown ids (a 0-feature sweep prints an honest null and exits 0) — HIGH sub-item (18), fix on its own branch.
- **Merged onto main (each on R's APPROVE + the director's check, under the user's 10-08 delegation):** RR-7 (D1 returned and reverted), the B-1 prereg (frozen) + its launch checklist, D's RR-3 F2 docstring, B's observability-shipping proposal (four rulings stamped), B's 09-30 follow-up, E's T-363 attribution lessons + retraction, D's census SQLite blind spot (T-356b), B's observability backup, B's two test-lock conversions (execution tests), B's relay_gap janitor check, D's Option B proposal + data pass, C's RR-1 §4 (records + driver + analysis script), D's RR-6 brief. Pending behind A's RR-2 suite: RR-2, D's pin branch (1bae7eb), one full suite on main, the push.

## What was decided

- **The anchor RE-SCORE is a SIGN, not a headline:** +0.24 with a paired 95% CI [−0.06, +0.51] that includes zero. The director's first wording ("sign UP") was withdrawn under `[NN-SHARPE-CI]` on C's correction. Then the campaign showed the effect is **not one sign**: the 2012–24 foundry baseline book gives −0.32 [−0.70, +0.04]. Window vs book follow-up pre-registered before computing.
- **The merged honest-N gate (Option A) understates N by at least half** (D's pre-registered pass: 258 distinct trials; N_eff 33 → 267 without borrowed credit). Rulings 9.1 (fourth evidence class + persist attribution streams), 9.2 (no borrowed credit), 9.3 (pin both gate inputs by sha256, fail closed — merging behind RR-2). Cloud `--discover` stays halted until D's Option B registry ships; the stale 08-05 registry never ships.
- **RR-6 SPLIT:** 6a the defects (tri-state gate verdicts with no defaults; a REQUIRED gate's NOT_EVALUATED refuses promotion), what the no-promotion ruling waits for; 6b the design questions, its own brief.
- **The nightly verifier certifies origin/main, 65 commits behind local main since 10-08** — found by B's first-artifact check of the backup (its code never ran). Push proposed to the user (their gate); runner stays pinned to origin; `relay_gap` row added.

## What was learned

- **A handoff that depends on a message nobody is obliged to send is not a handoff.** "Tell me when they're open" cost five days. The director polls.
- **macOS purges /tmp after three days** — campaign logs and the resume wrapper vanished. Persistent logs live under the worktree's `data/logs/`.
- **Merge the exact hash an agent names, never the branch tip** — the Option B merge took a script the "docs only" guard warned about without aborting; the guard now aborts. **Run every test file that touches a changed module**, not only the branch's own tests — B's backup refactor broke a text-lock test on main that D found; fixed as an execution test.
- **Backticks inside a double-quoted `git commit -m` are command substitution** — the RR-6 brief's merge message (75ad730) lost the word `timeframe` ("reads  at :1283"); the brief itself is correct. Long messages go through `-F`.
- **The agents corrected the director three times in one night** (the sign, the first-artifact for the te fix, the RR-7 D1 premise). That is the system working.

## What was learned (afternoon of 10-14)

- **Verify a merge by `git log`, never by the absence of an error.** A heredoc-fed `git merge -F -` with redirections failed silently; the reconciliation note cited a file not yet on main for one commit. Long messages go through `-F <file>` written BEFORE the merge command; the merge is confirmed by `git merge-base --is-ancestor`.
- **A failing assignment under `set -e` aborts before the commit** — a merge was left staged (no commit) once, and once a resolution script asserted and aborted before writing, so the merge commit carried conflict markers for one commit (fixed the next commit). Resolution scripts write first, assert never on regexes; commit only after `grep -c '<<<<<<<'` is 0.
- **After EACH merge, run every test file that touches a changed module** — not only after the last. RR-2 then the pin broke RR-2's fixture (composition); caught only by the full-suite record D produced before the push.
- **The main-tree suite hang is now three-for-three** (10-08 ×2, 10-14): state U, no sockets, at the first `_drive_pulse`. A worktree run of the same commit does not hang. B's finding stands; until fixed, the push record comes from a worktree run.

## What was worked on (afternoon of 10-14, continued)

- **B-1 (T-365), the decisive test, CLOSED as a refutation** — H1 not met; nothing meets H1 (verdict `27c47b8`, FINAL; R's first read 0 mismatches over 1,190 cells). Two census HALTs before any return (the short window had to open at 2021-07 by input availability; three calendar features are blind before 2018), three pre-data amendments proven by file time, panel and harness deterministic ×2. CURRENT_STATE and the ledger carry the prereg's own words only (R-3).
- **RR-6a merged** (`f38d875`; tri-state gate verdicts, no defaults; Gate 7 runs for the first time ever); **Engine D's registry wipe fixed and merged** (`059e2ec`); the RR-2 no-promotion constraint LIFTED for the local path. R's review of that unit PROVED a THIRD writer — Engine A's `EdgeRegistry` at import — now a HIGH row; the three-writer design (imports never write; one atomic writer; consumers refuse) is brief v4 on main, **at the USER's gate (3 engines) with R's design read done: BUILD IT**. The three never-registered edges are all REFUTED in the ledger (T-122/T-174, T-123/T-129, T-135) — archive recommended, the user's call.
- Merged on R's approval: the harness fail-closed fix (`a8688fc`), E's T-364 (`b265bc0`), the RR-2 fixture composition fix (`18fa3f4`), the window-vs-book result (`72485f7`), D's per-gate table and the 2g reconciliation, the news-panel worktree-agnostic tests, two more docs units. The push record: D's full suite at `f38d875` 4125 passed / 0 failed on a clean detached worktree. Local main is ~154 commits ahead of origin; the push awaits the user's word.

## What was learned (afternoon of 10-14, continued)

- **Quote every heredoc delimiter** (`<<'EOF'`) whose body carries backticks or `$`: an unquoted one ate two spans out of a CURRENT_STATE line (fixed next commit). Long commit messages go through `-F <file>` written before the merge command; a merge is confirmed by `git merge-base --is-ancestor`, never by the absence of an error (one docs merge failed silently and the note that cited it went in first).
- **Check the ledger's next T-ID against the agents' unit names** — B-1's row collided with E's T-364 and was renumbered T-365.
- **The main-tree suite hang is three-for-three**; a worktree run of the same commit is the push record. Two suites at once on this 8 GB host is the 10-08 shape — the director broke the one-heavy-job rule once (A's run released over D's suite) and corrected it in minutes.
- **Windows are set by input availability, and the smoke covers the window's first twelve months** — both learned by halts that cost nothing because they came before any number.

## Pick up next time

- **THE PUSH on the user's word** (asked 07:15, 10:30, 14:45, 15:45 on 10-14; record green at f38d875). **The three-engine registry design on the user's word** (brief v4 on main; R: BUILD IT). **Archive vs register** the three refuted edges (user's call; archive recommended). After the push: the 03:00 janitor covers the real tree; B's 07:17 watch reads relay_gap's first row and the backup's first push; D uploads the mirror snapshot (R1) and builds the registry unit; E's acct-3 redeploy with its user's confirmation; B's testpaths and adjustment-class units at 07:17 / 08:23. After the push: B's 07:17 watch reports relay_gap's first row + the backup's first push; D uploads the mirror snapshot (R1); B's read-side-403-as-denied unit; E's bundled te-guard + loc unit, then the acct-3 redeploy with the user's confirmation; C's window-vs-book result and harness fix (→ R); D's RR-6a after RR-2; A's B-1 §11 step 0 + smoke, then the run.
- Open for the director: reconcile the gap report's 2g counting tension (lines 42–46) before the T-196 ledger row is edited (R's note).
