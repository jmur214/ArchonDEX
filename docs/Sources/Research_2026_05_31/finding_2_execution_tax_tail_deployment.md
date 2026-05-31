<!-- Analyst response to prompt_2 (execution / alt-data / tax mechanics / tail construction / deployment). Received 2026-05-31 in two parts. Faithful structured capture preserving all effect sizes, evidence grades, and the hypothesis stack. Companion: prompt_2_execution_tax_tail_deployment.md -->

# Finding #2 — Deployability under honest priors (analyst review, 2026-05-31)

> **DIRECTOR NOTE (2026-05-31): we are CURRENTLY in a Roth — no tax drag right now.** The tax findings (Q8, H-Tax) are deferred-relevant: we use a Roth as long as possible, so taxes are a LATER concern, not current. The pre-tax Sharpe is the deployment-relevant number while in the Roth. This REORDERS the analyst's verdict — its #1 action ("the wrapper question / open a Roth") is ALREADY DONE. The execution-convention, regime-leakage, multiple-testing, skew-construction, and no-trade-band findings move to the front; the tax frontier work is parked until a taxable wrapper is on the horizon.

## BLUF
Borderline 0.81-Sharpe base is plausibly deployable but only after 4 corrections the architecture ignores or fights. **Execution cost is NOT the problem** (round-trip 2–8 bps, impact <0.1bp; STRONG). The killers in magnitude order: (1) **construction stack is structurally SHORT the convexity we want** (rebalancing + inverse-vol + 30% cap + crowded weighted-sum); (2) the **−0.577 after-tax figure is mis-calibrated 5–10× too harsh** (used 30%/15% not true IL 16.95%/4.95%) — [now moot: we're in a Roth]; (3) **daily-bar HMM cedes 30–70% of paper protective value to the overnight gap** on the only days it must fire; (4) **0.81 → honest live prior ≈ 0.30, 12–15% prob negative.** At borderline Sharpe, Lo 2002 requires **10–25 years of live data** for confirmation — any 12-month "validation" is statistical theater.

## Tier 1A — Execution cost NOT binding
- Almgren 2005 form: $50K AAPL trade impact ≈ **0.003 bp** (3 orders below half-spread). Frazzini-Israel-Moskowitz 2018 ($1.7T live): median 2.62 bps vs VWAP (upper bound for us).
- Honest round-trip: **1.5–4 bps SPY-tier, 5–12 bps lower-tier S&P.** "Just use 5 bps" is FOLKLORE 2–3× too high for mega-cap (Holden-Jacobsen: MTAQ overstates effective spread 50–70%).
- **dSharpe/d(bp_RT) ≈ −0.0015 at 200% turnover.** To sink 0.81→0.4 kill needs **266 added bps** (implausible); even at 800% turnover, 67 bps. **Execution cost cannot sink this.** Biggest uncertainty = σ assumption (if concentrated vol ~22% not 13%, thresholds scale ~70% up).

## Tier 1B — Fill-timing convention is where optimism hides
- **Lou-Polk-Skouras 2019 JFE:** cross-sectional momentum alpha is almost ENTIRELY overnight (close-open +1.88%/mo, intraday −1.43%/mo). Bogousslavsky-Muravyev 2023: 8.1 bps closing-price deviation reverts overnight → close-to-close backtest imports both uncapturable overnight alpha AND auction reversion noise.
- Haircut at next-open MOO vs MOC: **momentum loses 40–110 bps/mo**; value/quality/profitability <5 bps/mo; low-vol 20–40%. Bid-ask bounce adds 5–15 bps/mo spurious reversal "alpha" in close-to-close.
- **Naive t-1-close→t-close overstates momentum 40–120 bps/mo (~0.55 Sharpe if momentum-dominated) — most of our 0.81 could be the convention error itself. Highest-impact diagnostic to run first.**
- Recommend: **next-open MOO + flat 3bp SPY-tier / 8bp lower-tier** as deployment-honest baseline. Intraday bars needed only if turnover >400% or horizon <1d. For 5-day-hold daily, simple cost model captures >90% of variance.

## Tier 1C — Crisis execution bleeds 30–70% of HMM paper value
- Conditional-on-crisis-onset overnight gaps: p50 ≈ 2–3%, p90 ≈ 5–7%, p99 ≈ 8–10%, tail to −15% (3/16/20 = −9.7% gap, MWCB-1 at open; post-9/11 −8.2%). THIN (n≈10 events) but STRONG on jump/drift-burst literature.
- LULD/MWCB mechanics compound; flash-crash stub-quote tail real. **Realistic live capture of paper protective value: 30–60% (central ~40–50%), 20–30% in tails, 10–15% prob zero-or-negative** when drift-burst makes the open the local low.
- Order types: **pure stops worst** (→market at gap); stop-limits often don't fill; **marketable-limits-through-bid + MOO on ETFs best** (5–25 bps ETF, 50–200 single-name at reopen).
- **Haircut the HMM's paper drawdown reduction ×0.40 (range 0.25–0.60); accept possible zero on a single severe day.**

## Tier 1D — Backtest→live haircut → live prior ~0.30
- McLean-Pontiff: −26% OOS / −58% post-pub. **Suhonen-Lennkh-Perez 2017: median 73% deterioration across 215 alt-beta** (most applicable; complex strategies −30pp more). Hou-Xue-Zhang: 65% fail. Harvey-Liu-Zhu: t>3.0.
- DSR corrects in-sample MT + skew/kurt but NOT execution/regime-shift/decay/look-ahead/tax. Residual retention 40–70%.
- Compose: 0.81 → DSR ~0.55–0.70 → MP 26% → ~0.45; Suhonen 73% → ~0.22. **Honest live prior N(mean≈0.30, σ≈0.25), 95% CI [−0.20,+0.80], P(beat 0.81)<10%, P(negative) 12–15%.**
- **Lo 2002: n_years ≈ 6.18/SR². SR=0.4 needs 39yr; 0.6 needs 17yr; 0.8 needs 9.6yr.** 125-day paper SE(Sharpe)≈0.18 → 0.3 live has CI [−0.05,+0.65]. **Can't distinguish skill from luck in any practical forward window. Pre-commit a kill rule; treat year 1 as ruin-avoidance not confirmation.**

## Tier 2 — alt-data, regime inputs, skew construction
- **Q5 alt-data:** STRONG survivors net-of-cost + FREE from EDGAR (T+1/T+2): **short interest / days-to-cover** (Rapach-Ringgenberg-Zhou: "strongest known predictor of aggregate returns") + **Form-4 insider cluster buys** (Cohen-Malloy-Pomorski: ~1.1%/mo). 13F crowding THIN (45-day lag). Sentiment/NLP FOLKLORE-THIN at retail. Google Trends FOLKLORE. **Highest add: short-interest as long-side RISK FILTER + insider cluster buys as confirmation overlay — +0.05–0.15 Sharpe as filter, both free T+1.** Consumes trial budget.
- **Q6 regime inputs:** STRONG leading features — near-term forward spread (Engstrom-Sharpe 2018, dominates 10y-3mo), credit spreads / excess bond premium (Gilchrist-Zakrajšek 2012), VIX term slope (VIX/VIX3M). **But price-only HMM at AUC 0.89 should NOT be expanded without pre-registered embargoed test; AUC 0.89 itself warrants leakage audit. If adding anything, add excess bond premium as ONE theory-grounded feature; don't kitchen-sink.**
- **Q7 skew construction — MOST IMPORTANT STRATEGIC FINDING:** **our construction is structurally SHORT skew, contradicting the tail-capture objective.** (1) periodic rebalancing = short-vol/short-skew/short-gamma (sells winners, buys losers); buy-and-hold/trend has POSITIVE skew. (2) inverse-vol sizing caps right-tail participation (down-weights convex winners). (3) 30%-cap-10-names weighted-sum around crowded momentum/low-vol loads the most crash-prone negatively-skewed exposures. **Combined: engineered for smooth Sharpe AGAINST the fat right tail we want.** Fixes: (a) let winners run (asymmetric/no rebalance, trailing stops); (b) TSMOM/trend overlays (long-skew); (c) explicit small long-vol/options tail sleeve funded from core; (d) barbell. **If tail-capture is genuinely co-equal, the rebalance+inverse-vol+cap stack is the WRONG architecture — a trend/barbell overlay is the structural fix, not a parameter tweak.** THIN on our exact book, STRONG on each mechanism.

## Tier 3 — methodology/ops
- **Q8 tax (Illinois) — [PARKED: we're in a Roth]:** −0.577 used 30%/15% but true IL = **16.95% ST (12% fed + 4.95% IL) low-income → ~40.8% top**, IL flat 4.95% no LT break. So (a) federal ST→LT is the only lever, (b) recoverable fraction highly rate-dependent. At low bracket, harvesting losses can beat deferring gains; at 32%+ LT extension dominates. **Recompute frontier at 16.95% not 30% — taxable viability likely FAR better than −0.577.** §475(f) MTM only if trader-tax-status qualifies (unlikely at $5–15K). Adaptive policy reads marginal bracket → switch harvest(low) vs extend(high).
- **Q9 no-trade bands — cheapest structural fix:** ±20–25% bands capture ~80% of rebalancing benefit at ~30% turnover (Donohue-Yip 2003). For daily-signal book, threshold (not calendar) rebalancing is highest-Sharpe-per-turnover. **Wider bands simultaneously cut turnover (tax), let winners run (restore skew), cut cost — rare Pareto win across all 4 problems. A few lines of code. STRONG.**
- **Q10 ML:** Gu-Kelly-Xiu 2020 — trees/NN beat linear but gain concentrated in MICROCAPS, shallow 2–3-way interactions, value where you can't trade cheaply. **For liquid S&P, nonlinear gain small, not worth overfit risk vs DSR budget. Default = regularized linear (ridge/elastic-net) with monotonic priors; nonlinear ML is a distraction until microcap universe or nonlinear alt-data.** Re-validate AUC 0.89 under purged-CV+embargo (high AUC = classic look-ahead signature).

## Tier 4 — unasked
1. **Wrapper dominates everything — Roth IRA eliminates tax drag, $7K limit matches AUM. "Open a Roth and run there" is the single highest-value action.** [DIRECTOR: ALREADY DONE — we're in a Roth.]
2. **Wash-sale × HMM interaction:** regime de-gross realizes ST losses that wash-sale may disallow on 30-day re-entry. Overlay + tax layer interact, never modeled jointly. [Roth-moot now.]
3. **Psychological sustainability:** 0.30 live Sharpe → 2–3 consecutive losing years likely; kill rule must distinguish "expected drawdown" from "broken" — needs ~5–7yr to tell apart. Pre-commit kill rule in writing before deployment.

## Pre-registered hypotheses (ranked by info-value-per-trial)
- **H-Tax (0 trials, was highest):** recompute after-tax at 16.95% IL + Roth. [DONE/PARKED — we're in Roth; pre-tax 0.81 stands as deployment number.]
- **H-Convention (1 trial) — NOW #1:** re-run baseline with next-open MOO + split-only prices, nothing else. Predict: if momentum-dominated, Sharpe drops 0.2–0.5 from convention alone; if survives >0.5, edge more real than feared.
- **H-Band (1 trial):** replace fixed rebalance with ±20% no-trade bands. Predict turnover −60–70%, skew→positive, (after-tax Sharpe +0.1–0.2 — Roth-moot but turnover/skew/cost still win). Cheapest structural fix.
- **H-Regime-Leakage (0 new strategy trials):** re-validate AUC 0.89 under purged-CV+embargo. Predict 0.6–0.75 honest; if >0.85 audit for look-ahead. [Director: T-089 verified CAUSAL path, AUC held 0.887 — partial pass; still want purged-CV + the missing-2008/1970s caveat.]
- **H-Trend (3–5 trials):** add TSMOM/trend overlay as skew-restoring sleeve. Predict skew→positive, crisis dd −20–40%, standalone 0.3–0.5 diversifying.
- **H-ShortInterest (1–2 trials):** short-interest long-side risk filter. +0.05–0.15 Sharpe.
- **H-Insider (2–3 trials):** Form-4 cluster-buy confirmation overlay. Small lift, better in smaller names, orthogonal.
- **Dominant message: the two highest-value actions consume 0–1 trial and are CORRECTIONS to mis-calibrated assumptions (fill convention, [tax]) — not new alpha searches. Spend scarce DSR budget on H-Convention + H-Band; do H-Regime-Leakage as re-analysis; only then additive sleeves.**
