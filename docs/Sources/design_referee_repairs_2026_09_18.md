# Referee repairs — the design, and a verdict that changes the unit

**Status: DESIGN. Nothing built. Plan-before-touch, per the 2026-09-18 ruling.**
**Agent:** B · Branch `feature/referee-repairs-design` · **0 N_trials**

## 0. The verdict first: BOTH DISPATCHED REPAIRS ARE ALREADY DONE

Verified against live code today, not against memory or the audit that raised them:

| repair | live state | landed |
|---|---|---|
| Engine E loads the legacy HMM | `config/regime_settings.json` → **`hmm_3state_crisis_v1.pkl`**; the `HMMConfig` dataclass default agrees | `20f6fc6`, 2026-08-26 |
| HMM blind pre-2020 (12 un-backfilled tickers) | panel **5,041/8,361 complete rows (60.3%)**, span back to **2006-04-04**; `tlt_ret_20d` NaN **36.6%**, was 82.1% | `068afba`, 2026-08-26 |

**The record is what is stale.** `health_check.md:130` still reads *"Status: not started"* and quotes
`config/regime_settings.json:101` as pointing at `hmm_3state_v1.pkl` — a line that has not said
that for three weeks. The fresh-eyes audit read the living doc in good faith, C10 re-raised it,
and a dispatch was spent on work already merged.

## 1. This is T-195's class, and I am the reason it recurred

On 2026-08-27 I closed T-195's stale record and wrote the lesson down:

> *A doc that PROPOSES fixes and a doc that IMPLEMENTS them must link in both directions.*

The day before, on 08-26, I had fixed the two HMM defects in code and **never closed their
`health_check` rows.** I wrote the rule and had already broken it. That is the same shape as
yesterday's trigger finding — **a patch where a rule was needed** — one layer up, and it has now
cost two dispatches (T-195, and this one).

So the honest unit here is not "repair the referee". It is: **close the record, and make this
class detectable instead of relying on whoever fixes something to remember to close its row.**

## 2. What actually remains (small, and real)

**(a) `multires_hmm.py:86` still defaults to the legacy model.**
`MultiResolutionHMM.__init__` does `artifacts or MultiResHMMArtifacts.default()`, and that
default names `hmm_3state_v1.pkl`. Unreachable in production — the detector always passes
`daily_path=cfg.hmm.model_path` — and `multires_enabled=False` besides. But it is a legacy
pointer hiding behind a fallback, which is the exact shape this program keeps finding. Propose:
derive the default from `HMMConfig`, or delete the fallback so a caller must be explicit.

**(b) The partial-backfill guard I recommended in August and never built.**
`health_check` carries my own suggestion: *"a check that fails when a ticker's span is materially
shorter than its `tr_reconciled` counterpart, so a partial backfill announces itself."* The
repoint fixed the two automated consumers; nothing stops the next truncation. Propose: a test
comparing each `data/processed/<T>_1d.csv` span against its `tr_reconciled` twin, failing on a
material gap for the load-bearing tickers.

## 3. The class fix — structural, therefore the user's call

Both recurrences share one mechanism: **a HIGH finding's row can outlive the defect it
describes, and nothing notices.** `[NN-AUDITS-NOT-CURRENT]` tells a reader that audits are not
current state — but `health_check.md` IS the current-state surface, so a stale row there is
believed.

Proposed, for review rather than for building now:

1. **A HIGH entry must cite a verifiable anchor** (`file:line` plus the string it expects to
   find), and `doc_lint` fails when the quoted line no longer contains it. That converts "this
   row is stale" from something a human must notice into something CI states. It is the
   closure-receipt pattern (T-339) pointed at findings instead of measurements.
2. **Fixing code that a HIGH row describes must close the row in the same commit** — enforced
   the only way it can be: the anchor check above fails the moment the code changes, so the
   commit that fixes the defect cannot be green until the row is updated.

⚠ **This touches `doc_lint` and the health-check contract — the referee's own bookkeeping — so it
is exactly the kind of change the constitution says is not autonomously modifiable.** Bringing it
as a proposal, not a branch.

## 4. What I propose to do next, pending review
1. **Close the two `health_check` rows** with dated resolution stamps and commit hashes
   (record-only, no code).
2. **(a)** and **(b)** above as one small unit, propose-first since both sit in Engine E's
   measurement path.
3. **§3 only on the user's word**, since it modifies a gate.

I have deliberately touched none of it yet.
