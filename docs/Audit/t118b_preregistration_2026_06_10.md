# T-118b PRE-REGISTRATION — Crisis-Replay Evaluation of the Regime-Transition De-Grossing Overlay

> ## ADDENDUM v2 (2026-06-10, SAME DAY, still PRE-UNBLINDING — supersedes the
> ## conflicting clauses below; every change TIGHTENS or DISCLOSES, none loosens)
>
> An adversarial red-team review of the director's decisions (independent
> fresh-context agent, run before any T-118 output existed) found three defects in
> v1. C's campaign is still in flight; nothing has been unblinded. Corrections:
>
> **1. The episode list is RE-DERIVED honestly from the locked mechanical rule.**
> Applying "S&P 500 TR peak-to-trough DD ≥ 15%" over 2000-2025 actually yields:
> **dotcom (2000-03→2002-10, ~−47%), GFC, 2011, 2018Q4, COVID-2020, 2022.**
> v1's E3 (2015-05→2016-02, ~−13/14% TR) does NOT clear the threshold and is
> REMOVED. Dotcom DOES clear it and was wrongly absent. DISCLOSURE: the crisis
> HMM's data floor is 2006-04 (T-103) — the overlay is structurally blind to
> dotcom. Resolution (the less-favorable-to-the-overlay form): the GATE evaluates
> the **5 actionable episodes {GFC, 2011, 2018Q4, COVID, 2022}**; the dotcom
> window's ΔMaxDD is computed and REPORTED alongside (expected ≈ 0) with the
> blindness stated as a deployment caveat in any recommendation. Sign test
> becomes **≥ 4/5**; median is over 5 episodes.
>
> **2. IN-SAMPLE/OOS asymmetry disclosed + a new OOS requirement (tightening).**
> The driving model trained on 2006-04→2019-12 (T-103): **GFC, 2011, 2018Q4 are
> IN-SAMPLE for the HMM; COVID and 2022 are OOS.** New co-equal PASS criterion:
> **both OOS episodes must individually improve (ΔMaxDD > +0.5pp).** In-sample
> and OOS results are reported as separate splits, always.
>
> **3. Return-units benefit floor added (closes the net-negative-PASS hole).**
> New co-equal PASS criteria: (a) **26-yr cumulative return: overlay-on ≥
> overlay-off** (terminal-wealth not worse — benefit-minus-drag in one number);
> (b) the research's ratio test, operationalized: **episode-frequency-annualized
> crisis benefit ≥ 3× the realized calm-period drag**. And a binding-episode
> floor: **GFC ΔMaxDD ≥ +5pp** (an overlay that can't materially blunt the
> episode that motivates it does not PASS).
>
> **4. PRIMARY CONFIG designated (closes the best-of-36 multiplicity hole).**
> The gate is evaluated on ONE pre-designated configuration: **de-gross level
> 0.5 × k = 5 days × the hysteresis pair closest to the shipped RiskConfig
> defaults (degross_delta 0.4 / regross_level 0.3 / regross_bars 10)** — the
> center-of-grid default, named before any results exist. All other campaign
> configs are SENSITIVITY ONLY; if a different config is ever preferred, it
> requires fresh out-of-sample validation under a new pre-registration. The
> no-multiplicity claim in §3 below holds only under this designation.
>
> v1's §5 thresholds otherwise stand (median ΔMaxDD ≥ +3pp across the 5
> actionable episodes; calm-drag ceiling unchanged; no-single-episode >50%).
> PASS now requires ALL of: v1 (i)-(iv) + OOS-both-improve + terminal-wealth +
> 3× ratio + GFC floor. This addendum is committed while the campaign runs;
> after unblinding, no further edits of any kind.

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
