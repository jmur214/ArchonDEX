---
task_id: T-2026-08-06-339
title: T-339 — the CLOSURE MANIFEST: closure-grade artifacts made un-deletable
date: 2026-08-06
worker: Agent B
branch: feature/closure-manifest-t339
status: DONE. Both integration-bar artifacts produced. The root cause is WIDER and DIFFERENT than the reported deletion — see §2.
---

# T-339 — every closure is one cleanup away from unverifiable. Now it isn't.

## 1. The manifest (`scripts/closure_manifest_t339.py` → `data/research/closure_manifest_t339.json`)
221 ledger rows swept; **105 carry a MEASUREMENT-grade verdict** (quote a Sharpe/Sortino/
CI/DSR/MaxDD/CAGR or consume N_trials). Receipt state:

| state | count | meaning |
|---|---|---|
| **COMPLETE** | **17** | written verdict **and** locatable data artifacts |
| **DOC-ONLY** | **77** | verdict survives; **no task-linkable data** |
| **MISSING** | **11** | neither — **already unverifiable** |

## 2. ⚠ The root cause is NOT (only) deletion — it is the ABSENCE OF A TASK→RECEIPT LINK
C/T-337 found five deleted Arm-1 run dirs. The sweep found something worse and more
general:

**49 `performance_summary.json` files are alive on disk under `data/trade_logs/<uuid>/` —
and the UUIDs are cited in NO document.** I checked: a sampled run UUID appears in zero
files under `docs/`. The ledger's artifact column names an *audit doc*, never a run id.

**So those receipts cannot be associated with the closure they support. A receipt nothing
points at is already unverifiable while sitting on disk** — which is also *why the
deletions went unnoticed*: nothing referenced them, so nothing broke visibly when they
went. Restoring the five Arm-1 dirs would not fix the class; only a durable task→receipt
link does.

This reframes the standing rule: it is not enough that files exist somewhere. **The
closure must record where its receipt lives.**

## 3. ALREADY UNVERIFIABLE — the answer to the dispatch's part (4)
**11 closures with no receipts at all:**
`T-041, T-041b, T-173, T-180, T-200, T-209, T-212, T-218, T-259, T-263, T-334`
(T-180 is the reported case; **T-041/T-041b, T-173, T-209, T-212, T-218, T-259, T-263** are
newly surfaced. T-334 is mine from last week — its receipts are live parquets, not a
task-keyed dir, so it is a manifest-resolver false positive worth fixing rather than a real
loss; stated rather than quietly excluded.)

**Plus 77 DOC-ONLY** — the verdict is readable but the numbers cannot be re-derived. Some
of these are re-analyses with no separate data artifact by design; others are genuine
losses. **The manifest does not distinguish those two, and I am not claiming it does** —
separating them needs a per-row read, which is a follow-up, not a claim I can make now.

## 4. ARCHIVED — `s3://…/closures/<TASK-ID>/<kind>/` (immutable, task-keyed)
**123 objects pushed across 93 task prefixes**; 11 MISSING closures skipped (nothing to
push). Layout is task-keyed by construction, so the link the system lacked now exists in
the archive itself. `[NN-ARCHIVE]` extended from code to measurement artifacts.

**INTEGRATION-BAR ARTIFACT — restored from S3 and verified readable end-to-end:**
```
$ python -m scripts.closure_manifest_t339 --verify T-311
{ "task": "T-311", "restored_files": 2, "rc": 0,
  "readable": ["t311_deep_reverify.json (json OK)",
               "deep_reverify_sleeve_t311_2026_07_27.md (122 lines)"] }
```

## 5. The standing rule, wired — enforcement point STATED
`check_closure_receipts()` in `scripts/doc_lint.py`.

**Why doc_lint and not the census** (the dispatch left the choice to me): the closure
*claim* is made in the **ledger — a document**, so the check belongs where the claim is;
doc_lint already runs pre-commit; and a census check fires at **run** time, before a
closure exists to have a receipt.

**FORWARD-ONLY (grandfathered at 2026-08-06):** the 105 historical measured closures are
*reported* by the manifest, not failed by the gate — retroactive enforcement would block
every commit for exactly the debt this gate exists to stop accruing.

**Proven to bite, not just to exist:** inserting a fabricated measured row
(`T-999 … Sharpe 1.9, ci_low 0.4`) produced
`[FAIL] T-999: measured verdict with NO locatable receipt (archive it under
closures/T-999/ and cite the audit doc)`, and the gate returned green when removed.

**And it cannot go silently inert:** the first version reported green because
`scripts.closure_manifest_t339` was unimportable under doc_lint's bare `sys.path` — a
checker that no-ops while reporting OK is worse than no checker (the exact silent-wrongness
class this program keeps paying for). Fixed: the repo is put on `sys.path`, and an
unimportable manifest now returns **WARN with "receipt check INERT"**, never PASS.
