# Fresh-Eyes Program Audit — 2026-09-17

> **Who:** an independent reviewer session (not the director, not agents A–E), cold-started on
> the prescribed reading path, with four read-only sub-audits (architecture, code health,
> live-path risk, operating process). Every load-bearing claim below was verified against code
> or command output at HEAD `41f80ad`. Nothing in the repo was modified except this file, the
> session summary, and one consolidated `health_check.md` entry.
>
> **Why:** the user asked for a review of the machine and of the director's work, the gaps and
> inefficiencies, and a proposal for how an independent reviewer fits into the director + A–E
> setup. The plan of record (`~/.claude/plans/foamy-foraging-horizon.md`, Phase 5) already
> calls for alternating DEFECT / OPPORTUNITY rounds by agents "briefed with the goal but NOT our
> roadmap". This is DEFECT round 1. The Sept-20 program checkpoint it pre-stated is 3 days away
> and has no owner, no review doc, and no dispatch.

---

## 0. Where the machine actually stands (one honest paragraph)

Three Alpaca paper accounts fire daily on AWS Batch: account-1 the 3-asset trend sleeve
(40 days of record), account-2 the deploy candidate VOO 85 / MTUM 15 / SGOV cash (arrived
2026-09-15, 2 days of record, and its tracker lost both days to an undurable path — T-351),
account-3 the LLM agentic trader. Ten shadow "books" run alongside. **All ten streams are inside
the 60-day minimum; nothing is decidable** (`docs/State/performance_digest.md`, 2026-09-16). The
in-house alpha hunt closed H0 in June after ~2 years of pre-registered tests; the sleeve's timing
was priced as value-destroying for terminal wealth (T-333); static and gated leverage closed with
numbers (T-312/T-315). What is deployed as "offense" is a low-cost index core plus the one
CI-significant tilt (long-only momentum) plus a cash leg that earns the bill rate — i.e. the
structural stack the plan estimates at +225–430 bps/yr over the user's robo. The user's "isn't
really outperforming" is accurate and, at this point, by construction: the machine is a
first-rate measurement laboratory wrapped around an allocation that a good robo also holds.
The offense that remains is (a) making the structural stack actually accrue a clean record,
(b) the forward-only faculties (AI desks, portfolio brain) earning authority by record, and
(c) capacity-constrained niches institutions cannot occupy — of which the program has found
exactly one real signal (CEF discount capture, t_HAC 2.31, T-267) and parked it.

---

## 1. Findings — ranked by what they cost

### A. Safety: things that would block real money today (verified)

| # | Finding | Evidence | Severity |
|---|---|---|---|
| A1 | **The "cross-account" wash guard is one-account.** `tax_lots.jsonl` lives under each account's OWN S3 prefix (`cloud_state.py:158` in `DURABLE_PATHS`; prefix per `ARCHONDEX_PAPER_STATE_PREFIX`). The only writer is `order_manager.py:543`, executed only when a guard is attached; account-1 runs with `wash_guard=None` (`run_paper_cloud_day.py:74` allow-list = `{"deploy_candidate"}`), so **no account-1 fill has ever entered any lot ledger**, and account-2's container never pulls another prefix's lots (the only `pull_readonly_from` use is notes, `:695`). The driver comment at `:419-425` ("reads every account's lots… a VOO buy CAN be refused because of an account-1 SPY loss") and the digest's "⚠ Coupled" banner are **false in code**. This is the T-342 channel-liveness class ("has the consumed field EVER been non-empty?") and silent-wrongness #8: a control on the record that has no feed. | `scripts/run_paper_cloud_day.py:418-452`, `paper_trader/cloud_state.py:158`, `paper_trader/order_manager.py:539-546` | **CRITICAL** (for the record's honesty now; for money later) |
| A2 | **No price collar.** Orders are `MarketOrderRequest` (`paper_client.py:206-217`). `PRICE_DRIFT` exists in reconciliation but is never evaluated on the cloud path: `inputs_fn` passes no `expected_prices`, `window_closed=False` (`run_paper_cloud_day.py:493-509`, `reconciliation.py:149,172-184`). A fill at a wildly wrong price is accepted. | as cited | CRITICAL for real money |
| A3 | **Journal durable only at container exit.** S3 push happens once at `:1315`; no `try/finally`. A Fargate timeout/OOM after a fill loses the journal → next run sees an unexplained position → position-drift HALT daily, and there is no operator adopt-with-reason tool. | `run_paper_cloud_day.py:1315-1322` | HIGH |
| A4 | **Cash-drift detection is dead while holding**: held-reconcile adopts cash every run when positions are explained. | `held_reconcile.py:99-101`, `scheduler.py:258-261` | HIGH |
| A5 | **No pre-trade gate at submit.** Notional cap, no-short, per-name cap are constructor-level only; `OrderManager` submits any qty handed to it. Account-3's note schema allows `target_weight ∈ [−0.20, +0.20]` so a short is constructible. | `llm_analyst_constructor.py:241-247`, `note_schema.py:90` | HIGH |
| A6 | **Calendar fallback is 2026-only and there is no broker clock**; a calendar-API outage on a 2027 holiday submits resting DAY orders that fill next open on a stale signal. | `market_calendar.py:35-40,65` | MEDIUM |
| A7 | **No fleet-wide halt object**: the halt file is per-prefix, so stopping the fleet is three writes. | `cloud_state.py` halt comment | MEDIUM |
| A8 | Stale-bar threshold is 5 calendar days; a 4-day-old bar trades. | `run_paper_cloud_day.py:160-164` | LOW |

What is genuinely good on this path and should be kept verbatim: paper-endpoint pinning
(`paper_client.py:181-196`), client-order-id idempotency with journal-before-POST and
restart-adopts-broker-truth (`order_manager.py:161-183, 380-425`), the per-submit kill-switch
check ahead of the wash guard (`order_manager.py:366-385`), Secrets-Manager binding with no echo,
and the arm interlock (`scheduler.py:167-206`).

### B. Structure: the architecture no longer describes the product

| # | Finding | Evidence |
|---|---|---|
| B1 | **The production runner's `main()` is 1,157 lines** (`run_paper_cloud_day.py:304-1460`), thirteen `# --- T-xxx` blocks appended in place, 13 `args.strategy ==` branches. The 09-14 `sleeve_cap` NameError that fail-closed account-2 lived here. It is the highest-blast-radius function in the repo and it lives in `scripts/`, not a package. | code-health + architect |
| B2 | **The deployed strategy bypasses the shared pipeline.** `_run_family_strategy` (`:140`) serves four constructors; account-1's `trend_sleeve` is inline at `:527-595` ("stays inline + untouched"). The one path carrying real forward-record accrual is the unrefactored one. | architect |
| B3 | **Five hand-copied constructors** re-implement target-weight → floor(equity·w/px) → delta → `OrderSpec` (`sleeve:101-115`, `offense:99-124`, `btc:86-100`, `deploy:199-265`, `llm:247-256`); `llm` uses `int()` where the others use `floor`, so they diverge on negatives. No shared primitive in `order_construction.py`. | architect |
| B4 | **The governance surface points at the wrong layer.** Production reaches 79 files / 21,301 lines; only 1,133 of those are in `engines/` (2%). `engine_charters.md`, `PROJECT_CONTEXT.md`, `docs/README.md`, all 7 engine `index.md` files and `[NN-ENGINE-BOUNDARIES]` contain **zero occurrences of `paper_trader`**. There is no charter for the live product: nothing states who may emit an `OrderSpec`, who may write `DURABLE_PATHS`, or where constructor / order-manager / heartbeat authority sits. | `grep -c paper_trader docs/Core/*.md engines/*/index.md` |
| B5 | **Production imports T-numbered research scripts** (`build_news_panel_t289.py` at `:1374`, `archive_altdata_t136.py`, `similarity_t237.py`); anyone archiving "one-offs" breaks the news clock. `scripts/` has 252 files, 146 T-named, 70 referenced by nothing. | architect |
| B6 | **The paper image bakes gitignored local data** (`build_paper_image.sh:38,58` copies `data/universe/sp500_membership_pit.parquet` and `data/processed/tr_reconciled` from one Mac's disk). Image contents depend on un-versioned state. | architect |
| B7 | **43 text-assertion tests in 21 files** read source as a string (`inspect.getsource`, `.read_text()`), including five that "lock" `run_paper_cloud_day.py` wiring and one written two days AFTER the 09-14 lesson that text assertions cannot catch an undefined name (`test_ledger_backup_2026_09_16.py:76`). | code-health |
| B8 | **Silent-default excepts on the live path** return plausible emptiness with no degraded flag: `intel_pulse.py:120,142,189`, `sleeve_tracker.py:102` (corrupt file → `[]` → NAV history silently resets), `market_calendar.py:65`, `heartbeat.py:363,373`, `scheduler.py:374`, `paper_config.py:39`; and on the measurement path `combined_candidate_scorecard.py:327` (unreadable tax config → default rates → a plausible after-tax number, an `[NN-FAIL-CLOSED]` violation). | code-health |
| B9 | Three placeholder tests (`assert True`) claim coverage of `alpha_engine`, `portfolio`, `backtest_controller`; `test_news_edge.py` has zero asserts. | code-health |

### C. Process: the director loop produces narrative faster than state

| # | Finding | Evidence |
|---|---|---|
| C1 | **`CURRENT_STATE.md` is 52 days stale** (last reconciled 2026-07-27); it does not know about the drill week, Act 2, the arrival event, Phase 6, or the fleet revisions. The Stop hook has warned about this at every session end for ~45 days; it is advisory by design and has been ignored every time. | `git log -1 -- docs/State/CURRENT_STATE.md` |
| C2 | **12 September task IDs never reached `TASK_LEDGER.md`** (T-344/346/348–356; last row T-327 "dispatched"). `docs/Sessions/2026-09/` does not exist despite 119 commits since the last summary (08-27). `ROADMAP.md` last touched 06-19; `capability_ledger.md` 07-02. The only reliably current surface is machine-written (`data/state/janitor_report.md`) — and `docs/State/janitor_report.md` is a dead 09-02 copy of it showing a suite FAIL that no longer exists. | process audit |
| C3 | **Session-start costs ~46k tokens** before the first prompt (CLAUDE.md 5.5k + CURRENT_STATE 10.7k, paid TWICE because the hook re-cats it + SESSION_PROCEDURES 5.8k + hook stdout 15k + MEMORY.md 4.3k). CURRENT_STATE's line 3 is a single 40KB paragraph of nested "Prior, …" history. | chars/4 |
| C4 | **Worker inboxes are 80–145KB append-forever files** with June dispatches at the tail; outboxes are inconsistent (A/C/D overwrite; B = 250KB / 1,993 lines). No status field, no machine-readable open-item count. Every worker cold-start pays this. | `ls -la data/coordination/` |
| C5 | **~10k lines of dashboard_v2 work exist only in the working tree** (25 modified + 27 untracked files, all mtime 09-10; last `dashboard_v2/` commit 06-17; "awaiting the user verdict" since 07-07). Imports and 39 sampled tests pass. One `git checkout` from loss; violates the repo's own commit-early rule. | `git status`, `git log -- cockpit/dashboard_v2` |
| C6 | **Commit messages are 300–600-word essays**; `git log --oneline` is unusable for scanning, and the record the process trusts most lives in the field least designed to hold it. | `git log -5` |
| C7 | **Phase 6 has produced no autonomous change in 15 nights.** 21 ledger rows: 19 `checks_only`, fix phase `DISABLED`, zero `merged: true`. The first two approvals (`ops/approvals/`) reached main only during this audit (the director merged `feature/director-pass` at `41f80ad` while this was being written; two hours earlier they existed on an unmerged branch only). The ledger backup reported "19 rows current" while local had 21. Rung 0 is prepare-only by design, so "no autonomous change" is the contract, not a defect — the observation is that the rung's first real artifact (a human-answered approval) is still pending. | `data/state/autonomy_ledger.jsonl`, `ops/approvals/` |
| C8 | **Branch and worktree hygiene**: 23 `feature/*` branches carry unmerged commits (21 June-era orphans; the 07-28 lesson says stranded fixes are a recurring class); C's and D's worktrees are 19 and 10 commits behind main; a `feature/launchd-hygiene` stash sits on no worktree. | `git branch --no-merged main` |
| C9 | **The root volume had 1.8 GB free** (87% used) before today's restart, 9.8 GB after. The janitor's "suite FAIL 3 of 4 nights, environmental" mystery (`disk_free_gb` 9.9 → 4.9 across the week) is consistent with disk pressure; `data/` is 8.8 GB, none of it on any quota. | `df -h /`, ledger `env` rows |
| C10 | **Open HIGH items in `health_check.md` since June–August have no owner**: Engine E production loads the legacy HMM; the HMM is blind pre-2020 because 12 tickers (incl. GLD/TLT/IEF/QQQ/IWM/DBC) were never deep-backfilled in `data/processed/` while `tr_reconciled/` versions exist; Engine F producers dead on the prod path. These are the "referee" the constitution says must be trustworthy. | `health_check.md:25-70,105-128` |

### D. Things I looked for and did NOT find (honest negatives)

- No secrets in git history or logs; `.dockerignore` and Secrets Manager binding are correct.
- No `cockpit/dashboard/` references — that ban has held.
- No TODO/FIXME on the live path.
- `doc_lint.py` passes (it lints anchors and link shape, not freshness — which is why C1/C2 pass green).
- The default test tier: see the session summary for the run result at HEAD.

---

## 2. The strategic gap: what "top 1% retail" would actually require here

The program's own evidence says the market is close to efficient to this operator on price
inputs. I agree with that read and would not re-open it. Top-1% retail is not "a signal that
beats SPY by 5%/yr"; by the retail-trading evidence base it is: never blow up, near-zero cost,
tax-optimal, contribution-maximal, a small number of evidenced tilts, and — for the few who have
one — a capacity-constrained niche institutional money cannot occupy. The plan of record has
converged on exactly that, honestly. Where it is still short:

1. **The structural stack has no clean record yet.** It is the only near-term number that
   matters (the plan's +225–430 bps/yr), it went live two days ago, and both days' tracker points
   were lost (T-351). Priority zero is a clean, durable, liveness-checked record of the deploy
   candidate — not more books.
2. **The one real alpha is parked when it could be forward-tested today.** T-267 (CEF discount
   capture, t_HAC 2.31) was parked for lack of a PIT NAV history to *backtest*. A *forward*
   shadow book needs no history: the T-334 archive already captures 361 funds × 30 fields daily
   since 07-29. A report-only CEF discount book (z-score entry on the daily panel, 25 bps/side,
   SPY twin) costs 0 N_trials, is orthogonal to the exhausted price vocabulary, and is the
   cheapest genuinely-new stream the program can start. It is also the one niche on the list a
   $10–50k Roth can actually occupy and a $10bn fund cannot.
3. **The record's honesty has a hole (A1).** A machine whose selling point is "it will say so
   with receipts" cannot carry a control on the record that has no feed. This is more important
   than any new stream.
4. **The referee is not maintained.** HMM blind pre-2020, legacy HMM in prod, dead Engine-F
   producers, silent-default excepts on the live path, text-assertion locks — all open, all
   unowned. The constitution says the referee is never autonomously modifiable; it does not say
   nobody owns it.
5. **The program is spending its scarce resource (director context and user attention) on
   narrative.** 46k tokens per session start, 145KB inboxes, essay commits, a dashboard the user
   was asked to judge in July that nobody has committed. Every one of these is a fixed tax on
   every future unit of work.

---

## 3. Proposal: how an independent reviewer fits in

**Role:** the *referee-side* reviewer — not a sixth worker inside the dispatch loop, not a
second director. The constitution (`autonomous_development_prestatement.md`) says the thing
being measured must never control the measurement; today the director both dispatches the work
and grades it. The reviewer sits on the other side of that line: read-only by default, writes
findings in a fixed format, never dispatches A–E (one director), and fixes only what the director
explicitly hands over.

**Standing duties**

| duty | cadence | first instance |
|---|---|---|
| Write the pre-stated program checkpoint review (the Sept-20 sentence test: "structural stack live and accruing, or research instrument mistaken for an investment system") | per checkpoint | **Sept 20 — 3 days away, unowned** |
| DEFECT round (this document is round 1): fresh-eyes + adversarial pass on the live path, the referee, and the record | ~6–8 weeks, alternating | done |
| OPPORTUNITY round: "what lever toward the goal has this program not thought of?", briefed on goal + constraints, not the roadmap | ~6–8 weeks, alternating | ~Oct (the plan's own date) |
| Merge audit: sample the week's merges against their stated gate (first artifact observed? census clean? claim vs. feed?) | weekly | next week |
| Current-truth check that is not advisory: CURRENT_STATE / TASK_LEDGER / Sessions coverage vs. the week's commits, reported as a number | weekly | this doc, §1.C |

**What I did in this session (autonomous, reversible):** this audit; the first
`docs/Sessions/2026-09/` summary; one consolidated `health_check.md` entry pointing here (no
new tracker doc, per the 06-19 doc-system audit's anti-proliferation rule); a memory note.

**What needs the user's or director's word before anyone touches it** (Engine B / live path /
production account per CLAUDE.md), in the order I would take it:

1. **A1** — decide: feed account-1 (and -3) fills into ONE shared lot ledger with a liveness
   check ("has a non-account-2 lot EVER appeared?"), or correct the record and the digest banner
   to say the guard is single-account. Either is honest; the current state is neither.
2. **A2 + A5** — marketable-limit orders (arrival ± X bps) and a pre-trade gate in
   `OrderManager` (notional ≤ cap, sell ≤ held on long-only accounts, orders/day ≤ K), flag-gated,
   proven by a drill that forces each refusal and observes the journal line.
3. **A3** — checkpoint `orders.jsonl` to S3 after the "submitting" record and after each fill;
   an operator adopt-with-reason tool.
4. **B1/B2** — extract `main()` into an ordered step registry with ONE strategy pipeline
   (fold `trend_sleeve` into `_run_family_strategy`), converting the five text-assertion wiring
   tests into execution tests proven by reversion. This is the change that makes every later
   live-path fix safe.
5. **C5** — commit the dashboard work to a branch today (nothing is lost; the verdict can wait).
6. **C1–C4** — a mechanical reconciliation pass: CURRENT_STATE rewritten as a ≤1-page dashboard
   with history moved to `docs/Archive/`, the 12 missing ledger rows, inbox rotation (archive
   closed dispatches; keep open items ≤ 1 screen), the hook made to stop re-catting CURRENT_STATE.
7. **The CEF forward book** (§2.2) — a report-only stream on the existing T-334 panel; 0 N.
8. **C10 referee items** — the HMM backfill repoint (one-line, already diagnosed) and the
   legacy-HMM prod load, reviewed as their own units because they shift every regime reading.

**Boundary I hold:** I do not merge to main, deploy to an account, or edit engine B / live-path
code without the explicit word. When a finding turns out to be wrong I say so in the record
that carried it, not in a new doc.
