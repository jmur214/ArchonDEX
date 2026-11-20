---
name: pattern_cloud_input_availability
description: 2026-11-20 T-411 — the paper image is git-archive + 2 staged data sets, so any ROOT/data read on the paper path is blind in-cloud unless an S3 pull brings it BEFORE the reader runs; three silent-starvation shapes found (absent file → [], read-before-sync, never-fed parameter)
metadata:
  type: project
---

The paper image (`scripts/build_paper_image.sh`) is `git archive` + ONLY the PIT membership
parquet + `data/processed/tr_reconciled/`. No `data/` file is tracked in git. So a reader on the
paper path sees a `data/...` file in a Fargate container only if an S3 pull brings it, and only if
that pull runs BEFORE the reader in `run_paper_cloud_day.main()`. The pulls are: `cloud.pull()`
(DURABLE_PATHS/DIRS, step 1), the news tape (before the intel pulse), `pull_readonly_from`
(account-3 notes), and `pull_altdata()` — which runs at step 7, AFTER the intel pulse and the eval
harness.

**Three starvation shapes found in one pass (all report "ok" with zero work):**
1. ABSENT → silent `[]`: `eightk_feed` returns [] when the 8-K panel or special-sits file is
   missing; the event desk had never opened a position (0 in 38 sessions on 09-18).
2. READ-BEFORE-SYNC: the eval harness's KXFED/FRED reads, the agentic `query_rate_path` and the
   thesis-scan rate path all run before `pull_altdata()`.
3. NEVER-FED PARAMETER: `ThesisBook.record(falsifiers_fired=...)` has only a test caller, so
   "resolver" falsifiers are deadline-only.

**Why:** prior liveness sweeps flagged these channels "UNVERIFIABLE" but nobody traced WHY. The
director's 11-19 health row called the KXFED/FRED readers "reads only, no production effect",
which was true of the checkout-root question and missed the step order.

**How to apply:** for every `ROOT / "data" / ...` read on the paper path, answer three questions:
is it staged in the image? which pull brings it? does that pull run before the reader? Then grep
every optional parameter of a durable-book `record()` for a production caller. Pairs with
[[pattern_flag_vs_path_disconnect]] (config says live, path says dead) and
[[pattern_product_moved_charters_stayed]].
