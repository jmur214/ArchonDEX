# Documentation-System Audit — external fresh-eyes review (2026-06-19)

> Cold, independent audit of ArchonDEX's **documentation & knowledge system** (not the trading
> logic, not code quality — the docs: organization, currency, automation, cold-onboarding, and
> failure modes). Reviewer onboarded cold via the prescribed reading path and verified every
> load-bearing claim against code/live runs. All findings cite checkable `file:line`.
>
> Scope note: this is the durable record of the chat-delivered audit commissioned via commit
> `3717210` ("fresh-eyes documentation-SYSTEM audit prompt"). Actionable items are queued in
> `docs/State/health_check.md` (consolidated entry, same date) — deliberately NOT a new State
> tracker (see Failure Mode: tracker-proliferation).

## TL;DR verdict

One of the most **deliberately-engineered** doc systems I've audited — lifecycle-organized,
hook-instrumented, with explicit anti-rot disciplines, a real culture of brutal honesty, and even
*self-diagnosing* meta-docs. It is also **quietly eroding in the places it tells you to trust most.**
The always-loaded constitution carries stale headline numbers the rules say *win*; the "at-a-glance
dashboard" is a 1,100-word wall; the supersession discipline (a non-negotiable) points at a
`MEMORY.md` file **that does not exist**; the linter built to catch all this **runs, prints `[FAIL]`,
and exits `0`**; and the system's instinct on each discovered blind spot is to *spawn another tracker
doc*. It still serves its real purpose (durable decision-memory for a solo director + rotating AI
agents) but has crossed the line where it can mislead a careful reader, and its self-correction
machinery is partly dead.

---

## 1. Cold-onboarding — oriented vs. misled

Followed the prescribed order: `CLAUDE.md` → `CURRENT_STATE.md` → `SESSION_PROCEDURES.md` →
`docs/README.md` → `docs/Core/README.md` → `PROJECT_CONTEXT.md` / `GOAL.md`.

**Oriented well (genuine strengths):** `CLAUDE.md` is an excellent constitution (concrete,
rationale-backed non-negotiables that cite their own regression tests). `SESSION_PROCEDURES.md` is
the best file in the repo (Paths 1–6 decision tree, lifecycle rules, trade-log cleanup). The hooks
are carefully engineered — externalized for syntax-checkability, fail-open, with an explicit
"never brick session-end" invariant.

**Misled (in encounter order):**
1. **The first post-constitution read is the worst-organized file.** `CURRENT_STATE.md:3` header is a
   single ~1,100-word paragraph of dense T-ID shorthand. Hard caps (`:27`) apply to the sections but
   **not** the header — which became the dumping ground the caps exist to prevent. Not "at-a-glance."
2. **North-star is half-stale.** `GOAL.md:4` still opens "interacting with the `trading_machine-2`
   codebase" with the old "outperform the market" framing, then bolts the current success bar on at `:18`.
3. **Architecture bible contradicts itself and the code.** `PROJECT_CONTEXT.md:27` calls Engine C
   "*Planned*" while its own table at `:79` marks it "✅ Functional"; `:18` asserts the True-Edge
   selector is applied in present tense — `DESIGN_FIDELITY.md:19` confirms it was **NEVER-BUILT**
   (`signal_processor.py:615` is weighted-sum only); `:86` calls Live Trading "Scaffolded — broker
   interface exists" but that stub was archived as dead (T-169, `health_check.md`).
4. **A Tier-1 "rarely changes" onboarding doc has 4 broken pointers.** `docs/Core/README.md` says
   health_check lives in `docs/Audit/` (`:106`, it's in `docs/State/`); points to a root
   `DOCUMENTATION_SYSTEM.md` (`:114`, **doesn't exist**); calls `docs/Archive/` "Gitignored" (`:109`);
   references `docs/Core/forward_plan_<date>.md` (`:108`, wrong path).

**Trust timeline:** a doc-only reading would have been **wrong on three load-bearing facts** — the
baseline Sharpe, whether the True-Edge selector exists, and the honest N_trials. I would not trust a
doc-only model without cross-checking code, which is the opposite of what a doc system is for. To its
credit, `CURRENT_STATE.md:27` warns it decays past 3 days.

---

## 2. System map

- **Root instruction layer:** `CLAUDE.md` (constitution, auto-loaded); `README.md` (human-facing,
  the only doc consistently using "ArchonDEX"); **a second, competing instruction system** at
  `.agent/` + `.aider.conf.yml` (see Failure Mode F).
- **`docs/` (lifecycle-organized):** `Core/` (stable design + `NON_NEGOTIABLES.md` depth-copy);
  `State/` (**now 15 files** of "current truth"); `Measurements/<YYYY-MM>/` (frozen raw cells);
  `Audit/` (frozen verdicts); `Sessions/` (frozen summaries + `Other-dev-opinion/`); `Archive/`;
  `Sources/`.
- **AI memory:** `.claude/agent-memory/<agent>/` — 6 of 10 subagents have a curated `MEMORY.md` +
  `project_*`/`feedback_*`/`pattern_*` notes (272 KB, 52 files, all git-tracked).
- **Automation:** `sessionstart_context.sh`, `stop_freshness.sh`, PostToolUse→`sync_docs.py`,
  pre-commit→`doc_lint.py`.

**Meta-pattern:** the State layer grows by *self-similar accretion* — each blind spot spawned a new
doc (`capability_ledger.md`, `conditional_shelf.md`, `DESIGN_FIDELITY.md`). Each is individually
sound; collectively a reader must reconcile **8+ overlapping "current-truth" surfaces.**

---

## 3. Failure modes (each: how it misleads / self-corrects?)

**A. Constitution carries stale headline numbers the rules say *win*.** `CLAUDE.md:131` +
`NON_NEGOTIABLES.md:116` say baseline "0.598"; live is 0.751/~0.81 (`CURRENT_STATE.md:13,74`).
`CLAUDE.md:129` freezes "~75" N_trials; dashboard says "125 rows / ~260+" (`:73`). The DSR/MBL bar is
`2·ln(N)/SR²`, so a 3.5×-stale N yields a wrong threshold *in the constitution*, and
`CLAUDE.md` says "this file wins." `health_check.md:689` explicitly says "Do not quote 0.598 as
current." **Self-corrects? No** — precedence protects the stale numbers.

**B. Internal numeric contradiction inside the dashboard.** `CURRENT_STATE.md:13` (anchor table) gives
26yr ci_low **0.371**; `:17`/`:37` give **0.382** and use it to size the headline distance to the 0.40
kill-line. 16yr similarly carries both 1.162/0.676 and 1.105/0.625. **Partially** — supersession is in
the ledger; both still print live with no inline marker.

**C. "At-a-glance dashboard" that isn't; header has no cap.** (See §1.1.) **No** mechanism caps the header.

**D. Supersession non-negotiable points at a phantom file.** `CLAUDE.md` + `CURRENT_STATE.md` invoke a
single "**MEMORY.md**" repeatedly; **no such root/docs file exists** — only 6 per-agent
`.claude/agent-memory/<agent>/MEMORY.md`. `SESSION_PROCEDURES.md:463` points to a third dead path
(`.claude/projects/.../memory/`). "Follow the supersession pointer" is unresolvable. **No.**

**E. The doc-linter runs, reports `[FAIL]`, and exits `0`.** Live `python scripts/doc_lint.py
--pre-commit`: `[FAIL] TASK_LEDGER rows complete: 11 issue(s)`, plus 3× `[WARN]` because `MEMORY_DIR`
is hardcoded to `/root/.claude/projects/-Users-jacksonmurphy-Dev-trading-machine-2/memory/` (macOS,
old-repo-name, doesn't exist) — final `EXIT: 0`. `--no-verify` bypasses it; CI (`feature_ablation.yml`)
only backs the Foundry gate, not doc-lint. The one automated guard for memory/supersession hygiene
**protects nothing here.** **No — the corrector is broken.**

**F. A second, contradictory instruction system at the root.** `.agent/` + `.aider.conf.yml`
(GPT-4.1-mini, git-tracked): `.agent/rules.md:7` points to `docs/Audit/engine_charters.md`
(**doesn't exist**); `.agent/rules/terminal-commands.md` says testing/debugging/downloading are
"always approved" (CLAUDE.md gates these); `.agent/workflows/4_autonomous_evolution.md` names
`data/governor/edges.yml`/`ga_population.yml` vs CLAUDE.md's `edge_weights.json`. Looser on safety,
partly broken. **No** — nothing flags it.

**G. Auto-generated `index.md` are systemically stale.** `sync_docs.py` regenerates them and the
PostToolUse hook fires, but **nothing stages/commits the output**: across history 22 commits touched
`engines/**/*.py`, only 2 ever touched any `index.md`. Running it now produces immediate diffs (e.g.
`engine_b_risk/index.md` missing the entire T-209 `decompose()` backbone its code ships).
`sync_docs.py --help` silently rewrites 9 tracked files (no argparse). **No** — hook generates
freshness, workflow never captures it.

**H. "Archive, never delete" has a silent data-loss path.** `.gitignore:44` is a bare `Archive/`;
`git check-ignore -v docs/Archive/SOME_NEW_FILE.md` → matched. Existing 10 files predate the rule
(git ignores only untracked); **any newly-archived doc is silently un-committable** and lost when the
ephemeral container is reclaimed. `docs/Core/README.md:109` documents Archive as "Gitignored" while
`docs/README.md` treats it as committed history — ambiguous authority on whether the archive is even
version-controlled. **No.**

**I. AI memory is load-bearing but rotting and director-invisible.** All 52 files predate the
2026-06-18 pivot; zero reference the new goal. Unmarked dead theses:
`edge-analyst/project_alpha_frontier_lane_closed_2026_06_15.md:48` still lists VRP as "open" (refuted,
T-174); `architect/strategic_frame_..._2026_06_15.md:36` redirects to the "T-132 frontier" the pivot
declared exhausted. Writing is prompt-enforced; **reading is not** (no agent lists its own MEMORY.md as
required reading) and **no hook surfaces memory**. The single sharpest strategic objection — *"is an
autonomous 6-engine system even the right vehicle for a $5K Roth vs a 2-line index+satellite?"*
(`architect/strategic_frame_...:41`) — **lives nowhere in `docs/`.** **Partially** (best insights are
hand-promoted into `capability_ledger.md`); indexes have no cap/stamp/supersession column.

**J. Brittle surfacing greps (silent-non-fire).** SessionStart surfaces via
`grep -E "^### \[(HIGH|MEDIUM)\]"`, but live findings titled `### [MEDIUM 2026-06-04 by
engine-auditor] …` are **missed** (text before `]`). 4 engine-auditor MEDIUMs never reach the banner.
`health_check.md` is 1,251 lines / 173 KB, mostly RESOLVED graveyard inline with live items. **No.**

---

## 4. Doc ↔ code ↔ work relationship

Where the doc is a **frozen audit with a verdict**, accuracy is high and the measurement discipline
(bootstrap-CI, census, fail-closed, MBL) is real and enforced *in code* — the most trustworthy part of
the system. Where the doc is a **mutating description of the code** (PROJECT_CONTEXT status table,
generated `index.md`, charters), it **lags or lies**. The system diagnosed this exact asymmetry itself:
"the doc system is verdict-and-state-centric, not intent-fidelity-centric — a structural blind spot"
(`DESIGN_FIDELITY.md:31`).

Maintenance has tipped from *helping* toward *competing*: 15 State files, an 8-surface reconciliation
problem, a 173 KB health_check, generated tables nobody commits, three docs disagreeing on the baseline
Sharpe. The honesty culture is genuine and rare (docs say "REFUTED," "the hope is dead," "nothing
strictly clears"). But care is being spent *adding* discipline-docs faster than *enforcing* the
disciplines already written — and the enforcement layer is dead exactly where it's needed.

---

## 5. Verdict + highest-leverage fixes

**Purpose (as inferred):** a durable shared brain for one director + rotating stateless AI agents on a
months-long falsification program — so no session re-derives a dead conclusion, every measurement is
honestly gated, and architectural intent survives agent turnover. It achieves the first two; it is
failing intent-fidelity and beginning to fail decision-continuity as surfaces multiply and contradict.

**Fixes (cheap; none are a redesign). Items marked [PROPOSE-FIRST] touch the doc system itself
(CLAUDE.md rules / hooks / linter / gitignore) and per CLAUDE.md need user go-ahead:**
1. **[PROPOSE-FIRST]** De-number the constitution — replace `0.598`/`~75` in
   `CLAUDE.md`/`NON_NEGOTIABLES.md` with a pointer to `CURRENT_STATE.md`. Rule files encode rules, not
   measurements that go stale and then "win."
2. **[PROPOSE-FIRST]** Fix or delete the enforcement layer — repoint `doc_lint.py` `MEMORY_DIR` at the
   real `.claude/agent-memory/`; make `--pre-commit` exit non-zero on `[FAIL]`; add an `index.md`-matches-
   `sync_docs` check; back doc-lint in CI. A linter that exits 0 on FAIL manufactures false confidence.
3. **[PROPOSE-FIRST]** Resolve the "MEMORY.md" phantom — create one canonical file or rewrite every
   reference to the real per-agent path.
4. **[PROPOSE-FIRST]** Cap the `CURRENT_STATE.md` header; scrub the duplicate anchor numbers (keep 0.371).
5. **[PROPOSE-FIRST]** Archive or reconcile `.agent/` + aider config (broken, looser on safety).
6. **[PROPOSE-FIRST]** Fix the `Archive/` gitignore trap so `docs/Archive/` is tracked.
7. **Content drift (autonomous-eligible):** sweep `trading_machine-2` → ArchonDEX in the *current-truth*
   docs (`GOAL.md:4`, `PROJECT_CONTEXT.md`); fix the 4 broken pointers in `docs/Core/README.md`; re-tag
   `PROJECT_CONTEXT.md:18,79,86` to match build reality.
8. **AI memory:** add a pivot banner + "last reconciled" line to each `MEMORY.md`; add each agent's own
   memory to its required-reading; promote the architect's "is the vehicle even right?" objection into
   `docs/State/`.
9. **Resist the next tracker.** Fix existing surfaces rather than add a 16th State file; consolidate
   `capability_gap_drawing_board`/`conditional_shelf`/`cleanup_manifest` into durable trackers once their
   moment passes.

The architecture is sound; the disciplines are written; the failures are upkeep and dead-wiring. Until
the enforcement layer is real and the constitution stops carrying stale numbers that "win," a careful
reader is right to verify every doc claim against the code — the exact dependency a doc system exists to
remove.

---

*Reviewer: external fresh-eyes pass, read-only investigation (left no code/doc footprint beyond this
note + the queued health_check entry). Method: cold onboarding via prescribed path, three parallel
verification sub-agents (number-contradiction, automation/sync, AI-memory), plus direct live checks of
`doc_lint.py`, `git check-ignore`, `sync_docs.py`, and the source files cited above.*
