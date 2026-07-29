---
run_date: 2026-07-28
agent: external research agent (no codebase access, web-enabled), debiased TWO-MESSAGE design
model: Claude Opus 5 — self-reported (per-section)
executed_by: user (separate chat session; relayed verbatim to the director in installments)
prompt_working_copy: data/coordination/prompt_research_agent_v3_2026_07_28.md
status: findings triaged 2026-07-28 (Director Triage below); full verbatim rests in the
  session transcript (87b8cee4) — this doc preserves the complete decision-relevant record
  (all verdicts, numbers, citations, So-whats)
bias_note: the director's brief said "daily bars" as a constraint — the USER flagged this as
  director bias (intraday is DEFERRED in the ledger, not refuted). Queue for the adversarial
  follow-up round.
---

# External Prompt Run — Research Agent v3 (2026-07-28)

Two-message design: MESSAGE 1 = the unanchored map (constraints+goal only, no history);
MESSAGE 2 = revised map + targeted answers after seeing our verdicts. Every claim was flagged
[BACKTEST]/[OOS-REPL]/[LIVE] with per-claim confidence — a discipline worth reusing.

---

# MESSAGE 1 — the unanchored map (headline record)

**TL;DR (verbatim):** "The largest reliable edges are structural, not predictive… Most 'alpha
signal' ideas are large-but-fragile… The honest prior is that you will not beat SPY on gross
returns [SPIVA: 92% of active funds trail over 20yr]. The winning strategy is to stack the
small, near-certain edges… expecting most to fail."

**Blind top-10 (reliability-weighted):** 1 TLH (~30-80bps) · 2 structural moderate leverage
via capital-efficient funds (~1-3%/yr claimed) · 3 asset location (5-30bps) · 4 cost
minimization (5-15bps) · 5 automation/time-in-market (cited 1.2pp Morningstar gap) · 6 global
diversification (robustness) · 7 trend overlay — "mostly Sharpe; usually NET NEGATIVE on
terminal wealth for pure long equity unless combined with leverage" · 8 factor tilts
(momentum/quality the survivors) · 9 rebalancing hygiene / anti-equal-weight · 10 archive
PIT data now (Form 4, 8-K/10-K text, short interest, options-implied).

**NOT-pursue list:** CAPE timing; vol-managed overlays (Cederburg et al. — not implementable
in real time); naive 3× LETF holds (TQQQ −79% in 2022); MA-rule over-optimization (Zakamulin);
high-turnover in taxable; social sentiment; most published anomalies (58% decay, t>3 bar);
LLM-on-history (Lopez-Lira & Tang contamination); crypto (blanket prior — NOTE: disagrees
with our MEASURED T-272 one-era lift; our forward-shadow handling stands, stricter than
either).

**Staged recs:** Stage 0 unconditional (cheap vehicles VOO/SPLG, asset location, immediate
investment, cross-account wash guard, start archiving) → Stage 1 TLH (keep if ≥20bps live) →
Stage 2 leverage decision [later self-retracted] → Stage 3 Roth-only satellites vs
deflated-Sharpe + t>3.

---

# MESSAGE 2 — revised map + targeted answers (headline record)

## Task A verdict table (verbatim)
1 TLH — survives, downgraded hard (decays to ~9bps/yr in yrs 6-10 [Alpha Architect 2023
study]; honest range 30-60bps early → 10-20; budget ~25bps avg) · 2 leverage — **CASUALTY:
"your result covers it, and live records agree with you"** (NTSX −25.84% in 2022 vs −18.11%
SPY, lost to SPY over 8yr; PSLDX +100bps = PIMCO bond alpha, unholdable taxable; "your null
wasn't a cost-assumption artifact"); residual: lifecycle-DECLINING leverage untested but
"2× on $10K is $10K" — low confidence it's worth a trial · 3 asset location — PROMOTED:
trend sleeve Roth-only is a CONSTRAINT not an optimization (100-200bps ST-gains drag at 24%
bracket would exceed the whole edge) · 4 cost minimization — PROMOTED TO #1: **the cash-leg
leak** (Schwab sweep 0.01-0.05% vs T-bills ~3.83% = ~370bp spread on the flat leg; flat ~30%
of time ≈ 110bps/yr on the portfolio; "larger than any alpha in your measured-real column,
riskless") · 5 automation — shrinks 12×: Fulkerson-Jordan-Riley-Yan (FAJ forthcoming, SSRN
4904652) replicate Morningstar's sample → poor timing costs 0.10%/yr; rest is mechanical
cash-flow artifact [VERIFY CITE before rewriting our recorded ~1.2%] · 6 international —
partial casualty: we tested CRISIS CORR (T-313); the LONG-HORIZON terminal-wealth claim
(ACO 39-country 1890-2023) is untested; robustness question, arguably against the mandate ·
7 trend — "your −4.6pp/yr low-yield lag IS the terminal-wealth-vs-Sharpe trap… a Sharpe
strategy with a regime dependency"; AQR 2019: even cash-adjusted, trend's excess was muted ·
8 tilts — our momentum/quality = the literature's surviving set; MTUM live +97-125bps/yr vs
SPY, MaxDD −34.08 vs −55.19; "stop testing new factors" · 9 hygiene · 10 archiving — promoted.

## New suggestions from our history (Task A tail)
(a) **CEF data objection is self-inflicted prospectively** — NAVs published daily free
(sponsors/CEFConnect); archive now = a PIT panel nobody can buy, 5-year fuse. (b) **The
regime dependency is partly ARITHMETIC** (a long/flat strategy mechanically earns cash when
flat) — see Q6. (c) **Two nulls are the same finding**: static-leverage-loses and
gated-2×-execution-bound both say measured slippage ≥ measured edges → execution/turnover
engineering is a first-order target; **Novy-Marx & Velikov buy/hold spread** = "the single
most effective simple cost mitigation" (our T-298 asymmetric damping is family-adjacent;
explicit entry/exit bands untried).

## Task B highlights
**Q1 (crisis streams):** "wrong question — with leverage closed, a crisis hedge is a pure
drag." BTAL works and costs −5.26%/yr live; duration failed 2022; **DBMF is a SLOW-crash
hedge** (+1.80% in 2020 vs +21.53% in 2022; 60-day replication lookback structurally can't
catch a two-week crash) → our frozen T-316 gates get a PRE-STATED crash-speed annotation
(gates unchanged). **"Your flat-leg cash IS your crisis hedge"** — connects to the cash-leg
fix. **Q2 (thematic):** Ben-David et al. — thematic ETFs lose ~4%/yr alpha for 5yrs, driven
by launch-at-peak-overvaluation → the desk's valuable output is "is the theme already in the
price," with 'a thematic ETF now exists' as a negative signal; second-order/supply-chain
literature real but needs a PIT coverage graph we don't have (→ archive queue);
Profit Mirage (51.5-62.2% Sharpe decay past cutoff) VINDICATES the LLM-history ban;
ChronoBERT/ChronoGPT + entity anonymization (Glasserman-Lin; Kim-Muhn-Nikolaev) now make a
GATED exception measurable; **zero audited live LLM investment records exist**; thesis
scoring: the binding constraint is POWER not scoring rule → **mandatory decomposition: ≥10
quarterly-checkable sub-claims per thesis + matched null-generator baseline + score
sub-claims against prediction markets (reading ≠ trading)**. **Q3 (text/alt-data):** Form 4
best (long-leg alpha, opportunistic-vs-routine classification needs accumulated history);
USASpending = the one underexplored gap; Lazy Prices short-leg-bound; Google Trends
structurally unbacktestable (renormalized) = the canonical archive-or-never lesson; 13F dead
on latency; social flow dead. **Q4 (capacity corners):** the largest capacity-constrained
edge = broker cash sweep (an inattention tax, no decay); CEF revive-as-archiving; odd-lot
tenders real, ~$1k/yr, a hobby not a build (mini-tender scams: verify against SEC filing,
never the broker notification); microcap and index-recon dead. **Q5 (holdings):** momentum
satellite = blended intermediate lookback + buy/hold spread + NO crash overlay (crashes live
in the short leg; MTUM's live DD confirms) + Roth-only, ~75-100bps expected, add no more
parameters; conditional contributions = firm null, don't spend a trial; automation ~15bps.

## Q6 — the regime question (the highest-stakes answer)
**F1:** r* estimates span ~0.7%-3.1% — "nobody knows," both sides live. **F2 (uncomfortable):**
Rogoff-Rossi-Schmelzing (AER 2024, 700yr) — real rates trend-stationary around a DECLINING
trend → high-cash-yield eras are the transitory deviation, and the baseline drifts away from
us; low-rate regimes persist decades. "If you rely on high cash yields you are making an
implicit macro bet against a 700-year mean-reversion result — state it explicitly or remove
the reliance." **F3:** most of the regime dependency may be ARITHMETIC — a long/flat strategy
mechanically earns cash when flat; the fix is a reparameterization, not a forecast:
**re-run the 60-year attribution in EXCESS-OF-CASH terms.** Three pre-statable outcomes:
(i) excess-of-cash edge stable across yield regimes → the dependency was the cash term, an
identity; (ii) excess-of-cash edge itself regime-dependent → a genuine conditional effect,
only then worth a conditioning trial; (iii) excess-of-cash edge ≈ 0 throughout → "the
strategy is a cash-yield harvesting vehicle wearing a trend costume, and its future is a
rate forecast." Don't condition on yield regime (no non-data-mined support); reparameterize.
"Nothing else in this document has a better ratio of information gained to effort spent."

## Task C — the allocation answer
**(a) One data source: daily PIT CEF NAV archiving** (runner-up Form 4; archive both).
**(b) One return stream: NONE — decline the premise; take the structural cash-yield capture**
(~110bps/yr riskless at current rates, zero trial cost; "verify first: does your backtest
credit the flat leg with T-bill yield while the live account earns the sweep rate?" —
DIRECTOR: verified YES, backtest credits short rate [T-255], live paper earns 0). If a
stream is demanded: momentum + buy/hold spread, Roth, 10-15%. **(c) One process change:
reparameterize everything into excess-of-cash terms**, starting with the 60-year trend
attribution (runner-up: the anonymization+Chrono LLM protocol).

**The quantified structural stack:** cash-leg +80-120 · Roth-only location +100-200 (vs a
taxable-trend baseline) · expense/execution/turnover +10-25 · TLH +15-40 · sec lending +2-8 ·
automation +10-20 · momentum satellite +10-20 = **+225 to +430bps/yr**, with the caveat that
the two largest are leak-plugs vs a misconfigured baseline, not alpha. **The decisive
asymmetry:** the sleeve's own −460bps low-yield-era lag EXCEEDS the entire structural stack;
over 40yrs, +100-200bps → ×1.5-2.2 terminal, −460bps → ×0.17. "The single largest
terminal-wealth decision in front of you is not what to add. It's whether to run the trend
ensemble at all, and that turns on the Q6 reparameterization."

**Prior on beating SPY over 40yr (agent's estimate):** gross 20-30%; after-tax/after-cost
with the structural stack and the regime risk resolved, 50-60% — "not because you found
alpha… tax location, cash yield, and cost discipline are not zero-sum; they're recoverable
losses, and most retail investors don't recover them."

**Closing (verbatim):** "A multi-year program that produces mostly nulls under
pre-registration… is not a failed program. It's a functioning one. … The main thing I'd
change is where you point that machinery next — at your own cash placement, tax location,
and turnover, which nobody publishes papers about because there's no paper in it."

---

# DIRECTOR TRIAGE (2026-07-28)

**VERIFIED SAME DAY:** the cash-leg claim is REAL in our code — backtest credits the flat
leg at the daily short rate (core/combined_candidate_scorecard.py:190, the T-255 fix); the
live sleeve parks in raw cash (sleeve_constructor.py:100) and no paper-path component
accrues yield. Every live record is structurally biased against the sleeve vs its own
backtest spec; the sleeve's regime-option premium requires ACTUALLY EARNING the cash yield.

**ADOPTED:** T-333 the excess-of-cash attribution (pre-registered, 3 outcomes pre-stated —
the program's top-priority analysis; it decides whether the flagship runs at all) · T-332
cash-leg program (books/digest cash-drag accounting; acct-2 Act-2 holds SGOV-class + VOO
core from day 1; broker-sweep check → transition runbook; acct-1 untouched, annotated) ·
T-334 archive queue (CEF NAV/price/distributions, Form 4, USASpending; keep FINRA/8-K) ·
thesis-desk v2 AFTER the first canonical scan (valuation-embedding claim, thematic-ETF
negative signal, ≥N quarterly sub-claims + null-generator baseline + prediction-market
benchmarking) · buy/hold-spread pre-registered retest (momentum construction; optionally the
T-298 family) · T-316 crash-speed annotation PRE-STATED now, frozen gates unchanged ·
momentum-satellite construction per Q5 · option-package numbers updated (TLH ~25bps).

**USER DECISIONS:** (1) LLM-history ban amendment (recommend: ban stays default; narrow
pre-registered anonymized/Chrono exception class); (2) behavior-gap correction (1.2% →
~0.1-0.2%) pending cite verification (SSRN 4904652); (3) the Rogoff macro-bet statement into
the sleeve's strategy docs.

**DISAGREEMENTS HELD:** crypto (their blanket prior vs our measured T-272 forward-shadow —
our handling stands); international terminal-wealth (legit untested adjacent question;
queued low, robustness-not-edge, arguably against the mandate).

**CROSS-RUN TRIANGULATION** (with 2026-07-28_fresh-eyes-direction-review.md): all three
documents independently converge on — nulls are the base rate; the reliable wins are
structural (cash leg, Roth placement, TLH, hygiene) and archival (PIT accumulation); the
forward laboratories are the right vehicle for everything predictive; and the process asset
(pre-registration + honest N + the census) is the durable thing. The fresh-eyes review adds
the integration-verification asymmetry; this run adds the excess-of-cash lens and the
decision it forces.
