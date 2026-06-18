# External Fresh-Eyes Gap Assessment — ArchonDEX (2026-06-18)

**Author:** independent capability/gap audit (commissioned via the "Fresh-Eyes Gap
Analysis" prompt). No prior involvement, no stake in the conclusions.
**Method:** five parallel forensic passes — production-path trace, Engine A alpha
breadth, execution/risk/live path, measurement rigor & alpha-vs-beta, and D/E/F +
overbuild — each verifying **code against claims**, plus direct reads of the configs,
`GOAL.md`, and the builders' own same-day `docs/State/capability_gap_drawing_board_2026_06_18.md`.
All findings are code-verified, cited `path:line`. Where this agrees with the builders'
own doc it says so; the value-add is independent verification plus the blind spots that
doc cannot see from the inside.

> **Relationship to the builders' drawing-board doc:** that doc is unusually honest and
> pre-empts much of the standard critique (closet-beta, survivorship, refuted edges,
> the regime-conditional door). This assessment confirms those claims against code and
> then goes one level up — to the structural blind spots that an insider doc, however
> candid, is least able to surface.

---

## 0. One-line verdict

A **rigorously-instrumented, honestly-measured, risk-managed beta machine with no
validated alpha** — and its own instruments say exactly that. The engineering
discipline (measurement, execution realism, paper infra) is real and rare. The stated
goal ("perform like a quant desk," "significantly outperform the market") is, with high
confidence, **unreachable in this design space** (retail, equity-only, daily-bar, small
AUM, retail data), and the project has already done the expensive work of proving it.
The honest reading of its own evidence: **risk-managed beta is the ceiling; the money
should stay in the robo.**

---

## 1. What the system actually does (production path)

`scripts/run_backtest.py` → `ModeController.run_backtest()` → `BacktestController.run()`
(`orchestration/mode_controller.py:1005`):

- **Data** — `DataManager.ensure_data`; a **static 109-ticker survivor list**
  (`config/backtest_settings.json:5-114`), daily bars, 365-day warmup.
- **Signals** — `AlphaEngine.generate_signals` (`engines/engine_a_alpha/alpha_engine.py:716-950`)
  → `SignalCollector` fires ~20 edges → `SignalProcessor` (tanh-normalize, trend/vol
  micro-regime gates, ensemble shrink λ=0.35) → aggregate to long/short/none. **Edge
  weights are hand-set static values** in `config/alpha_settings.prod.json:32-58` — not learned.
- **Portfolio** — signal→weight (inverse-vol/equal); HRP only if dynamic-opt enabled
  (default OFF).
- **Risk** — `RiskEngine.prepare_order` (`engines/engine_b_risk/risk_engine.py:1115+`):
  ATR sizing, per-position cap ~30%, max 10 positions, 1% ADV, 30% sector, 100% gross,
  ATR stops (1.8×).
- **Execution** — next-bar **OPEN** fill, **no look-ahead** (`backtester/backtest_controller.py:1442-1520`),
  realistic ADV-bucketed Almgren-Chriss slippage (`engines/execution/slippage_model.py:156-283`),
  real Alpaca SEC/FINRA fees (`backtester/alpaca_fees.py`), borrow costs.
- **Metrics** — block-bootstrap CI + execution census + DSR, to `performance_summary.json`.
- **Paper/live** — real idempotent Alpaca **paper** integration, auction-only (OPG/CLS),
  **reconcile-only by design; schedule DISABLED**. No wired engine→real-money order path.

**Exists in files but inert in the production path** (the pattern to watch for — it is pervasive):

| Component | Status | Evidence |
|---|---|---|
| ML predictor | imported, never called | `engines/engine_a_alpha/ml_predictor.py`; no `.predict()` in path |
| MetaLearner | disabled (and refuted T-149) | `config/alpha_settings.prod.json:24-25` |
| HMM `p_crisis` ("AUC 0.887") | **computed every bar, consumed by nothing** | only entropy-confidence damps `risk_scalar` (`engines/engine_e_regime/advisory.py:204-209`); level signal feeds `regime_transition_overlay.py`, default OFF |
| Regime-conditional weighting | off since Apr | `config/governor_settings.json:13` `regime_conditional_enabled:false`; every edge `regime_gate=None` |
| Governor (Engine F) learning | **neutralized to identity** in measured path | `orchestration/run_backtest_pure.py:462-472` resets weights → all 1.0 |
| Lifecycle manager | no evidence ever fired | no `lifecycle_history.csv` |
| Discovery promotion | promotes nothing | T-196 0/35 H0 |
| `evaluator.py` + `evolution_controller.py` | **631 lines fully dead** | imported only by tests/`__main__` |
| "News/LLM" sentiment | VADER lexicon, not an LLM | `intelligence/news_collector.py` |

**Net:** at prod-default flags the adaptive/"autonomous" machinery changes **almost no
trades**. Production is a static, hand-tuned weighted-sum of ~20 edges with inverse-vol
sizing and ATR stops. The genuinely-live parts are the execution simulator, the risk
caps, and the **coarse 5-axis** regime advisory (not the validated HMM).

---

## 2. Capability gaps vs. the goal (prioritized)

1. **No validated alpha — the book is closet beta.** Confirmed by the project's own
   HAC + 1000-iter block-bootstrap evidence (`scripts/edge_compression_t117.py`,
   `docs/Audit/edge_compression_t117_2026_06_06.md`): **12 of 13 dense edges are
   factor-negative** (α t-stat < −2, p(α>0)≈0). The three flow edges carrying **~94% of
   PnL** — `volume_anomaly` (raw Sharpe 5.63), `short_term_reversal` (4.48), `gap_fill`
   (3.21) — are **all** factor-negative. The Sharpe is market/momentum/size beta +
   risk-management + survivorship.
2. **Risk model is a stub by quant-desk standards.** `factor_analysis.py` exists but is
   **never called by `risk_engine.py`** — no factor-neutrality, no VaR/ES, no
   covariance-based risk budgeting in live sizing; only gross/sector/notional caps. The
   one validated predictive signal (HMM `p_crisis`) is not wired to sizing.
3. **Signal breadth is wide but entirely in the most-arbitraged corner** (daily-bar,
   cross-sectional, equity price/volume/calendar). No genuinely orthogonal modality is
   live: news is VADER lexicon; the 5 cached positioning parquets + 641 insider files
   have **zero code consumers**.
4. **The "autonomous" loop is open at nearly every joint** (Discovery promotes nothing,
   governor identity in measurement, ML/metalearner off, lifecycle never observed to
   fire). Self-evolution is aspirational in production.
5. **No conditional structure is live.** `regime_gate` plumbing
   (`engines/engine_a_alpha/signal_processor.py:585-596`) is fed empty dicts. The
   single most-defensible idea — fork the provably bull-conditional book by the
   *validated* HMM regime — has never been run with the validated input.
6. **Survivorship is un-quantified on the headline.** PIT machinery exists but ships
   default-OFF (`config/backtest_settings.json:161`); the survivor-vs-PIT A/B
   **stalled 4×** (`docs/Audit/pit_universe_hook_t154_2026_06_11.md`). Only a lower
   bound exists: ΔCAGR −3.5pp, 20.5% of PnL from out-of-index names ("plausibly 7–13pp").
   (Mercy: survivorship hits CAGR hard but Sharpe only ~−6%, so the *no-alpha* verdict
   is robust to it.)
7. **Measurement defect (now fixed in this assessment, see §6):** Discovery Gate-6
   factor-alpha used homoskedastic OLS SE, not HAC (`core/factor_decomposition.py`),
   inflating t-stats on autocorrelated returns → gate more permissive than advertised.

---

## 3. Overbuilt / misdirected

Non-test LOC ≈ 107K. Estimate: **~40–45K load-bearing, ~30K archivable run-once
research, ~8K closed-out speculative strategy machinery, ~4K true duplication.**

- **`scripts/` (170 files, 42K LOC) is larger than all eight engines combined** and is
  the center of gravity; ~132 of 170 are imported by nothing. **65 T-xxx one-off
  harnesses = 13,833 LOC**, never archived — in direct violation of the project's own
  "archive, never delete / leave it tighter" rule.
- **`scripts/path_c_synthetic_compounder.py` (1,672 lines)** — self-labeled "DESIGN-PHASE
  FEASIBILITY TEST. Not production code," orphaned, a module-global state hazard
  `scripts/run_isolated.py:155-157` must defensively reset.
- **Sleeve / managed-futures / crisis-replay cluster ≈ 7,600 LOC** where every in-house
  verdict is closed-negative; the lone survivor is "buy a 20% DBMF ETF."
- **14 scripts carry private Sharpe reimplementations** bypassing `core/metrics_engine.py`
  — each a re-entry point for the bare-std/CI-less bugs the non-negotiables forbid. Plus
  4× `validate_regime_signals*` (2,365 LOC) and 3× `factor_decomp*` (1,345 LOC) variants.
- **`CLAUDE.md` repeatedly guards `live_trader/`, which does not exist** (paper code is
  in `paper_trader/`).
- **The measurement apparatus** (bootstrap CI, DSR/PSR/PBO-CSCV, census, determinism
  pinning) is the genuinely excellent part — and is itself plausibly overbuilt relative
  to a $5–50K account. Keep it; but its scale is the tell unpacked in §4.

---

## 4. Blind spots (what the builders are too close to see)

The drawing-board doc already self-diagnoses closet-beta, survivorship, refuted edges,
and the regime-conditional door. The real blind spots are one level up:

1. **The measurement apparatus has become the product, and that got reframed as a win.**
   The builders' doc literally says "what IS genuinely quant-desk-grade: the measurement
   apparatus." They built a world-class instrument whose headline finding, by its own
   readings, is "no edge." For a $5–50K account that conclusion was reachable at maybe
   10% of the effort. The project has optimized for *the ability to prove there's no edge*
   over *having capital in the right place* — a sunk-cost/identity loop that is hard to
   see from inside because each rigorous step is locally correct.
2. **They keep hunting the single most-efficient corner of the market and call the rest
   "dead."** The kill list (options flow, dealer gamma, prime-broker, cross-asset) is
   correctly labeled inaccessible — but the *survivors* (daily-bar, cross-sectional,
   equity, retail data) are the **hardest** place to find alpha, not "home turf." Every
   open "door" (regime-conditional, multi-gene Discovery) is still in that corner, and
   the MBL arithmetic says even a found 0.1–0.2 Sharpe lift can't clear the bar at
   honest-N. They tag these "low prior" yet keep them open — because closing them means
   writing down that the stated goal is unreachable.
3. **Two known biases both point up, so "borderline" is optimistic.** Survivorship
   inflates the headline *and* the cost model is "optimistic for the book's 50–100 small
   names" (their own words), and the two are un-netted. The CI discipline is rigor
   against *noise* straddling a threshold; it does nothing against *systematic directional
   bias*. So 0.751 likely sits **below** the 0.40 CI-aware kill line once both haircuts
   are applied.
4. **The benchmark choice silently encodes the answer.** The deploy gate is: beat a
   low-cost, tax-managed, diversified robo, net-of-cost *and* after-tax, using an
   actively-traded small equity book the project's own analysis says is beta (generating
   short-term gains in a small account). Overcoming the cost/tax drag of being active
   requires alpha they've shown they don't have. Applied honestly, the gate is nearly
   self-refuting. They half-see it (Roth-only, T-191) without drawing the structural
   conclusion: the constraints + benchmark define a problem with, very probably, no
   solution in this design space.
5. **"6 engines = a hedge fund" is an org metaphor doing architectural work it
   shouldn't.** The division-of-cognitive-labor framing is *the reason* the codebase is
   153K LOC — every concern gets an engine, charter, boundary. But a real desk's edge
   isn't its org chart; it's proprietary data, capital, leverage, and execution speed —
   none of which a retail daily-bar account has. The metaphor faithfully modeled the part
   of a hedge fund that doesn't generate returns, and produced complexity instead of edge.

---

## 5. Honest verdict + highest-leverage changes

**Verdict.** "Significantly outperform the market" is not achievable here, and the
project's own rigorous instruments have accumulated strong evidence for exactly that.
**Risk-managed beta is the realistic ceiling, and the money should stay in the Schwab
robo.** That is the correct finding, reached honestly. The genuine asset built here is
the *measurement and execution discipline*, not the strategy.

Highest-leverage moves (note #1–#2 are decisions, not code — that is the point):

1. **Run the 26yr leave-one-out alpha attribution now, as a kill-gate** (~$20). T-117
   all but guarantees "beta." When confirmed, *formally close* the equity-alpha hunt
   rather than leaving doors ajar.
2. **Resolve the goal, in writing, to one honest target** — the single highest-leverage
   change. Either (a) "risk-managed beta delivery, judged vs the robo, with 'money stays
   in robo' an accepted outcome," or (b) "a falsification/research platform, no
   real-money pretense." The current goal is unreachable and is what drives continued spend.
3. **If continuing technically, do exactly one push: wire the validated HMM `p_crisis`
   to de-risk in crisis — as beta-quality control, not alpha.** The 26yr −33% MDD, not
   the return, is what loses to a robo. The HMM (AUC 0.887) is the only validated
   predictive signal and is currently consumed by nothing. Re-run with the HMM, not the
   coarse 5-axis advisory that failed in April.
4. **Run the cleanup the project's own rules mandate.** Archive the 65 T-xxx one-offs
   (13.8K LOC), the 631 dead governance lines, `path_c_synthetic_compounder`, and the
   closed-negative sleeve cluster; collapse the 14 private Sharpe reimplementations onto
   `core/metrics_engine`; delete the `live_trader/` guard ghost.
5. **Quantify the two upward biases before quoting any headline again.** Finish the
   stalled PIT survivor-vs-PIT A/B and net realistic small-cap costs into the 26yr/16yr
   anchors. Until then, treat 0.751 as an upper bound probably under the kill line.

**Credit where due.** Block-bootstrap CI, the hard-gated execution census shared across
local/cloud, the fail-closed non-negotiables, the honest next-bar-open execution sim with
real slippage/fees/borrow, the idempotent paper-trading state machine, and a documented
track record of catching the project's own clouded numbers are genuinely quant-desk-grade
and rare. The instrument is excellent and is telling the truth. The only thing left that
is actually high-leverage is acting on what it says.

---

## 6. Concrete fix landed alongside this assessment

**Discovery Gate-6 factor-alpha standard errors: homoskedastic OLS → Newey-West HAC.**
`core/factor_decomposition.py::regress_returns_on_factors` computed the intercept t-stat
with homoskedastic OLS standard errors, which understate the SE on serially-correlated
daily returns and inflate the alpha t-stat — making Gate 6 **more permissive than
advertised**, in the dangerous direction. This violated the project's own HAC/block-
bootstrap measurement standard, and disagreed with the already-trusted HAC estimator in
`scripts/factor_decomp_substrate_honest.py`.

Fix: ported that estimator's exact convention into the canonical module — added
`newey_west_lag` (Politis auto-lag `floor(4·(T/100)^(2/9))`) and `newey_west_cov`
(Bartlett kernel; `lag=0` reduces to White HC0), rewired the SE to HAC, and recorded the
chosen lag on `FactorDecomp.hac_lag`. The change is conservative: on iid returns HAC ≈
OLS (existing recovery tests stay green), and it only tightens the gate on autocorrelated
returns. Regression tests added in `tests/test_factor_decomposition.py`
(`test_hac_tstat_more_conservative_than_ols_on_autocorrelated_returns`,
`test_newey_west_cov_lag0_equals_white_hc0_and_is_symmetric`, `test_newey_west_lag_formula`,
`test_hac_and_ols_agree_on_iid_returns`). Targeted suite: **22 passed, 1 skipped**.

## 7. Open proposals (NOT executed — need a go)

- **PIT survivorship A/B (multi-hour run).** Complete the 4×-stalled survivor-vs-PIT
  full-engine backtest to put a real number on headline inflation. Left as a proposal
  because it is a long compute job, not a quick edit.
- **The strategic decisions in §5 (#1, #2)** are the user's to make.
