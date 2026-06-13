# ArchonDEX — Collaborator Handoff Snapshot

> **Point-in-time snapshot: 2026-06-12 (PM).** This is a frozen onboarding doc.
> The **live-truth** files are `docs/State/CURRENT_STATE.md` (at-a-glance state +
> hard caps) and `docs/State/TASK_LEDGER.md` (every closed task). If this doc and
> those disagree, **they win** — read them first, then come back here for the
> workflow mechanics. Reading order on any session start is pinned in
> `CLAUDE.md` → `docs/State/CURRENT_STATE.md` → `docs/Core/SESSION_PROCEDURES.md`
> → `docs/README.md`.
>
> Authored by the director session. Where a fact came from a specific worker
> session it is attributed (e.g. "per Agent C's outbox"). I could NOT live-query
> the worker sessions (they run in separate worktrees with the user as message
> bus — see §2); their status here is read from their `data/coordination/*_outbox.md`
> files and branch HEADs as of this snapshot, and some is explicitly marked
> UNCONFIRMED where the outbox is stale.

---

## 1. Mission & current objective

**What it is.** ArchonDEX (the repo was renamed from `trading_machine`; the working
dir is still `trading_machine-2`) is an autonomous algorithmic trading system built
on a **6-engine architecture** (A: Alpha/signals, B: Risk, C: Portfolio, D:
Discovery, E: Regime, F: Governance). It runs daily-bar US-equity strategies, with a
full backtest → measurement → (eventually) paper → live pipeline. The owner is
**retail** with both a **taxable** and a **Roth** account, staging ~$5K toward $50K+.

**The actual goal** (from `CLAUDE.md`): *not* to grow the codebase but to
continuously improve and tighten it. Most sessions should leave the system smaller
and more correct, not larger.

**Where we honestly stand.** The headline base-alpha question closed **negative** and
that verdict is load-bearing: the 6-edge ensemble is **bull-conditional** (clean,
fully-reproduced cloud anchors — 16-yr Sharpe **1.021**, 26-yr **0.237**), survivor-
biased upper bound, and **0 of 11 edges clear a factor-α t>2 bar**. So the program is
*not* "fix the base's alpha" (we can't validate it) but two tracks run in parallel:
1. **Risk / de-gross track** — make the book *survivable* (drawdown reduction is
   legitimate risk-adjusted edge, named honestly, not alpha).
2. **New-alpha track** — industrialize published literature through the falsification
   gauntlet rather than inventing artisanal edges.

**The current objective (this week).** The full reproducibility/anchor saga is
**closed** — the cloud anchors are published and bitwise-reproducible. Two cloud
campaigns are **in flight on those anchors**: **C's T-118 HMM transition-trigger
de-gross overlay** (the headline risk-track experiment) and **A's sleeve A/B
close-out**. When those land, "the fork" convenes — a strategic decision on
architecture/mission direction — with its full measurement base now complete. In
parallel, **paper trading was just approved** (design-only so far) and E is building
the order-execution plumbing.

A newer user directive (2026-06-11, `docs/State/forward_plan.md` top block) reframes
the search: **stop requiring every candidate to be all-weather** — decompose into
conditional sleeves (aggressive-alpha vs drawdown-control) combined via *validated*
regime/account switches, rather than killing anything that isn't a uniform lift.

---

## 2. Orchestration overview

**The model: one director + five worker sessions + the user as message bus.** This is
the **multi-session orchestration** pattern (`docs/Core/MULTI_SESSION_ORCHESTRATION.md`),
which is distinct from in-session `Agent`-tool subagents (both are first-class; see §3).

- **Director** (this session): holds strategic context, the forward plan, the gate
  criteria, cross-task synthesis. Writes worker task briefs, synthesizes their
  reports, makes go/no-go calls, **merges to main**, maintains the ledger/state docs.
  Runs in the **main worktree** (`/Users/jacksonmurphy/Dev/trading_machine-2`). Does
  NOT run long backtests/builds itself (context pollution) — it dispatches.
- **Workers (Agents A–E)**: each runs in its **own git worktree** (a fully independent
  checkout — `../trading_machine-agent-{a,b,c,d,e}/`) so they never trample each
  other's HEAD. Each executes one well-scoped task end-to-end (read context → code →
  test → run → commit → push its branch) and reports back a ≤5-line headline.

**How work is dispatched and flows back — the file-based coordination protocol.** There
is no live agent-to-agent messaging. State passes through files in
**`data/coordination/`** (the user relays chat headlines between sessions; the files
carry the detail):

| File | Direction | Purpose |
|---|---|---|
| `agent_<x>_inbox.md` | director → worker | the current task brief (one task, self-contained) |
| `agent_<x>_outbox.md` | worker → director | the worker's ≤5-line headline + proposed ledger row + audit pointer |
| `agent_<x>_t###_staged.md` | director (parked) | pre-written briefs staged for later dispatch |
| `task_queue.md` | director | backlog |

**Shared state stores and where they live:**
- **`docs/State/CURRENT_STATE.md`** — the at-a-glance live dashboard (hard caps: ≤5
  items/section, exactly 1 "next decision"). The Stop hook checks its freshness stamp.
- **`docs/State/TASK_LEDGER.md`** — append-only row per closed task (T-### IDs).
- **`docs/State/forward_plan.md`** — the verbose narrative strategy ("why and where next").
- **`docs/Audit/<topic>_<YYYY_MM>.md`** — one per task; the detailed work record.
- **Memory**: the director's persistent memory lives OUTSIDE the repo at
  `~/.claude/projects/-Users-jacksonmurphy-Dev-trading-machine-2/memory/` (indexed by
  `MEMORY.md`); per-lens agent memory lives in `.claude/agent-memory/<lens>/`.

**Director decision authority** (from `CLAUDE.md`): autonomous to fix charter drift,
remove dead code (to `Archive/`, never delete), add tests/types, refactor, update docs
— **except** anything touching Engine B (Risk) or `live_trader/`, new engines/deps/
services, changes spanning 3+ engines, or boundary/charter language: those are
**propose-first to the user**. The director merges all worker branches; **workers
never push to main**.

**The T-114 protocol (critical):** workers do **NOT** write `TASK_LEDGER.md`. They
propose a ledger row in their outbox; the **director writes it at merge time**. This
keeps the ledger single-writer and merge-ordered.

---

## 3. Sub-agents

⚠️ **Naming collision, read this first:** the six **ENGINES** are A–F (software
modules under `engines/`). The five worker **AGENTS** are A–E (sessions). **They are
not the same A.** Agent C is *not* "Engine C's owner" — e.g. Agent C's recent work
spans Engine B (vol-estimator) and Engine C (portfolio reachability) and owns the
Engine-B/C/E de-gross campaign.

**There are actually TWO subagent systems** — don't conflate them:

**(a) The five multi-session worker agents (A–E).** These are the "five" in the
handoff request. They are **operational lanes, not fixed identities with prompt
files** — the director assigns each task to whichever lane has the continuity (prior
session memory) and lens-fit. Each agent's "config" = its current `inbox.md` brief +
its worktree + its accumulated session memory. Their de-facto stable lanes and current
status (from outboxes/worktree HEADs at this snapshot):

| Agent | Worktree | De-facto lane | Recent tasks | Current status |
|---|---|---|---|---|
| **A** | `../trading_machine-agent-a` | Portfolio sleeves + measurement re-pricing | T-128 sleeve, T-136 survivor data, T-157 LPS re-price | **Sleeve A/B close-out relaunch dispatched** — branch `feature/spot-sleeve-closeout-relaunch` created at main HEAD; **outbox is stale (last entry T-157)** so whether cloud cells are submitted yet is **UNCONFIRMED** |
| **B** | `../trading_machine-agent-b` | Cloud / infra / reproducibility | T-134 speed, T-140 determinism, T-142 hermetic, **T-155 anchors** | **FREE** — T-155 merged; next is the enable-A/B batch (director must pre-register first) |
| **C** | `../trading_machine-agent-c` | Risk/portfolio mechanism + the **T-118 de-gross campaign owner** | T-153 vol-estimator, T-158 reachability, T-162 disambig | **T-162 DONE (reported, not yet merged); T-118 campaign IN FLIGHT** (per C's outbox: 52 cells, ~34 running, 0 failed) |
| **D** | `../trading_machine-agent-d` | Alpha/edge/discovery + data substrate | T-150 intraday, T-149 metalearner, T-154 PIT/survivor | **T-161 harness-fix bundle dispatched** (inbox written); worktree still on `feature/pit-universe-hook-t154` → **not yet started/confirmed** |
| **E** | `../trading_machine-agent-e` | Deployment engineering (the live/paper stack) | T-139/141/146/148/151/152 deployment stack, **T-159 paper design** | **T-160 paper-loop PR-1/PR-2 build dispatched** (inbox written); worktree still on `feature/paper-readiness-design-t159` → **not yet started/confirmed** |

  - **Invocation:** `./scripts/setup_agent_worktree.sh <name> <branch>` creates/refreshes
    the worktree; the user starts a Claude Code session with that dir as cwd and pastes
    the director's brief (the worker reads its `inbox.md`). Continuity sessions are
    re-prompted with "Continuation —"; fresh ones with "Cold start. You are a worker
    session…". There is **no committed per-agent prompt file** — the brief *is* the prompt.
  - **Expected I/O:** input = the `inbox.md` brief (task, method, boundaries, output
    path); output = a pushed feature branch + an audit doc + a `outbox.md` headline +
    a proposed ledger row.

**(b) The in-session cognitive-lens subagents** (`Agent` tool, zero setup). Definitions
live in **`.claude/agents/`** (10 files: `architect.md`, `engine-auditor.md`,
`code-health.md`, `edge-analyst.md`, `risk-ops-manager.md`, `regime-analyst.md`,
`ml-architect.md`, `quant-dev.md`, `ux-engineer.md`, `agent-architect.md`).
`docs/Core/roles.md` defines the **seven cognitive lenses** these implement (the file
count is larger because some are auditor/meta roles). These are used *within* a single
session for scoped, synthesizable sub-tasks (search, audit, code-health scan) — they do
**not** get their own worktree. *(I did not re-verify the exact 7-lens↔10-file mapping;
read `docs/Core/roles.md` if you need it precisely.)*

**When to use which** (`MULTI_SESSION_ORCHESTRATION.md` decision tree): trivial → do it
in the director; small synthesizable result → in-session `Agent` subagent; multiple
long-running independent tasks → multi-session workers.

---

## 4. Repository & branch topology

**Key directories** (top level):
- `engines/` — the six engines + helpers: `engine_a_alpha/`, `engine_b_risk/`,
  `engine_c_portfolio/`, `engine_d_discovery/`, `engine_e_regime/`,
  `engine_f_governance/`, plus `data_manager/` and `execution/`. Charters:
  `docs/Core/engine_charters.md` (engine boundaries are **inviolable** — see §8).
- `orchestration/` — `mode_controller.py` (the real backtest/paper/live controller
  lineage), `run_backtest_pure.py` (the governance-side-effect-free path).
- `backtester/` — `backtest_controller.py`, `execution_simulator.py`, the deployment-
  stack modules (`divergence_monitors.py`, `safef_car25.py`, `after_tax_metrics.py`,
  `dynamic_optimizer.py`-adjacent), the crisis-replay harness.
- `core/` — `metrics_engine.py` (Sharpe/Sortino/**bootstrap CI**), `account_router.py`,
  `hermetic.py`, `multiple_testing.py` (StepM/SPA).
- `scripts/` — all CLIs (run, build, submit, isolate, lint, sync). **Never guess a
  command — consult `docs/Core/execution_manual.md`** and add any new command there
  in the same turn.
- `config/` — JSON config (env-suffixed: `*.dev.json` / `*.prod.json`), the substrate
  manifest, account routing.
- `cockpit/` — dashboards. **`cockpit/dashboard/` is DEPRECATED — never edit it; use
  `cockpit/dashboard_v2/` only.**
- `live_trader/` — a 64-line **stub**, slated for archival (see §7/§9). Propose-first.
- `data/` — gitignored runtime state (price caches, trade logs, governor state,
  coordination files, measurements). NOT in git.
- `docs/` — organized by **lifecycle**, not topic: `State/` (current truth, mutates),
  `Core/` (stable design), `Audit/` (per-task records), `Measurements/<YYYY-MM>/` and
  `Sessions/<YYYY-MM>/` (frozen), `Archive/` (retired). `docs/README.md` is the
  "where do I find X" index.
- `Archive/` — where dead code/docs go (**never `rm`**).
- `tests/` — 2,391 tests collect clean as of this snapshot; contract tests + golden
  master + property suite + forbidden-pattern lint are CI-gated.

**Branch strategy:**
- `main` is the integration branch; the director merges onto it (HEAD at snapshot:
  `6448a55`). Workers never push to main.
- **Experiment/task branches are named `feature/<topic>-t<NNN>`** where `t<NNN>` is the
  task ID (e.g. `feature/hmm-transition-trigger-overlay-t118`, `feature/earnings-pin-bundle-t155`).
  One branch per task, one worktree per active worker.
- **Do experiment results merge back or get discarded?** **It depends on the verdict,
  and the branch is preserved either way** (we Archive, never delete):
  - **Positive / shipped capability** (default-OFF + canon-proven) → **merged to main**
    (e.g. the entire deployment stack T-139/141/146/148/151/152).
  - **Refuted / negative** → often **NOT merged** but the **audit doc + ledger row are
    still written** (the negative result is the deliverable). Example: `feature/h-band-no-trade-t098`
    is refuted+inert, branch left unmerged. The branch list in `git branch -a` is a
    graveyard of ~100 such task branches — they are the experiment trail, intentionally kept.
  - The **measurement** (numbers, CIs, mechanism) is what's "kept" regardless of
    merge — captured in `docs/Audit/` and `MEMORY.md`.

There is also an **external collaborator branch convention** seen recently:
`claude/<topic>` (the outside-dev review came in on `claude/project-review-improvements-e0gy45`,
merged as T-156 after independent director verification).

---

## 5. How to run an experiment end to end

**From a clean clone:**

1. **Dependencies.** Python 3 (the cloud image pins a base digest; local dev uses the
   venv). `pip install -r requirements.txt` for the runtime; **`requirements.lock.txt`**
   is the pinned set the cloud image builds from (includes `hypothesis`, `openpyxl`,
   `xlrd` added via T-155). Core libs: pandas≥2.0, numpy≥1.24, yfinance, requests,
   beautifulsoup4, vaderSentiment, scikit-learn (for HRP/Ledoit-Wolf), boto3 (AWS).
2. **Config / env vars (NAMES only — never commit values):**
   - **Broker (Alpaca):** `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` (and legacy aliases
     `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`; base-URL vars `ALPACA_API_BASE_URL` /
     `ALPACA_BASE_URL`). **Values live in `.env`** — `.env` is intentionally readable
     for this project but its contents must **never** be echoed into chat or committed.
   - **AWS:** local sessions share `~/.aws/credentials` under **profile `archondex`**
     (account `407539788432`, region `us-east-1`). CI auth is via the GitHub repo
     secret **`AWS_ROLE_TO_ASSUME`** (OIDC; at `github.com/jmur214/ArchonDEX`).
   - **Run-control env vars:** `PYTHONHASHSEED=0` (determinism — see below);
     `ARCHONDEX_BUILD_PUSH=1` (registry-direct image build); `ARCHONDEX_HERMETIC`
     (block live network fetches); the per-cell `ARCHONDEX_{CELL_ID,YEAR,START_DATE,
     END_DATE,REP,RESULTS_BUCKET,…}` that the cloud entrypoint reads;
     `ARCHONDEX_SKIP_SUBSTRATE_VERIFY` (escape hatch, avoid).
3. **External services:** Alpaca (market data + paper/live broker), AWS (Batch compute,
   ECR images, S3 results bucket `archondex-results-407539788432`), GitHub Actions
   (the **canonical image build venue** — local Docker is retired, see §9). Free data:
   Stooq/yfinance caches, FRED/macro archives under `data/macro_data/`.

**Local backtest (the canonical commands — from `docs/Core/execution_manual.md`):**
```bash
# Standard prod backtest (updates governor learned state):
PYTHONHASHSEED=0 python -m scripts.run_backtest --env prod --mode prod

# Deterministic A/B (no governor mutation; reproducible):
PYTHONHASHSEED=0 python -m scripts.run_backtest --no-governor
# preferred wrapper that handles anchor save/restore + md5 compare:
python scripts/run_deterministic.py

# Multi-year foundation measurement:
PYTHONHASHSEED=0 python -m scripts.run_multi_year --years 2021,2022,2023,2024,2025 --runs 3 \
    --output docs/Measurements/<YYYY-MM>/<name>.md
# add --use-historical-universe for survivorship-correct universe
```
- `--env {dev,prod}` selects config pair; `--mode {sandbox,prod}` selects governor
  state path; `--no-governor` skips the post-run write; `--reset-governor` neutralizes
  learned weights for clean in-sample measurement. **Determinism requires
  `PYTHONHASHSEED=0`** (string-hash randomization changes `set()` iteration order →
  FP-summation drift).
- **Discovery cycle** (edge promotion is autonomous — never promote by hand):
  `python scripts/run_autonomous_cycle.py` (add `--loop` for continuous).

**Cloud campaign (for ≥4 cells AND >2h local wall-time — `docs/Cloud/CLOUD_USAGE.md`):**
```bash
# 0. Pre-flight (STOP if any fail):
aws sts get-caller-identity --profile archondex     # expect account 407539788432

# 1. Build + push a provenance-pinned image (THE ONLY sanctioned build path —
#    never raw `docker build .`, which bakes host __pycache__ → the stale-bytecode bug):
ARCHONDEX_BUILD_PUSH=1 scripts/build_backtest_image.sh HEAD \
    407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:sha-<short>
#    (or push to main → GitHub Actions builds it; the `:dev` tag is RETIRED — use sha-tags
#     + the env-pinned job definition only.)

# 2. Mandatory 2-cell verify spec FIRST (canon_md5 of the two cells MUST differ, else the
#    patch didn't apply — this caught a $1.50 wasted 75-cell run). Then submit the grid:
python scripts/submit_substrate_run.py --reps 3 --arms 1,2 --job-timeout 21600   # 26-yr = 6h, never less
#    (copy + adapt this launcher's Cell dataclass for non-substrate campaigns.)

# 3. Pull results:
aws s3 sync s3://archondex-results-407539788432/<launch_prefix>/ data/trade_logs_cloud/<id>/ \
    --profile archondex --region us-east-1
python -m scripts.metrics_report --run-ids $(ls data/trade_logs_cloud/<id>/ | paste -sd,)
```
- Each cloud cell runs `python -m scripts.run_isolated --runs 1` inside the container
  (entrypoint `scripts/cloud_entrypoint.sh`); `run_isolated.py` flags include
  `--save-anchor`, `--runs N`, `--show-hashes`, `--journal-mode`.

**Where outputs land:** local trade logs → `data/trade_logs/<uuid>/trades.csv` +
`performance_summary.json`; measurements → `data/measurements/` and
`docs/Measurements/<YYYY-MM>/`; cloud results → S3 then `data/trade_logs_cloud/` and a
launch CSV at `data/cloud_runs/substrate_<ts>.csv`; the narrative verdict → a
`docs/Audit/*.md` doc + a `TASK_LEDGER.md` row.

---

## 6. Evaluation — how we judge success

**The unit of determinism: `canon_md5`** — the md5 of the run's `trades.csv`. Two runs
of the same commit+substrate must produce the **same canon** (proven 3-builds-1-canon).
Cross-container determinism is the gold standard (local `--runs N` can't see the
FP-summation-order class of bug). **Anchors** are the published reference canons:
26-yr `529e5520`/Sharpe 0.237, 16-yr `62db5c0d`/1.021, 2022 `0a62b754`/1.6 — image
`sha-5323a3c`, job def `archondex-backtest-t155-anchor:3` (per Agent B's T-155 outbox).

**Statistical gates (non-negotiables in `CLAUDE.md`; full numbers in
`docs/Core/NON_NEGOTIABLES.md` and `docs/Audit/honest_n_mbl_computation_2026_05_12.md`):**
- **Every Sharpe headline must report a bootstrap-CI lower bound** (`ci_low`) from
  `MetricsEngine.bootstrap_distribution` (block bootstrap, Künsch 1989, ~1000 iter).
  A bare point-estimate is "not a measurement." Already wired into every
  `performance_summary.json`.
- **Kill / gating decisions compare `ci_low`, not the point estimate.** The kill
  thesis "Sharpe < 0.4 net of costs" reads as `ci_low < 0.4`. A point 0.45 with
  ci_low 0.10 does NOT clear the gate.
- **DSR (Deflated Sharpe):** strict `ci_low > DSR-benchmark (~0.66)` — currently
  **fails on every window** → nothing is formally "validated" yet.
- **MBL (minimum backtest length, Bailey-López de Prado):** `T_years ≥ 2·ln(N_eff)/SR²`.
  At the accumulated **honest N** (~75–260 trials incl. every cloud cell / aggregator
  iteration), the 26-yr window needs **SR ≥ 1.55** to clear DSR — the 0.237 baseline
  cannot, by design. **Pre-register every measurement** (hypothesis + threshold +
  N_trials consumed) BEFORE running; no goalpost-moving.
- **Float guards** use tolerance, not equality (`std < 1e-12`, not `std == 0`).

**The T-118 headline gate (the in-flight campaign's success criterion):** the frozen
gate is **Sharpe-difference ci_low > 0 AND 26-yr MDD improved by ≥25% AND no single-
event dependence**. The crisis-replay second read is **pre-registered and LOCKED** in
`docs/Audit/t118b_preregistration_2026_06_10.md` (Addendum v3 FINAL: 7 enumerated crisis
episodes, sign test ≥6/7, all-3-OOS must improve, GFC floor ≥+5pp, calm-drag ceiling —
no further amendments). The harness is tested code: `scripts/crisis_replay_t118b.py` +
`tests/test_crisis_replay_t143.py`.

**Where to look:** per-run `performance_summary.json`; the ledger `docs/State/TASK_LEDGER.md`;
per-task `docs/Audit/*.md`; the dashboard at **`cockpit/dashboard_v2/`** (v1 deprecated);
the live dashboard `docs/State/CURRENT_STATE.md`.

---

## 7. Current state & next steps

**Most recently completed (merged to main):**
- **T-155 Part 3 — THE ANCHORS** (`4dbbbf0`): 9/9 bitwise-unanimous, **canon
  continuity on every window** (the feared hermetic re-baseline never happened). The
  T-128 placement-lottery + bytecode + data-drift saga is fully closed. Fleet is ARM64;
  CI (GitHub Actions) is the canonical build venue.
- T-154 (survivor inflation −3.54pp lower bound; risk-adjusted verdicts survive),
  T-157 (LPS unharvestable verdict survives the auction model), T-158 (the **allocator
  divergence** — see §9), T-159 (paper-trading readiness design), T-156 (outside-dev
  review, independently verified).

**In flight (per worker outboxes / branch HEADs at this snapshot):**
- **C — T-118 de-gross campaign RUNNING** on the published anchors: 52 cells, ~34
  running / ~21 runnable, 0 failed (per C's outbox). Launch branch
  `feature/hmm-transition-trigger-overlay-t118-launch`. Verdict is hours out; analysis
  follows the frozen gate + the LOCKED T-118b read.
- **C — T-162 reported DONE but NOT YET MERGED** (see the loose end below).
- **A — sleeve A/B close-out relaunch** dispatched (`feature/spot-sleeve-closeout-relaunch`);
  self-report not yet in (status UNCONFIRMED).
- **E — T-160** (paper-loop PR-1 OrderManager/journal/ledger + PR-2 reconciliation/
  dry-run scheduler, pure-new `paper_trader/`) dispatched; not yet confirmed started.
- **D — T-161** (harness fixes: `ensure_data` timeout, PIT-mask fail-loud, OFF-proof
  close-out) dispatched; not yet confirmed started.
- **B — FREE** (T-155 closed).

**Concrete next tasks the collaborator (as director) should pick up, in order:**
1. **⚠️ Merge T-162** — Agent C's outbox reports it DONE (branch
   `feature/allocator-disambig-t162`, pre-reg commit `48393fd`, result `e2cba84`) with a
   clean **H-mix** verdict (the Apr-23 allocator artifact explains ~all of the local↔cloud
   Sharpe split — worth ~1.1 Sharpe on the 2022 cell — with a small irreducible BLAS
   residual). It is verified-pre-registered and ready; the director just needs to merge +
   write the ledger row + reconcile CURRENT_STATE. **This is the top loose end.**
2. **Monitor the T-118 campaign**; when cells land, run the frozen-gate + T-118b analysis.
3. **The director-held allocator-identity decision** (now evidence-complete via T-162):
   archive the `data/research/allocation_recommendations.json` Apr-23 artifact vs commit
   its intent to config. **Deliberately deferred to post-anchors**; it decides which
   system every *local* number describes. Largest single behavioral lever since the
   metrics-pipeline bug.
4. **Pre-register the enable-A/B batch** (T-148 buffering enable + T-153 vol-estimator
   enable specs) BEFORE dispatching to the (free) Agent B.
5. **When T-118 + sleeve verdicts are in → convene "the fork"** (the architecture/mission
   decision) with the 2026-06-11 conditional-sleeve directive on the table.
6. **Optional/cosmetic (user, AWS console):** add `ecr:BatchGetImage` to the CI role —
   second-tag image pushes fail without it (first push succeeds; non-blocking).

---

## 8. Conventions & guardrails

**Commits** (`.claude/skills/commit/SKILL.md`): `<type>(scope): <summary <60 chars>` +
WHY-body. Types: feat/fix/refactor/docs/test/chore/archive/wip. Atomic (one logical
change). **Verify `git diff --staged` shows no secrets (`APCA_*`/keys/`.env`) and no
`data/` files before every commit.** Director merges to main end commit messages with a
`Co-Authored-By:` trailer.

**Git actions allowed autonomously:** add/commit/status/diff/log, branch, checkout -b,
stash. **MUST propose first:** `git push` to any remote, `git merge` onto main,
`git pull`, `git tag`, and **anything force/reset/delete** (these are deny-listed at the
permission layer).

**Hard guardrails (things that must NOT be modified / will silently break):**
- **Archive, never delete.** `rm`, `git clean`, `git reset --hard` are deny-listed.
- **Engine boundaries are inviolable** — no engine does another's job. Read the charter
  in `docs/Core/engine_charters.md` before touching engine logic. Risk logic stays out
  of Engine A; signal generation stays out of Engine B.
- **Engine B (Risk) and `live_trader/` are propose-first** — every change ships
  default-OFF + canon-proven; *enabling* anything is user-gated.
- **Never edit `cockpit/dashboard/`** (deprecated) — use `cockpit/dashboard_v2/`.
- **Never hand-edit `data/governor/edge_weights.json` or promote edges manually** —
  Engine F manages lifecycle; the `--discover` cycle promotes.
- **`.env` is readable but never echoed into chat or committed.**
- **The T-114 ledger protocol:** workers propose ledger rows in their outbox; only the
  director writes `TASK_LEDGER.md`, at merge.
- **The sanctioned image build path only** (`scripts/build_backtest_image.sh` /
  CI) — raw `docker build .` bakes host `__pycache__` and reintroduces the stale-bytecode
  +0.21-Sharpe artifact.
- **`PYTHONHASHSEED=0` for any determinism-sensitive run** — omit it and `set()`
  iteration order drifts canons.
- **Substrate manifest discipline:** `data/processed/`+`data/raw/`+governor anchors are
  pinned by `config/substrate_manifest.sha256`; the 9 live mutable governor files are
  excluded. Updating an anchor is a deliberate, manifest-regenerating, director-
  coordinated act (anchors are symlinked + write-protected `0o444` across worktrees).

**Worktree data isolation (silent-corruption trap):** `setup_agent_worktree.sh`
symlinks read-only `data/` subdirs but **copies `data/governor/`** per agent (two
concurrent backtests writing the same governor files race and corrupt). Never symlink
`data/governor/`. Within one worktree, back-to-back backtests serialize on its governor
copy.

**Session-close hygiene** (some automated via hooks): update `execution_manual.md` if
new CLI was used; run `python scripts/sync_docs.py` if you touched `engines/**/*.py`;
run the doc-lint (`python scripts/doc_lint.py`) BEFORE pushing (it checks the
`MEMORY.md` byte-cap and ledger column counts — both have silently broken pushes
before); write a session summary to `docs/Sessions/<YYYY-MM>/`.

---

## 9. Known issues & gotchas

- **🔴 THE ALLOCATOR DIVERGENCE (T-158, the biggest live gotcha).** Local and cloud
  have run **different trading systems** since 2026-04-23. A learned artifact,
  `data/research/allocation_recommendations.json` (fail-quiet loader, `mode` in the
  override safe-keys at `engines/engine_c_portfolio/policy.py:138`), flips every **local**
  `allocate()` to **adaptive** (vol-target + exposure-cap overlays LIVE, max_weight 0.15);
  the file is **not in the cloud image**, so every **cloud** canonical number ran
  **mean_variance** (overlays dead, max_weight 0.30). **Cross-substrate (local↔cloud)
  comparisons are allocator-confounded** — only compare within-cloud. T-162 quantified
  this (worth ~1.1 Sharpe); the archive-vs-config decision is pending (§7).
- **`policy.py` normalization cancels signal-level timing (T-156/T-122).** Inverse-vol
  weights are normalized by their sum → **scale-invariant in signal level**: any uniform
  timing/regime signal cancels algebraically before it can move gross exposure.
  Conditioning must be expressed **downstream of normalization** (capital/position
  layer), never at signal level. De-gross levers must target Path-A `target_notional`.
- **No order-state machine exists anywhere (T-159).** All three execution paths assume
  `submit == filled`. The `live_trader/` stub fire-and-forgets GTC market orders, has no
  idempotency (crash → double-submit), sizes via the dead Path B, and never routes exits;
  `orchestration/mode_controller.py`'s Alpaca adapter **fabricates fills at intended
  prices** (`:28`, `:103`). This is why paper trading needs a real build (E's T-160), and
  why the stub is slated for archival (PR-4, hard-gated).
- **`ensure_data` no-timeout network fetch (T-154 footgun).** A C-level blocking read
  that `SIGALRM` can't interrupt — it stalled D's 12-yr A/B four times. The live ensemble
  harness is **not safe for unattended multi-hour local runs** until T-161 lands the
  timeout. Workaround: run offline (unset Alpaca keys → cache-only) or use the cloud.
- **Local Docker is retired as a build venue** — `Docker.raw` buildkit metadata is
  corrupted (4th disk/corruption incident). **GitHub Actions is the canonical build
  path.** Local daemon is now non-critical.
- **CI role lacks `ecr:BatchGetImage`** — second-tag image pushes fail cosmetically
  after the first succeeds (one-line IAM fix pending).
- **Substrate-conditional findings reverse on substrate change.** Multiple "DEFENSIBLE"
  5-yr lifts (T-055e, T-057) reversed on the extended window. Any positive lift measured
  on substrate X must be **re-verified on the production substrate** before any flag-flip
  recommendation (`CLAUDE.md` non-negotiable #9).
- **Single-cell OFF-canon ≠ 26-yr-inert** (~0.009 benign leak, T-126) — a default-OFF
  proof on one cell doesn't prove deep-window inertness; add a deep-window canon check.
- **T-162 brief-window shared-data caveat** (per C's outbox): during the ~10-min artifact
  displacement, any *other* local backtest would have transiently run mean_variance. If
  any local run happened this afternoon between C's pre-reg and restore commits, re-check it.
- **Naming collision** (restated — it bites newcomers): Engines A–F ≠ Agents A–E.
- **Cloud cost discipline:** always run the **2-cell verify spec** before a full grid
  (a key-namespace typo once produced 75 identical cells); 26-yr cells need
  `--job-timeout 21600` (a too-tight timeout SIGKILLed a completed run mid-S3-upload).

---

*End of snapshot. For anything not covered here, the index is `docs/README.md`; the
live state is `docs/State/CURRENT_STATE.md`; the command reference is
`docs/Core/execution_manual.md`; the rules are `CLAUDE.md` + `docs/Core/NON_NEGOTIABLES.md`.*
