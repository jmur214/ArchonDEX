# Alpha-frontier research program — 2026-09-30

> **For the director.** Every item below is a self-contained worker brief in the repo's dispatch
> format (setup, background with `file:line` citations, numbered deliverables, acceptance,
> pre-registration, what to commit). Fire any brief into a worktree unchanged. Companion files:
> `docs/Sources/alpha_frontier_review_2026_09_30/{00_what_the_machine_is,01_gap_report,02_route_research}.md`,
> `tests/test_referee_repairs_proposed.py` (16 `xfail(strict=True)`), `scripts/probe_*.py`.
> Branch `research/alpha-frontier-2026-09-30`. Nothing here implies a real-money date.
>
> **Read first (three findings that change the order of everything):** (1) the backtester sizes
> every position from a frozen initial-capital figure (`backtester/backtest_controller.py:158, 325, 647`)
> — every equity-book verdict ran on ≈ 2× sizing equity; (2) production Discovery overwrites the
> gauntlet verdict (`orchestration/mode_controller.py:1338, 1397-1403`) so Gates 1/5/6/7/8 never bound
> on promotion, and Gate 4's null is a point mass (`significance.py:84`); (3) the operator's wrapper is
> an Alpaca IRA: options Level 2 only, **no crypto** (the BTC leg is IBIT-only in the Roth), no
> margin/futures/shorts — which retires half of the project's own alpha map before evidence matters.

## Index

| Brief | Route | N_trials | Est. wall-time | Parallel group | Blocked on |
|---|---|---|---|---|---|
| **RR-1** Backtester sizing from frozen `portfolio.capital` | referee | 0 | 1–2 d | P0 | — |
| **RR-2** Discovery verdict overwrite + Gate-4 null | referee | 0 | 2 d | P0 | — |
| **RR-3** Honest N: fail-closed, exact E[max], correlation-aware | referee | 0 | 2–3 d | P0 | run-registry access (Mac/S3) |
| **RR-4** Engine F retirement burden of proof | referee | 0 | 1–2 d | P1 | — |
| **RR-5** Cash yield, financing, dividends in the backtester + scorecard symmetry | referee | 0 | 3 d | P1 | RR-1 |
| **RR-6** Discovery: terminal-wealth gate, held-out window, Gate 5/6/7 fixes | referee | 0 | 3 d | P2 | RR-2 |
| **RR-7** Record hygiene (edge-weight key, HMM/N/bootstrap record, manifest, IRA-crypto note) | referee/docs | 0 | 0.5 d | P0 | — |
| **B-1** Raw-signal decile re-evaluation of 35 features + XS edges | A | +2 | 4–5 d | R1 | — |
| **B-2** Small-cap momentum + insider clusters on T-265 | E | +2 | 4–5 d | R1 | — |
| **B-3** CEF satellite / beta-matched backtest + forward shadow book | E | +1 / 0 | 3 d | R1 | — |
| **B-4** Frozen GBM cross-sectional ranker, two universe arms, CPCV | A | +2 | 5 d | R2 | B-1 panel |
| **B-5** Levered diversified book vs 1× SPY under honest Roth financing | C/D | +1 | 3 d | R1 | — |
| **B-6** Lazy Prices: panel repair, 10-Q, long+short, two universes | I | +2 | 5 d | R2 | — |
| **B-7** T-118r regime overlay re-run on the repointed HMM panel | regime | +1 | 1 d | R1 | `tr_reconciled` on the runner (RR-7 §3) |
| **B-8** Execution-timing cells for the monthly rebalancer | J | +1 | 1–2 d | R2 | — |
| **B-9** Multi-factor combination tilts at deployable weights | B | +1 (family of 4 pre-declared arms) | 2 d | R1 | — |
| **B-10** Gold 10% permanent leg (one trial) | H | +1 | 1 d | R2 | — |
| **F-1…F-10** Forward shadow books / KPI (0 N) | G/H/I/J/E | 0 | 1–2 d each | F | new external feeds are propose-first (CLAUDE.md) |
| **P-1…P-4** Paid-data tier (not recommended today; each has a trigger) | — | +1 each | — | — | budget ruling |

**Parallel groups.** P0 (RR-1, RR-2, RR-3, RR-7) run together — different files. RR-5 waits for RR-1
(same file); RR-6 waits for RR-2 (same file). R1 (B-1, B-2, B-3, B-5, B-7, B-9) run together with P0 —
all standalone harnesses, none touch the referee. R2 after R1 (B-4 needs B-1's panel; B-6/B-8/B-10 are
just lower priority). F books any time; each is report-only and needs the director's word on any new
external feed. **File overlaps:** RR-1/RR-5 (`backtest_controller.py`, `portfolio_engine.py`);
RR-2/RR-6 (`discovery.py`); B-1/B-4 (`data/research/b1/`); B-3 writes a NEW `paper_trader/cef_shadow_book.py`
and does not wire it (director wires).

**What would refute the operator's belief that this can beat SPY.** If, under the corrected referee
(RR-1…RR-5 merged) and on the honest substrate, B-1, B-2, B-3, B-5 and B-9 ALL return
`ci_low(Δ log terminal wealth vs SPY) ≤ 0` at deployable weights, then the belief is refuted at the
level of everything free data can reach: the price vocabulary (right construction), the two
capacity-bounded niches the map ranks highest (right universe), the one alpha ever found (CEF), the
only structural route (levered diversification at honest cost), and the only underpowered-by-design
tilt test (combinations). What would remain is the paid tier (P-1) and forward books whose clocks run
past 2027 — and the honest statement that the tilt is the ceiling and the levers are contribution
rate, wrapper, and cost.

## 3.1 Referee repairs (PROPOSALS — the referee is never autonomously modified)

Every brief below produces a branch + a proposal doc + passing versions of the matching
`tests/test_referee_repairs_proposed.py` tests (xfail marker removed on the branch). **No
brief merges.** The director reviews; the user rules on merge. Ranked by how many "H0"
verdicts the defect touches. N_trials: 0 — these are corrections, not hypotheses; any
historical cell re-run under the corrected referee is labeled RE-SCORE, never a new trial.

Common SETUP for every RR brief:
```bash
cd <repo root>
git worktree add .claude/worktrees/<branch> -b <branch> origin/main
cd .claude/worktrees/<branch>
python -m pip install -r requirements.txt -q
python -m pytest tests/test_referee_repairs_proposed.py -q   # must show the targeted xfails
```
Common HARD CONSTRAINTS: do not touch `engines/engine_b_risk/`, `paper_trader/`, `ops/`,
`config/*.prod.json`; do not push; do not merge; do not edit `data/governor/*`; write the
proposal doc in `docs/Sources/referee_repair_proposal_<RR-id>_<date>.md`; read
`docs/Core/autonomous_development_prestatement.md` first.

---

### RR-1 — Backtester sizing from frozen `portfolio.capital` (touches EVERY equity-book verdict)
**subagent_type:** quant-dev · **branch:** `fix/referee-rr1-sizing-capital` · **est. wall-time:** 1–2 days · **parallel group:** P0 · **overlaps:** `backtester/backtest_controller.py` (RR-5 also edits it — sequence RR-1 before RR-5)

**Background.** `backtester/backtest_controller.py:157-158` sets `self.portfolio.capital = initial_capital`
once (PortfolioEngine has no such attribute natively — `engines/engine_c_portfolio/portfolio_engine.py:59-100`);
`:325` returns it from `get_portfolio_capital()`; `:647` computes sizing `equity = get_portfolio_capital() + Σ MV`.
Nothing updates `capital`. Once cash is deployed, sizing equity ≈ initial capital + MV ≈ 2× true equity
(cash + MV, `portfolio_engine.py:353`). Engine B's gross guard (`risk_engine.py:1376-1382`, read-only) mixes
the inflated `equity` with true-equity gross, so gross ratchets past 1.0. This is the mechanism behind the
1.7–2.3× gross and negative cash that the in-code T-243 narrative (`:545-584`) attributes to held-position
accumulation. Failing test: `test_backtester_sizing_capital_tracks_deployed_cash`.

**Deliverables.**
1. A 30-line probe `scripts/probe_rr1_sizing_equity.py`: run `BacktestController` on the golden fixture
   (`tests/golden/`) with `BACKTEST_DEBUG` off; log per-bar `get_portfolio_capital()`, `portfolio.cash`,
   true equity, gross. Confirm sizing equity diverges from true equity after the first fill. Commit the
   log as `docs/Sources/referee_repair_proposal_RR-1_<date>.md` §1.
2. The fix on the branch: `get_portfolio_capital()` returns `self.portfolio.cash`; delete the dynamic
   `capital` attribute at `:157-158` and `:1435-1436`; sizing `equity = cash + Σ MV` (one definition,
   shared with `_log_snapshot`). Keep `deployable_cash_account` semantics unchanged.
3. Golden-fixture diff: `tests/golden/golden_equity.csv` will change. Regenerate ONLY on the branch,
   commit the before/after diff, and state the change in gross, trade count, and Sharpe.
4. RE-SCORE (labeled, not new N): the canonical 26-yr equity baseline cell (the "0.751 / ci_low 0.382"
   in `docs/State/GOAL.md`) and the T-196 harness on 3 features (`triple_witching`, `january`,
   `mom_12_1`) via `scripts/run_isolated.py` with the corrected controller. Report point + ci_low
   before/after side by side. If the substrate is not on this machine, submit via
   `scripts/submit_substrate_run.py` per `docs/Cloud/CLOUD_USAGE.md` and say so.
5. The verdict list: name every ledger row whose evidence is an equity-book Sharpe measured through
   this controller (T-002…T-272 sweep rows, T-196, T-215, T-239, T-241) and mark each
   "UNTESTED under corrected sizing" in the proposal doc. Do NOT edit `TASK_LEDGER.md`; the director does.

**Acceptance.** Probe reproduces divergence; targeted xfail becomes a pass on the branch; full default
test tier passes except golden-pinned tests, each of which is listed with its before/after; the
re-score table exists with ci_low both sides; proposal doc states the direction of bias (expected:
free leverage FLATTERED bull-year Sharpe and CAGR, hurt 2022) with the measured numbers.

**Pre-registration.** Hypothesis: sizing equity ≠ true equity after the first fill (H1 = the bug is
live). Refutation: if the probe shows sizing equity == cash + MV on every bar, the finding is wrong;
write that and stop. N_trials: 0.

**Commit.** `fix(backtester): size from cash + MV, not frozen initial capital (RR-1 proposal)` +
probe + proposal doc + regenerated golden (branch only).

---

### RR-2 — Production Discovery: the gauntlet verdict is overwritten; Gate 4 has no null (touches every Discovery cycle; T-193; T-196's two Gate-1/2 survivors)
**subagent_type:** engine-auditor (read) then quant-dev (fix) · **branch:** `fix/referee-rr2-discovery-verdict` · **est. wall-time:** 2 days · **parallel group:** P0 · **overlaps:** `engines/engine_d_discovery/`, `orchestration/mode_controller.py` (RR-6 also edits discovery.py — sequence RR-2 first)

**Background.** Three linked defects. (a) `engines/engine_d_discovery/significance.py:84` permutes
the strategy's own returns; mean and std are permutation-invariant, so every null Sharpe equals the
actual and p is floating-point noise (`scripts/probe_gate4_permutation_null.py`: p = 0.973 for SR 5.2;
`docs/Measurements/2026-05/gates_2_to_6_audit_2026_05.md:208-210` misdiagnosed this as "mathematically
correct"). (b) `orchestration/mode_controller.py:1338` passes `significance_threshold=None`, which
`discovery.py:1498-1499, 1781-1782` maps to `gate_4_passed=False` for every candidate; the T-195
harness (`scripts/run_foundry_eval_t195.py:104`) does the same, so T-196's H1 was unreachable.
(c) `mode_controller.py:1397-1403` then overwrites `passed_all_gates` with
`sharpe>0 ∧ robustness_survival≥0.7 ∧ BH-reject`, dropping Gates 1/5/6/7/8 from promotion and using
0.7 where `validate_candidate` uses 0.60 (`discovery.py:957`). Failing tests:
`test_gate4_permutation_null_has_nonzero_spread`, `test_gate4_rejects_a_sharpe_5_series`,
`test_production_discovery_does_not_overwrite_gauntlet_verdict`.

**Deliverables.**
1. `significance.py`: new `monte_carlo_permutation_test(strategy_returns, signal=None, asset_returns=None, ...)`.
   When `signal` and `asset_returns` are given: permute the SIGNAL against the asset returns (block-permute
   with block = n^(1/3) to preserve signal autocorrelation), strategy_null = signal_perm × asset_returns.
   When only `strategy_returns` is given: stationary-block SIGN-FLIP null around zero mean. Return both
   p-values when both are computable. Keep the function name and dict keys so `discovery.py:1485-1487`
   and `apply_bh_fdr` need no change beyond passing the two extra arrays (attribution stream = with − base;
   the candidate's own signal panel and the with-arm asset returns are already in scope at `:1291-1320`).
2. Power test in `tests/test_significance.py`: SR-3 series → p < 0.01 under both nulls; SR-0 series →
   p ∈ [0.3, 0.7]; the existing "near 0.5" comment deleted.
3. `mode_controller.py:1338` and `run_foundry_eval_t195.py:104`: pass `significance_threshold=0.05`
   (from `config/discovery_settings.json`, add the key). `validate_candidate`: `None` → `ValueError`
   (fail loud), not a silent fail.
4. Delete the Pass-2 overwrite at `mode_controller.py:1397-1403`; keep BH-FDR as a *post-filter on
   candidates that already passed all gates* (`passed_all_gates and bh_reject`), logging the count it removed.
   Align the PBO threshold to the one config value.
5. Convert `test_production_discovery_does_not_overwrite_gauntlet_verdict` from a text assertion to an
   execution test: run `_run_discovery_cycle` on the golden fixture with a stubbed `validate_candidate`
   returning `passed_all_gates=False, sharpe=1.0, robustness_survival=0.9` and assert nothing is promoted.
6. RE-SCORE: the two T-196 features that cleared Gates 1–2 (`triple_witching`, `january`) through the
   corrected gauntlet on the T-196 substrate. Report every gate's value. Expected: both fail a working
   Gate 4 or Gate 8 (calendar features, no mechanism). State it either way.

**Acceptance.** Probe re-run shows null_std > 0.3 on all four series; power test passes; the three
xfails pass on the branch; every integration test that monkeypatched Gate 4 to p=0.001
(`tests/test_discovery_gate_remediation.py:165, 353`; `tests/test_discovery_gates_7_8.py:151`) now
uses the real null on a synthetic alpha series instead; the charter drift at
`docs/Core/engine_charters.md:353-365` (4 gates described vs 9 in code) is listed in the proposal doc
with the proposed text.

**Pre-registration.** H1: the corrected null has power (SR-3 → p<0.01). Refutation: if the
signal-permutation null also has null_std < 0.05 on the probe series, the construction is wrong;
report and stop. N_trials: 0 (the T-196 re-score is a re-score).

**Commit.** `fix(engine-d): valid Gate-4 null + stop overwriting the gauntlet verdict (RR-2 proposal)`.

---

### RR-3 — Honest N: fail-closed, exact E[max], correlation-aware (touches Discovery Gate 0/8 only — NO sleeve/tilt verdict flips)
**subagent_type:** quant-dev · **branch:** `fix/referee-rr3-honest-n` · **est. wall-time:** 2–3 days (day 1 is data) · **parallel group:** P0 · **overlaps:** `core/measurement/mbl_gate.py`, `core/observability/run_registry.py`

**Background.** `core/measurement/mbl_gate.py:79-80` returns N=1 when the registry is absent →
`compute_mbl_min`=0 → Gate 0 passes; `discovery.py:1733-1740` swallows exceptions to N=1 and skips
Gate 8 when N≤1; production passes batch size (`mode_controller.py:1248`). `:58` uses `2·ln N/SR²`,
the upper bound BBLdPZ (2014) quote for intuition; the exact form is `E[max_N]²/SR²`
(`scripts/probe_mbl_n_effective.py`: 38.7% overstatement at N=260). Every run counts as one trial
(`:90`; `run_registry.py:229-244`; `scripts/backfill_run_registry_t336.py:11-28`). Four inconsistent N
series exist (75 / 76–78 / 231 / ~260 / ~295). **What this does NOT touch:** T-251/259/279/282/284/312/318
are paired-difference CIs against zero, not DSR-gated — state this in the proposal so nobody expects them
to flip. Failing tests: `test_mbl_min_uses_exact_expected_max_not_upper_bound`,
`test_n_effective_is_not_a_raw_row_count`, `test_mbl_n_effective_fails_closed_when_registry_absent`.

**Deliverables.**
1. `compute_n_effective(db_path)` raises `FileNotFoundError` when the registry is absent; `discovery.py`
   Gate 0/8 propagate (fail closed) unless the caller passes an explicit `n_trials_for_dsr`; production
   passes the registry N, not batch size; log the N used in `performance_summary.json.census`.
2. `compute_mbl_min` uses `E[max_N]` via the Euler-γ approximation already in
   `core/metrics_engine.py:627-634`; keep the old formula behind `--upper-bound` for comparison.
3. **The empirical ρ̄ (first deliverable of value):** from the run registry's run dirs on the Mac/S3
   (`data/trade_logs/*/`, equity curves), build the correlation matrix of daily returns across all
   registered runs; report ρ̄, the ONC-cluster count (López de Prado 2019, `sklearn` KMeans over the
   correlation-distance matrix with silhouette selection), and N_eff under (i) the equicorrelated
   identity `E[max]²·(1−ρ̄)` and (ii) cluster count. Dedupe determinism reps (identical `trades_canon_md5`)
   before counting. Write `data/observability/n_effective_<date>.json` and the table in the proposal doc.
4. `compute_n_effective_correlated(db_path, method="onc"|"equicorr")` in `mbl_gate.py`; Gate 0/8 read it.
5. Reconcile the four N series into ONE in the proposal doc and propose the CLAUDE.md `[NN-MBL]` text
   (currently "~75"); do not edit CLAUDE.md.

**Acceptance.** Three xfails pass; `python -m scripts.probe_mbl_n_effective` reproduces; the ρ̄ table
exists with the run count, dedupe count, ρ̄, cluster count, and the resulting SR_req on the 12- and
26-yr windows; the proposal doc has a section titled "Verdicts this does not change" listing the seven.

**Pre-registration.** H1: ρ̄ across registered runs > 0.3 (trials are heavily correlated). Refutation:
ρ̄ < 0.1 ⇒ the raw count was honest and only the 2·ln N inflation stands. N_trials: 0.

**Commit.** `fix(measurement): fail-closed honest-N, exact E[max], correlation-aware N_eff (RR-3 proposal)`.

---

### RR-4 — Engine F retirement burden of proof (touches no persisted historical verdict; prevents future false retirements)
**subagent_type:** regime-analyst (Engine F is in its lane) · **branch:** `fix/referee-rr4-lifecycle-burden` · **est. wall-time:** 1–2 days · **parallel group:** P1 · **overlaps:** `engines/engine_f_governance/lifecycle_manager.py`, `evolution_controller.py`

**Background.** `lifecycle_manager.py:742-745` retires unless `ci_low ≥ SPY_sharpe − 0.3` (retire
unless proven good); `:267-275` annualizes per-trade dollar PnL by √252 regardless of frequency;
`:958-960` paused→retired uses the point estimate; `evolution_controller.py:191, 203` promote and
retire on the same threshold (no hysteresis; charter `docs/Core/engine_charters.md:395` says "strong
hysteresis"); `governor.py:662-663` swallows a missing benchmark and skips the pass;
`benchmark.py:100-104` uses dividend-reconciled SPY while edge PnL is split-only
(`data_manager.py:756`). Probe: `scripts/probe_engine_f_retirement_burden.py` — a true-SR-0.6 daily
edge is retired in 33–53% of simulations at 250–1000 trades; needs ≈96,000 trades to clear. Failing
tests: `test_engine_f_does_not_retire_a_true_sr_0p6_edge_after_1000_trades`,
`test_engine_f_sharpe_annualization_respects_trade_frequency`,
`test_engine_f_sharpe_helper_uses_tolerance_std_guard`, `test_paused_retirement_gate_reads_ci_low_not_point`.

**Deliverables.**
1. Hysteresis band: RETIRE iff `ci_high < threshold` (proven bad); KEEP iff `ci_low ≥ threshold`
   (proven good); otherwise `under_review` with the band width logged. Promote in `evolution_controller`
   on `ci_low ≥ threshold + 0.1`. Config keys, defaults in `LifecycleConfig`, documented in the docstring
   (delete the stale "recent decay" text at `:28-32`).
2. Annualize by measured trades/yr: `sqrt(252 · n_trades / n_trading_days_active)`; same factor in the
   bootstrap helper; tolerance guard (`std < 1e-12 or not isfinite`).
3. Benchmark on the same adjustment basis as the edge PnL (price-only SPY from `data/processed/SPY_1d.csv`
   while the book is price-only; both TR after RR-5).
4. paused→retired reads `ci_high` under the same rule; missing benchmark → `RuntimeError` (fail closed),
   not a skipped pass.
5. Re-run the probe with the corrected gate; report retire rates for true SR ∈ {0.3, 0.6, 1.0} and the
   FALSE-KEEP rate for true SR ∈ {−0.3, 0} so the band is honest both ways.
6. In the proposal doc: the governor-weight double-application (`alpha_engine.py:1068` × `risk_engine.py:1173,1177`)
   as a SEPARATE Engine B propose-first item — describe, do not fix.

**Acceptance.** Four xfails pass; probe retire rate for true SR 0.6 at 1000 trades < 10% and false-keep
for true SR −0.3 at 1000 trades < 10%; `docs/State/lessons_learned.md:14` (T-043 "ci_low captures what
point estimate misses") is cited and corrected in the proposal, not edited.

**Pre-registration.** H1: the corrected gate has ≤10% false-retire at SR 0.6 / N=1000 and ≤10% false-keep
at SR −0.3 / N=1000. Refutation: if no band width satisfies both, report the trade-off curve. N_trials: 0.

**Commit.** `fix(engine-f): hysteresis retirement band, frequency-aware annualization (RR-4 proposal)`.

---

### RR-5 — Cash, financing, and dividends: one convention in the backtester (touches every absolute equity-book number and the scorecard deploy rule)
**subagent_type:** quant-dev · **branch:** `fix/referee-rr5-cash-financing-tr` · **est. wall-time:** 3 days · **parallel group:** P1 (after RR-1) · **overlaps:** `backtester/backtest_controller.py`, `engines/engine_c_portfolio/portfolio_engine.py`, `core/combined_candidate_scorecard.py`

**Background.** Idle cash earns 0% (`portfolio_engine.py:90, 353`; zero hits in `backtester/`);
negative cash is free (`:216-220`); the sleeve harness credits the FF RF path
(`scripts/deep_reverify_sleeve_t311.py:90`) and the scorecard robo credits DGS3MO + a DGS10 coupon
(`combined_candidate_scorecard.py:237-244`) while the strategy leg is verbatim (`:430`) with a flat 4%
haircut (`:378-386`) and a marginal-ci_low deploy rule (`:604`). Equity edges are price-only
(`data_manager.py:756`); SPY benchmark is TR (`benchmark.py:100-104`); T-256 measured the SPY gap at
0.685%/yr; the equity book "was never credited dividends" (07-02 gap audit Part 1 §6). Failing test:
`test_portfolio_engine_has_cash_accrual_api`.

**Deliverables.**
1. `PortfolioEngine.accrue_cash_interest(date, rate_series)`: positive cash × (DGS3MO/252); negative cash
   × (DGS3MO + 150 bps)/252 as the honest retail financing placeholder (levered-ETF embedded cost class;
   RR-1 should make negative cash rare). Called once per bar from the controller. Rate series from
   `data/macro/DGS3MO.parquet`; missing rate → HALT (`[NN-FAIL-CLOSED]`), never 0.
2. Dividend crediting: for tickers with a `tr_reconciled` file, credit `(TR_ret − price_ret) × MV` to cash
   on each bar; for others, HALT in measured runs and set `census.dividends_blind = n` (allow-listed only
   in sandbox mode). Add `census.cash_convention = "dgs3mo_tr_v1"` to `performance_summary.json` and to
   `tests/test_contracts.py`.
3. Scorecard: strategy leg through the same accrual; remove the flat 4% haircut (both sides earn the
   path); deploy rule becomes the PAIRED block-bootstrap `ci_low(Δ log wealth) > 0` (reuse
   `deep_reverify_sleeve_t311.py:139-180`), with the old marginal rule kept as a diagnostic column;
   `:327` tax-config read failure → HALT.
4. RE-SCORE the canonical 26-yr baseline under RR-1 + RR-5 together; report cash-yield, financing, and
   dividend contributions as separate lines in bps/yr.

**Acceptance.** xfail passes; the golden fixture diff is committed with the three contribution lines;
contract test guards the new census key; the proposal doc lists every ledger row that quoted an
equity-book CAGR or a scorecard deploy verdict as "RE-SCORE REQUIRED."

**Pre-registration.** H1: the corrected book's 26-yr CAGR moves by > 0.5%/yr (dividends ≈ +1.5%,
financing ≈ −x%, cash ≈ +y%). Refutation: |Δ| < 0.2%/yr ⇒ the conventions were immaterial; say so.
N_trials: 0.

**Commit.** `fix(backtester): cash yield, financing charge, dividend credit; scorecard symmetry (RR-5 proposal)`.

---

### RR-6 — Discovery: a gate that measures the goal, a held-out window, and two internal defects (touches future Discovery only)
**subagent_type:** quant-dev · **branch:** `fix/referee-rr6-discovery-gates` · **est. wall-time:** 3 days · **parallel group:** P2 (after RR-2) · **overlaps:** `engines/engine_d_discovery/discovery.py`, `core/factor_decomposition.py`, `core/oos_lock.py`

**Background.** Gate 1 is `contribution > 0.10` Sharpe (`discovery.py:1412`); a ρ≈0, SR-0.3 diversifier
adds ≈ +0.05 by construction and T-122 showed uniform timing signals cancel in the allocator (Δ=0.000).
Gate 6 passes `returns=attribution` (`:1582`) into a regression that subtracts RF (`factor_decomposition.py:233`)
— α biased down ≈ RF/yr; fail-open on missing cache (`:1592-1595`, `:294-295`). Gate 5/7 with-arms reuse the
Universe-A signal cache (`:1275, 1535, 1672` vs `:1530, 1667`). Discovery has no held-out window
(`mode_controller.py:1194-1197, 1335, 1412`); `core/oos_lock.py` is never imported by Engine D. Failing test:
`test_gate6_alpha_of_a_factor_neutral_spread_is_not_shifted_by_rf`.

**Deliverables.**
1. Gate 1 replacement (config-switchable, default ON for new cycles): paired block-bootstrap
   `ci_low(Δ log terminal wealth vs SPY-TR)` of (book + candidate at deployable weight ≤ 0.25, cash at
   DGS3MO) minus (book) > 0 AND `ci_low(Δ Sortino) > −0.05`. ΔSharpe reported as a diagnostic column.
2. Gate 6: `regress_returns_on_factors(..., already_excess=True)` for attribution spreads; missing factor
   cache → HALT in measured runs.
3. Gate 5/7: build the with-arm from fresh (unwrapped) baseline edges on the alternate data_map, or key
   the cache on `(data_map_id, now)`.
4. Held-out window: `hunt()` and GA fitness on `[start, T−24mo]`; `validate_candidate` Gates 2–8 on the
   full window but Gate 1' (above) additionally on `[T−24mo, T]` alone; consult `oos_lock` at cycle start
   and refuse to run when the frozen window overlaps.
5. Charter/index text proposal for the 9-gate reality.

**Acceptance.** xfail passes; a synthetic ρ=0 SR-0.3 candidate at 20% weight passes Gate 1' and fails
the old Gate 1 (both shown); a synthetic uniform timing signal is no longer cancelled; contamination test:
Gate 5 contribution on a data_map where the candidate is pure noise is ≈ 0, not the Universe-A value.

**Pre-registration.** N_trials: 0. Refutation of the Gate 1' design: if on the golden fixture Gate 1'
passes a candidate whose true α is 0 in > 10% of 50 seeded noise candidates, tighten before proposing.

**Commit.** `feat(engine-d): terminal-wealth contribution gate, held-out window, Gate 5/6/7 fixes (RR-6 proposal)`.

---

### RR-7 — Record and reproducibility hygiene (zero N, half a day)
**subagent_type:** code-health · **branch:** `chore/referee-rr7-record-hygiene` · **est. wall-time:** 0.5 day · **parallel group:** P0 · **overlaps:** docs only + one config key

**Deliverables (each its own commit).**
1. `config/alpha_settings.prod.json`: rename `news_sentiment_edge` → `news_sentiment_v2`
   (`engines/engine_a_alpha/edges/news_sentiment_edge.py:32`); test `test_prod_edge_weight_keys_match_edge_ids`
   passes; add a generic test that every `edge_weights` key matches a registered EDGE_ID.
2. Proposal text (not edits) for: `docs/State/CURRENT_STATE.md` and `health_check.md` HMM entries
   (fixed 08-26; `docs/Audit/backfill_repoint_2026_08_26.md`); CLAUDE.md `[NN-MBL]` "~75" and
   `[NN-SHARPE-CI]` "Politis-White" (code is fixed moving-block n^(1/3), `core/metrics_engine.py:923`);
   `TASK_LEDGER.md:143` T-196 "2 at gate_3" → "2 cleared Gates 1–2, killed by forced Gate 4."
3. `config/substrate_manifest.sha256`: report whether `data/processed/tr_reconciled/*`, VVIX, SKEW,
   Shiller, DFII10 are pinned; if not, the exact `scripts/` command to re-pin and a note that the cloud
   image may lack the 08-26 repoint data until re-baked. Do not re-pin (needs the substrate).
4. One bootstrap: list the three implementations (`metrics_engine.py:864`, `deep_reverify_sleeve_t311.py:139`,
   `excess_of_cash_attribution_t333.py:54`) and propose the single paired-block API they should share.
5. Record correction: Alpaca IRAs cannot hold crypto (search-verified 2026-09-30, alpaca.markets/support
   "can-ira-trade-crypto") — the BTC 5% leg's spec () must state the
   executable vehicle in the Roth is a spot ETF (IBIT; MSBT 0.14%); and IRAs are options Level 2 only.
6.  "$0 short borrow" and the lost branches
   (`feature/factor-neutrality-sizing-t218`, `feature/no-borrow-cash-budget-t232`) recorded in the proposal.

**Acceptance.** Commits land on the branch; proposal doc lists each record change with its verifiable
anchor per the 09-18 design note's "HIGH entries cite a verifiable anchor" rule.

**Commit.** `chore(record): edge-weight key fix + referee record-hygiene proposals (RR-7)`.

---

**Which settled "refuted" verdicts survive the repairs, and which revert to "untested":**
- **Survive (built on the T-306 index substrate with the fair cash convention, paired CIs, not the
  equity backtester):** T-311 sleeve, T-312 gated leverage, T-315 static leverage, T-314 adaptation,
  T-318/T-320 tilts, T-333, T-255/T-259/T-266, T-296 RSST (cash convention correct; wealth gate void
  for a data reason), T-279 PUT, T-282/T-284, T-172/178/220/221 regime (own panel).
- **Revert to UNTESTED under corrected sizing/cash/dividends (RR-1 + RR-5):** every verdict whose
  evidence is an equity-book Sharpe/CAGR through `BacktestController`: the 26-yr 0.751/0.382 baseline,
  T-196 (all 35, plus the two mislabeled), T-215, T-239, T-241, the T-255→T-272 "return-frontier sweep"
  rows that used the equity book, T-122's Δ=0.000 (mechanism still holds; the number does not),
  T-248 HRP (equity-book base leg + pre-T-255 robo cash).
- **Revert to UNTESTED for a different reason (wrong universe, not wrong referee):** T-144 Form 4,
  T-137 8-K, T-145 13F (S&P names only), T-249 small-cap momentum (assumed haircut).
- **Plausibly confounded, one re-run settles:** T-118r (regime overlay on the truncated HMM panel).


## 3.2 The cheapest decisive re-runs (free, ≤ 1 week each, N_trials ≤ 5 each)

Common SETUP for every B brief:
```bash
cd <repo root>
git worktree add .claude/worktrees/<branch> -b <branch> origin/main
cd .claude/worktrees/<branch>
python -m pip install -r requirements.txt -q
# substrate: data/ is a Mac-local / S3 artifact. If absent: aws s3 sync per docs/Cloud/CLOUD_USAGE.md,
# or submit the cell via scripts/submit_substrate_run.py and say so in the audit doc.
python -m pytest tests/test_contracts.py -q
```
Common HARD CONSTRAINTS: pre-registration doc FROZEN (committed, director-acknowledged) BEFORE the
first run — `docs/Sources/prereg_<brief>_<date>.md` in the T-260 format
(`docs/Sources/prereg_deep_reverify_speeds_t260.md`); `[NN-SHARPE-CI]`, `[NN-MBL]`, `[NN-CENSUS]`,
`[NN-FAIL-CLOSED]` apply; NO tuning after seeing results; every arm and every N_trials increment
declared up front; no edits to `engines/engine_b_risk/`, `paper_trader/`, `ops/`, `config/*.prod.json`,
`data/governor/*`; do not push. Audit doc: `docs/Audit/<brief>_verdict_<date>.md` with YAML frontmatter
(`task_id, title, date, author, outcome, status, reproduce`). Determinism ×2 (bit-identical md5) before
any number is quoted. Session summary per `docs/Sessions/_template.md`.

**Referee caveat that applies to every B brief:** until RR-1/RR-5 merge, do NOT run anything through
`BacktestController`. Every brief below is a standalone harness (the T-249 / T-311 / T-318 pattern) with
its own explicit cash, cost, and dividend conventions, so its numbers are honest today.

---

### B-1 — Raw-signal decile re-evaluation of the 35 foundry features + cross-sectional Engine A edges (THE decisive test of "exhausted price vocabulary")
**subagent_type:** edge-analyst · **branch:** `research/raw-signal-decile-b1` · **est. wall-time:** 4–5 days · **N_trials:** +2 (two families: long-only satellite; long/short diagnostic) · **parallel group:** R1 · **overlaps:** none (new script) · **blocked-on:** nothing (RR-3's N_eff only sharpens the DSR line)

**Background.** Every feature ever tested was wrapped as a single-gene long `CompositeEdge`
(`top_percentile 80` or `greater 0`), added to the 6-edge book, and run through the full backtester with
1.8×/2.5× ATR stops, per-bar re-solve, 0% cash, and the RR-1 sizing defect
(`scripts/run_foundry_eval_t195.py:90-107`; `engines/engine_d_discovery/discovery.py:1291-1320`).
T-122 showed uniform timing signals cancel algebraically in the allocator (Δ = 0.000). No feature or
edge was ever evaluated as rank → decile → monthly rebalance. The 35 features are listed in
`core/feature_foundry/features/` (registry: `core/feature_foundry/feature.py:93-131`, per-(ticker, date)
scalar via `Feature.__call__`). Cross-sectional Engine A edges to include: `momentum_12_1_v1`,
`momentum_6_1_v1`, `short_term_reversal_v1`, `low_vol_factor_v1`, `betting_against_beta_v1`,
`overnight_intraday_v1`, `volume_anomaly_v1`, `herding_v1`, `dist_52w_high` (score panels via each
edge's `generate`/`score` on the substrate). Fundamentals-based edges (SimFin ~2020+) run as a separate
short-window sub-arm. Pattern to copy: `scripts/smallcap_momentum_gauntlet_t249.py:50-78` (monthly
top-decile EW) and `scripts/tilt_decision_measure_t318_t320.py:108-172` (blend + regret + rolling CI).

**Deliverables.**
1. `scripts/build_signal_panel_b1.py`: month-end panel of every signal above × PIT S&P 500 members
   (`engines/data_manager/membership.py::members_on`) on the canonical 26-yr equity substrate
   (`data/processed/`, 2000-01 → 2025-12); cache `data/research/b1/signal_panel_<md5>.parquet` with a census
   block (n_signals, n_tickers/month, NaN share per signal; HALT if any signal is > 50% NaN in > 10% of
   months — `[NN-FAIL-CLOSED]`). Both legs PRICE-ONLY from the same files (consistent basis; the
   dividend-yield differential across deciles is a disclosed second-order bias; add a `tr_reconciled`
   arm for the ETF twin only).
2. `scripts/raw_signal_decile_b1.py`: per signal, per month: rank; **Arm L** = top-decile EW long,
   hold one month, 10 bps round-trip; **Arm LS** (diagnostic — a Roth cannot short) = top − bottom decile,
   borrow 50 bps/yr on the short leg. Per signal report: monthly Spearman IC and its Newey-West t (6
   lags); Arm L and LS Sharpe/Sortino with 1000-iter paired block bootstrap (block = 6 months on monthly
   returns); **the goal metric:** Δ log terminal wealth of (75% SPY + 25% Arm L, rebalanced monthly) vs
   100% SPY, paired block-bootstrap `ci_low`; turnover and cost drag in bps/yr; MaxDD.
3. Multiple testing inside the family: BH-FDR at q = 0.05 over the IC t-stats (≈ 45 signals). Report
   the count rejected and the list.
4. Sign-ambiguity rule (frozen): the literature sign is pre-declared for each signal in the prereg
   (momentum +, reversal −, low-vol +, size −, etc.); no flipping after the fact. Calendar features are
   tested as a single dummy-regression sub-family with their T-196 signs.
5. Determinism ×2; audit doc with the full table; a one-paragraph verdict per family.

**Acceptance.** Panel census committed; 45-row table with IC-t, BH-adjusted p, Arm L Sharpe ci_low,
25%-satellite Δ log wealth ci_low; determinism md5 pair; the prereg predicted (a) how many signals
would clear BH at q=0.05 and (b) which three the author expected to be strongest — both compared to
the result in the verdict.

**Pre-registration (frozen before run).** H1: at least one non-calendar signal has BH-adjusted IC p < 0.05
AND 25%-satellite Δ log wealth ci_low > 0 on 2000–2025. **Refutation:** zero signals meet both ⇒
"exhausted price vocabulary" is CONFIRMED on the construction the literature uses — the strongest
negative the project can obtain, and it closes Route A on this universe for good. Window 2000-01→2025-12
(26 yr; DSR-required point SR ≈ 0.55–0.65 at N≈260 for any single arm to be quoted as evidence — the
satellite Δ-wealth ci_low is the gate, the SR line is context). N_trials += 2. Any survivor goes to
RR-6's Gate 1' under the corrected referee; nothing is deployed from this brief.

**Honest prior.** 20% that any signal clears both bars. Momentum (12-1) is the likely survivor as a
long-only satellite — but it is already deployed as MTUM, so the *marginal* discovery value is in
whether anything else does; 8% for a non-momentum survivor.

**Commit.** `feat(research): B-1 raw-signal decile re-evaluation — panel, harness, prereg, verdict`.

---

### B-2 — Small-cap momentum and insider clusters on the T-265 survivorship-complete panel
**subagent_type:** edge-analyst · **branch:** `research/smallcap-t265-b2` · **est. wall-time:** 4–5 days · **N_trials:** +2 (momentum family; insider family) · **parallel group:** R1 · **overlaps:** `data/research/t265/` (read-only) · **blocked-on:** nothing

**Background.** T-249 killed small-cap momentum on a *literature* survivorship haircut, never a
measurement: gross Sharpe 3.21, net Sortino ci_low 0.49 on survivor-only Stooq
(`docs/Audit/smallcap_momentum_gauntlet_t249_2026_06_26.md`). T-265 then built the survivorship-complete
panel (Alpaca SIP 2016-01→2026, 4,674 tickers $50M–$2B incl. pre-2020 delistings; XBRL EPS/shares by CIK;
36% CIK→ticker join loss) and ran only PEAD on it (null). T-144 tested insider clusters on 669 S&P names
and wrote "insider alpha concentrates in small caps; at our universe scale it is priced"
(`docs/Audit/form4_insider_gauntlet_t144_2026_06_10.md:6-8, 61-63`). The SEC structured Form 4 panel
(6.89M rows 2006+, all filers, `data/insider_sec/`, loader `scripts/analyze_form4_clusters_t144.py:69-119`)
has never been joined to T-265. Loaders: `scripts/smallcap_pead_pilot_t265.py::_load_prices` (`:212`),
`stage_map` (`:117`). The project's map ranks these #13 and #4.

**Deliverables.**
1. **Momentum arm** (`scripts/smallcap_momentum_t265_b2.py`): universe = T-265 names with median 20-day
   dollar ADV ≥ $1M at formation; signal = 12-1 month return; monthly top-decile EW long, one-month hold;
   delisting handling FROZEN: bankruptcy/deregistration codes → −100% on the delisting month; other
   delistings → Shumway (1997) −30% unless a last trade price exists; costs by ADV bucket: 35 bps RT
   ($20M–$200M), 75 bps RT ($1M–$20M); ADV cap 2% per name. Twins: IWM total return and SPY total return
   (`tr_reconciled`). Report: standalone Sharpe/Sortino ci_low; **25%-satellite Δ log wealth vs SPY**
   paired ci_low; the stress arm with all delistings at −100%.
2. **Insider arm** (`scripts/smallcap_insider_t265_b2.py`): join `data/insider_sec/` to T-265 by CIK
   (not ticker — avoids the 36% loss); open-market purchases only (transaction code P, exclude 10b5-1
   flagged, exclude option exercises); **cluster** = ≥ 3 distinct insiders buying within 30 calendar days,
   Cohen-Malloy-Pomorski opportunistic filter (drop insiders whose buys fall in the same calendar month
   in ≥ 3 prior years); event study on CAR(0,126) with Newey-West t, PIT-formed on the filing acceptance
   date + 1; portfolio: EW, 6-month hold, 75 bps RT, cap 40 names; twin IWM TR over the same windows;
   satellite Δ log wealth vs SPY at 25%. Census: clusters/yr, names/yr, share of universe with any Form 4.
3. Both arms: determinism ×2; audit doc; **do not** run PEAD × insider here (that is the conditional
   brief C-1 and only if this insider arm shows t_HAC > 2 on CAR).

**Acceptance.** Both scripts run from cached T-265 stages; census blocks; the momentum table with the
survivor-only T-249 number beside the survivorship-complete number (the haircut, MEASURED); insider
event-study table by cluster size {3, 4, 5+}; both satellite ci_lows; determinism.

**Pre-registration.** Momentum H1: 25%-satellite Δ log wealth ci_low > 0 vs SPY-TR on 2016-01→2026-06
with delistings at the frozen rule. Refutation: ci_low ≤ 0 in the base arm ⇒ T-249's kill stands,
now measured. Insider H1: CAR(0,126) t_HAC > 2.0 for clusters ≥ 3 AND satellite ci_low > 0. Refutation:
t_HAC < 2 ⇒ insider clusters are priced in small caps too — close the region. 10-year window: any
standalone SR quoted must carry the DSR line (≈ 0.9 at N≈260, 10 yr) as context; the satellite paired
ci_low is the gate. N_trials += 2.

**Honest prior.** Momentum 30% (the literature's survivor, but 10 years, one regime, and the cost model
binds); insider 30% (the cleanest free-data event signal on the map; decay post-2016 documented).

**Commit.** `feat(research): B-2 small-cap momentum + insider clusters on the survivorship-complete panel`.

---

### B-3 — CEF discount capture: satellite and beta-matched backtest variants + the forward shadow book
**subagent_type:** edge-analyst (backtest) then quant-dev (book) · **branch:** `research/cef-variants-b3` · **est. wall-time:** 3 days + the book · **N_trials:** +1 (backtest family); 0 (forward book) · **parallel group:** R1 · **overlaps:** `paper_trader/` — the book is a NEW file; brief writes it but does NOT wire it into `run_paper_cloud_day.py` (director wires) · **blocked-on:** nothing

**Background.** T-267: the only t_HAC > 2 alpha in project history (2.31 on 2004–2026, 25 liquid CEFs,
monthly long cheapest quintile, 20 bps RT; MaxDD −42.7%; post-2011 t 0.90; Sortino 1.28 ci_low 0.55;
`docs/Audit/cef_lowerbound_probe_verdict_t267_2026_07_02.md`; harness `scripts/cef_lowerbound_probe_t267.py`;
panel `data/research/cef_panel_t267.parquet`). Parked for MDD and "no retail PIT data path." The
beta-hedged and satellite variants were never run (beta 1.30 was only netted in a regression). The T-334
daily panel (`data/macro_data/alt/cef_daily.parquet`, 361 funds × 30 fields since 2026-07-29) is accruing
and a forward book was dispatched and never built (`CURRENT_STATE.md:36`; 09-17 audit §2.2). Shadow-book
pattern: `paper_trader/event_shadow_book.py` (`DeskConfig`, signal-t / fill-t+1, twin, promotion gates).

**Deliverables.**
1. **Satellite arm:** 90% SPY-TR + 10% cheapest-quintile CEF book (monthly, 20 bps RT, T-267 construction
   unchanged) vs 100% SPY-TR: paired Δ log wealth ci_low, ΔSortino ci_low, MaxDD both. Same at 5%.
2. **Beta-matched twin (a Roth cannot short, so no hedge):** compare the CEF book against a twin with
   the same realized beta built from SPY + cash (β̂ from the T-267 regression, re-estimated rolling
   36 months, PIT); report alpha as the paired difference — the honest "is it the discount or the
   leverage."
3. **Forward shadow book** `paper_trader/cef_shadow_book.py` on the T-334 panel: entry when discount
   z-score < −1.5 vs the fund's own trailing 252-day distribution AND 30-day ADV ≥ $500k; EW across
   qualifying funds capped at 20; exit at z > 0 or 12 months; 25 bps/side; signal-t / fill-t+1 close;
   TWINS: SPY-TR and an EW all-CEF-universe twin (the honest "is it discount selection or CEF beta");
   falsifier and evaluability below; report-only, `DeskConfig`-parameterized, fail-closed on missing NAV.
   Unit tests mirroring `tests/` for the event book.

**Acceptance.** Backtest table (standalone / 5% / 10% / beta-matched) with ci_lows; determinism; the
book runs on the cached panel with a first artifact observed (a state file with ≥ 1 qualifying fund or
the explicit "0 qualify today" line) — `[NN-FIRST-ARTIFACT]`; the falsifier is in the book's docstring.

**Pre-registration.** Backtest H1: 10%-satellite Δ log wealth ci_low > 0 vs SPY-TR on 2004–2026.
Refutation: ci_low ≤ 0 at both 5% and 10% ⇒ the alpha is real but too small/too correlated to move
terminal wealth — record and keep only the forward book. Forward book: twin = EW CEF universe; falsifier
= after 36 months of record, paired diff ci_low vs the EW-CEF twin ≤ 0; **evaluability date 2029-10-01**
(monthly signal; 36 months is the minimum for any power — stated so nobody reads month 6). N_trials: +1 / 0.

**Honest prior.** 35% that the 10% satellite clears (the alpha exists; the question is only size and
correlation); 25% that the forward book beats its CEF twin by 2029 (post-2011 t was 0.90).

**Commit.** `feat(research): B-3 CEF satellite/beta-matched arms + report-only forward shadow book`.

---

### B-4 — One frozen nonlinear cross-sectional ranker (Gu-Kelly-Xiu 2020 class) with combinatorial purged CV
**subagent_type:** ml-architect · **branch:** `research/xsec-gbm-ranker-b4` · **est. wall-time:** 5 days · **N_trials:** +2 (S&P PIT arm; T-265 small-cap arm) · **parallel group:** R2 (after B-1's panel exists — reuse it) · **overlaps:** `data/research/b1/` (read) · **blocked-on:** B-1 deliverable 1

**Background.** The only nonlinear test ever run was T-149: HistGradientBoosting vs ridge over **8
existing edge signals**, 109 tickers, 2021–24, 1-day target, CPCV 15 paths — ridge won, IC 0.006
(`scripts/metalearner_falsification_t149.py:14-40, 87-104`). The literature model class (monthly
horizon, raw characteristics, tree ensembles, expanding refit, purged CV) has never been run. The
"price vocabulary is exhausted" claim was made without it. Evidence to weigh in the prereg: Gu-Kelly-Xiu
(2020) alpha concentrates in microcaps and short legs; Avramov-Cheng-Metzker (2023) show it collapses
after excluding microcaps/distressed names and after costs.

**Deliverables.**
1. Feature matrix: the B-1 monthly panel (35 foundry + Engine A cross-sectional scores) + standard
   price/volume characteristics (size, 12-1, 6-1, 1-month reversal, 60d vol, idio vol, beta, dollar
   volume, turnover, MAX5, 52w-high distance, Amihud); SimFin fundamentals ONLY in a 2020+ sub-arm.
   Cross-sectional rank-normalize monthly; target = next-month excess return rank.
2. **ONE frozen spec** (pre-registered, never tuned): LightGBM, 500 trees, depth 4, lr 0.03,
   min_child_samples 200, subsample 0.8, colsample 0.8, seed 0; expanding-window annual refit; 1-month
   embargo; CPCV with 8 groups / 2 test groups for the OOS estimate (T-149 pattern); ridge baseline with
   the same folds.
3. Portfolio: top-decile EW long-only monthly (10 bps RT S&P; 35/75 bps small caps); LS diagnostic.
   Report OOS Spearman IC with HAC t, decile spread, standalone Sharpe ci_low, **25%-satellite Δ log
   wealth ci_low vs SPY-TR**, and the GBM − ridge paired difference.
4. Arms: (a) PIT S&P 500 2000–2025; (b) T-265 small caps 2016–2026 (delisting rule from B-2).

**Acceptance.** Determinism ×2 (LightGBM `deterministic=True`, single thread); the prereg names the
expected IC (author's guess) before the run; audit doc with the fold-level IC distribution, not just the
mean; feature-importance table (diagnostic only).

**Pre-registration.** H1: OOS IC HAC-t > 2.5 AND GBM − ridge IC difference > 0 with ci_low > 0 AND
25%-satellite Δ log wealth ci_low > 0 in arm (a). Refutation: any of the three fails in arm (a) ⇒
nonlinear ML on this vocabulary is H0 for a long-only large-cap holder — the ML question closes.
Arm (b) reported the same way. N_trials += 2. The model is NOT deployed; a pass sends the ranker to
RR-6's Gate 1' as a candidate.

**Honest prior.** 12% for arm (a) (the literature says the alpha is not in long-only large caps);
25% for arm (b).

**Commit.** `feat(research): B-4 frozen GBM cross-sectional ranker with CPCV — two universe arms`.

---

### B-5 — Route C re-test: levered diversified portfolio vs 1× SPY under HONEST Roth financing
**subagent_type:** regime-analyst · **branch:** `research/levered-diversified-b5` · **est. wall-time:** 3 days · **N_trials:** +1 (one family; financing spread is a characterization sweep, not a selection) · **parallel group:** R1 · **overlaps:** `scripts/deep_reverify_sleeve_t311.py` (import, do not edit) · **blocked-on:** nothing

**Background.** HRP (T-248) ran on 2019–23 with an equity-book base leg "that leans on shorts a cash Roth
can't do" and pre-T-255 cash conventions; RSST (T-296) ran on the fair harness but its wealth gate was
void (AQR over-capture). Neither asked the operator's question: with leverage available ONLY through
daily-reset levered ETFs (SSO/UPRO/UBT/TMF-class, or NTSX/RSSB-class stacked funds), at their embedded
financing (≈ 3-month rate + a swap spread) plus expense ratio plus volatility decay, does a 1.5× diversified
book beat 1× SPY on terminal wealth, and at what financing spread does it stop? Substrate: T-306
(`data/research/substrate_multidecade/`: equity_tr 1926+, bond_tr 1962+, gold_tr 1968+, cash = FF RF)
with the T-311 conventions (`scripts/deep_reverify_sleeve_t311.py:55-130`).

**Deliverables.**
1. Levered-ETF simulator: `r_L = L·r_underlying − (L−1)·(cash + spread) − ER`, daily reset (quarterly
   for NTSX-type). FROZEN inputs (02_route_research §Route C, search-verified 2026-09): swap spread
   s = 50 bp over DTB3 (pre-2018) / SOFR (2018+), sweep 0–400 bp as characterization; ER: NTSX 0.20%,
   RSSB 0.41%, RSST 1.00%, SSO 0.89%, UBT 0.95%, UPRO 0.90%, TMF 0.90%; 5 bp per rebalanced dollar.
   Validate the synthetic against live SSO (2006+), UPRO/TMF (2009+), NTSX (2018+), RSSB/RSST (2023+)
   overlap before extending back; report the tracking error of the synthetic.
2. Arms (all vs 1× equity_tr): (i) NTSX-synthetic 90/60; (ii) RSSB-synthetic 100/100; (iii) 1.9×
   equal-risk equity/bond/gold at inverse-vol weights, monthly (the RP-at-SPY-vol arm); (iv) 100% equity
   + 50% SG-CTA overlay at T-bill + 50 bp and 1.0% ER (the RSST-class trend overlay; SG CTA monthly
   2000+, AQR TSMOM 1985+ for the deep window) and the same at 25%; (v) 1× 60/40 unlevered control.
   Windows: 1972–2025 (gold floats) and 2000–2025; report Δ on ρ(stock, bond) > 0 sub-samples and the
   2022 window separately. Break-even arithmetic to reproduce in the doc: Δ(1.5×60/40 − SPY) ≈ 0.6·T −
   0.1·E − 0.5·s − ER; break-even SR_rp ≈ (E + 0.9·s + ER)/16.2.
3. Metric: paired block-bootstrap Δ log terminal wealth vs 1× equity, 21-day blocks, 1000 iter; MaxDD;
   the **break-even spread** at which arm (ii)'s ci_low crosses 0 (sweep spread 0–400 bps; reported as
   a curve, not a pick).

**Acceptance.** Determinism; the curve; a sentence stating whether financing is the binding constraint
(if break-even spread < the current embedded spread, it is).

**Pre-registration.** H1: arm (ii) at the current embedded spread has Δ log wealth ci_low > 0 vs 1× SPY
on 1968–2025. Refutation: ci_low ≤ 0 at the current spread ⇒ Route C is closed for a levered-ETF Roth
holder; the break-even curve is the record. N_trials += 1.

**Honest prior.** 15% (NTSX/RSSB arms), 20% (RP arm), 25% (trend-overlay arm), 0% for any
SSO/UBT/TMF construction. The 2022 correlation flip and the post-2009 term-premium collapse cut against
the bond arms; the operator's own T-315 result (1.25× SPY significantly loses) is the base rate; the
trend overlay is the one arm whose leg has a positive standalone return rather than an insurance cost.

**Commit.** `feat(research): B-5 levered diversified book vs 1x SPY under retail financing — break-even curve`.

---

### B-6 — Lazy Prices: repair the panel, add 10-Q, run long AND short legs on S&P PIT and T-265
**subagent_type:** ml-architect · **branch:** `research/lazy-prices-repair-b6` · **est. wall-time:** 5 days (3 parsing) · **N_trials:** +2 · **parallel group:** R2 · **overlaps:** `scripts/lazy_prices/`, `data/edgar/` · **blocked-on:** nothing

**Background.** T-237 ran long-only top-tercile non-changers on S&P PIT-691, annual, 2006–2025, and left
no verdict doc ("leaning H0" in three secondary docs). T-341b diagnosed the panel: 10-K only (no 10-Q),
15.1% parse failures, 2006 rows 98.4% fail (Item 1A not required pre-Dec-2005), 15 mega-caps 100%
Item-7 failure; repair specified, not applied (`docs/Audit/similarity_parser_diagnosis_t341b_2026_08_15.md`).
Cohen-Malloy-Nguyen (2020) alpha concentrated in the SHORT leg and in low-attention names; the project
never tested either. EDGAR full-text search + the T-265 CIK universe give the small-cap arm.

**Deliverables.** (1) Apply the T-341b repair; add 10-Q (Items 1A/2 → cosine + Jaccard on the prior
same-form filing); census of parse coverage per year. (2) Re-run T-237's construction (quarterly rebalance
now) on S&P PIT, reporting long non-changers, short changers (diagnostic), and 25%-satellite Δ log
wealth. (3) T-265 small-cap arm 2016–2026 with 75 bps RT. (4) Loughran-McDonald tone change as a second
pre-declared signal in the same family (not a third trial).

**Pre-registration.** H1 (S&P): long-leg 25%-satellite Δ log wealth ci_low > 0. H1 (T-265): same.
Refutation: both ≤ 0 AND short-leg t_HAC < 2 ⇒ Lazy Prices is H0 on free data for this operator —
record as the first verdict doc T-237 never got. N_trials += 2. **Honest prior.** 12% / 20%.

**Commit.** `feat(research): B-6 Lazy Prices panel repair (10-K+10-Q) and two-universe re-run`.

---

### B-7 — T-118r regime overlay re-run on the repointed HMM panel (closes the one confounded regime verdict)
**subagent_type:** regime-analyst · **branch:** `research/t118r-rerun-b7` · **est. wall-time:** 1 day · **N_trials:** +1 · **parallel group:** R1 · **overlaps:** `scripts/analyze_t118r.py` · **blocked-on:** verifying `data/processed/tr_reconciled/` is present on the runner (RR-7 §3)

**Background.** T-118r's overlay fired only in 2022 and 2025 with +0.0 in GFC/COVID
(`docs/Audit/hmm_overlay_rerun_t118r_2026_06_14.md:40-60`) — the signature of a uniform posterior from
the truncated TLT panel (82% NaN `tlt_ret_20d`), attributed at the time to the Δ-trigger. The panel was
repointed 2026-08-26 (`engines/engine_e_regime/macro_features.py:156-173`; 60.3% complete rows from
2006-04-04). T-172/178/220/221 used their own panel and are unaffected.

**Deliverables.** Re-run `scripts/analyze_t118r.py` unchanged on the repointed panel; census the
posterior (share of bars with p_crisis ∈ (0.2, 0.8), and non-uniform bars pre-2020); report the same
table as the original beside it.

**Pre-registration.** H1: the overlay's paired Δ vs the unconditioned sleeve has ci_low > 0 on 2006–2026.
Refutation: ci_low ≤ 0 with a non-uniform pre-2020 posterior ⇒ T-118r's refutation stands, now on honest
inputs. N_trials += 1. **Honest prior.** 15% (T-172/178/220/221 already refuted the mechanism on clean
inputs).

**Commit.** `feat(research): B-7 T-118r re-run on the repointed HMM panel`.

---

### B-8 — Index-level overnight/close execution-timing overlay for the monthly rebalancer (Route J, cheap)
**subagent_type:** edge-analyst · **branch:** `research/execution-timing-b8` · **est. wall-time:** 1–2 days · **N_trials:** +1 · **parallel group:** R2 · **overlaps:** none · **blocked-on:** nothing

**Background.** The project measured its own fills at 0.26–1.02 bps and noted the overnight split as an
execution-timing candidate (Lou-Polk-Skouras 2019). T-135 refuted the single-name L/S overnight factor
at large-cap; this is not that. Question: for a monthly core+satellite rebalancer at Alpaca, does
executing buys at the close (capturing the overnight leg) vs at the open, and rebalancing on
turn-of-month day −1 vs +1, change terminal wealth by more than the measured cost?

**Deliverables.** On SPY/VOO/MTUM/SGOV daily OHLC (2000–2025 where available): simulate the deploy
candidate's monthly flow under {open, close} × {TOM −1, 0, +1} execution; report Δ log wealth vs the
baseline (close, day 0) with a paired bootstrap; bps/yr. Cross-check against the paper fleet's own
fill journal (`paper_trader/` order journals on S3 — read-only) for realized open-vs-close slippage.

**Pre-registration.** H1: one cell beats baseline by ci_low > 0 bps/yr. Refutation: none does ⇒
execution timing is noise at this turnover — record and stop. N_trials += 1. **Honest prior.** 15%;
if positive, ≤ 20 bps/yr — free, compounding, and small.

**Commit.** `feat(research): B-8 execution-timing cells for the monthly rebalancer`.

---

### B-9 — Multi-factor combination tilts at deployable weights (the missing power test)
**subagent_type:** regime-analyst · **branch:**  · **est. wall-time:** 2 days · **N_trials:** +1 (one family; four pre-declared arms jointly reported, arm (i) is the decision arm) · **parallel group:** R1 · **overlaps:**  (extend, do not fork) · **blocked-on:** nothing

**Background.** T-318/T-320 tested single tilts (momentum CI-significant at 15–20%; quality and
small-value straddle). A 20% single tilt with 2%/yr long-only alpha and 8% tracking error has t ≈ 1.3
on 26 years — underpowered by construction. Two 20% tilts with ρ ≈ −0.3 (value × momentum, Asness-
Moskowitz-Pedersen JF 2013) give α 0.8%/yr at TE 1.9% → t ≈ 2.2: same alpha per tilt-dollar, twice
the power. Never run. Harness:  (blend, regret, rolling
CI); legs  (); French factors  ().

**Deliverables.** Arms (FROZEN, no further weight search): (i) 60/20/20 VOO/MTUM/AVUV; (ii) 70/15/15;
(iii) 80/20/0 (current deployment); (iv) 80/0/20. Pre-2013 MTUM = French big-high-momentum
portfolio; pre-2019 AVUV = French small-value-robust-profitability; 50% haircut on French-era alpha
(long-only ETFs capture ≈ half of the academic L/S premium, Novy-Marx-Velikov); ER 0.03/0.15/0.25%;
5 bp per rebalanced dollar; annual rebalance; window 2000-01→2026-06; secondary French-only
1963→2026 sign test. Metric: paired Δ log TW vs 1× SPY-TR, block bootstrap ci_low; regret table as in
T-318; DSR line at N ≈ 264 reported.

**Acceptance.** Determinism ×2; the four-arm table; the prereg's predicted t for arm (i) beside the
measured one.

**Pre-registration.** H1: arm (i) ci_low > 0. Refutation: arm (i) ci_low ≤ 0 ⇒ multi-factor closed,
momentum stays at 15%. N +1. **Prior 25%.**

**Commit.** .

---

### B-10 — Gold 10% permanent leg (one trial, then a forward twin)
**subagent_type:** regime-analyst · **branch:**  · **est. wall-time:** 1 day · **N_trials:** +1 · **parallel group:** R2 · **overlaps:** T-306 substrate (read) · **blocked-on:** nothing

**Background.** Stock-bond correlation +0.52 in 2022; WGC 2025: the risk-minimizing gold weight rises
in positive-correlation regimes; Erb-Harvey (FAJ 2013; SSRN 5525138, 2025): long-run real return ≈ 0
and post-ATH multi-year returns low — gold is at/near ATH in 2025–26. The sleeve already holds GLD
inside a timing rule; a permanent 10% leg has never been scored on terminal wealth. Substrate:
 (1968+), IAUM 0.09% ER (splice LBMA → GLD → IAUM).

**Deliverables.** 90% core / 10% gold, monthly rebalance, 1971–2026 and 2000–2026; paired Δ log TW vs
1× SPY ci_low; MDD both; the 2022 window. Then a forward twin (core without gold) on the existing
 shadow pattern, evaluability 2028-09-30.

**Pre-registration.** H1: ci_low > 0 on the full window AND MDD reduction ≥ 3 pp. Refutation: ci_low
< 0 on the full window OR on 2000–2026 alone. N +1. **Prior 25%** — the hedge case is strong, the
wealth case thin.

**Commit.** .

---

### Conditional briefs (dispatch only on the named trigger)
- **C-1 PEAD × insider interaction** on T-265 — trigger: B-2 insider arm CAR t_HAC > 2. N +1.
- **C-2 T-216 3-way conjunctive selector on the deep window** — trigger: any B-1 survivor. N +1.
- **C-3 Jump model (Nystrup et al.; arXiv 2402.05272) as a drop-in for the HMM feeding T-252's
  consumer** — trigger: B-7 shows a non-uniform posterior still fails; no re-opening of regime gating
  (T-220 stands). N +1.
- **C-4 Multi-factor satellite combinations** (60 VOO / 20 MTUM / 20 QUAL-or-small-value) at deployable
  weights — trigger: §2 Route B evidence that combinations beat single tilts post-2020; run on the
  T-318/T-320 harness (`scripts/tilt_decision_measure_t318_t320.py`). N +1.


## 3.3 Forward shadow books at 0 N_trials (report-only; the `paper_trader/event_shadow_book.py` / `dbmf_shadow.py` pattern)

Common rules. Every book: signal-t / fill-t+1 close; a pre-stated TWIN; a pre-stated FALSIFIER with an
EVALUABILITY DATE below which nobody reads the number; costs charged at the venue's honest level; fail
closed on a missing input (park, never guess); zero effect on orders; `[NN-FIRST-ARTIFACT]` — the brief
is not done until the first state file has been observed. **Any book that needs a NEW external feed
(Binance/Bybit funding, SqueezeMetrics, Alpaca options data, HuggingFace weights) is propose-first under
CLAUDE.md "new external services" — the brief builds the reader behind a flag and the director rules on
enabling it.** `subagent_type: quant-dev` unless stated. Each book ships with unit tests mirroring the
event book's and a docstring carrying twin / falsifier / evaluability verbatim.

| Book | Spec | Twin | Falsifier | Evaluability | New feed? | Prior |
|---|---|---|---|---|---|---|
| **F-1 CEF discount book** | see B-3 §3 — z < −1.5 vs own 252-day, ADV ≥ $500k, ≤ 20 EW, exit z > 0 or 12 mo, 25 bps/side, on the accruing T-334 panel | SPY-TR and EW all-CEF universe | after 36 months, paired diff ci_low vs the EW-CEF twin ≤ 0 | **2029-10-01** | no (T-334 accrues) | 25% |
| **F-2 RSST 20% stack** | 20% of the core replaced by RSST (100% equity + 100% managed futures); daily NAV | SPY-TR | ci_low(Δ log wealth) < 0 at 24 months | **2028-09-30** | no (NAV via existing price fetch) | 35% |
| **F-3 DBMF/KMLM blend** | the accruing 5% DBMF leg → 50/50 DBMF/KMLM | DBMF-only leg | after 24 months, blended Δ log wealth ci_low < 0 vs twin AND blended MDD not lower | **2028-09-30** | no | 20% vs SPY; 60% for MDD ≥ 5 pp |
| **F-4 IBIT funding-rate de-risk** | IBIT 5% leg → 0% when 7-day mean Binance+Bybit BTC funding ≥ 0.05%/8h (~55% ann.), else 5% (BIS "Crypto Carry": high carry predicts crashes) | unconditioned IBIT leg | after 365 days, ci_low < 0, or < 3 de-risk episodes (unevaluable → extend) | **2027-09-30** | **yes** (Binance `fundingRate`, Bybit `funding/history`; venue-survivorship census) | 25% |
| **F-5 IV-conditioned covered calls on IBIT** | 30–45 DTE, 20–30-delta call sold only when 30-day IV percentile ≥ 80% AND IV−RV ≥ 5 pts; Level 1 legal in the IRA | unconditioned IBIT leg | after 12 monthly cycles, ci_low < 0 OR overlay short in ≥ 2 of the 3 largest up-months | **2027-10-31** | **yes** (Alpaca options: indicative feed as trigger, >15-min OPRA history as mark; log the discrepancy) | 20% |
| **F-6 GEX regime conditioner** | vol-target multiplier halved on days SqueezeMetrics GEX ≤ trailing-252 20th pct; optional one-trial backtest 2011–26 first ("neg-GEX-day RV ≥ 1.3× other days", N +1) | unconditioned core | after 250 trading days, ci_low < 0 OR conditional-RV ratio < 1.2 | **2027-10-15** | **yes** (SqueezeMetrics daily CSV, 2011-05+, true PIT) | 25% |
| **F-7 Long small-cap earnings straddles** | Alpaca-optionable $300M–$3B, confirmed earnings date, NBBO straddle spread ≤ 8% of mid; long call + long put at t−3 close, exit first open after; 1.5% NAV each, ≤ 8 concurrent; cost = paid spread from OPRA history + per-contract fee | same cash in SPY | after 200 events, mean net straddle return ci_low ≤ 0 OR book Δ log wealth ci_low < 0 | **2027-06-30** | **yes** (Alpaca options data) | 15% |
| **F-8 ChronoBERT small-cap tone book** (`subagent_type: ml-architect`; SEPARATE AI track under `[NN-AI-GATE]`, never integrated) | Russell-2000-like (price > $5, ADV > $2M); ChronoBERT-realtime (vintage Y−1) mean-pooled tone on the Benzinga panel, 21-day aggregation, ridge head fit on an expanding window ending before the scoring date; long-only top decile EW, ≤ 25% | same-universe EW book without the overlay | ci_low(Δ) ≤ 0 after 24 months of fills OR turnover > 150%/yr | **2028-10-01** | **yes** (HF `manelalab/chrono-bert-v1-*`, MIT; PIT-4B `Diamegs/PIT-4B-*` for monthly vintages) | 10% |
| **F-9 Opportunistic-insider book** | T-334 Form-4 daily index (accruing since 07-29) parsed to transactions; ≥ 2 opportunistic (CMP routine filter) open-market buyers in 30 days, price > $5, ADV > $1M, hold 3 months EW ≤ 25%, 5 bps one-way large / 60 bps small | same-universe EW without the screen | ci_low(Δ) ≤ 0 after 24 months | **2028-10-01** | no (index accrues; XML parse is new code) | 20% |
| **F-10 Execution-shortfall KPI** (not a book) | per-order implementation shortfall vs arrival mid, by order type × TIF × time-of-day, REAL accounts only (paper fills at the quote); LOC at close for integer shares, day-limit near the close for fractional | marketable-order IS | LOC/limit IS not ≤ marketable IS over ≥ 500 fills | when 500 real fills exist | no (order journals on S3) | 60% the KPI shows the saving; ~0% visible in ci_low TW |

Honesty about clock length: none of F-1…F-9 is evaluable inside the operator's 12-month horizon;
F-4/F-5/F-6/F-7 read in late 2027, the rest in 2028–29. They are cheap and they are the only honest
instrument for options, crypto, and text — but they cannot answer this year's question.

## 3.4 The "if one paid dataset opens" tier

None of these is recommended today. Each has a named trigger from a free brief; the operator's stated
rule (free-only; "a blocked frozen prereg is the trigger to re-ask with a concrete case") is followed.

| # | Dataset | Price (search-verified 2026-09) | Frozen pre-registration it unblocks | What the money buys | Trigger |
|---|---|---|---|---|---|
| **P-1** | **Norgate Data Platinum US** — survivorship-free EOD to 1990, delisted names, PIT Russell 2000 / S&P 600 / 400 membership; Windows NDU + `norgatedata` | **$346.50 / 6 mo; $630 / yr (unchanged)** | B-2 extended: small-cap 12-1 momentum top-decile EW long-only on PIT Russell 2000, 1990–2026, delisting returns included, 60/120 bps, 25% satellite Δ log TW ci_low > 0 vs SPY-TR; and the same window for E1 insider clusters (Form 4 2006+) and E5 deletions (S&P 400/600). N +1 each | A 36-year window drops the DSR-required point SR from ≈ 0.9 (10 yr) to ≈ 0.5 — the only way a small-cap satellite can ever be quoted as deployment evidence under `[NN-MBL]`. Also removes the 36% CIK→ticker join loss | B-2's 2016+ momentum or insider arm returns ci_low > −0.10 (not clearly dead). The project's own sequencing rule: "$0 pilot first; Platinum only to EXTEND a live signal" |
| **P-2** | **Point-in-time options surface**: ORATS ($199/mo delayed; no free tier now) or Databento OPRA historical (pay-as-you-go ~$0.04/GB; a year of EOD chains for a few hundred small caps is small) | ~$200–600 one-time (Databento) or $199/mo (ORATS) | G4: single-stock IV-percentile / term-slope conditioning of the F-7 straddle universe (buy only when IV-pct < 40 and term slope inverted), 2019–2026, N +1, H1 "conditioned straddles ≥ 2× unconditioned mean return, ci_low > 0" | The one Route-G test that is executable at Level 2 AND has a backtestable history. Nothing else on Route G is worth paying for at this account size | F-7 shows mean net straddle return ci_low > −1% after 200 events |
| **P-3** | **CBOE DataShop SPX EOD option chains** | ~$100–300 per year of history (MEM) | D4: VIX-term-structure-gated 5–10% OTM put-spread overlay at fixed delta vs the free PPUT proxy, 2008–2026, N +1 | Whether a gated, defined-risk hedge can be terminal-wealth neutral (the free proxy can only say "not clearly dead") | the free PPUT×VIX3M/VIX blend in B-5's secondary sign test shows ci_low > −0.02 |
| **P-4** | **Sharadar SF1/SEP** (PIT fundamentals `datekey`, delisted-inclusive prices 1998+) | ≈ $69/mo ($499/yr) — conflicting listings; unverifiable live | B-4 arm (a) with PIT fundamentals pre-2020 (value/quality/accruals characteristics rebuilt on `datekey`); T-318/T-320-class tilts with PIT screens | Removes the SimFin ~2020+ wall and the FSDS rebuild labor | B-4 arm (b) IC HAC-t > 2 on price-only features (the model class works somewhere) |

Make-or-refute on the obvious two: **Norgate — make the case, conditionally.** It is the only purchase
that changes what `[NN-MBL]` allows the project to *say* about a small-cap satellite, and it is cheap;
but it is worthless if B-2's free 10-year pilot is clearly dead, so the pilot goes first. **Options
surface — refute for now.** The wrapper allows only long options; the literature that said buying pays
was just deflated by an order of magnitude (DJKMW 2026); the forward book F-7 is the honest first step
and costs nothing.

## 3.5 The honest prior

**Probability that this program yields a deployable portfolio with `ci_low(terminal wealth vs SPY) > 0`
on the honest substrate within 12 months: about 25%.** Reasoning. The referee has two defects that
invalidate every equity-book number and one that made Discovery unable to promote anything; fixing them
is necessary but is not evidence — it re-scores, it does not discover. Of the free backtests, the ones
with a genuine chance are the two capacity-bounded niches on the right universe (insider clusters and
small-cap momentum, ~30% each but positively correlated through small-cap beta and a single 10-year
regime), the CEF satellite (~35%, the only t > 2 alpha, decaying post-2011), and the combination-tilt
test (~25%). Even a REAL 25% satellite with 2–4%/yr excess and 8–10% tracking error has t ≈ 1.5–2 on
26 years, so the paired ci_low sits near zero when the effect is true — the bar is structurally hard
for small satellites, and the project's own base rate for pre-registered families clearing ci_low is
roughly one in ten. Everything on options, crypto, and text is forward-only with evaluability in
2027–29, so it cannot answer within 12 months. The wrapper (IRA: no shorts, no margin, no futures,
Level 2, no crypto) removes the half of the alpha map that institutions cannot occupy *because* it
needs those instruments. Net: ~25% that one satellite clears at deployable weight under the corrected
referee; ~50% that the referee repairs land, B-1 confirms the price-vocabulary H0 on the right
construction, and one or two satellites show points-win/CI-straddle — at which point "the 15% tilt is
the ceiling and the real levers are contribution rate, wrapper, and cost" becomes an EARNED statement
rather than an assumed one; ~25% that nothing clears and the CEF alpha is gone. The base rate for retail
systems beating SPY net of costs is low, and this one starts from a candidate that is SPY plus a tilt.
But the current H0 was produced by a referee with two critical defects, on the wrong universe, through
machinery that would kill most real signals — so the 25% is not a guess dressed as a number; it is the
probability that the first honest test of the right things comes back positive.
