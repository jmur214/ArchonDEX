# ArchonDEX Re-Architecture Plan (2026-06-18)

**Supersedes the prior alpha-hunt direction.** Resolved goal (user, 2026-06-18): NOT academic
factor-orthogonal alpha, NOT learning-only — **an autonomous system that trades itself and DOES
WELL = beats the Schwab robo net-of-cost/after-tax on risk-adjusted/tail terms, paper-confirmed.**
The robo holds the real money and IS the benchmark. Built from the 6-front scoping pass
(`wf_3fd9c1da`), grounded in the code + both external reviews.

## Honest framing
A genuine re-approach, not a relabel: the codebase already contains **wired-but-OFF** machinery
never honestly composed against the robo bar — vol-target (`portfolio_vol_target_enabled=False`),
PIT universe (`use_historical_universe=false`), the HMM regime overlay (OFF), and a **built-but-unused
robo scorecard** (`core/combined_candidate_scorecard.py`, T-176/T-191). Real unexplored ground.
But brutal: the base is 0.751/ci_low 0.382 (Roth-only, −33% MDD, after-tax LOSES ~4pts CAGR to the
robo), the book is beta (12/13 edges factor-negative, 3 flow edges carry ~94% PnL), both in-house
crisis defenses are refuted, and retail cross-sectional alpha is folklore. **Most individual bets
below will be null.** The value is testing the RIGHT things — beta shape, tail, after-tax turnover —
with the rigor intact (block-bootstrap CI, MBL, DSR, census, walk-forward), and failing fast. **A
paper-confirmed "the money stays in the robo" is a SUCCESSFUL outcome of this plan, not a failure.**

## The single highest-leverage move
Promote `core/combined_candidate_scorecard.py` from report-only to the **PRIMARY deploy gate**, paired
with fixing the **Gate-6 OLS→HAC defect** (`core/factor_decomposition.py:206-212`). Today we gate on
factor-orthogonal academic alpha — the wrong target — using upward-biased t-stats. Re-aiming the gate
at the robo bar and un-inflating the ruler is a few hours that make every later phase measure the
right thing honestly.

## Phases

### Phase 0 — Clean base + re-aim the gate + un-bias the measurement (~5-7 days, mostly mechanical)
The cheap prerequisite. Gate = INTEGRITY, not alpha.
- **Archive the bloat** (to `Archive/`, never delete): 67 `T-xxx` one-off scripts (~13.8K LOC),
  `path_c_synthetic_compounder.py`, the closed-negative sleeve cluster, the `live_trader/` guard-ghost.
- **Fix Gate-6 OLS→HAC** (Newey-West SEs; unit tests; DOC the OLS→HAC delta — headline alphas should
  DROP, that's the honest direction).
- **Promote the robo scorecard to the deploy gate** — `evaluate_deploy_readiness(candidate, robo_proxies,
  account)`; gate = `ci_low(Sharpe_candidate) > ci_low(Sharpe_robo)` AND/OR material MDD improvement,
  after-tax; demote factor-orthogonality to diagnostic-only.
- Consolidate the 14 private Sharpe reimpls onto `core/metrics_engine.py` + a CI guard.
- **Record-drift to correct:** `value_trap_v1`/`growth_sales_v1` carry 0.5 weight (NOT weight=0
  paused) in `config/alpha_settings.json` — re-derive any "fundamentals are inert" claim.
- **Gate:** suite green on the cleaned base (no silent census shrinkage); HAC delta documented; the robo
  scorecard runs as the gate and correctly says "do NOT deploy today." Tag `Base-Clean-Ready`.

### Phase 1 — Beta-engineering layer (~6-8 weeks) — THE BEST SHOT
Accept the book is beta; engineer its SIZE/SHAPE/REALIZATION to beat the robo on risk-adjusted/tail/
after-tax. Compose three orthogonal, already-wired levers:
- **Vol-targeting** (`portfolio_vol_target_enabled=True`) — with the T-150/T-153 sigma-floor defect
  GUARDED first (sigma collapses to ~0 on ~14% of bars — must fix before any paper run).
- **Long/flat 200d trend overlay on LIQUID ETFs** [SPY, AGG, GLD] (AQR positive-skew/crisis-alpha —
  matches the skew preference; our bought DBMF sleeve is the bought version). Sub-gate: trend-capture
  efficiency >0.7 or it's a chop drag.
- **Defensive quality (ROIC, gross-profitability) + high-IVOL/lottery exclusion** tilt.
- **Odds:** beat the robo on RAW return <20%; on after-tax/tail (the real bar) **~40-60% IF all three
  compose** — the plan's single best shot. The honest win is the TAIL (cut the −33% MDD), not the
  headline. Vol-target's ~0.40→0.50 lift is gross; net ~0.35-0.45 after de-gross slippage — fragile.
- **Gate:** clears `evaluate_deploy_readiness` vs ≥1 robo proxy AFTER-TAX, DSR/n_trials-penalized,
  walk-forward OOS. Pre-register the full param grid; AWS Batch 26yr + block-bootstrap CI.

### Phase 2 — Universe de-biasing (PIT cheap; microcap GATED) (~PIT: hours; microcap: memo only)
- **Wire the PIT hook** (`use_historical_universe=true`, one config line, fully built + T-189 halt) →
  re-baseline every number on the survivorship-corrected substrate. Odds: adds breadth ~70%, net
  improvement ~40% — the correction REDUCES Sharpe (a less-biased estimate of the same answer, not new
  alpha). The trap: seeing the drop and blaming implementation.
- **Re-run Phase-1's composed strategy on the PIT universe** (report the verdict on the less-biased
  substrate).
- **Microcap = GATE MEMO ONLY, default DEFER.** <20% viable at retail (50-100bps friction observed,
  ~58% post-pub decay → ~30bps net, position-size caps to 1-2 names, MBL violated by orders of
  magnitude). Proceed ONLY if a concrete ≥100-150bps gross edge is pre-identified AND Norgate ($80/mo,
  survivorship-free) is funded.

### Phase 3 — Trader-like conditional/combined selection (~3-4d build + 2-4wk validation) — GATED LAST
The user's higher-belief bet: fundamental thesis × technical confirmation × regime conditioning as a
conditional-multiplier system, using the already-wired `regime_gate` plumbing (no Engine-A boundary
cross). Gated LAST on purpose so its near-certain null is cheap + unambiguous on a clean base.
- **Odds <20%** to beat the robo (12/13 edges factor-negative; retail stock-selection is the hardest
  place; daily-bar caps "trader-like" timing; every condition multiplies the DSR penalty; the
  post-gating universe collapses to 2-4 names/side where slippage eats the edge).
- **Count every condition as a trial** (N = #fund × #regime × #timing); pass to DSR; log every branch.
- **Gate:** clears the robo scorecard AFTER-TAX on OOS (not IS), n_trials-penalized. **A clean,
  well-measured FAIL logged to the decision diary IS the success condition** — it closes a high-belief
  front with evidence instead of an open "someday."

## Kill / Defer (honest)
- **KILL pure intraday/HFT** (78-390× wall-time, PDT-blocked <$25K, DOA). Daily post-close timing
  aggregates as an optional pre-registered Phase-3 sub-experiment is the only survivor.
- **DEFER microcap thrust** (gate-permit only).
- **KILL the refuted in-house crisis defenses** (de-gross T-118r, sleeve T-128r) — don't re-litigate.
- **DEFER new engines/deps/3+-engine changes** — this rides on wiring/measuring EXISTING OFF machinery
  (repoint-over-rebuild).
- **DEFER live ML/sentiment/LLM** (propose-first; "conditional" must not creep into "conditional+ML").
- **Phase-0 cleanup is NOT progress** — hygiene that unblocks, not a win.

## How we measure "does well" (no self-deception)
Clears `evaluate_deploy_readiness` vs a robo proxy (60/40 + schwab-like) AFTER-TAX, net-of-cost, on
**ci_low(Sharpe)** (block-bootstrap 1000) AND/OR material (~≥20%) MDD improvement surviving the
after-tax/slippage haircut. Guards (all in-tree): MBL pre-flight, DSR with n_trials counting EVERY
arm/condition, pre-registration + walk-forward OOS, census-canonicality, fail-closed path, and the
**proxy-vs-real-robo gap held explicit** — only paper-vs-actual over 6-12 months decides. "Money stays
in the robo, paper-confirmed" = a SUCCESSFUL falsification, logged as such.

## Director-recommended decisions (see chat for the open questions)
- Phase order P0→P1→P2→P3 (P3 = the high-belief bet, last by design; an early narrow P3 spike is
  available on a dirtier base if desired).
- Phase 0 measurement/cleanup = autonomous-OK (our own rules + executing the agreed reframe). The
  **Engine B vol-target flip (Phase 1) stays PROPOSE-FIRST** (brought for review at the Phase-1 gate
  with the sigma-floor guard).
- Primary gate account: **Roth** (the realistic deployment account; in Roth the tax/turnover lever is
  off → the bar sharpens to risk-adjusted + tail/MDD). Taxable as a secondary diagnostic.
- Robo proxy: proxy-then-paper two-stage (don't over-invest in a replica before there's something to
  test). Microcap Norgate spend: off the table unless the Phase-2 gate memo finds a concrete edge.
