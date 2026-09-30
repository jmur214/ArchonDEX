# 01 — Gap report (Phase 1, 2026-09-30)

> Alpha-frontier review, branch `research/alpha-frontier-2026-09-30`. Stance toward the
> Sept-30 prior pass was adversarial: each seeded claim was attacked with code, the
> ledger, the audit dir, and `git log --all` (234 remote heads fetched; the local clone
> was shallow at 2026-08-28). **Of nine seeded claims: 4 confirmed as stated, 4 confirmed
> but materially narrowed, 1 mostly refuted.** Fourteen defects the prior pass did not
> list were found; eight have failing tests. Limits of this pass: `data/` is absent in
> the container, the AWS credentials are placeholders (S3 unreadable), and the egress
> proxy blocks every market-data and paper host (web search works; page fetch does not).
> Nothing here was measured on real returns; every number comes from the referee's own
> code on synthetic or calibrated inputs, and says so.
>
> **Flag for the operator (referee repairs, propose-only):** two defects change what
> every historical Discovery verdict means — the production orchestrator overwrites the
> gauntlet verdict (§2 N-2) and the backtester sizes from a frozen capital figure
> (§2 N-1). Neither was known. Both are in the measurement path. Both are in
> `tests/test_referee_repairs_proposed.py` as `xfail(strict=True)`.

## 1. Apparatus defects — the nine seeded claims, scored

Probe scripts: `scripts/probe_gate4_permutation_null.py`, `probe_engine_f_retirement_burden.py`
(output in this dir), `probe_mbl_n_effective.py`, `probe_spy_ci_low_kill_threshold.py`.
Tests: `tests/test_referee_repairs_proposed.py` (16 xfail).

### 1A.1 Gate 4 permutation null — CONFIRMED as a defect; its historical consequence OVERSTATED
- **Code:** `engines/engine_d_discovery/significance.py:84` `shuffled = rng.permutation(returns)`;
  `:93` `p_value = (null_sharpes >= actual_sharpe).mean()`. A permutation leaves mean and
  std invariant; the null is a point mass at the actual Sharpe.
- **Probe:** null_std 9e-17…2e-15 on four series; p = 0.229 (SR 0), 0.554 (SR 0.5),
  0.629 (SR 1.6), **0.973 (SR 5.2)**. A signal-permutation null on the same series gives
  p = 0.51 / 0.67 / 0.23 / **0.00**; sign-flip null agrees. Gate 4 has zero power in
  either direction.
- **Mandatory:** `discovery.py:1795-1803` conjunctive `and sig_passed`. Unit test
  `tests/test_significance.py:211-214` says p "will be near 0.5"; every integration test
  monkeypatches Gate 4 to p=0.001, so the real null is never exercised.
- **The project already looked at this and misdiagnosed it.** `docs/Measurements/2026-05/gates_2_to_6_audit_2026_05.md:208-210`
  (May 2026) rated Gate 4 "SUSPECT" for *geometry* while stating the mechanics are
  "mathematically correct: it… tests whether the temporal ordering matters for the
  Sharpe ratio." The Sharpe ratio is order-invariant. That sentence is the bug.
- **Narrowing (the prior pass's consequence is wrong):** "Discovery has never promoted
  because of Gate 4" does not hold. Every recorded candidate — 93/93 across all
  diagnostic JSONLs, T-193, T-196 — died at **Gate 1** (`docs/Measurements/2026-05/discovery_diagnostic_2026_05.md:24-49`,
  `docs/Audit/phase0b_local_discover_t193_2026_06_17.md:43-64`). Gate 4 is a latent wall
  behind Gate 1, never the killer. Two T-196 features that cleared Gates 1–2 were then
  killed by a *forced* Gate 4 fail (§2 N-2), mislabeled "gate_3".
- **Correct null (proposal):** permute the signal against returns (destroys alignment,
  preserves both marginals), or a stationary-block sign-flip around zero mean; report
  both. The BH-FDR step at `mode_controller.py:1390` then has something to correct.
- **Historical verdicts touched:** none directly (nothing reached Gate 4). Every future
  Discovery run, and the two T-196 Gate-1/2 survivors (`triple_witching`, `january`
  — both calendar features with no mechanism; low prior even under a working Gate 4).

### 1A.2 Engine F retirement burden — CONFIRMED, and worse than stated
- **Code:** `lifecycle_manager.py:742-745` retire unless `ci_low ≥ benchmark_sharpe − 0.3`;
  `:267-275` per-trade **dollar** PnL, `mean/std·√252` "assuming daily trade frequency";
  `:62-82` bootstrap on the same array; `retirement_min_trades=100`. Benchmark = SPY
  daily-return Sharpe (`governor.py:626-637`, `core/benchmark.py:233-235`) from the
  dividend-reconciled file (`benchmark.py:100-104`) while edge PnL is split-only
  (`data_manager.py:756`). Standalone: no correlation or contribution term (`:705-756`).
- **Probe (production helpers, 30 sims/cell, benchmark 0.8 → threshold 0.5):**

  | true SR | trades/yr | N trades | years | code point | code ci_low | **retire rate** |
  |---|---|---|---|---|---|---|
  | 0.3 | 50 | 1000 | 20 | 0.62 | −0.34 | 0.40 |
  | 0.6 | 50 | 1000 | 20 | 1.43 | +0.48 | 0.20 |
  | 0.6 | 252 | 250 | 1 | 0.62 | −1.30 | 0.50 |
  | 0.6 | 252 | 1000 | 4 | 0.56 | −0.41 | 0.33 |

  Arithmetic: a daily-frequency edge with true SR 0.6 needs ≈ 96,000 trades (≈ 380
  years) for `ci_low` to clear 0.5; true SR 1.0 needs ≈ 3,900 (15 yr); true SR 1.5
  needs ≈ 970 (4 yr). Only SR ≳ 1.5 edges survive on human timescales. The √252
  convention *inflates* the point estimate 2.2× for a 50-trade/yr edge and does not
  rescue the ci_low.
- **Additional defects (agent audit, verified):** paused→retired gates on the POINT
  estimate (`:958-960`) — two conventions in one module; promote and retire thresholds
  identical (`evolution_controller.py:191, 203`) — no hysteresis, contrary to the
  charter; a missing SPY file silently skips the whole lifecycle pass (`governor.py:662-663`);
  governor weight enters Engine B sizing twice (`alpha_engine.py:1068`, `risk_engine.py:1173,1177`);
  bare `std == 0` guard (`:272`); factor-α gate inert (no `factors=`, `governor.py:653-656`).
- **Is it live?** Yes on the backtest path with `lifecycle_enabled: true` and journal
  `None` → direct `edges.yml` mutation (`mode_controller.py:1058-1079`); measurement runs
  snapshot/restore `edges.yml` so decisions are discarded (`run_isolated.py:109-112`).
  No autonomous promotion has ever occurred; no autonomous retirement persisted.
- **Repair (proposal):** kill on `ci_high < threshold` (proven bad), keep on
  `ci_low ≥ threshold` (proven good), review band between; annualize by actual trades
  per year; benchmark on the same adjustment basis; score contribution to the book
  (Δ book Sharpe at deployed weight), not standalone.

### 1A.3 Every candidate wears production machinery — CONFIRMED, with two corrections
- ATR stop 1.8× / TP 2.5× on every entry, trailing 1.5 ATR on by default, no off-switch
  (`risk_engine.py:1389-1394`, `:61-63`; `risk_settings.prod.json:6-7`); backtester loads
  prod risk config (`mode_controller.py:534, 540`). Stop priced off the signal-bar close,
  filled next open (`risk_engine.py:901`). Allocator: Σw=1 over names that fired this bar,
  clip [0, 0.30], no renormalize, re-solved every bar (`policy.py:248, 327-330`;
  `optimizer.py:86, 118`; `backtest_controller.py:652-657`). Shorts zeroed by config
  (`portfolio_settings.json:6`). Idle cash earns 0% (`portfolio_engine.py:90, 353`; zero
  hits for interest/cash_yield in `backtester/` or `engine_c_portfolio/`; the Sept
  `cash_adj` feed is the paper tracker only).
- **Correction 1 — "30% + 70% cash" is wrong for the gauntlet book.** Held non-firing
  names persist (`backtest_controller.py:545-584`), and sizing uses a frozen capital
  figure (§2 N-1) so the book runs **1.7–2.3× gross with negative cash and free
  borrowing**. The distortion is leverage, not cash drag. For a levered book, 0% cash is
  a *subsidy* (no financing charged), not a penalty. The cash-yield penalty is real only
  where cash is positive: the sleeve harness (now fixed, T-255) and any scorecard
  comparison of a positive-cash strategy.
- **Correction 2 — the seeded question has a clean answer: NO.** Neither the 35 foundry
  features nor the Engine A edges were ever evaluated as raw signal → rank → decile →
  monthly rebalance → total-return P&L. T-195 wraps each feature as a single-gene
  long `CompositeEdge` (`top_percentile 80` or `greater 0`), adds it to the 6-edge book,
  and runs the full backtester (`scripts/run_foundry_eval_t195.py:90-107`;
  `discovery.py:1291-1320`). Decile evaluators exist only in standalone scripts
  (`smallcap_momentum_gauntlet_t249.py:49-60`, `tilt_decision_measure_t318_t320.py:229`).
  T-122 additionally showed the inverse-vol normalization **algebraically cancels any
  uniform timing signal** (Δ = 0.000), so every calendar/macro feature died at Gate 1 by
  construction. **This is the highest-value re-run in the project** (program brief B-1).

### 1A.4 Honest-N inflated — CONFIRMED on both mechanisms; the consequence REFUTED
- `core/measurement/mbl_gate.py:90` `SELECT COUNT(*) FROM runs`; `:58` `2·ln(N)/SR²`.
  Registry ingests every `performance_summary.json` (determinism reps included,
  `run_registry.py:229-244`); the ledger backfill adds synthetic rows "no PCA/correlation
  reduction" (`backfill_run_registry_t336.py:11-28`). Four inconsistent N series exist
  (75 / 76-78 / 231 / ~260 / ~295).
- **Probe:** at N=260 the `2·ln N` bound overstates E[max]² by **38.7%**; required SR on
  the 26-yr window drops 0.654 → 0.555 (exact) → 0.393 at ρ̄=0.5 → 0.259 at ρ̄=0.9
  (equicorrelated identity E[max]² · (1−ρ̄); the seeded "ρ̄ + (1−ρ̄)N" formula is not
  one I can source and is *less* generous than the exact identity). The empirical ρ̄
  requires the registry's return series (not in this container) — first deliverable of
  repair brief RR-3.
- **Not double-deflation:** requiring `ci_low·√T ≥ √(2 ln N)` has the same form as the
  DSR at 95% (`SR·√T ≥ E[max_N] + 1.645`); the stack is coherent, only the bound is loose.
- **REFUTED consequence:** none of T-251/259/279/282/284/312/318 is gated on the DSR bar;
  each is a paired-difference or log-wealth CI against zero (agent audit, verdict docs).
  **A lower N_eff flips none of them.** N_eff matters only for Discovery Gate 0/8 — which
  (§2 N-3) fail open to N=1 without the registry and receive batch size (≤10) from
  production. Closest calls that a *CI-level* change would flip: T-279 vs 60/40
  (ci_low −0.00), T-282 vs plain sleeve (ci_low +0.00), T-259 (2022 hard-gate was a
  BIL/DGS3MO basis artifact, T-266).

### 1A.5 Benchmark asymmetries — half OVERSTATED, half CONFIRMED and partly already fixed
- **"Strongest" gate:** `core/benchmark.py:416-417` `max(SPY, QQQ, 60/40) − 0.2` exists
  and is ex-post — but `gate_sharpe_vs_benchmark` has **no live callers**; Discovery
  Gate 1 replaced it (`discovery.py:1409-1411`), Engine F uses SPY−0.3. OVERSTATED.
- **Scorecard cash:** robo cash earns DGS3MO (`combined_candidate_scorecard.py:244`),
  AGG gets a DGS10 coupon (`:237-238`, a 10-yr yield on a ~6-yr-duration fund), strategy
  side is taken verbatim with 0% cash (`:430`). CONFIRMED — and already known: the
  2026-07-02 gap audit Wave 0.2 fixed the AGG leg; the strategy leg was never given the
  symmetric fix. Additional: a flat 4% rf haircut is subtracted from every row's Sharpe
  (`:378-386`) while the robo's cash earns the actual ~2% path; the deploy rule compares
  two marginal `ci_low`s, not a paired Δ (`:604`); tax-config read failure defaults
  silently (`:327`, already in the 09-17 audit). Robo proxy never anchored to Schwab
  Intelligent Portfolios' published returns (grep: nothing; `:38-39` "Neither is the real
  robo"). **Net bias in Sharpe terms:** for a positive-cash strategy, cash fraction × T-bill
  ≈ 0.65%/yr at 35% cash (the gap audit's own number) ≈ 0.04–0.06 Sharpe at 12–15% vol;
  the flat-4% haircut cuts the other way by ~(4% − 2%)/σ ≈ 0.13–0.17 against the
  *lower-vol* robo. The asymmetries partially cancel and are uncontrolled. Fix both.

### 1A.6 `ci_low < 0.4` kills SPY — CONFIRMED (analytic + calibrated; not measured on real SPY)
- Analytic 5th-percentile lower bound on 12 years at SR 0.65/0.75/0.85: 0.13/0.21/0.30
  (iid), negative under fat tails (skew −0.5, excess kurtosis 12). Project's own
  `bootstrap_distribution` on a SPY-calibrated GARCH-t(4) 12-yr series: ci_low 0.22 /
  0.29 / 0.86 / −0.04 / 0.21 across five seeds (4/5 below 0.4; point 0.62–1.37).
- Consequence: a kill rule that kills its own benchmark is a rule about sample length,
  not about edge. Repair: gate on `ci_low(Δ vs SPY) < 0` (paired, same window), which
  is what the sleeve/tilt harnesses already do (`deep_reverify_sleeve_t311.py:139-180`).
- **Run on real data when the substrate is available:** `probe_spy_ci_low_kill_threshold.py --csv <SPY_TR.csv>`.

### 1A.7 Regime family closed with crippled inputs — MOSTLY REFUTED
- The truncation was real (`TLT_1d.csv` from 2020-04-09; `tlt_ret_20d` 82% NaN; GFC/COVID
  0 complete bars) and was **repaired 2026-08-26** (repoint to `tr_reconciled`, 60.3%
  complete rows from 2006-04-04; `macro_features.py:156-173`; `docs/Audit/backfill_repoint_2026_08_26.md`).
  `CURRENT_STATE.md` and `health_check.md` are stale on this; `design_referee_repairs_2026_09_18.md`
  says so. The `hmm_3state_crisis_v1.pkl` repoint is also done (commit 5d0840f).
- **T-172, T-178, T-220, T-221 built their own 2000–2026 panel** (DGS10 bond returns,
  separately fetched VIX; `regime_oos_loco_t172_2026_06_16.md:5, 22-35, 116`) and were
  not fed the truncated production panel. Those verdicts stand.
- **T-118r is plausibly confounded:** overlay fired only in 2022 and 2025 (post-2020-05
  only), GFC/COVID +0.0 — exactly a uniform-posterior signature — attributed at the time
  to the Δ-trigger. One re-run on the repointed panel settles it (brief B-9, 1 N_trial).
- Residual: `tr_reconciled` is absent from `config/substrate_manifest.sha256`, so the
  cloud image may not carry the repointed data (§2 N-13). Verify before any regime re-run.

### 1A.8 Gate 1's +0.10 excludes diversifiers — CONFIRMED (strictly `> 0.10`)
- `discovery.py:1412` `contribution > 0.10`; contribution = Sharpe(book+cand) − Sharpe(book)
  through the full backtester. A ρ≈0, SR 0.3 candidate at optimal weight w* = (0.3/0.81)·
  (σ_b/σ_c)… adds ΔSR ≈ √(0.81² + 0.3²) − 0.81 ≈ **+0.054**, below the bar by
  construction; at ρ=0.3 it adds ≈ 0. Combined with T-122 (uniform signals cancel in
  the allocator), the gate rejects exactly the class the goal needs.
- Production replaces even this with `ensemble Sharpe > 0` in Pass 2 (§2 N-2), but the
  early return at Gate 1 leaves `robustness_survival = 0`, so Gate 1 still kills.
- **Proposed gate:** does the candidate, at its deployable weight (≤ 25% long-only, cash
  at DGS3MO), raise the book's `ci_low(Δ log terminal wealth vs SPY)` above 0 and not
  worsen `ci_low(Δ Sortino)`? Paired block bootstrap, same window. Report ΔSharpe as
  a diagnostic, never as the gate.

### 1A.9 Inflators — CONFIRMED (each), with one deflator added
- Flat 1 bp half-spread, impact term unreachable (`slippage_model.py:316-319`; caller
  passes a single-row Series, `backtest_controller.py:1545-1553, 781`); stop fills at
  the stop level on gap-throughs (`execution_simulator.py:445-450`); free borrowing and
  1.7–2.3× gross (§2 N-1); 109 survivor tickers by default (`backtest_settings.json:5-115, 165`;
  PIT swap exists and is hardcoded on in several cloud scripts, off in the default
  CLI); HMM pickle training window not verified in this pass. Deflator the prior pass
  missed: price-only strategy vs total-return SPY benchmark (T-256 measured 0.685%/yr
  on SPY; larger on the equity book's own dividends, T-215 "never credited").
- Any positive result from the program must be produced with: impact on, stops off for
  factor sleeves, gross ≤ 1.0 with financing charged, PIT universe, TR both sides.

## 2. Defects the prior pass did not list (N-1 … N-14)

| # | Defect | Where | Severity | Test |
|---|---|---|---|---|
| **N-1** | **Backtester sizes from frozen `portfolio.capital`** — set once to initial capital (`backtest_controller.py:157-158, 1435-1436`), returned by `get_portfolio_capital` (`:325`), never updated; sizing equity = initial + MV (`:647`) ≈ 2× true equity once deployed. Explains the 1.7–2.3× gross and negative cash the in-code T-243 narrative (`:545-584`) attributes to held-position accumulation. Every equity-book Sharpe ever measured ran on this. | backtester | CRITICAL | yes |
| **N-2** | **Production Discovery overwrites the gauntlet.** `mode_controller.py:1338` passes `significance_threshold=None` → `gate_4_passed=False` for every candidate (`discovery.py:1498-1499, 1781-1782`); then Pass 2 (`:1397-1403`) sets `passed_all_gates = sharpe>0 ∧ PBO≥0.7 ∧ BH-reject(degenerate p)`. Gates 1(+0.10)/5/6/7/8 non-binding on promotion; PBO threshold drift 0.7 vs 0.60. The T-195 harness passes the same `None`, so T-196's H1 was structurally unreachable. | orchestration | CRITICAL | yes (text) |
| **N-3** | **MBL/DSR gate fails OPEN.** No registry → `compute_n_effective`=1 (`mbl_gate.py:79-80`) → MBL=0 → Gate 0 passes; `discovery.py:1733-1740` `except: n=1`, `if n>1` → Gate 8 skipped. Production passes batch size (`mode_controller.py:1248`), T-195 passes 35. The T-336 "honest N by default" ledger claim is true of the signature only. `[NN-FAIL-CLOSED]` violation. | measurement | HIGH | yes |
| **N-4** | Gate 5/7 with-arms reuse the Universe-A signal cache while base-arms compute fresh (`discovery.py:1275, 1535, 1672` vs `1530, 1667`; `gate1_signal_cache.py:68-72, 140-167`). Transfer "contribution" is not a transfer measurement. Moot until something reaches Gate 5. | Engine D | HIGH | — |
| **N-5** | Gate 6 subtracts RF from an attribution **spread** (`discovery.py:1582` → `factor_decomposition.py:233`): α biased down ≈ RF/yr (5% in 2023–24 > the 2% threshold). Fail-open on missing cache / <30 obs (`:294-295`; `discovery.py:1592-1595`). Report-only today. | Engine D | MEDIUM | yes |
| **N-6** | **Discovery has no held-out window.** TreeScanner labels, validation, and GA fitness all use the full `data_map` (`mode_controller.py:1194-1197, 1335, 1412`); `core/oos_lock.py` is never imported by Engine D and cannot bind on a substrate ending 2024-12-31. | Engine D | HIGH | — |
| **N-7** | Bootstrap is fixed moving-block with block = n^(1/3) (`metrics_engine.py:923, 940`), not "Politis-White" as CLAUDE.md `[NN-SHARPE-CI]` states; three separate bootstrap implementations coexist (metrics_engine / t311 paired 21-day / t333 circular). ci_low likely optimistic on daily equity. `np.percentile` over all samples incl. NaN (`:950`). | measurement | MEDIUM | — |
| **N-8** | Engine F: per-trade √252 vs daily-annualized SPY; paused→retired on point (`:958-960`); no promote/retire hysteresis; missing benchmark skips the pass; weight double-applied in sizing. | Engine F | HIGH | yes (2) |
| **N-9** | Stop/TP priced off the signal-bar close but filled at next open (`risk_engine.py:901`); realized stop distance is off by the gap. | Engine B (read-only) | LOW | — |
| **N-10** | `alpha_settings.prod.json` keys `news_sentiment_edge`; EDGE_ID is `news_sentiment_v2`; weight never applied. | config | LOW | yes |
| **N-11** | `CURRENT_STATE.md` (09-17) and `health_check.md` still carry the HMM as blind/legacy; both were fixed 08-26. `CLAUDE.md [NN-MBL]` quotes N≈75 against ≈260 recorded. Current-truth surfaces lag the referee. | docs | MEDIUM | — |
| **N-12** | T-196 "0/35, 33 at gate_1, 2 at gate_3": the two "gate_3" deaths cleared Gates 1–2 and were killed by the forced Gate 4 (N-2); `gate_3_passed` is never set (`discovery.py:1134-1135`). The H0 is a Gate-1 null for 33 and untested for 2. | record | MEDIUM | — |
| **N-13** | `config/substrate_manifest.sha256` (14,120 lines) has no `tr_reconciled`, VVIX, SKEW, Shiller, or DFII10 entries; the baked cloud image may lack the data the 08-26 repoint reads. `archondex-data-…` bucket provisioned, referenced by nothing. EDGAR corpora (2.7 GB), T-265, T-306 have no S3 sync path. | data/ops | HIGH | — |
| **N-14** | Free Alpaca IEX minute bars start **2020-07-27**, not 2016 (`intraday_features_t150…:37`); 2016+ SPY minutes came from the account's SIP entitlement. The seeded "free from 2016" premise is wrong for a universe-wide test. | data | LOW | — |

Also verified: the `2026-06-16` measurement-integrity audit's `borrow_rate_model.py:231-243`
"$0 short borrow" finding is unfixed (borrow is a post-hoc curve-B annotation only,
`cost_aggregator.py:189-194`); `feature/factor-neutrality-sizing-t218` does not exist on
origin (branch lost); `feature/no-borrow-cash-budget-t232` cited at
`backtest_controller.py:568` does not exist on origin.

## 3. The strategic mismatch (1B)

Machine as built: 109 survivor mega-caps + SPY/QQQ/IWM/TLT/GLD, long-only, daily bars,
Alpaca IEX, no options, no futures, no shorting, no margin (Roth / cash account, T-281),
intraday sampled once on SPY only. Against the project's own map
(`docs/Sources/Alpha/Retail-algo-alpha.md`):

| Map region (rank) | Reachable now? | What it takes | Free? |
|---|---|---|---|
| A1 Microcap mean-reversion (#1) | **No.** Universe is mega-cap; T-265 panel is $50M–$2B 2016+ SIP (paid entitlement, already held) with 36% CIK→ticker loss. Alpaca trades these names. | Run on T-265 with delisting returns, 50–100 bps RT, ADV ≤ 2% sizing, ≥30 names; PIT membership from EDGAR frames | $0-marginal |
| C1 Managed-futures trend (#2) | **Partly.** Trend sleeve on SPY/AGG/GLD ETFs is live; no futures, no cross-asset breadth. DBMF shadow is a clock. | Free continuous-futures history (Nasdaq Data Link free tier, CHRIS is retired — verify; Stooq futures bot-walled) → Carver-style multi-asset trend replicated with ETFs (DBC/USO/UNG/UUP/FXE/TLT/IEF) | mostly |
| A3 CEF discount (#3) | **Yes — the one real alpha.** T-267 t_HAC 2.31; T-334 panel accruing since 07-29 (361 funds). Alpaca trades CEFs. | Forward shadow book (0 N), beta-hedged and 10%-satellite backtest variants on the T-267 panel | yes |
| A2 Insider clusters, microcap (#4) | **No.** T-144 ran on 669 S&P names ("insider alpha concentrates in small caps; at our scale it is priced"). 6.89M-row SEC Form 4 archived, never joined to T-265. | Join `data/insider_sec/` to the T-265 universe (CIK-keyed, avoids the ticker-map loss); Cohen-Malloy-Pomorski opportunistic filter | yes |
| B1 Earnings vol crush (#5) | **No.** No options data; Alpaca options history starts 2024-02 (search-verified). | Forward-only shadow book on Alpaca's indicative OPRA feed (15-min delayed, free); backtest needs ORATS/ThetaData (paid tier) | forward: yes |
| A4 Merger arb (#6) | No. Hand-curated; no deal feed. | EDGAR 8-K/DEFM14A parsing; discretionary — out of scope for a machine | yes, labor |
| A5 Spinoffs (#7) | **Partly.** `spinoff_reversion_v1` exists (paused), curated YAML + Form 10. | Run on T-265 (small-cap spin-cos) with forced-selling window; tiny N | yes |
| C2/C3 Commodity basis, crypto basis (#8–9) | No / **Partly.** No futures. BTC spot via Alpaca crypto; no perp/basis venue at Alpaca. | Crypto funding-rate capture needs a perp venue (not Alpaca); basis via IBIT vs CME needs futures. Forward-only shadow from free Binance/Coinbase funding history | data yes, execution no |
| B2 Put-write (#10) | Refuted as role (07-02); XSP CSP infeasible at $10–50k | — | — |
| D1/D2 Overnight, buy-the-dip (#11–12) | **Yes** (OHLC on disk). T-135 overnight L/S refuted at large-cap; RSI(2)-style never run as an overlay on SPY/QQQ | One pre-registered overlay probe | yes |
| E1 Small-cap momentum (#13) | **No.** T-249 killed on an *assumed* haircut on survivor-only Stooq (gross Sharpe 3.21, net Sortino ci_low 0.49); never re-run on T-265. | Re-run on T-265 with delisting returns | $0-marginal |
| A6 ETF NAV gaps (#14) | No. No iNAV feed. | Forward-only; low priority | — |
| Fixed-income RV, dispersion, cross-exchange crypto (#30–32) | **Dead for this operator.** No repo, no prime, no multi-venue. Do not dispatch. | — | — |

**The deploy candidate cannot beat SPY by more than its tilt allows.** 85/15 VOO/MTUM
with MTUM's long-run excess over the S&P of roughly 1–3%/yr (decayed post-publication)
bounds the terminal-wealth edge at ≈ 0.15–0.45%/yr before the 0.15% ER gap. If the
operator's goal is terminal wealth > SPY by a margin worth the operational risk, the
candidate needs a materially different composition (a satellite in one of the reachable
regions above) or the honest statement that the tilt is the ceiling and the levers are
contribution rate, wrapper, and cost.

## 4. Never-tried / blocked / mis-specified (1C, verified) and unused data (1D)

| Item | Verified status | Universe / substrate | Source |
|---|---|---|---|
| PEAD × insider-cluster interaction | **Never run, never pre-registered** | — | `whole_project_gap_audit:24`; not in shelf #15's 9 cells |
| 8-K / Form 4 / 13F as a class | Refuted on **S&P large/mid only** (624 / 669 / 669 names); T-144 doc itself says small caps are where the alpha lives | S&P PIT | `form4_insider_gauntlet_t144…:6-8, 61-63` |
| T-265 survivorship-complete panel | Built (24,990 events, 1,891 names, 4,674 tickers); **only PEAD run on it (null, t 0.34/0.45)**; prices reused by T-271/T-289 | small-cap 2016+ | `smallcap_pead_pilot_t265…` |
| Small-cap momentum (T-249) | Killed on literature haircut; **gross SR 3.21 / net Sortino ci_low 0.49 on survivor-only**; never re-run on T-265 | Stooq survivors | `smallcap_momentum_gauntlet_t249…` |
| Lazy Prices (T-237) | Run; **no verdict doc exists** (only "leaning H0" in three secondary docs); 10-K only; 15.1% parse failures, 2006 rows 98.4% fail, 15 mega-caps 100% Item-7 fail; repair specified (T-341b) not applied; short leg never tested | S&P PIT-691 | `similarity_parser_diagnosis_t341b…` |
| Minute-bar features (T-150) | `or_frac`, `last30_ret` passed MI screens; hand-off never dispatched (shelf #14). IEX minutes 2020-07+ only | 6 ETFs | `intraday_features_t150…:48-58, 94-98` |
| CEF (T-264/267) | t_HAC 2.31, MDD −42.7%, post-2011 t 0.90; **beta-hedged never run, satellite never run, forward book dispatched never built** | 25 CEFs 2004+ | `cef_lowerbound_probe_verdict_t267…` |
| True-Edge 3-way selector (T-216) | Built, dormant; 2-way local cut Sharpe 0.958, vs robos ci_low < 0, "beta"; g_regime used the pre-repoint HMM | 2018–25 | branch `feature/conditional-selector-build-t216` |
| Jump model vs HMM | Never run, no code | — | `Retail-algo-regime.md:244-337` |
| Robo anchored to Schwab published returns | Never | — | `combined_candidate_scorecard.py:38-39` |
| Options IV surface | Blocked (paid); the $0 VIX/VIX3M+SKEW proxy prereg T-342 is "DRAFT — NOT RUN" | — | `volterm_conditioner_prereg_t342…:6, 159` |
| T-212 vol-target part 2 / T-218 factor-neutral sizing | T-212 branch ends at the prereg (18dda0a), partly overtaken by T-262 (H0); **T-218 branch does not exist on origin — lost** | — | ls-remote |
| Nonlinear cross-sectional ML | One narrow run: T-149 HistGBM vs ridge over **8 edge signals**, 109 tickers, 2021–24, 1-day target, CPCV 15 paths; ridge won (IC 0.006). No raw-characteristic monthly ranker (Gu-Kelly-Xiu) ever | mega-cap | `metalearner_falsification_t149.py:14-40` |
| Shorting with realistic borrow | Never; borrow model returns $0 at the fill; Roth/cash account closes short legs anyway (T-281) | — | `measurement_integrity_audit…:33` |
| Regime refutations vs truncation | T-172/178/220/221 unaffected (own panel); T-118r plausibly confounded; nothing re-run post-repoint | — | §1A.7 |
| Open Source Asset Pricing (Chen-Zimmermann) | Never used; "candidate future use" only | — | `2026-07-08_research-agent-v2.md:234` |
| Wikipedia pageviews / Google Trends / ChronoBERT | Never run / skipped (renormalization) / "STILL OPEN" | — | inventory `:26, :33`; `…t339b…:66` |
| Foundry raw-signal decile eval | **Never** (see 1A.3) | — | `run_foundry_eval_t195.py:90-107` |
| RSST (T-296) / HRP (T-248) | Refuted; T-296 on the fair T-255 harness (cash at DGS3MO), T-248 on 2019–23 only, pre-T-255 (robo cash 4%, 0% flat leg inferred), base book "leans on shorts a Roth can't do" | sleeve / equity | verdict docs |

**Data on disk with no Engine A consumer (1D, from code — S3 unverifiable here):** SEC
structured Form 4 (6.89M rows 2006+), 13F panel (476k rows 2013+), 8-K items (183k
filings 1994+), 10-K similarity (10,860 rows 2005+, 10-K only), news panel (771k
articles 2015+), FINRA short volume/interest and SEC FTD (**forward from 2026-05/06
only**, not 2014+ as catalogued), Polymarket/Kalshi (2026-06+), GDELT tone (retired),
USASpending (2026-07+), CFTC COT (fetcher raises `NotImplementedError`), T-265 SIP
panel + XBRL EPS frames, CEF T-267 panel + T-334 daily panel, minute features, AQR TSMOM,
T-306 multi-decade substrate, `tr_reconciled` ETFs, CBOE strategy indices, Shiller,
VVIX/SKEW. Catalogued only: OSAP, Wikipedia pageviews, 13D/G, patents, transcripts,
GDELT bulk, any options surface, Sharadar/Norgate.

## 5. Ranking — (expected impact on beating SPY) × (cheapness) ÷ (N_trials)

Impact is judged on terminal wealth vs SPY, not on Sharpe. "Cheap" = free data on disk,
≤ 1 week, existing harness.

| Rank | Item | Impact | Cheap | N | Why here |
|---|---|---|---|---|---|
| 1 | **Referee repairs RR-1…RR-4** (frozen capital; Pass-2 overwrite + None threshold; Gate-4 null; fail-open N) | Changes what every equity-book number means | code only | 0 | Nothing measured after this is comparable to anything measured before it; do first |
| 2 | **Raw-signal decile re-evaluation** of 35 features + top edges, monthly, TR, cash at DGS3MO, no stops/allocator | Settles "exhausted price vocabulary" either way | on-disk | 2 (one long-only, one L/S family) | The single unrun test the whole H0 rests on |
| 3 | **Small-cap momentum + insider clusters on T-265** with delisting returns | Highest-ranked reachable regions on the map, never tested where the literature says they live | $0-marginal | 2 | T-249's kill was assumed, not measured |
| 4 | **CEF: forward shadow book (0 N) + beta-hedged + 10%-satellite backtest** | The only t>2 alpha; retail-sized | on-disk | 2 | Parked for a reason that a forward book does not need |
| 5 | **Cross-sectional GBM ranker, one frozen spec, monthly, PIT S&P, CPCV** | The model class the literature says works on price+fundamental characteristics; never run | on-disk | 1 | Closes the ML question honestly |
| 6 | **Route C risk parity with honest Roth financing** (levered ETFs: SSO/UBT-style embedded cost, not margin) | Only route that can beat SPY *terminal wealth* without alpha, if financing < premium | on-disk | 1 | T-248/T-296 ran on the wrong cash/leverage conventions |
| 7 | Lazy Prices re-run after T-341b repair, long+short, T-265 + S&P | Text modality; decayed post-2020 | on-disk | 2 | Panel is broken today; fix first |
| 8 | T-118r re-run on the repointed HMM panel | Settles the one confounded regime verdict | on-disk | 1 | Cheap closure |
| 9 | Overnight / RSI(2) SPY overlay probe | Small, free | on-disk | 1 | Low prior, near-zero cost |
| 10 | Forward books: options vol-crush (Alpaca indicative feed), crypto funding (Binance/Coinbase history), execution timing | 0 N; honest clock length 12–24 months | free | 0 | Cheap, slow |
| — | PEAD × insider interaction, T-216 3-way, jump model | Mechanism-first only after 3–5 report | — | 1 each | Conditional |

## 6. Scorecard of this pass against the seeded claims
Confirmed as stated: 1A.2, 1A.3 (core), 1A.6, 1A.9. Confirmed but narrowed: 1A.1 (latent,
not the killer; misdiagnosed in May), 1A.4 (mechanisms yes; "verdicts flip" no), 1A.5
(strongest gate dormant; scorecard cash already half-fixed), 1A.8 (holds, but production
Pass 2 replaces it). Mostly refuted: 1A.7 (4 of 5 verdicts used their own panel; the
backfill landed 08-26). Corrected premises: "70% cash" (the book is levered), "free minute
bars from 2016" (2020-07), "T-265 never used" (PEAD was run, null).
