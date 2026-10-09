---
id: merge-feature-doc-anchor-lint
status: pending
kind: merge
asked_by: agent_b
asked_on: 2026-09-30
---

# Merge `feature/doc-anchor-lint` — HIGH-row anchors in `doc_lint`

Approved in principle 2026-09-29, with the user's condition as design constraints: *no friction without an exit*. This change is referee-adjacent (it touches `doc_lint`, the health-check contract, and CI), so it goes through the full process: branch, this entry, the director answers. **Agent B did not merge it and cannot.**

## What it does
- An open HIGH row in `docs/State/health_check.md` can cite the code line that witnesses its defect, in this form: ``- Anchor: `path:N` contains `text` ``.
- `doc_lint` check 10 FAILs when line N no longer contains the text.
- Each failure names the exact fix: **(a)** close the row (the defect is fixed), or **(b)** deliberately update the anchor (the line only moved). For (b), the check reports where the same text now appears, as a lead to confirm rather than proof.
- The check applies only to open HIGH rows in Active Issues.
- Matching is an exact substring of the one cited line. It is never widened.
- Malformed anchors FAIL. So does `Anchor: none` given without a reason.
- HIGH rows flagged on or after 2026-10-01 that carry no anchor get a WARN. Older rows are grandfathered.

Commits `2ed7704` (check, janitor guard, 27 tests), `0221f95` (four seeded anchors and the Format doc), `93b5011` (CI).

## Evidence
- **Tests:** 27 new tests, plus 32 existing janitor tests, all green.
- **Reversion proof:** unregistering the check fails the entrypoint test. Restoring `mechanical=True` in the janitor fails the janitor test. Restoring the code makes both pass.
- **Retro-drill against the real history:** I put an anchor on the stale HMM row (`config/regime_settings.json:101` contains `hmm_3state_v1.pkl`).
  - At `20f6fc6^` it **PASSES**.
  - At `20f6fc6` (the 08-26 fix) it **FAILS**, and the message says "(a) applies — close the row".
  - That row actually stayed open three weeks and cost two dispatches.
- **Branch drill** (the seeded anchors read from each branch's own files):

| branch | result | the fix it names |
|---|---|---|
| `origin/main` | PASS, 4 anchors hold | — |
| RR-1 | 1 FAIL, text gone | close item (1) |
| RR-2 | 2 FAIL, text gone | close item (2) |
| RR-3 | 2 FAIL, **innocent moves** of RR-2's lines | re-point `:1338`, `:1399` (one line each) |
| RR-7 | 1 FAIL, text gone | close item (11) |

## What the drills changed (found by running, not by review)
1. **A symlinked root read every anchor as absent** (macOS `/var` → `/private/var`). Fixed by comparing resolved paths to resolved paths, and locked with a test.
2. **The move hint had misled.** On RR-3's branch, a seeded `return 1` anchor "moved" to a line in RR-3's new docstring: *"Both used to return 1"*, which announces that the defect is **fixed**. Anyone following the old hint ("the line only MOVED → change :80 to :146") would have kept a fixed defect's row open indefinitely. Two changes:
   - The hint now reads "**IF** the line only moved… confirm that line still witnesses the defect (a match can be a comment or a docstring)".
   - Item (4) is **not anchored**. Its witness is a two-line pair, and `2.0 * math.log(n_effective)` survives on RR-3's branch as well.

## Honest limits
- **It detects; it does not block.** The pre-commit hook is not installed on this Mac (`core.hooksPath` holds no hooks). Detection happens in two places:
  - **CI:** now runs on every push, because a fix is usually code-only.
  - **The nightly janitor:** runs the full doc_lint.

  So a fix that goes red shows up within one push or one night. It is not refused at commit time.
- **An anchor certifies that the quoted code is still there, not that the defect is.** A defect fixed somewhere else (for example, a guard added upstream while the witness line stays) will not trip the anchor. For the alpha-frontier row, the behavioral witnesses remain the `xfail(strict)` tests.
- **The janitor's fix phase is off.** When it is on, a broken anchor marks doc_lint non-mechanical, so an anchor failure is never handed to the autonomous session. That check lives in `janitor_nightly.py`. The guard itself does not inspect the content of a diff.

## Decisions for the director
1. **Merge:** approve or decline.
2. **Order.** If this lands before the RR branches, each RR merge turns doc_lint red until the alpha-frontier row is updated. That is the class this change exists to fix, and the table above gives the exact edit for each branch. **Recommended: lint first.** The alternative is to land it after the RRs and seed anchors only on what is still open.
3. **Unanchored new HIGH rows: WARN (as built) or FAIL?** Recommended: keep WARN until the `engine-auditor` and `code-health` templates carry the Anchor line (that is agent-architect's lane), then promote to FAIL. The exit, `Anchor: none — <why>`, costs one line.
4. **Proposal only:** a content rule in `janitor_guard.py` that refuses any diff touching a `- Anchor:` line. The guard is constitutional, so I did not edit it.

## To answer
Set `status:` to `approved` or `declined` in the frontmatter above and commit.
