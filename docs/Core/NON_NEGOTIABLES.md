# NON_NEGOTIABLES.md — ArchonDEX Hard Constraints (Canonical Expanded Copy)

> **Always-loaded source of truth is `CLAUDE.md`.** The hard constraints below
> are kept VERBATIM in `CLAUDE.md` because `CLAUDE.md` is the only file the
> harness guarantees to auto-load into every session. THIS file is the
> *expanded* canonical home: same rules, plus full rationale, named regression
> tests, audit cross-references, and worked numbers. If this file and
> `CLAUDE.md` ever disagree on the *constraint itself*, `CLAUDE.md` wins (it is
> the always-loaded copy) — fix the drift immediately. Do NOT delete the rules
> from `CLAUDE.md` and rely on this file or on an `@import`: per the verified
> Claude Code memory semantics, `@import` is not a reliable always-loaded
> mechanism for a separate non-negotiables file, so removing the rules from
> `CLAUDE.md` would silently un-load them.

These are not style preferences. Each is deny-list-backed, money/safety-path,
data-integrity, or measurement-discipline. Violating one is a correctness or
safety regression, not a lint nit. Cross-references below use stable rule
*titles* (not positional numbers) so they cannot rot when `CLAUDE.md`'s
bolded-rule order changes.

---

## `[NN-ARCHIVE]` Archive, never delete (deny-list-backed)

**Rule:** Legacy code goes to `Archive/` or `docs/Archive/`. The deny list at
the permission layer blocks `rm`, `git clean`, and `git reset --hard` for a
reason — if you think you need them, stop and ask.

**Why hard:** Deny-list-backed at the permission layer. Data-integrity +
irreversibility. Enforced by the permission layer, not by goodwill.

## `[NN-ENGINE-BOUNDARIES]` Engine boundaries are inviolable

**Rule:** No engine does another's job. Before modifying engine logic, read the
relevant charter in `docs/Core/engine_charters.md`. Risk logic does not belong
in Engine A. Signal generation does not belong in Engine B. If you catch
yourself crossing a boundary, stop — the architecture is telling you something
is wrong.

**Why hard:** Architecture-integrity constraint tied to the money/risk path.
Engine B (Risk) ↔ Engine A (Alpha) cross-contamination is a correctness/safety
failure that can silently corrupt risk sizing on real-money paths. Coupled with
the Engine-B approval gate ("Autonomous improvement — propose-first list").

## `[NN-NO-GUESS-CLI]` Never guess CLI commands

**Rule:** Consult `docs/Core/execution_manual.md`. If you use a new command, add
it there in the same turn.

**Why hard:** A guessed command can corrupt state, run the wrong substrate, or
silently no-op a measurement. The execution manual is the single source of truth
for how to invoke the system.

## `[NN-NO-EDIT-DASHBOARD]` Never edit `cockpit/dashboard/` (deprecated)

**Rule:** It is deprecated. Use `cockpit/dashboard_v2/` only.

**Why hard:** Absolute "never" with no judgment call — a bright-line prohibition
on a deprecated path.

## `[NN-NO-MANUAL-EDGES]` Never manually edit `data/governor/edge_weights.json` or promote edges by hand

**Rule:** Engine F manages lifecycle autonomously. The discovery cycle
(`--discover` flag) handles promotion.

**Why hard:** Data-integrity + autonomy-integrity. Manual edits corrupt the
autonomous lifecycle state and feed directly into capital allocation (sizing) —
a money-path-adjacent silent regression. See memory: registry status-stomp bug
(2026-04-25), production ensemble includes soft-paused edges at 0.25×.

## `[NN-ENV-READABLE]` `.env` is readable; never echo into chat / never commit derived literals

**Rule:** Secrets intentionally live in `.env`. You may read it. Never echo its
contents into chat output. Never commit literal values derived from it.

**Why hard:** Secrets-handling. Echoing `.env` or committing derived literals is
a credential-leak / live-broker-key exposure event — direct money/safety
regression. Bright-line, no judgment. Pairs with "Never commit secrets."

## `[NN-AUDITS-NOT-CURRENT]` Historical audits are not current state

**Rule:** Files in `docs/Archive/` are point-in-time snapshots superseded by the
current docs — do not treat their findings as present-day truth. Files in
`docs/Measurements/<year-month>/` are also point-in-time — useful for context,
not authoritative on current behavior. For current code-quality state, read
`docs/State/health_check.md`. For current strategy/plan, read
`docs/State/forward_plan.md` and `docs/State/ROADMAP.md`. For at-a-glance live
state, read `docs/State/CURRENT_STATE.md`.

**Why hard:** Correctness-of-truth. Treating a superseded audit as present-day
truth has repeatedly caused wrong flag-flip recommendations. The companion
supersession rule (in `CLAUDE.md`, "Superseded findings are not current truth"):
a finding tagged SUPERSEDED in `MEMORY.md` or `CURRENT_STATE.md`, or whose
`TASK_LEDGER.md` `status` has flipped, is no longer current truth. Memory
examples of this exact failure: T-087 reversal (a 5-yr false negative quoted as
truth), the "0.539/phantom" first-pass error (JSON-key bug).

## `[NN-SUPERSEDED]` Superseded findings are not current truth

**Rule:** A finding tagged SUPERSEDED in `MEMORY.md` or `docs/State/CURRENT_STATE.md`,
or whose matching `docs/State/TASK_LEDGER.md` row `status` has flipped (to
`refuted`/`superseded`), is automatically no longer current truth — regardless of
how confidently the original audit/measurement stated it. Do not quote it as
present-day evidence; follow the supersession pointer to the current verdict.

**Why hard:** Measurement-discipline + trust-integrity. Quoting a superseded
verdict as live truth is the exact failure the doc system exists to prevent.

## `[NN-PLAN-VS-STATE]` `forward_plan.md` vs `CURRENT_STATE.md` — which to edit when

**Rule:** `forward_plan.md` is the verbose narrative strategy/plan ("why and where
next"). `CURRENT_STATE.md` is the at-a-glance live-state dashboard ("what is true
right now", with hard caps + the last-reconciled stamp the Stop hook checks). When
the plan/direction changes, edit `forward_plan.md`; when measured or operational
state changes, reconcile `CURRENT_STATE.md`. If they disagree, `CURRENT_STATE.md`
is live truth.

**Why hard:** Prevents the two current-truth surfaces from drifting — the
single-canonical-surface discipline the AI-consumption doc overhaul targets.

## `[NN-SHARPE-CI]` Sharpe headlines must report bootstrap CI; kill thresholds CI-aware

**Rule:** Every measurement quoting a Sharpe (or Sortino, or any risk-adjusted
metric) in an audit doc, session summary, or `health_check.md` entry must also
report a bootstrap-CI lower bound from `MetricsEngine.bootstrap_distribution`
(already wired into `performance_summary.json` per backtest). A bare
point-estimate ("Sharpe = 1.30") with no CI is not a measurement; it's a guess.
Kill thresholds and gating decisions compare against `ci_low`, not
`point_estimate`. The kill-thesis trigger "Sharpe < 0.4 net of all costs" reads
as `ci_low < 0.4` (not `point < 0.4`); a point-estimate of 0.45 with
`ci_low = 0.10` does NOT clear the gate. Block-bootstrap (Künsch 1989, default
1000 iter, auto block length per Politis-White) is the project standard. Iid
resampling underestimates CI width on serially-correlated financial returns and
is not acceptable.

**Why hard:** Core measurement-discipline non-negotiable. Prevents implicit
goalpost-moving when noise straddles a threshold. Directly gates deploy/kill
decisions that govern real-money exposure.

## `[NN-MBL]` Backtest length must clear MBL given honest N

**Rule:** Per Bailey-Borwein-López de Prado-Zhu (Notices AMS 2014): a backtest's
window must satisfy `T_years ≥ 2 · ln(N_effective) / SR_target²` to have any
chance of clearing DSR. Honest N counts every distinct backtest configuration
ever run on the same data substrate, including aggregator-iteration trials (each
MetaLearner variant, each HRP slice, each Discovery cycle adds to N_trials). At
~75 accumulated N_trials, the 5-year substrate-honest window requires SR ≥ 1.55
to clear DSR — the corrected 0.598 baseline cannot clear it regardless of
measurement discipline. **The 5-year window is exploratory; no measurement on it
may be quoted as deployment evidence until the multi-decade extension lands.**
Pre-register every future measurement (hypothesis + threshold + N_trials_consumed)
BEFORE running.

> **GUARD (added 2026-07-28, from a real error — Agent B):** feed the formula the
> Sharpe of the **CLAIMED EDGE**, never a strategy's **ABSOLUTE** Sharpe when that
> Sharpe is beta-dominated. A long/flat equity sleeve showed absolute Sharpe ~1.5 that
> is mostly market exposure; its **ACTIVE** (difference-vs-benchmark) Sharpe was
> **−0.210** on the same 64yr window. Plugging the absolute number in produced a
> "clears DSR with 2.4-2.6× margin" claim that pointed the OPPOSITE way from the
> decision-relevant quantity — and sat four lines from the same document's "the sleeve
> LOSES to buy-hold." Deploy decisions ride on DIFFERENCE metrics; evaluate MBL on
> those. See `docs/Audit/mbl_framing_correction_t306_arc_2026_07_28.md`.

**Worked numbers / cross-ref:** `docs/Audit/honest_n_mbl_computation_2026_05_12.md`.
First measurement to PASS MBL Gate-0 was T-053b on the 12-yr window (memory,
2026-05-26). This is MBL Gate-0: it catches window length. It is orthogonal to
the substrate-re-verify rule below (which catches OFF-baseline change).

**Why hard:** Measurement-discipline / determinism. A hard Gate-0 on what
evidence can justify going live.

## `[NN-FP-GUARDS]` Floating-point std/var guards use tolerance, not exact equality

**Rule:** Pandas `Series.std()` on numerically-identical floats returns a
tiny-but-nonzero value (~2e-19 for `pd.Series([0.001]*100)`), not exactly 0. A
bare `if std == 0: return 0` guard fails for this input — division by ~2e-19
explodes to ~1e15. The required pattern is
`if std is None or std < 1e-12 or not np.isfinite(std): return fallback`.
Applied throughout `core/metrics_engine.py` after the T-061/T-065 sweep. Any new
numerator/denominator guard on a sample-statistic (std, var, mean) in
performance-metric code must follow this pattern. The bare-equality form is a
latent bug, not just a style issue.

**Locked-in regression test:**
`tests/test_metrics_engine.py::test_sharpe_constant_positive_returns_returns_zero_post_T061`.

**Why hard:** Determinism / numerical-correctness invariant in
performance-metric code.

## `[NN-SUBSTRATE-REVERIFY]` Substrate-conditional findings must be re-verified on the current canonical substrate before flag-flip recommendation

**Rule:** A positive lift measured on one substrate cannot be assumed to hold on
another, even when the substrate change is "just" extending historical depth.
Confirmed TWICE in the 2026-05-23 → 2026-05-24 cloud-campaign cycle:

- T-055e (vol-target regime+EWMA) showed Δ Sharpe +0.549, ci_low +0.047 on
  Alpaca-only substrate (DEFENSIBLE). On the post-T-082b extended substrate, the
  2022 "load-bearing trade-off" SIGN-FLIPPED positive, but no multiplier-sweep
  arm cleared ci_low > 0.
- T-057 (confidence-gated execution N≥3) showed Δ Sharpe +0.793 with
  non-overlapping CIs on Alpaca-only substrate ("strongest engine-completion
  lift ever measured"). On extended substrate the lift COLLAPSED to -0.075 with
  ci_low -0.532 (iid) / -1.154 (block).

In both cases mechanism diagnosis showed the original lift was an artifact of
the prior substrate's understated OFF baseline. **Required process:** any
measurement on substrate X that motivates a production flag-flip on substrate Y
must re-run on substrate Y under bootstrap CI before the user-decision gate.
When the canonical substrate changes (e.g., T-082b-style activation),
pre-existing "DEFENSIBLE" verdicts demote to "DEFENSIBLE (under prior
substrate); re-verify required" until re-tested.

**Cross-ref:** `memory/feedback_substrate_re_verify_before_recommend_2026_05_24.md`.
Orthogonal to MBL Gate-0 (the "Backtest length must clear MBL" rule above) —
that catches window length; this catches OFF-baseline change. Both T-055 and
T-057 closed negative on the 12-yr window (T-055h Δ -0.214; T-057/T-053b refuted
Δ -0.128).

**Why hard:** Measurement-discipline non-negotiable. Directly gates production
flag-flips that change real-money behavior.

## `[NN-FAIL-CLOSED]` Fail closed in the measurement path; never degrade to a plausible number

**Rule:** Any code that produces a headline metric (Sharpe, Sortino, MDD, CAGR,
trade count, ci_low) must HALT — raise or exit non-zero — when a load-bearing
input is missing, unbaked, stale, or unparseable AND the corresponding
edge/overlay/allocator is in the active set. It must NOT abstain to zeros, fall
back to a different-but-plausible code path, or emit a clean 0.0/NaN that reads
like a real (bad) measurement. When genuine graceful degradation IS required (a
test sandbox, the offline/paper live path), set an explicit
`degraded=True`/`skip_reason` flag the gate treats as a FAIL, never a silent
pass. Mandatory in measured/hermetic/cloud/anchor runs; the
offline-graceful-degradation constraint applies ONLY outside the measurement path.

**Why hard:** "Missing required input → abstain/None/fallback" is the SINGLE
repeating defect behind the program's worst clouded-number incidents — T-088 (5×
risk on all-defaults), T-167 (truncated universe → 0.237 collapse artifact),
T-171 (dropna'd trough → 2× MDD understatement), T-175 (simfin-blind 17-edge book
quoted as the 21-edge 0.751), T-177 (genes-inert candidates → Discovery promotes
nothing). A degraded measurement that does not announce itself is not a
measurement; it is a wrong number that looks right. Full diagnosis +
catalog: `docs/Audit/measurement_integrity_audit_2026_06_16.md`.

## `[NN-CENSUS]` Every backtest emits and gates on an execution census

**Rule:** Each canonical/measured run writes a `census` block to
`performance_summary.json` with at minimum: `edges_blind` (active edges that
emitted 0 non-zero signals, minus an explicit expected-dormant allowlist),
`n_resolved`/`n_in_panel`, `n_trades`, `trades_canon_md5`, `fundamentals_blind`,
`regime_unknown_bars`, `macro_panel_complete`, `config_paths` + per-config
filtered-key md5. A run is NON-CANONICAL (must not publish, upload to S3, certify
deterministic, or be quoted as a headline) if any census check fails:
`edges_blind` non-empty, `n_in_panel` < `n_resolved` − allowlist, `n_trades == 0`,
`trades_canon_md5` == empty-file md5, `fundamentals_blind > 0` while a value edge
is active, regime 100% unknown, or a config loaded from `{}`/a one-key fallback.
The cloud path MUST call the SAME `assert_census` as the local smoke runners.
Census std/var guards use tolerance (`std < 1e-12 or not np.isfinite`), never
bare `== 0`, everywhere in the measurement path. Census keys are guarded by
`tests/test_contracts.py` the same way summary keys are.

**Why hard:** Converts the silent-fail-open defect class (above) from a
months-later audit catch into a run-time refusal — the machine cannot produce a
corrupted headline number without announcing it. Rollout + the 6 invariants:
`docs/Audit/measurement_integrity_audit_2026_06_16.md`.

## `[NN-AI-GATE]` AI is an addition to a working system, never a fallback for a broken one

**Rule:** The system AS A WHOLE is the edge — improvement means making the
integrated machine (signals + risk + cost + tail-shaping + execution + composition)
beat the robo, NOT hunting a single alpha signal. No AI/LLM/foundation-model
component may be **integrated into the live/deployed system** until that system,
*without* the AI, demonstrably beats the robo (deployable, net-of-cost, after-tax,
honest substrate). AI is then judged ONLY by whether it makes the WHOLE system beat
the robo by MORE, held to the SAME falsification gates (gauntlet, DSR, beat-robo
deployable) as any other capability — no special pleading. AI **exploration**
(rigorously-gated hypothesis tests on a SEPARATE track, no live integration) is
permitted once the measurement apparatus is trustworthy (a sound apparatus catches a
band-aid/overfit and refutes it — that is the protection). The prior on any "AI finds
alpha" hypothesis is LOW until proven on the honest bar: the price vocabulary is
H0-exhausted (foundry, conjunctive), so value — if any — is in NEW DATA modalities
(text/news/filings), NOT a richer model of the exhausted price data.

**Why hard:** Reaching for AI when the system underperforms is the band-aid that makes
a no-edge system "look good" while masking the structural problem — the exact
self-deception the measurement discipline exists to prevent. The author has corrected
this bias repeatedly (2026-06 sessions). Two tiers, kept distinct: **EXPLORATION**
(safe once the apparatus is sound — it catches fakes) vs **INTEGRATION** (gated on a
working system). The gate converts a bias-prone in-the-moment judgment into an
objective precondition, the same way the deploy gate gates real money. See
`memory/feedback_plateau_before_ai_2026_05_01.md` (the seed) +
`feedback_fork_resolved_robo_benchmark_2026_06_15.md`.

## Never commit secrets

**Rule:** `.env`, anything in `config/alpaca_keys.json`, API tokens, broker
credentials. `.gitignore` already excludes these but verify before every commit
— `git diff --staged` should show no `APCA_*`, no keys, no secrets.

**Why hard:** Secrets-handling, money/safety path. Committing broker credentials
is a direct live-account compromise. Absolute "never," with a mandatory
pre-commit verification step. Pairs with "`.env` is readable."

## Never commit large data files

**Rule:** `data/trade_logs/*`, `data/processed/*`, `data/research/*.parquet`,
`data/governor/*.json`. These are gitignored — they're regenerable output, not
source.

**Why hard:** Data-integrity / repo-hygiene. `data/governor/*.json` also
overlaps the autonomous-state-integrity concern in "Never manually edit
edge_weights.json."

## Never force-push, rebase published history, or reset to a state before the last merge (deny-list-backed)

**Rule:** These are in the deny list for a reason. If you think you need them,
stop and propose.

**Why hard:** Deny-list-backed irreversibility. Rewriting published history is
unrecoverable and can destroy the audit trail of money-path changes.

## Branch for risky changes

**Rule:** Engine B modifications, `live_trader/` changes, cross-engine refactors
— these happen on a branch, not on main. Merge only after user review.

**Why hard:** Money/safety process constraint. Engine B (Risk) and
`live_trader/` are real-money paths; mandates branch + user-review gate before
merge. Workflow embodiment of the Engine-B propose-first gate.

## Git actions that require approval

**Authorized without asking:** `git add`, `git commit`, `git status`,
`git diff`, `git log`, `git branch`, `git checkout -b` (new branches),
`git stash`, `git stash pop`.

**MUST stop and propose first for:** `git push` to any remote; `git merge` onto
main; `git pull` (may introduce unreviewed changes); `git tag` (permanent
references); any deletion, force, or rewriting operation.

**Why hard:** Approval-gating list backed by the deny list. Defines the exact
bright line between authorized and must-ask git operations. Push/merge-to-main
affect shared/published and potentially deploy-feeding state.

## Autonomous improvement — MUST stop and propose first list (the core money/safety gate)

**MUST stop and propose first for:**

- Anything touching Engine B (Risk) or `live_trader/`
- New engines, new dependencies, new external services
- Changes spanning 3+ engines
- Changes to engine boundaries or charter language
- Changes to the documentation system itself
- Anything that would touch real money paths even hypothetically

When in doubt about which category a change falls into, ask. The cost of a
clarification is less than the cost of an autonomous refactor in the wrong
direction.

**Why hard:** The single most safety-critical enumerated gate in the system. It
explicitly fences off Engine B (Risk), `live_trader/`, and "anything that would
touch real money paths even hypothetically."
