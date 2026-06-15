---
name: pattern-verdict-on-unmerged-branch
description: Highest-leverage doc-drift mode here — CURRENT_STATE/LEDGER cite refuted-verdict audit docs that live only on unmerged feature branches; the number appears nowhere on main
metadata:
  type: project
---

The fork-deciding verdicts get committed to `feature/*` branches and their
numbers are promoted into `CURRENT_STATE.md` + `TASK_LEDGER.md` on main BEFORE
the audit doc is merged to main. The verdict is real (cloud-run data in
`data/cloud_runs/`, commits on the branch) but un-traceable from main.

**Confirmed 2026-06-15:**
- T-118r de-gross REFUTED (0.752→0.680) → audit `hmm_overlay_rerun_t118r_2026_06_14.md`
  is NOT on main; lives on `feature/hmm-transition-overlay-rerun-t118r`
  (commits 61ef84a, 7f6d0f9). `0.680` appears nowhere in `docs/Audit/` on main.
- T-128r sleeve REFUTED → ledger cites `spot_sleeve_closeout_relaunch_2026_06_12.md`
  "(clean re-run)" but that file is the 2026-06-12 INVALID-substrate relaunch,
  NOT the clean re-run. Clean verdict is on `feature/spot-sleeve-closeout-clean-t128r`.

**Why:** the multi-session worktree pattern (CLAUDE.md MULTI_SESSION_ORCHESTRATION)
means workers commit audits on their own branches; the director updates
CURRENT_STATE from the relay BEFORE merge. The dashboard runs ahead of main.

**How to apply:** when a CURRENT_STATE/LEDGER verdict quotes a Sharpe to 3dp,
grep `docs/Audit/` on main for that exact number AND `ls` the cited filename
before trusting the citation chain. If absent, check `git log --all -- <file>`
and `find . -iname "*<taskid>*"` — the data + branch usually exist. Distinguish
"verdict is fake" (rare) from "verdict is real but its doc isn't merged"
(the actual failure mode here). Logged to health_check 2026-06-15 as HIGH.
Related: [[pattern_verdict_buries_capability]] (the inverse — a verdict that
hides a still-shipped capability).
