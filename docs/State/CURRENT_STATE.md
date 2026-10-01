# CURRENT_STATE — ArchonDEX

**Last reconciled with source docs:** 2026-09-30 (the alpha-frontier review rulings; prior content: the director's 09-17 reconcile `1efea7f`; FORM: restructured to one page by Agent R the same day under director ruling 6. The full narrative history — every prior reconcile block back to 2026-06 and the retired anchor/verdict tables — is preserved VERBATIM in `docs/Archive/state_history/CURRENT_STATE_full_history_to_2026_09_17.md`. This file says what is true NOW; `forward_plan.md` says why and where next; `TASK_LEDGER.md` carries the rows; `docs/Measurements/2026-09/` the point-in-time records.)

## Now (as of 2026-09-30)

- **THE ALPHA-FRONTIER REVIEW (outside, 2026-09-30, branch merged):** two referee defects verified on main by the director — the backtester sizes from a frozen capital figure (N-1) and production Discovery overwrites the gauntlet verdict with Gate 4 forced-false (N-2). Every equity-book verdict demotes to UNTESTED (below). Dispatched: RR-1/2/3/7 in parallel (propose-only; the user rules on each merge), B-1 prereg-first. Honest prior ~25% that one satellite clears the wealth bar within 12 months. `docs/Sources/alpha_frontier_program_2026_09_30.md`.

- **Fleet (3 paper accounts, AWS Batch, daily):** acct-1 `:35` trend sleeve (SPY/AGG/GLD {42,105,210}, gate-d accruing, 40 days) · acct-2 `:19` **deploy candidate — ACT 2 LIVE**: the ARRIVAL EVENT fired and HELD 09-15 (12 VOO / 5 MTUM / 1 SGOV, $9,978.42 of the $10k tier, 3 buys no sells, canonical; Rule-B contributions grow the cap ~$583/mo from Oct-11) · acct-3 `:7` ai_trader (price_fed cohort accruing). Deploys are SURGICAL per account (`scripts/redeploy_one_account.py`, revision-pinned, schedule↔jobdef pairing guard). Fleet-mirror slices built; the serving endpoint is at the USER'S gate.
- **Act 1 (T-327 drill week, 09-03→09-10) CLOSED 6/6:** seven defects surfaced that no suite had caught; drills 2, 7, 9–17 carry forward; **drill 12 is BLOCKED, not latent** (see wash guard).
- **The wash guard is SINGLE-ACCOUNT (T-358, from the 09-17 fresh-eyes audit):** the lot ledger roots at each container's own prefix; account-1 has NO lot file; the "coupled to account-1" claim on three surfaces was intent, not in force — corrected; two tests that locked the claim reframed. Approved phased build: a refusal-incapable RECORDER on account-1 first, sibling read-only pulls + the liveness check ("has a non-acct-2 lot EVER appeared?") second.
- **⏳ THE 61-DAY WINDOW STARTS AT THE RECORDER'S FIRST ARTIFACT, NOT BEFORE (T-359).** Account-1 has never written a lot event, so its wash history begins the day `paper_state/data/state/tax_lots.jsonl` first appears from a scheduled firing — and the window then needs 61 days of *fills* before a cross-account refusal is even possible. **Until then, the absence of a cross-account refusal is NOT evidence that the coupling is working, and NOT evidence that it is broken.** It is evidence of nothing at all. This line exists because T-358 was exactly the inverse mistake — a confident cause offered for an absence whose real cause was an unfed channel — and the reverse error (reading a quiet guard as a working one) is now the available one.
- **Measurement layer is two-armed at last:** the agentic shadow book's first day is 09-17 (the retired ANALYST_DESK phantom had masked a one-armed A/B for 36 sessions). The A/B REFUSES to pool across an information boundary (cohort registry `config/information_cohorts.json`: price_blind ≤09-10, price_fed from 09-11 with a `treatment_caveat`; live-price cohort building). Deploy-candidate tracker was ephemeral until 09-17: 09-15/16 points are reconstructible-with-labeling, never blended (T-351).
- **Phase 6 rung 0:** janitor SCHEDULE-VERIFIED on a dedicated runner worktree, forensics + env instrumented, authority ledger survives via extension-only S3 sync; the DIRECTOR PASS exists (prepare-only enforced in code, observe-only by mode, approvals queue in `ops/approvals/`) — **first scheduled firing 07:00 09-18**.
- **Program checkpoint (pre-stated ~Sept 20):** the bar "structural stack live and accruing" was met 09-15; the independent review is assigned to Agent R (`docs/Measurements/2026-09/program_checkpoint_review_2026_09_20.md`).

## Validated (max 5) — settled verdicts the machine is built on

- **The trend sleeve is a REGIME OPTION, not a default** (T-311 64yr: shallower in 9/9 crises, Sortino CI-significant; wealth REVERSED at depth, buy-hold 2.9×; T-333: timing significantly value-destroying net of cash, −5.16pp/yr, CI excludes 0). Demoted to regime-shelf record; decision memo at gate-d maturity.
- **Ensemble speeds {42,105,210} SETTLED** (T-260: ΔSortino CI-significant on both deep windows).
- **Long-only MOMENTUM is the only CI-significant tilt** (T-320; the decayed variant straddles) → deployed as the 15% MTUM satellite. Growth/tech REFUTED; small-value real-but-decayed (T-318).
- **1× buy-hold SPY in the Roth is the wealth-maximizing default** under any forward-ERP haircut (T-315); Rule-B always-invest adopted, sub-1% effect (T-299).
- **Engine E `hmm_p_crisis` is predictive (AUC 0.887)** — but production loads the legacy HMM and the panel is blind pre-2020 (12 tickers never deep-backfilled; `health_check.md` HIGH; owner B per the 09-17 rulings).

## Recently refuted / superseded (max 5, rolling)

- **Static leverage** (T-315): no arm CI-beats at any L; 1.25× significantly LOSES; −2% ERP haircut kills all.
- **Gated leverage at depth** (T-312): paired Δwealth straddles on ~10 crises; the one "significant" window was 1929 alone.
- **Bounded adaptation #1, vol-stress** (T-314): in-sample +0.143 Sortino → OOS +0.051, straddling; the frozen spec is the ceiling.
- **Equity-book verdicts — DEMOTED to UNTESTED (2026-09-30; SCOPE CORRECTED same day by C's code-level read, superseding the director's first wording which was wrong in both directions):** every verdict whose NUMBER `BacktestController` produced ran under the frozen-capital sizing defect (RR-1). The authority for the scope is the verdict list in the RR-1 proposal (`docs/Sources/referee_repair_proposal_RR-1_2026_09_30.md` §5, branch `fix/referee-rr1-sizing-capital`): **29 verdicts by production** — spanning **T-041b → T-211, the 0.751 anchor included**, nearly all BEFORE T-255 — **plus 2 by CONSUMPTION** (T-170, T-206: their own scripts never call the controller but blend or decompose a controller curve); 7 more await the reviewer's classification rather than a guess. **T-239 is RESTORED** — it reads raw prices and the trend overlay, no controller output; demoting it discarded a valid verdict. T-196 additionally carries RR-2 (Gate 4 forced-false) and RR-3 (cloud N=1). **Live consequence, T-170:** the BACKTEST RATIONALE for arming the DBMF forward shadow (T-316) rested on a controller curve and is UNTESTED; the shadow's forward gates are live measurements and STAND. The T-306-substrate verdicts (sleeve, tilts, leverage, offense, regime) SURVIVE — confirmed at code level AND by the consumption test: they read no equity-book curve. The RE-SCORE's sign is genuinely open (on the golden fixture, removing the free leverage IMPROVED 2021 Sharpe; the defect over-sized 241 bars and UNDER-sized 10).
- **Anonymized-historical eval for news text** (T-339/b): VOID ×2 (identity lives in what a company does); the forward record cannot be shortcut.

## In flight (max 5)

- Deploy-candidate record accrual — 60-day gate → first evaluable read ~mid-Nov; the single most decision-relevant stream.
- Wash-guard recorder on account-1 (E; phase 1 approved) → sibling pulls + liveness check (phase 2).
- Post-audit structure work: `main()` extraction into an ordered step registry with ONE strategy pipeline + the five text-assertion wiring tests converted to execution tests (E, C rider; branch) — sequenced BEFORE the collar/pre-trade gate and journal checkpoint (director YES, pending the user's word).
- CEF forward shadow book on the T-334 daily panel (C, after Friday; report-only, 0 N, falsifiers pre-stated) — the only t_HAC>2 alpha ever found, parked on backtest history a forward book does not need.
- Referee repairs (B, after the director pass's first artifact): HMM backfill repoint; legacy-HMM production load.

## Next decision (exactly 1)

- **USER:** the word on fresh-eyes audit items 2–3 — a marketable-limit collar + pre-trade gate in `OrderManager` (notional ≤ cap, sell ≤ held on long-only, orders/day ≤ K) and the order-journal checkpoint to S3 after submit/fill with an adopt-with-reason tool. Engine B / live path; director YES; flag-gated; each refusal proven by a forced drill; lands after the `main()` extraction.

## Standing constraints (max 5)

- **Real money: NO date.** An evidence-triggered OPTION the user takes only on confidence; the weekly digest is the assessment surface; nothing in the system implies a deployment date.
- **Data budget: free-only** (user ruling); a blocked frozen prereg is the trigger to re-ask with a concrete case.
- **Honest N_trials ~260+ effective;** MBL rises with N; every measurement pre-registered (`[NN-MBL]`); `ci_low`, never point (`[NN-SHARPE-CI]`).
- **Canonical substrate = the multi-decade build (T-306);** every 2000-2026 verdict is re-verify-required per `[NN-SUBSTRATE-REVERIFY]`.
- **Wrapper facts (any Roth IRA; broker undecided — 'Alpaca IRA' is the 2026-09-30 review's assumption):** no margin ⇒ no shorts, no futures; crypto only via spot ETF (IBIT-class); options conservatively Level 2 (covered calls / cash-secured puts / long options). This retires half the alpha map before evidence matters — routes needing shorts, futures, or premium-selling structures do not dispatch.
- **Live-path / Engine B / new external services / referee changes are propose-first;** the referee (measurement stack, gates, firewalls) is never autonomously modifiable (`autonomous_development_prestatement.md`).

## Open (known, owned or dated)

- Janitor suite-FAIL 09-11/12/13 UNDIAGNOSED (environmental; disk/load now instrumented; host disk was 1.8 GB free before the 09-17 restart) · host disk balloon (repeat 100%-full episodes) · btc-sleeve silent-stop alarm stuck in ALARM since Jul-11 (unretired leftover) · drills 2/7/9–17 · brain-book clock starts ~10-13/15 (rung-1 scoring ≥ ~2027-01-12) · dashboard_v2 redesign banked UNREVIEWED on `feature/dashboard-v2-redesign-2026-09` awaiting the user's verdict.

---

*Hard caps per section are the anti-rot discipline. When a slot fills, the oldest item moves to the archive file above or to `MEMORY.md`. Keep this file to one page; put narrative in the ledger row, the session summary, or the measurement doc it belongs to.*
