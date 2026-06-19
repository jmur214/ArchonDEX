is anything in our documentation such as the claude.md or other files too strict - for example the constraint about not working on the engines without my approval, so that good work is halted and diverted to other places that are less relevant instead?

Honest read: mostly well-tuned, with one rule that's clearly too strict and one that's quietly under-strict. Specifics:

## The Engine B / live_trader propose-first rule is correctly calibrated

I want to address this directly because you raised it as the example. The discipline is *not* halting Engine B work or diverting it. Look at what's happened on Engine B in the last 3 weeks: T-055, T-055c, T-055d, T-055e, T-055g, T-055h, T-057, T-057b, T-057c-det, T-057c-fp-followup, T-088. Eleven Engine B dispatches. The rule didn't slow any of them down; it just kept the *flag-flips* gated.

That gating then caught two real failures:
- T-055e cleared the strict gate on 5-yr substrate. Approved at "user-decision gate," not auto-flipped. T-055g/h then refuted it on the larger substrate. If you'd been on auto-flip, vol-target would be in prod right now with a -0.214 Sharpe drag.
- T-057 same story: +0.793 lift → autonomous flip would have shipped → 12-yr re-verify showed -0.128.

Without the propose-first ceremony, you'd have shipped both. The "ceremony" was the gate that protected you. Keep it.

For the *non-B* engines (A, C, D, E, F), CLAUDE.md already grants autonomous improvement. T-006, T-013, T-022, T-043, T-087, T-089 all proceeded without per-instance approval. The discipline isn't symmetric — Engine B is special, and rightly so.

## What IS too strict

**1. "Changes to the documentation system itself are propose-first."** This rule held up the doc-system overhaul. The dev had to write a 4KB proposal, get external review, get my review, get your review, then implement. That's correct for *structural* changes (new files in `docs/State/`, hook edits, reading-order changes) but overkill for minor maintenance (fixing a stale link in execution_manual.md, updating a path in README.md, expanding an example in SESSION_PROCEDURES.md). Carve out: "structural changes propose-first; minor maintenance autonomous." Same shape as how engine work is split.

**2. The "never guess CLI commands" rule has a hidden tax.** It pushes agents to either (a) read all 25K bytes of execution_manual.md before any bash invocation, or (b) ceremoniously add a new entry for every single new CLI use. In practice agents do (a) once per session, which inflates session warmup. The rule's goal — don't break things with confident wrong commands — is right. But the implementation cost is high. Worth examining whether the protective value at this maturity level still justifies it, or whether `--help` + a small cheat-sheet covers the same ground.

**3. The hard ban on `cockpit/dashboard/`** is correct *and* permanent — it's been "deprecated" for months. Either it gets deleted (which the "Archive never delete" rule prohibits without ceremony) or it stays forever as a grep-tax + cognitive-load tax on every session that wonders "which dashboard?" Add an explicit deletion date: "deprecated, archive by 2026-Q3, delete from working tree by 2026-Q4."

## What is quietly UNDER-strict

**1. "Archive never delete" has no compaction policy.** Today's archive will be next year's junkyard. Every session that greps for a function name hits the archive. Every agent reading docs/Archive/ files might mistake them for current truth (CLAUDE.md says "Files in `docs/Archive/` are point-in-time snapshots — do not treat their findings as present-day truth," but that warning is only seen if the agent reads CLAUDE.md and remembers it during a grep). Pair the "archive never delete" rule with a **quarterly compaction**: archive entries older than 1 year get tombstoned into a single index file per quarter, raw files moved to a cold-storage subdir excluded from default grep. The doc overhaul flagged this; it should ship as part of doc_lint.

**2. "Pre-registration before any run" is rule `[NN-MBL]` (MBL Gate-0) but only the MBL part is mechanized.** The other half — that every run is pre-registered with hypothesis + threshold + N_trials_consumed — is purely on-honor. The deterministic-gates hook spec the other dev drafted addresses this; until that ships, you're trusting discipline at a place where mechanization is available.

**3. Engine boundaries are "inviolable" but the aggregator architecture I keep flagging genuinely touches the A↔C boundary.** Strictly read, it'd require propose-first ceremony spanning two engines. That could discourage the one structural change the project most needs. Worth a pre-emptive clarification in CLAUDE.md: signal *combination* (linear or non-linear aggregator) is Engine A's authority; portfolio *allocation* (weighting positions across signals' outputs) is Engine C's. The hierarchical aggregator I've been describing stays in Engine A by that reading. Pre-clarifying prevents future paralysis.

## What's perfectly calibrated and shouldn't move

- CI-aware kill thresholds (non-negotiable `[NN-SHARPE-CI]`)
- MBL Gate-0 (#7)
- Substrate re-verify before flag-flip (#9)
- Float-equality on sample statistics (#8)
- Never force-push / rebase published history
- Never commit secrets, never commit large data files
- Engine B + live_trader propose-first

These have all earned their place by catching real failures.

## Net answer to your question

The discipline isn't pushing good engine work to less-relevant places. Look at what's been shipped in the last month: 90% of it directly serves the headline alpha question (T-053b, T-055, T-057, T-087, T-088, T-092 in flight). The "diversion" you might be sensing is the contract test suite (T-090/T-091) and determinism work (T-057c-det) — but those caught **10 confirmed bugs** between them. That's not diversion; that's the falsification machine doing what it was built to do.

Two concrete adjustments:
1. **Loosen:** doc-system propose-first only applies to structural changes, not maintenance.
2. **Tighten:** add a quarterly archive-compaction pass + a deletion date for `cockpit/dashboard/`.

Both are doc-lint additions, both can ride along on the next doc-system iteration.

