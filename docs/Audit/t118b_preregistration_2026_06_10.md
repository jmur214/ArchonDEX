# T-118b PRE-REGISTRATION — Crisis-Replay Evaluation of the Regime-Transition De-Grossing Overlay

**Status:** LOCKED 2026-06-10, committed BEFORE any T-118 campaign output has been
seen by anyone (C's 52-cell grid is in flight; no results unblinded). Companion to
`t118_gate_power_critique_logged_2026_06_10.md` (the pre-unblinding power critique)
— this document operationalizes the conditional path that note authorized.
Methodology source: external research 2026-06-10 (blind-spots pass, Area 2), template
adopted with director-calibrated thresholds. Conventions per Kaminski crisis-alpha /
SG-index crisis-window practice; capital accounting in portfolio-NAV terms ONLY
(no Universa-style sleeve-return accounting, ever).

## Standing relationship to the frozen T-118 gate
The frozen T-118 gate (Sharpe-difference ci_low > 0 AND 26-yr MDD −≥25% AND no
single-event dependence) STANDS for the running campaign and is reported first.
This pre-registration governs the SECOND read: a crisis-replay analysis computed
from the SAME campaign artifacts (the 26-yr cells' per-bar equity/gross_notional
snapshots contain every episode) — **zero new compute; this is an analysis
pre-registration, not a new campaign.** If the frozen gate PASSES, this analysis is
reported as corroboration. If the frozen gate FAILS in the specific
power-critique pattern (crisis benefit + small calm drag + Sharpe-CI straddling
zero), THIS evaluation is the pre-registered successor verdict.

## 1. LOCKED EPISODE LIST
Mechanical rule: S&P 500 TR peak-to-trough drawdowns ≥ 15%; window = exact peak
trading day → exact trough trading day + 20 trading days. Six in-sample episodes:
- E1 2007-10 → 2009-03 (+20td)  [GFC]
- E2 2011-04 → 2011-10 (+20td)  [US downgrade/euro crisis]
- E3 2015-05 → 2016-02 (+20td)  [China/oil]
- E4 2018-09 → 2018-12 (+20td)  [Q4 2018]
- E5 2020-02 → 2020-03 (+20td)  [COVID — the FAST crash; tests crash-speed dependence]
- E6 2022-01 → 2022-10 (+20td)  [2022 — the SLOW grind]
Exact peak/trough trading dates are fixed mechanically from the S&P 500 TR series
at analysis time (no discretion); the episode SET above is locked now. Episodes E5
vs E1/E6 deliberately span fast-vs-slow crash speeds (the trend-crisis-alpha decay
critique). Post-registration drawdowns ≥15% append automatically as out-of-sample
episodes — reported, but never retroactively change this evaluation's pass/fail.

## 2. PER-EPISODE METRICS (overlay-on vs overlay-off, identical base, same cells)
a. ΔMaxDD within window (pp; positive = overlay shallower)
b. ΔTotal return within window (pp)
c. Δrealized vol within window
d. Days-to-de-gross from the regime-transition signal (mechanism check, uses the
   T-124 gross_notional column)

## 3. AGGREGATION (one hypothesis, six observations — no per-episode claims)
PRIMARY: median ΔMaxDD across the 6 episodes.
SECONDARY: exact binomial sign test; success = episode ΔMaxDD > +0.5pp.
Within-episode uncertainty: block bootstrap INSIDE episode windows only (5-10-day
blocks; never across the full sample). A Bayesian credible interval on mean
per-episode ΔMaxDD (weakly-informative prior) is reported descriptively.

## 4. CALM-DRAG CEILING (co-equal criterion — this is where the power lives)
Over all non-episode days in the 26-yr window: annualized CAGR(on) − CAGR(off)
must be ≥ **−40 bps**, with the stationary-bootstrap 90% CI excluding **−80 bps**.
Rationale: insurance must be actuarially fair to ourselves — calm drag bounded
well below the historical episode-frequency-annualized crisis benefit.

## 5. PASS / PARTIAL / FAIL (locked)
PASS iff ALL: (i) median ΔMaxDD ≥ **+3pp**; (ii) sign test ≥ **5/6**; (iii) the
calm-drag ceiling holds; (iv) no single episode contributes >50% of the aggregate
equal-weighted benefit. → recommend the overlay to the user-decision gate.
PARTIAL iff (i)+(iii) only → iterate trigger parameters (a NEW pre-registration),
do not deploy.
FAIL otherwise → the transition-trigger overlay family closes at this design;
report plainly.

## 6. INTEGRITY RULES
No post-hoc episode edits. No threshold edits after this commit. The v1-blind
disambiguation cells inform MECHANISM commentary only — never the gate. If any
ambiguity arises in mechanical date-fixing, resolve toward the interpretation
LESS favorable to the overlay and document it.
