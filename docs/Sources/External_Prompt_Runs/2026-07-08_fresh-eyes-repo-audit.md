---
run_date: 2026-07-08
agent: fresh-eyes codebase auditor (full repo read access, zero prior context)
model: not recorded (run predates the self-report rule — see SESSION_PROCEDURES.md "External prompt runs")
executed_by: user (fresh Claude Code session in the repo)
prompt_working_copy: data/coordination/prompt_fresh_eyes_agent_2026_07_07.md
report_working_copy: data/coordination/fresh_eyes_report_2026_07.md (gitignored relay space — archived here)
status: findings triaged 2026-07-08 — dispositions in docs/State/health_check.md ("Info-Layer fresh-eyes audit findings") and commit c2008dc
---

# External Prompt Run — Fresh-Eyes Repo Audit (Info-Layer program verification)

Permanent record per the archive-every-run rule. Triage summary: finding #1
(archivers can't fail loudly) FIXED same day (`scripts/verify_altdata_snapshot.py`
+ SNS/notification alarm, commit c2008dc); #2 (no per-account pulse; CloudState
not an archive layer) folded into T-288 + program-doc amendment; #3 (Phase A/B
capture-time discontinuity) resolved by making launchd permanent; #4 (no tests
on new senses) largely cured by the T-289/290/291/293 merge wave; #5 (Lane-3
safety greenfield) is by-design/sequenced. Full dispositions: health_check.md.

---

# THE PROMPT (as run)

# PROMPT — Fresh-Eyes Codebase Agent (full repo access, zero prior context)

You are a senior quant engineer doing an independent review of this repository. You have FULL read access to the codebase and docs, but NO conversation history and NO context beyond what is in the files. That is deliberate: the team has been deep in this system for months and wants an outsider's eyes. Do not ask the team what they meant — if the repo doesn't make it knowable, that itself is a finding.

## Orientation (read in this order, then stop reading broadly and start verifying)

1. `CLAUDE.md` — operating rules and non-negotiables (these bind you too: **read-only review — no edits, no `rm`, nothing destructive**).
2. `docs/State/CURRENT_STATE.md` — the live-state dashboard; current truth when docs disagree.
3. `docs/State/forward_plan.md` — the strategy narrative, including the 2026-07-07 program banner.
4. `docs/Sources/info_layer_program_2026_07_07.md` — the just-launched Information + Judgment Layer program spec. This is your primary review target.
5. `docs/State/TASK_LEDGER.md` + `docs/README.md` — task history and navigation. Use `docs/Audit/` for point-in-time evidence, but remember: archived/measurement docs are snapshots, not current truth; `edges.yml` is the sole edge-status authority.

## Your mission — three questions, evidence-based

### 1. Audit the new program spec against the codebase it claims to build on
The info-layer spec names specific reusable assets (a news collector with PIT timestamps, Kalshi/Polymarket archiver scripts, an FOMC list inside a probe script, a detector registry in Engine E, a BTC shadow tracker, an S3 cloud-state layer, a daily paper pulse). **Verify each claim by opening the actual files.** Do the named functions/line-ranges exist and do what the spec says? Are the integration points (the daily pulse in `scripts/run_paper_cloud_day.py`, the detector registry, `CloudState`) actually shaped the way the spec assumes? Where the spec's plan would collide with existing code structure, say exactly where and why.

### 2. Where is this system genuinely lacking?
Independent of the program spec: from the code and docs alone, what are the biggest weaknesses, fragilities, or blind spots? Candidates to investigate (not an exhaustive list — follow your own nose): single-points-of-failure in the paper-trading path; test coverage on the measurement-critical code vs the decorative code; config/flag sprawl (what's default-OFF and would anyone notice if it silently stayed off?); the honesty of the fail-closed discipline (grep for silent excepts / fallback-to-default patterns in measurement paths — the repo's own audits say this is the recurring disease); doc-vs-code drift in the places that matter (engine charters vs implementations); operational fragility of the launchd/cron/EventBridge scheduling mesh.

### 3. What would you attack?
Adversarial pass on the LLM judgment layer design (spec §Lane 3): given the actual code patterns in this repo (how notes/state/S3 sync work), where would prompt injection, schema-gaming, cost blowup, or silent degradation actually bite? Is the authority ladder enforceable in code as designed, or does it rely on discipline?

## Rules of engagement

- **Verify, don't trust.** The docs are unusually good but written by insiders; every load-bearing claim you repeat must be one you checked against code or data files yourself. Cite `file:line` for everything.
- Distinguish clearly between: **(a)** confirmed defects (with the failure scenario), **(b)** design risks (plausible, not yet demonstrated), **(c)** questions the repo cannot answer (missing docs/tests — themselves findings).
- Rank findings by severity. Ten sharp findings beat fifty vague ones.
- You may run read-only commands (pytest on existing tests, `git log`, greps, loading parquets to check schemas/row counts). Do NOT run backtests that mutate state, do NOT touch anything under `live_trader/`, `data/governor/`, or AWS.

## Deliverable

Write your report to `data/coordination/fresh_eyes_report_2026_07.md`: an executive summary (≤1 page — the five things the team most needs to hear), then the ranked findings with evidence, then the (a)/(b)/(c) classification. Blunt beats polite; this team explicitly prefers "brutal realism about system flaws" (it's in their CLAUDE.md). If something is genuinely good, one line saying so is enough.

---

# THE FINDINGS (verbatim — the full report file)

# Fresh-Eyes Review — Information + Judgment Layer Program & System Health

**Reviewer:** independent senior quant engineer (no conversation history; code + docs only)
**Date:** 2026-07-07
**Scope:** (1) audit `docs/Sources/info_layer_program_2026_07_07.md` against the code it claims to build on; (2) independent weakness assessment; (3) adversarial pass on the Lane-3 LLM design.
**Method:** every load-bearing claim below was checked against a specific file/line or data file. Cited as `path:line`.

---

## Executive summary — the five things to hear

1. **The DAY-1 "the FINRA data loss is STOPPED" claim is overstated — the archivers cannot fail loudly.** Both `archive_altdata_t136.py` and `archive_positioning_t136.py` return **exit 0 on every realistic failure** (API 401/403, layout change, zero rows) — failures come back as descriptive *strings*, never a non-zero exit (`archive_altdata_t136.py:242`, `archive_positioning_t136.py:232`). The wrapper's `ALTDATA_ARCHIVER_FAILED` token (`scripts/run_altdata_archivers.sh`) fires only on non-zero RC, which those scripts are structurally incapable of producing. Output goes to an unmonitored per-day log; there is **no heartbeat, no dead-man's-switch, no alarm** on the launchd path (contrast the paper loop, which has all three). If Kalshi's API changes tomorrow, the archiver prints "FAILED", exits 0, launchd is satisfied, and snapshots silently stop — the exact `[NN-FAIL-CLOSED]` disease this program was launched to cure. **This is a confirmed defect, and it lives in the code shipped as the urgent rescue.**

2. **Two of the spec's "key reused assets" are not shaped the way the plan assumes.** (a) `scripts/run_paper_cloud_day.py` is **hardwired single-account and monolithic** — there is no "per-account pulse pattern" to clone for the T-288 fleet or the Stage-2 4th LLM account; that abstraction has to be *built*, not reused. (b) `paper_trader/cloud_state.py` syncs a **fixed small-file list** (`DURABLE_PATHS`, `cloud_state.py:39-49`) via per-file `aws s3 cp`; it is not an archive-sync layer. Routing a growing news panel, daily altdata snapshots, and analyst notes "via CloudState" either re-uploads everything daily or needs new code — and any state the shadow book/analyst relies on must be added to `DURABLE_PATHS` or it evaporates with the Fargate container.

3. **Phase A and Phase B capture data at different times of day, and nobody flagged it.** The launchd archiver runs **18:30 ET** (`com.archondex.altdata-archive.plist:14-18`); the cloud pulse the spec wants to fold it into runs **09:45 ET** (`scripts/deploy_paper_cloud_trigger.sh:174`, `cron(45 9 ? * MON-FRI *)`). "Run both in parallel 2 weeks, then retire launchd" silently shifts the snapshot ~9 hours earlier — a different slice of intraday prediction-market state and a different FINRA vintage. The same 09:45 timing makes the "daily analyst note on the day's news" a *pre-open* note on near-empty same-day news.

4. **The fail-closed discipline is genuinely strong where it was hardened — and absent in the new senses.** `core/` carries only 4 `except` blocks total; `run_paper_cloud_day.py` fails closed hard (`return 67/68/69` on stale/missing/invalid sleeve inputs, lines 193-226). That rigor did **not** propagate to the ingest layer (finding #1) or to test coverage: 214 test files, solid coverage on the paper core (`test_btc_shadow_t276`, `test_paper_cloud_t186`, `test_paper_day_orders_t238`), **zero** on the archivers, calendar, event-state, or analyst. Verification of the new data spine is a manual director ritual ("3 consecutive days of growing row counts"), not an automated guard.

5. **Lane 3's safety rests almost entirely on code that does not exist yet.** `intelligence/analyst/` and `config/prompts/` are absent (greenfield, expected). The one solid reusable template — `paper_trader/btc_shadow.py` — is genuinely good (report-only, fail-closed, idempotent) and the shadow-book generalization is credible. But the semantic firewall, cost governor, and injection suite are all to-be-built; the authority ladder is enforceable **if** built as specced and **not enforced by anything today**. Stage-2 (a 4th account with real LLM order authority) additionally depends on the multi-account harness from finding #2 that isn't built.

The spec's own "Honest risks" section (lines 64) is unusually candid and pre-registers most of the *scientific* risks well. The gaps above are almost all **operational/integration** risks the science-focused framing understates.

---

## Ranked findings

### F1 — Archivers cannot fail loudly; "data loss STOPPED" is overstated  **(a) confirmed defect · HIGH**
- `archive_altdata_t136.py:237-242`: `main()` iterates the pull/snapshot functions and `return 0` unconditionally. `snapshot_kalshi` (`:233-234`) and `snapshot_polymarket` (`:197-198`) catch all exceptions and **return a string** (`"kalshi: FAILED (...)"`); a zero-row result returns `"kalshi: 0 matching markets"` (`:230`). None raise; none exit non-zero.
- `archive_positioning_t136.py:216-232`: identical pattern — every FINRA/FTD/SI failure path returns a string (`"...FAILED"`, `"...no files reachable"`, `"layout change"`), `main()` returns 0.
- `scripts/run_altdata_archivers.sh`: emits `ALTDATA_ARCHIVER_FAILED` only when `RC1`/`RC2` is non-zero — **unreachable** given the above. Logs to `data/macro_data/alt/logs/archive_<date>.log`; nothing polls it. launchd plist has no `KeepAlive`/failure hook.
- **Failure scenario:** Kalshi rotates its public endpoint (the code even anticipates "if 401/403, public access changed" at `:234`). The archiver logs the failure, exits 0, launchd reports success, no alarm fires. Snapshots stop; the loss is discovered only if a human reads the log or notices flat row counts. Indistinguishable from a legitimately quiet market day, because the system cannot tell "API broke" from "zero matches."
- **Note:** the spec assigns "zero-row days must flag loudly" to **Phase B, ~2-3 weeks out** (line 31). So the acute-urgency Phase A shipped *without* the one safety property that makes an archiver trustworthy. The parquet-append is idempotent and non-corrupting (`_append`, `:68`), so this is a silent-*gap* risk, not a data-corruption risk — but for a program whose thesis is "un-missing markets is not possible later," a silent capture gap is the whole ballgame.

### F2 — "Per-account pulse pattern" does not exist; the driver is single-account/monolithic  **(a) confirmed (doc-vs-code) · HIGH for Stage-2/T-288**
- `scripts/run_paper_cloud_day.py:64-321`: one `main()`, one `AlpacaPaperClient()` (`:97`), one `OrderManager`, one `LedgerStore(account="roth")` (`:124-126`), a single `--strategy` switch. No account loop, no per-account parameterization beyond the single credential pair from env.
- The spec's Stage-2 ("clone the per-account pulse pattern... zero contamination", line 50) and the parallel T-288 3-account fleet both assume an abstraction that isn't in this file. MEMORY confirms the fleet "awaits the user's 2 extra paper-acct keys" — i.e. unbuilt.
- **Consequence:** "clone, don't invent" (spec line 64) is not available for the 4th account; the multi-account harness is net-new work and is on the critical path for the LLM's real-account authority. New "pulse steps" (news append, altdata archive, analyst note) are inline insertions into a 260-line function before `cloud.push()` (`:312`), not registrations against an extension point.

### F3 — CloudState is a fixed-small-file sync, not an archive layer  **(b) design risk · MED-HIGH**
- `paper_trader/cloud_state.py:39-49`: `DURABLE_PATHS` is a hardcoded list of small state files (journal, ledger, heartbeat, `sleeve_tracking.json`). `push()`/`pull()` (`:95-122`) `aws s3 cp` each one every run.
- Spec routes the news panel (monthly parquets), daily altdata snapshots, and write-once analyst notes "via CloudState" (lines 25, 43). None of that fits: growing/large files re-`cp`'d daily, or (more likely) never synced because they're not in `DURABLE_PATHS`. Analyst notes and the LLM shadow book state must be explicitly added to `DURABLE_PATHS`, or on Fargate they vanish at container exit — the exact failure `cloud_state.py`'s own docstring (`:5-10`) was written to prevent.
- **Design fix implied:** a separate append/prefix-sync path for `altdata/`, `news_panel/`, `analyst_notes/` (S3 `sync`, not per-file `cp`), plus explicit registration of any state the shadow book/analyst reads back. Not hard, but it's unscoped work the "reuse CloudState" framing hides.

### F4 — Phase-A/Phase-B snapshot-time mismatch changes the series  **(b) design risk · MED**
- launchd 18:30 ET (`...plist:14-18`) vs pulse 09:45 ET (`deploy_paper_cloud_trigger.sh:174`). Folding one into the other is not time-neutral. For prediction markets (intraday-varying) and FINRA (end-of-day publication) the captured value differs. The "parallel 2 weeks then retire launchd" plan (spec 2.1) would create a discontinuity in the very time series the program is trying to start accruing.
- **Also:** the analyst note as "a final report-only pulse step" (spec 3.1) executes at 09:45 ET — pre-open, on same-day news that barely exists. Defensible as an overnight-digest note, but it is not the end-of-day synthesis the "day's news for holdings" language implies.

### F5 — Lane-3 authority ladder & firewall rely on discipline, not existing enforcement  **(b) design risk · MED**
- `intelligence/analyst/` and `config/prompts/` do not exist. The semantic firewall (symbol allowlist, weight/turnover/probability bounds), `cost_governor`, and injection fixture suite are all to-be-built. Nothing enforces the ladder today.
- The **good news, verified:** `paper_trader/btc_shadow.py` is a strong template — report-only (`:1-9`), fail-closed with explicit `degraded=True` and cash-parking (`:19-22`, `:109-117`), idempotent on date (`:119`), frozen pre-registered gates (`:46-57`), signal-t/fill-t+1 look-ahead-impossible construction (`:68` `.shift(1)`). Generalizing it to the LLM shadow book is credible and the safest part of Lane 3.
- **The risk is the ladder's enforceability under change.** G0→G1→Stage-2 gates are frozen *in a doc*; the code that would refuse promotion (kill_switch check pre-submission, firewall rejects) is unwritten. "Enforceable in code as designed" is achievable but currently aspirational; until the firewall + governor exist and are tested (the spec makes the injection suite a Stage-0 exit gate — good), the ladder is a policy, not a control.

### F6 — Prompt-injection defenses are probabilistic; schema-gaming is the real exposure  **(b) design risk · MED**
- The analyst ingests third-party news **content** (spec keeps `content`, line 25) — adversarial text by construction. The strongest defenses are structural and correctly chosen: no tools / no agent loop (spec 3.1), report-only stages, signal-t/fill-t+1. These I credit.
- The weaker links: "data/instruction separation" (spec 3.2(3)) is not a hard boundary for an LLM; and a schema-*valid* but adversarially-chosen action (allowlisted symbol, in-bounds weight, wrong direction) passes JSON validation and is caught only by the semantic firewall's economic bounds — which are to-be-built and only as good as their thresholds. Cost blowup is bounded by an unbuilt governor; the $5-8/mo estimate (spec 3.1) is plausible but unverifiable pre-build, and a homoglyph/inflated-`max_tokens` payload is exactly the cost-amplification vector the red-team suite must cover.
- **Verifiable positive:** because the shadow book consumes *yesterday's validated* actions and fills at today's close (btc_shadow pattern), an injected action cannot create look-ahead profit — the worst case is a bad paper trade in an isolated account, logged and Brier-scored. The blast radius is well-contained *by design*, if the isolation (finding #2's 4th-account harness) is actually built clean.

### F7 — The "detector registry" is not a registry  **(a) confirmed (doc-vs-code) · LOW-MED**
- Spec 2.4 says EventStateDetector is "registered per the existing pattern (`regime_detector.py:74-81`)." Those lines (`regime_detector.py:74-81`) are **hardcoded constructor assignments** (`self._trend = TrendDetector(...)`, etc.); `detectors/__init__.py` is a static 5-name `__all__` import list with no registry. Adding a 6th detector is a manual multi-site edit (constructor + `detect_regime` aggregation + the `RegimeConfig` dataclass + `__init__.py`), not a registration. Minor, but the language implies less integration surface than exists, and the aggregation path in `detect_regime` (`:146+`) will need the new axis wired in by hand.

### F8 — FOMC-list provenance & the probe's foreign-worktree path  **(a)/(c) · LOW-MED**
- The 1994-2025 FOMC list (`calendar_flow_probe_t250.py:17-50`) exists as claimed and is labelled "hand-compiled, best-effort" (`:17`). The spec's rule "2026 dates from the Fed site only" is right — but note the **existing** list is itself unverified against federalreserve.gov, and the modularization plan requires "output byte-identical" to this probe.
- Byte-identity verification is fragile: the probe hardcodes `ROOT='/Users/jacksonmurphy/Dev/trading_machine-agent-d'` (`:5`) — a *different worktree* — and reads `data/processed/SPY_1d.csv` and `RF=0.04` from there (`:5-13`). Re-running it for the byte-identical check depends on that sibling worktree existing and matching. The calendar extraction itself is fine to lift; the verification ritual around it is brittle.

### F9 — `fetch_history_alpaca` never reads `symbols`/`content` (not merely "discards")  **(a) confirmed · LOW (scoping)**
- Spec line 8: "content/symbols currently *discarded*." Precisely: `fetch_history_alpaca` (`news_collector.py:298-379`) extracts only `headline, summary, created_at, source, url` (`:348-352`) into `NewsItem`; it never touches `it.symbols` or `it.content`. So the panel build must **add** field extraction (a small change), and — more importantly — the depth/survivorship the entire lane rests on is genuinely unprobed: the on-disk proof corpus is **1,716 rows, single month, Jan-2024 only** (`data/intel/history/`, verified 1717 lines incl. header). The spec flags this honestly (it gates the lane on a probe), but the underline is worth it: **Lane 1's whole value is contingent on an Alpaca/Benzinga historical-depth fact nobody has confirmed**, and the fallback ("forward accrual becomes the panel's main value", spec 1.1) is a multi-year clock, not a near-term payoff.

### F10 — No automated test guards any ingest/new-senses code  **(c) gap · LOW-MED**
- 214 test files; none match archive/altdata/positioning/news-panel/calendar/event-state/analyst/cloud_state. The paper core is well-tested (`test_btc_shadow_t276`, `test_paper_cloud_t186`, `test_paper_day_orders_t238`). The data spine feeding the new senses has no regression net; the spec's verification is manual/director-driven. For a system whose stated identity is trustworthy measurement, the sensory intake is the least-guarded surface.

---

## What is genuinely good (one line each)
- Fail-closed rigor in the paper trading path is real and disciplined (`run_paper_cloud_day.py:193-226`, non-zero exits + non-canonical alarm).
- `btc_shadow.py` is a clean, honest, fail-closed report-only template — the right thing to generalize for the LLM shadow book.
- N-accounting and pre-registration discipline (spec "N-accounting", "Honest risks") are exemplary; the science risks are named, not hidden.
- The two "stale closures" the spec re-opened (news PIT corpus exists; prediction-market fetchers were merely unscheduled) are **verified true** — the corpus and the working idempotent fetchers both exist on disk.

---

## Classification

**(a) Confirmed defects / doc-vs-code facts (with failure scenario):**
- **F1** archivers cannot fail loudly (silent capture-gap on API drift/zero rows) — HIGH.
- **F2** single-account monolithic pulse; "per-account pattern" absent — HIGH for Stage-2/T-288.
- **F7** "detector registry" is hardcoded wiring, not a registry — LOW-MED.
- **F8** FOMC probe hardcodes a foreign-worktree path; existing list unverified vs Fed site — LOW-MED.
- **F9** `fetch_history_alpaca` reads neither symbols nor content; corpus is single-month — LOW (scoping).

**(b) Design risks (plausible, not yet demonstrated):**
- **F3** CloudState is fixed-small-file sync, not an archive layer — MED-HIGH.
- **F4** Phase-A/B snapshot-time mismatch changes the series — MED.
- **F5** authority ladder is policy-in-a-doc until firewall/governor are built — MED.
- **F6** injection: schema-gaming + cost-amplification caught only by unbuilt firewall/governor (blast radius well-contained by design) — MED.

**(c) Questions the repo cannot answer (themselves findings):**
- **F10** no test coverage on any ingest/new-senses code; verification is manual ritual.
- **F1/F9 corollary:** whether Alpaca/Benzinga history is deep and survivorship-clean is unknown and unknowable from the repo — the entire Lane-1 payoff hinges on a probe that hasn't run.
- Whether the launchd archiver actually ran unattended (vs. the 2026-07-07 14:47 manual kickstart) cannot be confirmed until multiple unattended days accrue — and, per F1, a failed unattended day would not announce itself.

---

## The single highest-leverage fix
Make the two archivers **fail closed**: `main()` should return non-zero if any required source returned zero rows or raised, and the launchd wrapper should surface that beyond an unwatched log (reuse the paper loop's CloudWatch `PaperRunHappened`-style heartbeat, or at minimum an SNS on the failure token). Until then, `CURRENT_STATE.md`'s "the FINRA shallow-at-source data loss is STOPPED" should read "…is being captured, but the capture is not yet self-verifying." One is a guarantee; the other is what actually shipped.
