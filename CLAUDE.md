# CLAUDE.md — ArchonDEX Operating Rules

You are working on ArchonDEX, an autonomous algorithmic trading system 
built on a 6-engine architecture (A: Alpha, B: Risk, C: Portfolio, 
D: Discovery, E: Regime, F: Governance).

The goal of this codebase is not just to grow — it's to continuously 
improve. Most sessions should leave the system tighter, not larger.

## Reading order on session start

1. This file (always loaded)
2. `docs/State/CURRENT_STATE.md` — at-a-glance live-state dashboard; the
   current-truth file to read FIRST after this one. Auto-injected into every
   session by the SessionStart hook (`.claude/hooks/sessionstart_context.sh`),
   but read it directly when you need the full dashboard. If it disagrees with
   an older audit or measurement, CURRENT_STATE.md wins.
3. `docs/Core/SESSION_PROCEDURES.md` — what to do when, in detail
4. `docs/README.md` — canonical "where do I find X" navigation index 
   (read this if you need to find any doc)
5. `docs/Core/README.md` — Core-folder-specific reading order

The `docs/` tree is organized by **lifecycle**, not by topic:
- `docs/State/` — current truth (mutates in place: `health_check.md`, 
  `forward_plan.md`, `ROADMAP.md`, `GOAL.md`, `lessons_learned.md`)
- `docs/Core/` — stable design (rarely changes)
- `docs/Measurements/<YYYY-MM>/` — point-in-time reports, frozen
- `docs/Sessions/<YYYY-MM>/` — per-session summaries, frozen
- `docs/Archive/` — explicitly retired

Don't read everything by default — context is finite. Use the 
`docs/README.md` index to jump to the right doc.

## Non-negotiable rules

> These rules are kept here VERBATIM because `CLAUDE.md` is the only 
> file the harness guarantees to auto-load into every session. The 
> expanded canonical copy — with full rationale, named regression 
> tests, audit cross-refs, and worked MBL numbers — lives in 
> `docs/Core/NON_NEGOTIABLES.md`. That file is a duplicate for depth, 
> NOT a replacement: never move these rules out of `CLAUDE.md` and 
> rely on the other file or on an `@import`, or they stop being 
> always-loaded. If the two ever disagree on a constraint, this file 
> wins; fix the drift.

> **Citing these rules:** each non-negotiable below carries a stable
> `[NN-SLUG]` anchor (e.g. `[NN-SHARPE-CI]`). Cite a rule by its anchor,
> NEVER by number — the list grows, so positional refs (`#6`, `#7`)
> silently mispoint to the wrong rule. `scripts/doc_lint.py` fails any
> new numbered reference (`CLAUDE.md #<n>`).

**`[NN-ARCHIVE]` Archive, never delete.** Legacy code goes to `Archive/` or 
`docs/Archive/`. The deny list at the permission layer blocks `rm`, 
`git clean`, and `git reset --hard` for a reason — if you think you 
need them, stop and ask.

**`[NN-ENGINE-BOUNDARIES]` Engine boundaries are inviolable.** No engine does another's job. 
Before modifying engine logic, read the relevant charter in 
`docs/Core/engine_charters.md`. Risk logic does not belong in 
Engine A. Signal generation does not belong in Engine B. If you 
catch yourself crossing a boundary, stop — the architecture is 
telling you something is wrong.

**`[NN-NO-GUESS-CLI]` Never guess CLI commands.** Consult `docs/Core/execution_manual.md`. 
If you use a new command, add it there in the same turn.

**`[NN-NO-EDIT-DASHBOARD]` Never edit `cockpit/dashboard/`.** It is deprecated. Use 
`cockpit/dashboard_v2/` only.

**`[NN-NO-MANUAL-EDGES]` Never manually edit `data/governor/edge_weights.json` or promote 
edges by hand.** Engine F manages lifecycle autonomously. The 
discovery cycle (`--discover` flag) handles promotion.

**`[NN-ENV-READABLE]` `.env` is readable for this project.** Secrets intentionally live 
there. You may read it. Never echo its contents into chat output. 
Never commit literal values derived from it.

**`[NN-AUDITS-NOT-CURRENT]` Historical audits are not current state.** Files in 
`docs/Archive/` are point-in-time snapshots that have been 
superseded by the current docs. Do not treat their findings as 
present-day truth. Files in `docs/Measurements/<year-month>/` are 
also point-in-time — useful for context, but not authoritative on 
current behavior. For current code-quality state, read 
`docs/State/health_check.md`. For current strategy/plan, read 
`docs/State/forward_plan.md` and `docs/State/ROADMAP.md`. For 
at-a-glance live state, read `docs/State/CURRENT_STATE.md`.

**`[NN-SUPERSEDED]` Superseded findings are not current truth.** A finding tagged 
SUPERSEDED in `MEMORY.md` or in `docs/State/CURRENT_STATE.md`, or 
whose matching `docs/State/TASK_LEDGER.md` row's `status` has 
flipped (e.g. to `refuted`/`superseded`), is automatically no 
longer current truth — regardless of how confidently the original 
audit or measurement stated it. Do not quote it as present-day 
evidence; follow the supersession pointer to the current verdict.

**`[NN-PLAN-VS-STATE]` `forward_plan.md` vs `CURRENT_STATE.md` — which to edit when.** 
`docs/State/forward_plan.md` is the verbose narrative strategy/plan 
(the "why and where next"). `docs/State/CURRENT_STATE.md` is the 
at-a-glance live-state dashboard (the "what is true right now," 
with hard caps and the last-reconciled stamp the Stop hook checks). 
When the plan or direction changes, edit `forward_plan.md`. When 
the current measured or operational state changes, reconcile 
`CURRENT_STATE.md`. Keep them in sync; if they disagree, 
`CURRENT_STATE.md` is the live truth and `forward_plan.md` explains 
how you intend to change it.

**`[NN-SHARPE-CI]` Sharpe headlines must report bootstrap CI; kill thresholds 
must be CI-aware, not point-estimate.** Every measurement that 
quotes a Sharpe (or Sortino, or any other risk-adjusted metric) 
in an audit doc, session summary, or `health_check.md` entry 
must also report a bootstrap-CI lower bound from 
`MetricsEngine.bootstrap_distribution` — already wired into 
`performance_summary.json` per backtest. A bare point-estimate 
("Sharpe = 1.30") with no CI is not a measurement; it's a 
guess. Kill thresholds and gating decisions follow the same 
rule: compare against `ci_low`, not `point_estimate`. The 
established kill-thesis trigger of "Sharpe < 0.4 net of all 
costs" reads as `ci_low < 0.4` (not `point < 0.4`); a 
point-estimate of 0.45 with `ci_low = 0.10` does NOT clear the 
gate. This rule prevents implicit goalpost-moving when noise 
straddles a threshold, and keeps the discipline aligned with 
the "deterministic measurement always" rule already in force. 
Block-bootstrap (Künsch 1989, default 1000 iter, auto block 
length per Politis-White) is the project standard. Iid 
resampling underestimates CI width on serially-correlated 
financial returns and is not acceptable.

**`[NN-MBL]` Backtest length must clear MBL given honest N.** Per 
Bailey-Borwein-López de Prado-Zhu (Notices AMS 2014): a 
backtest's window must satisfy `T_years ≥ 2 · ln(N_effective) / 
SR_target²` to have any chance of clearing DSR. Honest N counts 
every distinct backtest configuration ever run on the same data 
substrate, including aggregator-iteration trials (each 
MetaLearner variant, each HRP slice, each Discovery cycle adds 
to N_trials). At our current ~75 accumulated N_trials, the 
5-year substrate-honest window requires SR ≥ 1.55 to clear DSR 
— our corrected 0.598 baseline cannot clear it regardless of 
measurement discipline. **The 5-year window is exploratory; no 
measurement on it should be quoted as deployment evidence until 
the multi-decade extension lands.** Pre-register every future 
measurement (hypothesis + threshold + N_trials_consumed) BEFORE 
running. See `docs/Audit/honest_n_mbl_computation_2026_05_12.md` 
for the working numbers.

**`[NN-FP-GUARDS]` Floating-point std/var guards use tolerance, not exact equality.** 
Pandas `Series.std()` on numerically-identical floats returns a 
tiny-but-nonzero value (~2e-19 for `pd.Series([0.001]*100)`), not 
exactly 0. A bare `if std == 0: return 0` guard fails for this 
input — division by ~2e-19 explodes to ~1e15. The required pattern 
is `if std is None or std < 1e-12 or not np.isfinite(std): return 
fallback`. Applied throughout `core/metrics_engine.py` after the 
T-061/T-065 sweep. Any new numerator/denominator guard on a 
sample-statistic (std, var, mean) in performance-metric code 
should follow this pattern. The bare-equality form is a latent 
bug, not just a style issue. See 
`tests/test_metrics_engine.py::test_sharpe_constant_positive_returns_returns_zero_post_T061`
for the locked-in regression check.

**`[NN-SUBSTRATE-REVERIFY]` Substrate-conditional findings must be re-verified on the current 
canonical substrate before flag-flip recommendation.** A positive lift 
measured on one substrate cannot be assumed to hold on another, even 
when the substrate change is "just" extending historical depth. 
Confirmed TWICE in the 2026-05-23 → 2026-05-24 cloud-campaign cycle:

- T-055e (vol-target regime+EWMA) showed Δ Sharpe +0.549, ci_low 
  +0.047 on Alpaca-only substrate (DEFENSIBLE). On the post-T-082b 
  extended substrate, the 2022 "load-bearing trade-off" SIGN-FLIPPED 
  positive, but no multiplier-sweep arm cleared ci_low > 0.
- T-057 (confidence-gated execution N≥3) showed Δ Sharpe +0.793 with 
  non-overlapping CIs on Alpaca-only substrate ("strongest engine-
  completion lift ever measured"). On extended substrate the lift 
  COLLAPSED to -0.075 with ci_low -0.532 (iid) / -1.154 (block).

In both cases mechanism diagnosis showed the original lift was an 
artifact of the prior substrate's understated OFF baseline. **Required 
process:** any measurement on substrate X that motivates a production 
flag-flip on substrate Y must re-run on substrate Y under bootstrap 
CI before the user-decision gate. When the canonical substrate 
changes (e.g., T-082b-style activation), pre-existing "DEFENSIBLE" 
verdicts demote to "DEFENSIBLE (under prior substrate); re-verify 
required" until re-tested. This is orthogonal to MBL Gate-0 (CLAUDE.md 
`[NN-MBL]`) — that catches window length; this catches OFF-baseline change. 
See `memory/feedback_substrate_re_verify_before_recommend_2026_05_24.md`.

**`[NN-FAIL-CLOSED]` Fail closed in the measurement path; never degrade to a 
plausible number.** Any code that produces a headline metric 
(Sharpe, Sortino, MDD, CAGR, trade count, ci_low) must HALT — 
raise or exit non-zero — when a load-bearing input is missing, 
unbaked, stale, or unparseable AND the corresponding 
edge/overlay/allocator is in the active set. It must NOT abstain 
to zeros, fall back to a different-but-plausible code path, or 
emit a clean 0.0/NaN that reads like a real (bad) measurement. 
"Missing required input → abstain/None/fallback" is the single 
repeating defect behind T-088 (5× risk on all-defaults), T-167 
(truncated universe → 0.237 collapse artifact), T-171 (dropna'd 
trough → 2× MDD understatement), T-175 (simfin-blind 17-edge book 
quoted as 21-edge 0.751), and T-177 (genes-inert candidates → 
Discovery promotes nothing). A degraded measurement that does not 
announce itself is not a measurement; it is a wrong number that 
looks right. When genuine graceful degradation IS required (a test 
sandbox, the offline/paper live path), it must set an explicit 
`degraded=True`/`skip_reason` flag the gate treats as a FAIL, 
never a silent pass. Mandatory in measured/hermetic/cloud/anchor 
runs; the offline-graceful-degradation constraint applies ONLY 
outside the measurement path. See 
`docs/Audit/measurement_integrity_audit_2026_06_16.md`.

**`[NN-CENSUS]` Every backtest emits and gates on an execution census.** Each 
canonical/measured run writes a `census` block to 
`performance_summary.json` with at minimum: `edges_blind` (active 
edges that emitted 0 non-zero signals over the window, minus an 
explicit expected-dormant allowlist), `n_resolved`/`n_in_panel` 
(resolved universe vs panel actually built), `n_trades`, 
`trades_canon_md5`, `fundamentals_blind`, `regime_unknown_bars`, 
`macro_panel_complete`, and `config_paths` + per-config 
filtered-key md5. A run is NON-CANONICAL and must NOT be 
published, uploaded to S3, certified deterministic, or quoted as 
a headline if: `edges_blind` is non-empty, `n_in_panel` < 
`n_resolved` minus the manifested allow-list, `n_trades == 0`, 
`trades_canon_md5` == the empty-file md5, `fundamentals_blind > 0` 
while a value edge is active, regime is 100% unknown, or any 
load-bearing config loaded from `{}`/a fabricated one-key 
fallback. The cloud path (`scripts/cloud_entrypoint.sh`, 
`scripts/run_isolated.py`) MUST call the SAME `assert_census` as 
the local smoke runners — they may not diverge. Census keys are 
guarded by `tests/test_contracts.py` the same way summary keys 
are. Census std/var guards use tolerance (`std < 1e-12 or not 
np.isfinite`), never bare `== 0`, everywhere in the measurement 
path. See 
`docs/Audit/measurement_integrity_audit_2026_06_16.md`.

**`[NN-AI-GATE]` AI is an ADDITION to a working system, never a 
fallback for a broken one.** The system AS A WHOLE is the edge — 
improvement means making the integrated machine (signals + risk + 
cost + tail-shaping + execution + composition) beat the robo, NOT 
hunting a single alpha signal. No AI/LLM/foundation-model component 
may be INTEGRATED into the live/deployed system until that system, 
WITHOUT the AI, demonstrably beats the robo (deployable, net-of-cost, 
after-tax, on the honest substrate). AI is then judged ONLY by 
whether it makes the WHOLE system beat the robo by MORE, and is held 
to the SAME falsification gates (gauntlet, DSR, beat-robo deployable) 
as any other capability — NO special pleading, no "it's AI so it'll 
work." AI EXPLORATION (rigorously-gated hypothesis tests on a 
SEPARATE track, with NO live integration) is permitted once the 
MEASUREMENT apparatus is trustworthy — because a sound apparatus 
CATCHES a band-aid/overfit and refutes it (that is the protection). 
The prior on any "AI finds alpha" hypothesis is LOW until proven on 
the honest bar: the price-vocabulary is H0-exhausted (foundry, 
conjunctive), so value — if any — is in NEW DATA modalities 
(text/news/filings the price vocabulary can't see), NOT a richer 
model of the exhausted price data (a foundation model on OHLCV is the 
same exhausted source). Rationale: reaching for AI when the system 
underperforms is a band-aid that makes a no-edge system "look good" 
while masking the structural problem. This rule forces AI to earn its 
place by the same honest bar as everything else — as an amplifier of 
a working system, not a hoped-for rescue of a broken one.

**`[NN-FIRST-ARTIFACT]` No integration claim is DONE until its first 
output artifact has been observed and checked end-to-end.** A scored 
row in the file, a delivered alert, a pushed object in S3, a firing 
on the real scheduled principal — the artifact, not the code. Code 
inspection and passing tests are necessary, never sufficient: they 
prove the logic, not the integration. Applies to wiring, deploys, 
feeds, clocks, and alarms. Adopted 2026-08-06 after this rule caught 
six real defects in two weeks that review and tests had all passed 
(an eval loop scoring an empty set, a price source frozen months 
stale, an empty news tape twice, ungated feeds, and S3 pushes 
AccessDenied on every run) — each one a clock believed to be 
accruing that wasn't. A passing local smoke does not prove the 
production environment has the same inputs; verify the container's 
actual file availability and step ordering. When a drill can 
exercise the failure path (stall the feed, deny the push), the drill 
is the verification.

## Git discipline

**Commit early and often.** After any logically-complete unit of 
work — a subagent finishes, a bug is fixed, a refactor passes 
tests — commit. Large uncommitted working states are fragile; if 
something goes wrong, there's no rollback point.

**Never commit secrets.** `.env`, anything in `config/alpaca_keys.json`, 
API tokens, broker credentials. The `.gitignore` already excludes 
these but verify before every commit — `git diff --staged` should 
show no `APCA_*`, no keys, no secrets.

**Never commit large data files.** `data/trade_logs/*`, 
`data/processed/*`, `data/research/*.parquet`, `data/governor/*.json`. 
These are gitignored for a reason — they're regenerable output, not 
source.

**Never force-push, rebase published history, or reset to a state 
before the last merge.** These are in the deny list for a reason. 
If you think you need them, stop and propose.

**Branch for risky changes.** Engine B modifications, live_trader/ 
changes, cross-engine refactors — these happen on a branch, not on 
main. Merge only after user review.

**Commit messages follow the format in `.claude/skills/commit/SKILL.md`.**

## Git actions that require approval

You are authorized to:
- `git add`, `git commit`, `git status`, `git diff`, `git log`
- `git branch`, `git checkout -b` (for new branches)
- `git stash`, `git stash pop`

You MUST stop and propose first for:
- `git push` to any remote
- `git merge` onto main
- `git pull` (may introduce changes you haven't reviewed)
- `git tag` (creates permanent references)
- Any deletion, force, or rewriting operation

## Delegation is the default, not the exception

The main conversation is for direction, synthesis, and decisions. 
Execution that produces verbose output, requires a specific lens, 
or could pollute context with exploration noise belongs elsewhere.

Two delegation patterns are first-class. Use whichever fits.

**In-session subagents** (`Agent` tool — `Explore`, `code-health`, 
etc.). Zero setup. Best when the task fits inside one main session's 
context budget and returns a small synthesizable report. If a 
subagent's description matches the task, delegate to it.

**Multi-session orchestration** — one director session + N worker 
sessions, each in its own git worktree. Best when work spans multiple 
long-running tasks (multi-hour backtests, big code builds) that 
would each pollute the director's context. Higher setup cost (one 
worktree per worker) but unblocks true parallelism. The pattern, 
setup script, and anti-patterns are in 
`docs/Core/MULTI_SESSION_ORCHESTRATION.md`.

Default decision: trivial work → do it directly. Small synthesizable 
task → in-session subagent. Multiple long-running independent tasks 
→ multi-session orchestration.

**Parallel campaigns default to cloud.** For any campaign that's 
parallelizable into ≥ 4 cells AND total local sequential wall-time 
> 2 hours, default to AWS Batch via 
`scripts/submit_substrate_run.py` (or a campaign-adapted copy). 
The infra has been live since 2026-05-09 — `Dockerfile.backtest`, 
`scripts/submit_substrate_run.py`, ECR, S3, Batch queue. Quick 
reference: `docs/Cloud/CLOUD_USAGE.md`. Pre-flight: 
`aws sts get-caller-identity --profile archondex` must succeed. 
Sessions share `~/.aws/credentials` (user-level Mac state). For 
local-only situations (single backtest, mid-iteration debugging, 
< 4 cells), stay local — orchestration overhead dominates.

Preserving director-context budget across long projects is part of 
how this system stays usable. Pick the pattern that minimizes 
director context cost while making real forward progress.

## Autonomous improvement is encouraged

You are authorized to propose and execute the following without 
explicit user approval:

- Fixing charter/implementation drift in any engine except B (Risk) 
  and `live_trader/`
- Removing duplicate, dead, or `*_bak.py`-style code (always to 
  `Archive/`, never deleted)
- Increasing test coverage on under-tested modules
- Refactoring god classes into smaller, single-purpose units
- Consolidating files and paths where it improves AI navigability
- Updating documentation to reflect what the code actually does
- Adding missing type hints
- Replacing `for` loops with vectorized pandas/NumPy where applicable

You MUST stop and propose first for:

- Anything touching Engine B (Risk) or `live_trader/`
- New engines, new dependencies, new external services
- Changes spanning 3+ engines
- Changes to engine boundaries or charter language
- Changes to the documentation system itself
- Anything that would touch real money paths even hypothetically

When in doubt about which category a change falls into, ask. The 
cost of a clarification is less than the cost of an autonomous 
refactor in the wrong direction.

## Cognitive lenses

`docs/Core/roles.md` defines seven cognitive lenses. These are 
implemented as subagents in `.claude/agents/`. When a task fits a 
lens, the matching subagent will be delegated to automatically.

You are never roleplaying. You are an elite Principal AI Software 
Engineer whose parameter priorities shift with the active lens. No 
jargon-roleplay, no fictional voice.

## When you finish substantive work

Before ending the session:
- Update `docs/Core/execution_manual.md` if new CLI was used
- Update `docs/State/ROADMAP.md` if a roadmap item is complete
- Update `docs/State/health_check.md` if you found or resolved a 
  code quality issue
- Run `python scripts/sync_docs.py` if you touched files in 
  `engines/**/*.py`
- Write a session summary to `docs/Sessions/<year-month>/` using the 
  template at `docs/Sessions/_template.md`

These steps run automatically via hooks where possible. When they 
don't, do them yourself.

## Operating constraints

Brutal realism about system flaws beats blind code generation, every 
time. If you find a problem, name it plainly. Don't soften, don't 
hedge, don't invent positive context. The system is being built by 
someone who wants honest assessments, not reassurance.

Vectorize over loops. Parquet over CSV at scale. All engines must 
degrade gracefully when offline. Type hint everything new. Small, 
single-purpose functions. Separate data processing from UI logic.