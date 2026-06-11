# Fresh-View Full-System Review — 2026-06-11

**Requested by:** user ("we've been working on this project for months and still no
significant progress. I need your fresh view on what can really be improved and fixed
so the system is significantly better.")

**Method:** director session + three parallel read-only audits (architecture-vs-reality,
code-health, alpha-strategy), grounded in CURRENT_STATE.md, TASK_LEDGER.md,
health_check.md, deployment_boundary.md, the prior external reviews
(`docs/Sessions/Other-dev-opinion/`), and direct code reads. All file:line claims were
verified in code this session. No code was modified.

---

## Verdict

The "no significant progress" feeling is accurate, and it is not because the work was
bad — the falsification discipline here is genuinely world-class. It is because the
project has three structural inversions that guarantee the *feeling* of stasis no
matter how much work lands:

1. **The system you measure is not the system you built.** The headline numbers
   (26-yr Sharpe 0.237, MDD −59.29%) were produced by a configuration in which nearly
   every defense built over months is off, dead-wired, or unreachable.
2. **The architecture cannot express the only strategy class that has ever validated.**
   Every validated positive is a timing/risk/vol finding; the portfolio math
   algebraically cancels uniform signals, and the discovery gauntlet only tests the
   (now cleanly falsified) cross-sectional class.
3. **The apparatus has inverted over the product.** scripts+tests+docs ≈ 155K lines,
   ~4× the engine code; the live path is a 64-LOC stub plus a 0-byte `run_live.py`;
   the system has never traded, not even paper.

Each inversion is fixable. Fixing them is what "significantly better" looks like.

---

## 1. The system you measure is not the system you built

Verified on the default production path (arm0, shipped configs):

- Engine B always takes **Path A** (`risk_engine.py:1008`); Path B (`:1069`) never
  executes. On Path A the sizing line is effectively
  `target_notional = equity × target_weight × 1.0 × 1.0 × 1.0 × 1.0 × 1.0` — all five
  overlay multipliers inert by default. Of 10 defensive controls, effectively **2.5
  are live** (the corr-regime sector consumer is additionally dead at the producer
  side — Engine E writes the key in the wrong shape, `regime_detector.py:259` vs
  `risk_engine.py:830`).
- The **validated crisis HMM (`hmm_3state_crisis_v1.pkl`, OOS AUC 0.914) is never
  loaded by production** — `config/regime_settings.json` points at the legacy
  `hmm_3state_v1.pkl` (the AUC-0.49 false-negative model), and only T-103/T-105
  scripts reference the validated artifact.
- `portfolio_settings.json` has `"vol_target_enabled": true` — **true but
  unreachable**: prod `mode: "mean_variance"` early-returns before the adaptive-branch
  overlays (`policy.py:200`, overlays at `:334-391`).
- Engine F's factor-α retirement gate: `factor_alpha_enabled=True`, but
  `governor.evaluate_lifecycle` (`governor.py:607-610`) never passes `factors=`, so
  the gate body (`lifecycle_manager.py:613-617`) is a permanent no-op in the
  autonomous loop.
- **Estimate: ~40% of engine LOC executes on a default run; ~25-30% influences a
  trade.** Of the capability ledger's 34 behavior-altering rows, ~5 are live.

What the production system actually is, end-to-end: **a mean-variance rebalancer over
~6 beta-flavored edges with static exposure caps** — no conviction sizing, no working
drawdown response, no regime response in sizing, no crisis model. That is the machine
that drew −59%. T-100 found this empirically; this review confirms it from code.

The recurring bug class of the entire project is **flag-true-but-path-dead**
(T-088, T-100, T-101, T-106, the vol-target flag, the factor-α gate). A config flag is
never evidence anything runs. Any future capability claim needs the 3-way join:
config-flag × call-site-args × branch-reachability.

## 2. The architecture suppresses the validated strategy class

The washout T-122 found is exact and mechanistic. In
`engines/engine_c_portfolio/policy.py` (~264-304), inverse-vol weights are normalized
by `total = sum(inv_vols.values())` — the weight vector is **scale-invariant in signal
level**. Any uniform or near-uniform signal (i.e., every market-timing, regime, or
macro signal) cancels algebraically before it can move gross exposure. Consequences:

- The Engine-A risk brake (`signal_processor.py:543-551`, `norm *= risk_scalar` in
  stressed/crisis) is **structurally inert** — a uniform multiplier cancels in the
  same normalization. This mechanistically explains T-101's "capability failure, not
  wiring" and T-126's ~0.009 benign leak.
- Every `macro_*` edge and any timing-class candidate ever run through the gauntlet
  was killed **by architecture, not by evidence**. "The gauntlet rejected it" is not
  evidence against any timing hypothesis.
- The 8-gate gauntlet (9,352 LOC of Engines D+F) validates only cross-sectional
  edges — the lane that is now cleanly falsified — while overlays/sleeves (the lane
  holding every validated asset) have **no first-class validation machinery** and get
  bespoke hand-built A/Bs (T-118 being the correctly-designed exemplar).

Meanwhile the cross-sectional verdict is about as clean as falsification gets and
should be accepted: 0/13 edges clear FF5+Mom t>2 (compression makes joint α *more*
negative: −1.74 → −5.35); VRP equity-proxy, BAB-at-depth, 8-K, Form-4, 13F all closed
family-wise clean; LPS overnight α real (t=5.69) but unharvestable; metalearner closed
under its own pre-registration. High-raw-Sharpe edges are closet beta. The book pays
real costs to manufacture what MTUM/USMV sell for 15 bps.

**The category split is now strongly predictive:** risk/regime/forecasting findings
(HMM posterior AUC 0.914, Yang-Zhang > production EWMA with the EWMA
zero-variance-collapse over-lever state, trend-sleeve crisis alpha 8/8 windows) have
survived every escalation of rigor; cross-sectional return alphas have decayed
monotonically with every increase in rigor. The system keeps hunting in the falsified
lane because that is the only lane its machinery can see.

## 3. The apparatus has inverted over the product

- `live_trader/` is **64 LOC** across 2 files; `scripts/run_live.py` is **0 bytes**.
  Since March: 956 doc file-touches, 361 engine, 356 scripts, **1 live_trader**.
  `deployment_boundary.md`: "No paper trading. No live capital. No broker
  integration." The system has never traded.
- `scripts/` = 185 files / 44,310 LOC; ~122 are one-offs; 59 are task-numbered
  scripts for closed tasks; clone families (e.g., 4 `validate_regime_signals*`
  variants ≈ 2,114 LOC).
- **18 scripts hand-roll bootstrap and 10 hand-roll Sharpe** outside
  `MetricsEngine` — each one a chance to silently violate the block-bootstrap
  non-negotiable. The core statistical discipline is enforced by convention, not code.
- `health_check.md` is 164KB with 100 entries, **53 of which have an empty Status
  field**; `lessons_learned.md` 132KB; `forward_plan.md` 85KB and flagged by
  CURRENT_STATE as partially superseded. The living docs have stopped being
  at-a-glance.
- The paper loop re-implements fill/SL-TP semantics "for parity" with the backtester
  (`mode_controller.py:327,342`) — manually synchronized dual execution semantics,
  the exact bug class T-095 had to rule out.
- God functions in every hot path: `DiscoveryEngine.validate_candidate` 804 LOC,
  `RiskEngine.prepare_order` 765 LOC (inside the propose-first engine, so the debt is
  sticky), `ModeController.run_backtest` 436 LOC.
- ~6,300 LOC in the production tree is unreachable from any entry point, including a
  byte-identical 186-LOC twin (`research/promote.py` vs
  `engines/engine_f_governance/promote.py`). Production imports root-level
  `debug_config.py` (load-bearing for Engine F).
- The multi-agent/worktree/cloud apparatus generated its own crises: the pyc-taint
  saga, the LAPACK placement lottery, 29-day silent anchor divergence across 3 of 5
  worktrees. Weeks of director attention went to debugging the measurement substrate
  rather than the strategy.

A subtler process inversion: **the measurement immune system now rejects all change,
including validated defense.** Every flag-flip must clear ci_low>0 at honest-N MBL
bars that a 0.237 base can rarely clear, while the incumbent configuration — which
would itself fail every gate — keeps incumbency for free. Defense (whose value is
MDD/crisis response) is being held to an alpha-claim evidentiary standard.

---

## What the evidence says this system should become

The validated parts list assembles into exactly one machine: **a regime-aware,
risk-managed multi-asset allocator on cheap betas**, deployed at the actual capital
tier (the T-139/T-141/T-151 work establishes this is a $5-50K, Roth-first account).

| Validated asset | Role |
|---|---|
| HMM transition-trigger posterior (AUC 0.914) | De-gross overlay (T-118, in flight, correctly designed) |
| YZ vol forecast > EWMA (+ EWMA collapse failure mode) | Vol-target σ estimator (Engine B, propose-first) |
| Trend sleeve crisis alpha (8/8 windows, corr 0.29) | Capital-partitioned crisis diversifier |
| After-tax gate + router + safe-f (3 independent convictions) | Roth-first deployment policy |
| The falsification machinery | Repointed at the overlay/sleeve lane |

At this capital tier, the only levers that move terminal wealth are avoiding −59%
drawdowns and cheap compounding — not 1-2%/yr of hypothetical cross-sectional α.

## Prioritized plan

**P0 — already correct, finish it**
1. T-140 N≥5 unanimity re-baseline (single-threaded BLAS pinned). Nothing else is
   quotable until this lands.
2. T-118 de-gross verdict — the right culmination experiment.

**P1 — the pivot (the "significantly better" core)**
3. **Retire the factor-negative edge book** via the already-built T-043 gate. The fix
   is wiring `factors=` into `governor.evaluate_lifecycle` (Engine F,
   autonomous-allowed, essentially one argument). The book is the system's largest
   measured liability.
4. **Kill the Path A/B fork in Engine B** (propose-first): make Path A the only path,
   lift the surviving defenses onto it once, archive Path B. One consolidation
   replaces the three accumulating lift-flags (T-111/T-116/T-118) and ends the
   flag-true-but-path-dead bug class at its source.
5. **Repoint production to the crisis HMM** + **swap the vol estimator to
   max(YZ, EWMA-floor)** (both propose-first, pre-registered, judged on MDD/crisis
   hit-rate criteria — the T-108 8/8-windows form — not alpha-grade Sharpe ci_low;
   26 years contains ~3 crises and a full-window t-stat is underpowered for crisis
   machinery by construction).
6. **Build the overlay gauntlet** — first-class validation for timing/overlay/sleeve
   strategies (pre-registered deep-window A/B vs OFF, CI on the difference,
   per-crisis-window hit rates). Seeds exist: T-118's harness + T-143's crisis-replay.
7. **The pivot measurement:** 26-yr pre-registered A/B of {cheap-beta core + YZ
   vol-target + HMM transition de-gross + trend-sleeve partition} vs SPY buy-hold and
   60/40. The benchmark must be the user's replicable alternative, not zero.
8. **Start paper trading.** After the pivot measurement, getting *anything* trading
   paper through the deployment stack (auction fills, dyn-opt, buffering, router —
   all built, all OFF) converts the deployment lane from inert capability into a
   running system, and is the most visible "significant progress" available.

**P2 — debt burndown so future work is cheap**
9. Archive sweep: ~122 closed-task scripts → `Archive/scripts/<task-id>/`; dead twin
   `research/promote.py`; refuted edges → `Archive/edges/`; `debug/` + root one-offs;
   `config/backtest_settings.json.bak`; strip backtest *results* embedded in
   `alpha_settings*.json`.
10. Consolidate measurement math: one blessed aggregation helper in
    `core/measurement/`; doc-lint/contract-test against hand-rolled bootstrap in
    scripts.
11. Extract shared fill/SL-TP semantics for backtest + paper loop; parity contract
    test.
12. Triage `health_check.md` (53 status-less entries get a status or move to
    Archive); split `lessons_learned.md` by year; hard-cap `forward_plan.md` like
    CURRENT_STATE.
13. Decide `live_trader/`'s fate explicitly (it is currently ambiguous): either the
    paper/live path is `mode_controller` (archive the stub) or `live_trader/` is real
    (charter + build plan).

**Stop doing**
- Cross-sectional alpha hunts on this substrate (each raises the MBL bar for
  everything else; EV per test ≈ 0). Cap at ≤1-2 pre-registered,
  instrument-different tests/quarter; options-class VRP is the only currently
  fundable candidate.
- Discovery GA cycles on this universe (parked per the 2026-06-06 plan — keep it
  parked).
- Accumulating default-OFF capabilities without an enable-or-archive decision date.
  Every new inert flag is negative progress: it widens the built-vs-running gap that
  produced the −59% surprise.

## False-negative channels in the falsification machine (for the record)

1. Gate-1 contribution metric zeroes the timing class (HIGH; mechanism above).
2. As-deployed shared-ensemble attribution, never isolation — `volume_anomaly_v1`
   (t=−1.59, cleanest MI in T-132) is the one name where isolation could differ.
3. T-135 overnight harvest was priced under the legacy 5bps/side model, not the
   shipped auction-execution model (~1.3bps/side all-in on liquid large caps); a
   one-evening re-price would settle it (borrow/gap/tax probably still kill it).
4. Survivor substrate is sign-aware: inflates long-leg α, *deflates* short-leg α —
   event-lane nulls could be partly substrate artifact on short/distress legs.
5. FF5 t>2 measures factor-orthogonality, not "beats the replicable ETF" — the pivot
   measurements should benchmark the replicable alternative explicitly.

## Doc corrections queued (not applied; read-only review)

- `capability_ledger.md` Engine E rows still say `hmm_enabled=False` (stale since
  T-101).
- No living doc states that production loads `hmm_3state_v1.pkl`, not the validated
  crisis model — should be a HIGH health_check row given CURRENT_STATE leans on
  "hmm_p_crisis is VALIDATED-predictive" as load-bearing.
- `forward_plan.md` cites source files
  `docs/Sessions/Other-dev-opinion/6-6-26_{gaps,...}.md` that do not exist in the
  repo.

---

*Director synthesis of three subagent audits (architect, code-health, edge-analyst),
2026-06-11. The underlying audits' full evidence (file:line for every claim) is
preserved in this document's sections; nothing here relies on superseded findings —
cross-checked against CURRENT_STATE.md 2026-06-10 and TASK_LEDGER.md through T-151.*
