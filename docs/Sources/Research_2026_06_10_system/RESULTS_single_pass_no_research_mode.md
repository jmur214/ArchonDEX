# RESULTS — system-improvements hunt, single pass WITHOUT research mode (2026-06-10)

> **PROVENANCE (added 2026-06-10): the researcher had NO codebase access.** Literature/price/regulatory claims are independent and verifiable; any US-SPECIFIC judgment ("your gate…", "your overlay is the surviving family") derives solely from the prompt's self-description and partially echoes the director's framing — weight accordingly; verify locally before adoption (standing policy).

> Provenance: the user ran `PROMPT_system_improvements.md` without the deep-research
> feature. The agent executed a knowledge-first single pass with targeted searches
> for time-sensitive items. Director assessment: strong; full rerun NOT warranted
> (canon/validation/risk extractions are stable knowledge; searched items came back
> cited). The DATA prompt (sibling folder) SHOULD run in research mode — it is
> live-price verification work. Items the output itself flags as needing the deep
> pass: exhaustive OSS code-level mapping (our agents can do this locally),
> per-anomaly net-Sharpe tables, paywalled sources (Quantpedia OOS tracking,
> vectorbt.pro, Bandy/Krishnan exact parameters).
>
> Director-extracted top actions are tracked in the session todos; the verbatim
> output follows.

---

[Verbatim output as received 2026-06-10]

AREA 1 — Canon extracted as specs

1.1 Carver forecast-processing chain [M | high | replicated — pysystemtrade is the reference implementation]

PIPELINE (per instrument, per rule):
1. RAW FORECAST
   EWMAC(L_fast, L_slow): raw = (EWMA_fast(price) − EWMA_slow(price)) / σ_price_daily
   Standard speed set: (2,8) (4,16) (8,32) (16,64) (32,128) (64,256); slow = 4× fast
   Carry: raw = expected annual carry / σ_annual
2. SCALE so E[|forecast|] = 10:
   scalar = 10 / mean(|raw|), pooled cross-instrument, expanding window
   Carver's published scalars: EWMAC2,8≈10.6  4,16≈7.5  8,32≈5.3
   16,64≈3.75  32,128≈2.65  64,256≈1.87  carry≈30
3. CAP at ±20 (hard clip)
4. COMBINE: combined = Σ w_i · forecast_i · FDM
   Weights via handcrafting: group rules by correlation (>~0.7 = same group),
   equal-weight within group, equal across groups; small SR-based tilts only
   FDM = 1/sqrt(w'Σw) where Σ = forecast correlation matrix, floor corr at 0,
   cap FDM at 2.5; re-cap combined at ±20
5. POSITION (vol targeting):
   subsystem_position = (combined/10) × (capital × %vol_target × IDM × instr_weight)
                        / (instrument annualized cash vol per unit)
   %vol_target: 12–25% (Carver: ~25% max for aggressive; half-Kelly logic)
   IDM analogous to FDM, capped 2.5
6. BUFFERING (position inertia):
   buffer = 0.10 × |optimal_position|
   trade only to buffer edge when |current − optimal| > buffer

Code instead of prose: pysystemtrade — systems/forecasting.py, systems/forecast_scale_cap.py, systems/forecast_combine.py, systems/positionsizing.py, systems/portfolio.py; buffering in systems/buffering.py/position-sizing stage; handcrafting under sysquant/optimisation/. (Module names from memory of the repo — agents should grep the current tree; structure is stable.)

1.2 López de Prado meta-labeling, end-to-end [M | med | published, mixed independent replication]

def triple_barrier(prices, events, pt_mult, sl_mult, max_holding_days):
    vol = ewm_std(daily_returns, span=100)          # AFML getDailyVol
    for t0 in events:
        upper = price[t0] * (1 + pt_mult * vol[t0])
        lower = price[t0] * (1 - sl_mult * vol[t0])
        t1 = t0 + max_holding_days                   # vertical barrier
        label = sign of first barrier touched (0 or sign(ret) on vertical)

META-LABELING: primary model (existing edge) outputs SIDE; relabel y_meta = 1 if
primary trade was profitable else 0; train classifier on features → P(correct).
BET SIZING: z = (p − 0.5)/sqrt(p(1−p)); size = 2·norm.cdf(z) − 1; discretize
0.05–0.10; average over concurrently active bets.
SAMPLE WEIGHTS: average uniqueness = 1/concurrency over label lifespan; weight ∝
|attributed return| × uniqueness; optional time-decay. CV: purged K-fold + embargo
≈ 1% of sample.

Adjudication: meta-labeling's value case is filtering an existing edge with positive
expectancy. We currently lack that primary edge — sequence AFTER one exists.

1.3 Bandy safe-f / CAR25 [S | high | published; reconstructed from knowledge]

1. Define risk tolerance, e.g. P(intra-period drawdown > 20% over 2y) ≤ 5%
2. Build per-trade/per-day return distribution from backtest/live results
3. Monte Carlo: resample (with replacement) 2-year equity sequences ×1000 at
   candidate fraction f
4. safe_f = max f such that the 95th-percentile MDD ≤ 20%
5. At safe_f, compute CAGR distribution; CAR25 = 25th-percentile CAGR
6. Use CAR25 to RANK systems and ALLOCATE; recompute monthly rolling — falling
   safe_f/CAR25 is the system-health/kill metric

Composes with existing bootstrap infra — block-bootstrap machinery repurposed as a
position-sizing governor. Highest synergy-per-effort canon item.

1.4 Krishnan crisis hedges ranked for a small account [S–M | med | published/anecdotal]
(1) de-grossing on trend/regime triggers (free — the HMM overlay; cheapest
convexity); (2) trend-following overlay as crisis hedge; (3) put SPREADS not naked
puts — defined debit, ~1–2%/yr budget; (4) VIX call spreads (cap carry bleed; never
persistently long VIX futures); (5) ratio/weighted structures — skip below ~$100K.
At $5K only (1) and (2) make sense.

AREA 2 — OSS subsystems worth stealing [each S–M to port concepts]

- pysystemtrade: DYNAMIC OPTIMIZATION for small accounts — greedy integer-position
  selection minimizing tracking error vs the unrounded optimal portfolio (the
  solution to "$5K can't hold 13 edges × N names"). sysquant/optimisation/ +
  Carver's 2021-22 dynamic-optimisation blog posts. Also forecast combination +
  FDM + buffering (systems/forecast_combine.py).
- QuantConnect LEAN: reality modeling — pluggable fill/slippage/fee models per
  security (Common/Orders/Fills/, Common/Orders/Slippage/); free reference
  implementation of the Zarattini ORB line.
- Microsoft qlib: online serving + concept-drift adaptation (DDG-DA);
  Alpha158/Alpha360 feature sets as a feature-engineering checklist.
- vectorbt (free): vectorized parameter-grid sweeps for cheap robustness surfaces.
- Nautilus Trader: live order-lifecycle state machine as the spec for paper→live.
- bt/ffn: tree-structured allocation algos.
Skip wholesale adoption; steal subsystems. Nothing category-new since Jan 2026.

AREA 3 — Replication evidence & ranked shortlist

Chen–Zimmermann: for 161 clearly-significant characteristics, 98% reproduce
(t>1.96); Hou-Xue-Zhang mass failures mostly an artifact of microcap screens +
value-weighting. McLean–Pontiff post-publication returns ~50% smaller (replicated);
decay stronger for stronger in-sample predictors.

Shortlist (replicates + free data + not FF5+Mom-spanned by construction):
1. PEAD/SUE drift [M|high|replicated] — most naive return in microcaps + first 3
   days; at large/mid expect net SR ~0.2–0.4 as a sleeve, hold 20–60d.
2. Earnings-announcement premium [S|med|replicated] — calendar-driven, low
   turnover, survives value-weighting.
3. Cross-sectional seasonality (Heston–Sadka) [S|med|replicated] — prices only;
   orthogonal to FF5+Mom by construction.
4. Intraday momentum (GHLZ/Zarattini) — MIXED: Zarattini net Sharpe 1.33 SPY
   2007-24 + OOS holding up, Sharpe rises in high-VIX; but academic GHLZ
   overnight-form predictability disappears OOS (regime/signal-strength dependent).
   Verdict: always-on = expect falsification; high-vol-regime-conditional sleeve =
   coherent with the HMM work.
5. Cross-asset trend/carry via ETFs [M|high|replicated — most replicated class in
   existence] — the breadth the equity-only panel lacks.
Killed at our scale: short-term reversal (cost-dominated), BAB (closed), standalone
value (worst decay class).

AREA 4 — Validation upgrades

- CPCV [M|high]: AFML ch.12 — N=6 groups, k=2 test → 15 paths; purge = label
  horizon; embargo ≈1%. Use for the metalearner decision specifically.
- PBO via CSCV [S|high]: S=16 blocks, all C(16,8) splits; PBO = fraction where
  IS-best ranks below-median OOS. Add deploy gate: PBO < 0.2.
- Hansen SPA / MCS [S|high]: arch.bootstrap.SPA / MCS, stationary bootstrap
  B≥1000 — ONE family-wise test across the 13 edges vs benchmark per release
  (the correct complement to per-edge DSR).
- Romano-Wolf StepM [M|med]: arch.bootstrap.StepM — per-edge adjusted decisions,
  more power than Bonferroni.
- Page-Hinkley/CUSUM live drift [S|high]: CUSUM on standardized daily
  (live − expected) returns, k=0.5σ, h=4–5σ; PH δ=0.005σ, λ=50δ; tune false-alarm
  rate on backtest.
Genuine holes: family-wise (SPA/MCS) + deployment-time (PBO) — not more
per-strategy statistics.

AREA 5 — Risk & portfolio frontier

- HAR-RV exact spec (Corsi 2009): RV_{t+1} = c + β_d·RV_t + β_w·mean(RV_{t-4..t})
  + β_m·mean(RV_{t-21..t}); log-RV preferred (smearing correction on exponentiation).
  KEY ADAPTATION FOR US: no intraday RV on a daily-bar substrate → use
  Yang-Zhang/Garman-Klass OHLC range estimators as the RV proxy (~5–7× efficiency
  of close-to-close), then HAR on that. **Engine-B thickening = HAR on Yang-Zhang,
  not HAR on squared returns.** EWMA λ≈0.94 vs GARCH(1,1) is a wash — not worth
  trials.
- Vol-managed post-Cederburg: what survives = conditional vol targeting acting only
  in EXTREME states/transitions + expanding-window scaling constants + leverage cap
  1.0–1.5×. "Your HMM transition-triggered de-grossing is exactly the surviving
  family — the literature has converged on your bet."
- Drawdown control (Grossman-Zhou practitioner form): exposure_t = base × min(1,
  cushion/budget), cushion = (equity − (1−maxDD_budget)×HWM)/equity; multiplier 2–4
  ≈ CPPI; compose multiplicatively with vol targeting; floor exposure ~0.2.
- Kelly at retail: ¼–½ Kelly on SHRUNK Sharpe (use DSR point, not raw); at 3K
  obs/edge SR s.e. ≈0.25 → half-Kelly on the LOWER CI bound is the defensible rule.
  At honest 26-yr SR 0.24, implied full-system vol target is single-digit — worth
  confronting.

AREA 6 — Execution/ops at $5–50K on Alpaca (decision rules)

- **REGULATORY (post-cutoff, critical): FINRA Notice 26-10 ELIMINATED the PDT
  designation + $25K minimum, effective June 4, 2026** (SEC accelerated approval
  Apr 14, 2026; broker phase-in to Oct 20, 2027). Alpaca already removed PDT
  restrictions; **API fields pattern_day_trader / daytrade_count /
  last_daytrading_buying_power / daytrading_buying_power REMOVED by July 6, 2026**
  (use buying_power). [Director audit 2026-06-10: ZERO references in our code —
  clean.] Residual constraints: $2,000 margin-account minimum; intraday margin
  deficit unmet by close of 5th business day → 90-day opening freeze. Roth = cash
  account: T+1 settlement / good-faith-violation rules unchanged.
- Order mechanics: MOO/LOO = TIF=OPG before 9:28 ET; MOC/LOC = TIF=CLS before
  3:50 ET; auction orders get the official auction print → for a daily-bar system
  this is the no-slippage-model execution path. RULE: default all daily-signal
  executions to OPG/CLS. Fractional shares are day-order-only (incompatible with
  OPG/CLS) → round to whole shares + use dynamic optimization for the integer
  problem.
- Slippage at this scale: Almgren-Chriss is overkill below ~$100K large-cap. Use
  spread/2 + 1–2 bps/side; measure implementation shortfall per fill; recalibrate
  monthly. Orders <0.001% ADV → impact ~0.
- **Cross-account wash sale (Rev. Rul. 2008-5): taxable loss + substantially
  identical purchase in IRA within ±30d = loss disallowed PERMANENTLY (no basis
  adjustment in the IRA).** Decision rule: disjoint universes per account enforced
  in Governance (ticker ∈ exactly one account's tradable set, or 31-day
  cross-account blackout after any taxable realized loss).
- Roth vs taxable allocation: Roth ← high-turnover/ST-gain/rebalancing-heavy
  (regime overlay, PEAD, seasonality); taxable ← low-turnover trend/buy-tilt
  (harvestable losses, LT gains). Corollary: edge < marginal-ST-rate ×
  turnover-implied realization shouldn't run in taxable at all → **add an
  after-tax Sharpe deployment gate** (IL flat 4.95% + federal ST ⇒ ~30–40% drag on
  ST gains).

AREA 7 — Live-operations playbook (consolidated)

DAILY (automated, alarm on failure): position reconciliation broker==model (exact);
order audit (every intended order terminal, orphans alarmed); fill quality
(implementation shortfall logged; alarm if 20-trade rolling mean > 2× modeled
cost); P&L attribution live-vs-expected fed into CUSUM (k=0.5σ, h=4σ).
WEEKLY: safe_f/CAR25 recompute (alarm >25% drop); data-integrity diff vs prior
snapshot.
PRE-REGISTERED KILL CRITERIA (write before going live): live DD > min(1.5×
backtest MDD, backtest 95% bootstrap MDD bound); CUSUM alarm; rolling 60d live
Sharpe < 5th pct of bootstrapped backtest 60d Sharpes; any reconciliation failure
unresolved >1 session → flatten.
INTERVENTION POLICY: no discretionary overrides; only allowed manual action is
REDUCE/FLATTEN. Never manually add risk.
CAPITAL RAMP: paper ≥3mo zero reconciliation failures → 25% ≥2mo passing
divergence gates → 50% → 100%; each stage gate = kill criteria NOT fired.
INCIDENTS: blameless post-mortem; every incident becomes a new automated check.
(Best public artifact: pysystemtrade docs/production.md.)

AREA 8 — New since Jan 2026
1. PDT elimination (above) — same-day exit overlays no longer regulatorily gated
   at our size in the margin account.
2. Alpaca API breaking change — PDT fields removed July 6, 2026.
3. Zarattini line holding up OOS + Feb-2026 note: a short-horizon mean-reversion
   signal unprofitable STANDALONE improves an intraday trend strategy as a tactical
   EXECUTION overlay — template: dead edges repurposable as execution timing.
4. No category-defining new OSS framework.

TOP-10 IMPLEMENT LIST (free-first, with first steps)
1. OPG/CLS auction execution as default [S|high]
2. Carver dynamic optimization for small accounts [M|high]
3. Buffering (10% position inertia) [S|high]
4. After-tax Sharpe gate + Roth/taxable router + cross-account wash-sale hard
   constraint [M|high]
5. HAR on Yang-Zhang range vol for Engine B [S|high]
6. safe-f/CAR25 sizing governor [S|high]
7. SPA/MCS family-wise gate (arch package) [S|high]
8. Conditional (extremes-only) vol-targeting convention for the HMM overlay [S|high]
9. PEAD sleeve on free EDGAR data, Roth-allocated [M|med]
10. Page-Hinkley/CUSUM live-divergence monitors (tune on paper now) [S|high]

DO-NOT-BOTHER LIST
- Training the GBM metalearner now (see Q4; ridge expected to win at our scale)
- Almgren-Chriss below $100K large-cap
- Naked long-vol hedges (carry bleed dominates at retail; de-grossing is the hedge)
- Short-term reversal, standalone value, BAB
- Moreira-Muir unconditional vol scaling (fails real-time per Cederburg)
- Framework migration (steal subsystems only)
- Options-based VRP at $5K (granularity + tail risk)
- Idiosyncratic-alpha hunting on the survivor-biased panel before the panel fix
  (trials partially wasted)

THE 8 QUESTIONS (abridged — see verbatim above for full text)
Q1 CHANGE: (a) reallocate ~80% of trial budget from alpha discovery to
risk/portfolio/tax/execution engineering (near-deterministic gains); (b) the
crisis-overlay A/B framing can't have statistical power — use historical
crisis-replay + pre-registered calm-period cost ceiling ("cheap insurance with
bounded calm drag"), not Sharpe-significance [director: logged pre-unblinding as
docs/Audit/t118_gate_power_critique_logged_2026_06_10.md]; (c) the survivor panel
is a BLOCKER, not a parallel workstream — cross-sectional trials before the fix are
partially wasted.
Q2: t>2 orthogonal alpha is the right bar for CLAIMING alpha, the wrong bar for
DEPLOYING retail. The documented successful-retail path = deliberate factor/style
premia harvesting (trend/carry/momentum tilt) + vol targeting + diversification +
cost control, zero idiosyncratic-alpha claim. Realistic: net Sharpe ~0.6–0.9, MDD
~15–25% at 15–20% vol target (vs our 0.24/−59%). Restated deploy gate: deploy if it
adds to PORTFOLIO-level DSR after costs and taxes.
Q3: single highest-EV missing technique = Carver dynamic optimization (greedy
integer-position tracking-error minimization) — directly attacks the $5K
whole-share constraint; reference implementation in pysystemtrade.
Q4: GBM stacking at 13 edges × 3K obs: effective sample ~300–600 independent obs;
tree variance overwhelms interaction signal; the edges share one latent bull-beta
factor a tree would re-learn. Don't train until ≥5 individually-clearing,
low-correlation edges exist. If ever: depth≤3, heavy min-child-weight, monotonic
constraints, CPCV purge+1% embargo, permutation/MDA importance only, pre-registered
SPA of GBM-vs-ridge as the deploy condition. Expected: ridge wins.
Q5: intraday-as-features ranked: (1) realized-vol features — mostly capturable
FREE from daily OHLC via Yang-Zhang (no minute bars needed); (2) overnight/intraday
return decomposition (Lou-Polk-Skouras) — computable from daily OHLC, cheap add;
(3) first-half-hour/opening-range as regime-conditional feature (minute bars,
index-level via free Alpaca suffices); (4) realized skew/kurt from minute bars —
weak, skip.
Q6: at $5K the correct framing of live = PIPELINE VALIDATION + divergence
measurement, not return generation (heroic net SR 1.0 at 15% vol ≈ $750/yr pre-tax).
Run only lowest-turnover, auction-executed, whole-share-friendly sleeves live. Real
thresholds now: $2K margin minimum; ~$25–50K where multi-sleeve diversification
becomes expressible in whole shares.
Q7 decay: OOS ~26% lower (data-mining correction), post-publication ~50–58% lower;
decay ∝ in-sample strength. Slowest-decay harvestable at retail: price-momentum
variants, seasonality, PEAD in liquid mid/large, cross-asset trend/carry (barely
decays — risk premium, not anomaly). Fastest: value composites, accruals, simple
technical patterns.
Q8 blind spots: (1) after-tax evaluation missing from gates — bigger than modeled
transaction costs for taxable ST strategies; (2) **agent-generated-code risk is the
biggest unmodeled operational risk** — add mutation testing + golden-master signal
regression (bitwise expected outputs on frozen fixtures; we already have the
reproducibility substrate); (3) breadth > depth: IR ≈ IC·√breadth — a mediocre
trend rule across 20 uncorrelated ETF markets beats a brilliant 14th equity edge;
(4) build the crisis-replay harness as its own workstream; (5) since execution will
be at auctions, backtest fills should use official AUCTION PRINTS (Alpaca
historical includes them) — aligns sim to actual fill mechanism, eliminating a
live-vs-backtest divergence class pre-emptively.

COULDN'T VERIFY / PAYWALLED: vectorbt.pro internals; Quantpedia OOS tracking
dashboards; Bandy exact MC parameters (treat defaults as configurable);
Krishnan exact structure parameterizations; current empirical Alpaca fill-quality
stats at retail size (no credible public measurement — log our own implementation
shortfall instead); pysystemtrade exact current file paths (grep, don't hardcode).
