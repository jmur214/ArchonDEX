<!-- Analyst response to prompt_1 (alpha sourcing / sizing / regime / convexity / validity / survivorship). Received 2026-05-31. Faithful structured capture preserving all effect sizes, evidence grades, and the full hypothesis stack. Companion: prompt_1_alpha_sizing_regime_validity.md -->

# Finding #1 — Where the edge actually is (analyst review, 2026-05-31)

## Tier bottom-lines
- **Tier 1 (sizing, regime):** N=10 is directionally right but slightly tight; sweep N=15–20 + tighten cap 30%→15–20% for +0.05–0.10 Sharpe, **but not the lever that moves the dollar outcome.** Gradual 1/σ² vol-targeting fails OOS (Cederburg 2020 JFE); **state-discrete/binary switching on a predictive signal works** (Bongaerts-Kang-van Dijk 2020 FAJ: momentum Sharpe ~doubled, MaxDD 54.1%→20.1%). Honest lift +0.10–0.20 Sharpe, 30–50% MaxDD reduction — NOT the +25% Moreira-Muir fantasy.
- **Tier 2 (alpha frontier, convexity):** every classic factor decayed 30–60% post-publication. Realistic after-cost/after-tax retail Sharpe ceiling **~0.5–0.8**; our 0.81 is **at the top of the honest band**. 1.5+ is folklore for this style/scale. Durable retail edges live in capacity-constrained niches (microcap factor combos, illiquidity premium, low-coverage PEAD, Russell reconstitution). Convexity that survives scrutiny at $5–50K: **vol-scaled momentum (Barroso-Santa-Clara, Sharpe 0.53→0.97 in-sample, free)** + managed-futures ETFs (DBMF/KMLM). Long puts, VIX overlays, lottery stocks = net wealth-destroying.
- **Tier 3 (validity, survivorship):** we have **already exceeded the honest validity envelope**. N=260, T=12yr, SR=0.81 → DSR≈0.48 (coin flip), MBL≈12.4yr (on the wire), required-SR-to-clear-DSR≈1.30 (we don't have it). Three exits: pre-registered clustering for M_eff; fresh embargoed OOS; structural data expansion. Survivorship: pre-2020 backtests inflate annual return 50–250 bps (200–600+ if down-cap drift). Norgate Platinum (~$540/yr) justified before live.
- **Tier 4:** highest-value unasked question is **TAXES.** Daily-rebalanced taxable ≈ 100% STCG; drag 200–350 bps/yr → live after-tax Sharpe ~0.30–0.40, below T-bills risk-adjusted. 20-yr terminal-wealth gap on $10K vs money-market ≈ $2,600. **"The arena is wrong before the signal is wrong."**

## Q1 — Position count + concentration cap
- Fundamental Law IR = IC·√BR·TC. 10-name high-active-share book runs TC≈0.5–0.75 (higher than diversified MF) — STRONG framework, THIN specific estimate.
- Modern diversification curve moved far past "10 is enough": Statman 2004 optimum >120 stocks; Domian-Louton-Racine 2007 N=20 5%-tail ~28% below N=100; Alexeev-Tapon 2014 needs 50 calm / 60–100 crisis. **N=10 captures ~90% of diversifiable but only ~73% of total idio risk** → carrying ~3–5pp unwanted annualized idio vol vs N=30.
- Concentration-with-skill IS rewarded: Kacperczyk-Sialm-Zheng 2005 (+1.1–2.4%/yr industry-concentrated); Cremers-Petajisto 2009 (+1.13%/yr top active-share). STRONG.
- **SVD on S&P 500 yields only 5–10 dominant eigenvectors** → 50 names ≈ ~8–15 effective bets, closing the concentrated-vs-diversified gap.
- Kelly: full ≈ 30% (matches our cap); practitioners use ½ or ¼ Kelly → max weight 15% / 7.5%. **Our 30% cap is Kelly-aggressive and probably rarely binds — check how often.**
- Costs: effective spread 2.7–3.5 bps mean S&P, 1–2 mega-cap; round-trip 5–10 bps on zero-commission brokers. **Costs not binding** for N≤30 at our AUM unless on IBKR-Pro $1-min cliff.
- Evidence: framework/curves STRONG; "10 is enough" + "Buffett 5–10 generalizes" FOLKLORE; "N=10 leaving meaningful Sharpe" PLAUSIBLE-THIN.

## Q2 — Regime probability → exposure
- Moreira-Muir +25% is in-sample, not implementable. Cederburg 2020 JFE: vol-managed beats unmanaged in only 53/103 cases, 8/103 significant. Liu-Tang-Zhou 2019: look-ahead bias; post-correction MaxDD 68–93%. **Our empirical "gradual fails" is consensus.**
- Harvey et al. 2018: vol-targeting's only robust cross-asset benefit is left-tail kurtosis reduction, NOT Sharpe.
- **THE key result: Bongaerts-Kang-van Dijk 2020 FAJ** — conventional vol-targeting INCREASED MaxDD in 4/10 markets; **state-discrete (scale only in extreme states) raised Sharpe in all 10, ~doubled momentum Sharpe, MaxDD 54.1%→20.1%, turnover 1.4 vs 2.4.** Our "gradual fails, binary might work" is directly replicated.
- Why gradual misses turns: Cont 2001 vol clustering + leverage effect (neg returns precede vol spikes 1–5d); trailing estimator lags by ~half-life/2; GARCH-σ peaks ~10d AFTER the equity bottom. **Our HMM AUC 0.89 firing weeks ahead is the bypass the literature predicts.**
- Kaminski-Lo 2014 stopping premium: binary stops add 50–100 bps/mo under momentum/regime-switching DGPs; precondition P(dd|ON)>>P(dd|OFF) = exactly our AUC 0.89. Hurst-Ooi-Pedersen 2017: binary trend positive Sharpe every decade since 1880.
- Which lever: edge-set rotation (strongest theory, indirect), gross de-grossing in discrete states (strongest direct empirical), **position-count/cap-tightening have NO academic support (folklore).**
- **Honest reading: NO static overlay reliably adds OOS Sharpe; robust benefit is drawdown/tail-kurtosis reduction. Exception = regime-conditioned discrete switching on a high-AUC signal (+0.10–0.20 Sharpe, 30–50% MaxDD). Pre-register drawdown reduction as primary KPI, NOT Sharpe lift.**

## Q3 — Durable retail alpha frontier
- McLean-Pontiff 2016: −26% OOS, −58% post-publication. Chen-Velikov 2023: post-cost avg anomaly ~4–8 bps/mo gross, best net 10–20, combos ~20 bps/mo. Hou-Xue-Zhang 2020: 65% fail |t|≥1.96, 82% at 2.78. Harvey-Liu-Zhu: t≥3.0 hurdle.
- Our 6 edges: momentum/value/quality/profitability/investment survive with 30–50% haircut + crash risk. **Low-vol/BAB critically weakened** (Novy-Marx-Velikov 2022: ~56% of BAB alpha is microcap; value-weighted tc-adjusted net alpha 16 bps/mo, t=1.20 insignificant). Standalone size dead unless junk-controlled.
- **Realistic ceiling:** best live comp AQR QSPIX 10yr Sharpe ≈ 0.37. Arithmetic: pre-cost 0.9–1.1 → decay → execution → tax → **0.5–0.8 taxable, 0.7–1.0 tax-deferred.** Our 0.81 at top of band → modest overfit risk + limited "more factor work" upside. **1.5+ folklore.**
- Niches that work *because they don't scale* (ideal at our $5–50K): **microcap factor combos** (IR ~0.8–1.0 vs 0.4–0.5 large-cap; ~50 institutional owners vs 1,740; bid-ask 50–200 bps caveat); illiquidity premium 2.7–3.2%; low-coverage PEAD; Russell 2000 reconstitution; insider Form-4 "P" buys in low-coverage; retail-flow mispricing.
- Evidence: decay/cost/BAB/tax STRONG; ceiling 0.5–0.8 + microcap IR + PEAD-survives PLAUSIBLE-THIN; 1.5 retail FOLKLORE.

## Q4 — Convexity / tail capture
- Hurst-Ooi-Pedersen 2017: TSMOM gross Sharpe ~0.77 (net 0.5–0.6), profitable every decade since 1880, positive in 8/10 worst 60/40 drawdowns; monthly skew +0.2 to +1.0. 2008 SG Trend +20.9%, 2022 +27.3%. BUT 2010–2019 "CTA winter" real (3–5yr negative stretches).
- **Barroso-Santa-Clara 2015 = cheapest convexity win:** scale WML to 12% vol via rolling 6mo realized var → Sharpe 0.53→0.97, skew −2.47→−0.42, kurtosis 18.24→2.68, worst month −78.96%→−28.40%, MaxDD −96.69%→−45.20%. Works in all 6 international markets. **Single highest-EV action — a re-weight of an existing signal.**
- Retail implementation: micro futures (MES/M2K/MNQ/MCL/MGC) viable >$25–50K; **DBMF/KMLM** the realistic path (30–50% of headline trend at 1-share min). §1256 60/40 tax (~26.8% blended vs 37%+ STCG), MTM, no wash sale.
- Does NOT work retail: Israelov 2017 "Pathetic Protection" (5% put protection drags 3–5%/yr, divesting equity beats it); VIXY −50.3% annualized 10yr; Bali-Cakici-Whitelaw MAX effect (lottery stocks −1.18%/mo Carhart alpha); Universa barbell not buyable.
- **Allocation at $50K:** 70% convexity budget → vol-scale existing momentum (free), 25% → DBMF/KMLM, 5% cash, 0% long puts/VXX/lottery. At $5K: scrap futures, 20% DBMF + Barroso-Santa-Clara scaling.
- Flag: SG Trend *daily* skew is negative (−0.45); positive skew is monthly+ — match evaluation horizon.

## Q5 — Multiple testing
- DSR benchmark at N=260: 2.853. Daily annualized benchmark = 2.853 × (1/√3024) × √252 = **0.824 — higher than our 0.81.** DSR z ≈ −0.047, **DSR ≈ 0.48 (coin flip).** With kurtosis γ₄=5–7, DSR drops to 0.42–0.46.
- **Required SR to clear DSR≥0.95: ~1.30.** Gap from 0.81 enormous.
- MBL at SR=0.81, N=260: **12.4yr normal; 13–15 at γ₄=5; 16–18 at γ₄=7. On the wire.** Doubling trials 260→520 pushes MBL only to ~13.7yr but raises required SR ~0.04–0.05. **Can iterate forever; validity bar rises faster than SR can move on existing data.**
- **Correlation discount is the highest-leverage move.** Galwey 2009 (preferred over Cheverud): N_eff ≈ 92.9 at ρ=0.3. Lopez de Prado ONC clustering on PnL → cluster count as N. If 260 backtests are ~15–25 distinct ideas, **M_eff≈25–50 defensible** (within-cluster ρ>0.85, across <0.3). At M_eff=30: benchmark 2.85→2.04, MBL 12.4→**6.3yr**, required SR 1.30→**0.94** (still >0.81 but reachable). Defending requires publishing the matrix, clustering procedure, silhouette/gap, sensitivity, bootstrap CI on M_eff, pre-registration.
- Stack: trial registries w/ code+param hashes; t≥3.0; Romano-Wolf stepdown; double-bootstrap FDR; CPCV+DSR+PBO triad; PBO<0.5 minimum, <0.2–0.3 publication-grade.
- **Verdict: exceeded honest envelope. Stop tuning. Reset the OOS.**

## Q6 — Survivorship
- Shumway 1997: missing delisting returns avg −30%; Shumway-Warther 1999: Nasdaq bias 4.7× NYSE, −55% replacement → Banz size effect DISAPPEARS after correction.
- Per-era return inflation (S&P-ish long-bias): 1962–79 ~30–80 bps; 1980–99 ~50–120; **2000–03 dotcom 150–300; 2008–09 GFC 150–250**; 2010–19 ~30–70; 2020 ~50–150. ×2–4 if universe drifts down-cap. Sharpe inflation 0.1–0.3 diversified, 0.3–1.0 concentrated/small. **Long-only momentum most exposed** (loaders are pre-delisting losers).
- Per-era asterisks: 1962–89 very large (testing ~80–150 survivors, not the real S&P); 2000–09 worst decade; 2010–19 moderate (deletion AR collapsed to −0.6% vs −16% in 90s); 2020+ quasi-clean if full coverage.
- Fix: Norgate Platinum ~$540/yr or Sharadar SEP ~$50/mo. **Overwhelmingly justified before live.** "Wikipedia + Shumway haircut" = sanity check only, not primary.

## Q7 — Biggest blind spots (ranked)
1. **Taxes eating most of the edge.** Daily rebal → ~100% STCG; blended 30–45% marginal; drag 150–300 bps/yr; after-tax CAGR ~5.5%, Sharpe 0.45–0.55. 20yr on $10K: gross $46,610 vs after-tax $29,178 vs T-bills $26,533 — beating money-market by ~$2,600. Mitigations ranked: (1) §475(f) MTM election; (2) lengthen holding to LTCG; (3) **IRA/Roth wrapper (eliminates it; $7K limit matches our AUM)**; (4) HIFO lot accounting.
2. **Backtest→live haircut.** Harvey-Liu 2015: SR<1.0 → 30–50% haircut. Cascade 0.81 → 0.65 (MT) → 0.53 → 0.48 (exec) → **0.30–0.36 net.** Run 6+ months realistic paper.
3. **Wrong arena.** Managed futures via §1256 (60/40 tax); TSMOM positive every decade since 1880, 8/10 worst drawdowns = crisis alpha matching our tail objective. **Build a TSMOM-on-futures backtest before more equity work; if it clears 0.6 the equities conversation should end.**
4. **AUC 0.89 suspiciously high** — demands forensic leakage re-exam (purged walk-forward + embargo); if <0.65 under honest CV, overfit. [Director note: our T-089 already verified the AUC used the CAUSAL path, AUC held 0.887 — partial defense; but the "only 3 regimes in 2014-2025, no 2008/1970s" point stands.] Also: ATR is a vol proxy not idio-risk; 10 names + 30% cap may have effective N≈2–3.
5. **Kelly wrong default for tail capture** — regime-conditional fractional Kelly (0.25× unfavorable, 0.75× favorable); joint Kelly needs the 6-strategy correlation matrix.
- Misc: wash-sale nightmare without 475(f); never market-on-open (worst fill); add 5–10 bps unmodeled friction; keep LLM parked as explanation tool not signal.
- **"If my capital":** stop taxable trading until after-tax modeled + 475(f) priced; move retirement capital to IRA; weekend TSMOM-on-futures test; apply DSR+Harvey-Liu → expect ~0.30–0.40 net; tighten concentration to 15% or explicitly own the vol.

## Pre-registered hypotheses (ranked)
- **H1 (highest EV) — after-tax viability:** re-run with realistic STCG model. Keep-trading-taxable threshold: after-tax Sharpe>0.50 AND CAGR>T-bill+200bps.
- **H2 — survivorship correction (mandatory pre-live):** Norgate, re-run pre-2020. Predict return −75±75 bps/yr, Sharpe −0.15±0.15. Disqualify any sub-factor dropping >0.5→<0.3.
- **H3 — multiple-testing reset (mandatory):** ONC clustering, M_eff + bootstrap CI. Live acceptance: DSR≥0.95 AND PBO≤0.3 AND Romano-Wolf t≥3.0 AND fresh-OOS Sharpe≥0.5 CI excludes 0.
- **H4 — discrete regime overlay:** binary kill at P(ON,5d)>0.7, re-entry P<0.3. Deploy if ΔSharpe≥+0.05 CI>0 OR MaxDD reduction≥25%. Falsification: if no variant beats Bonferroni, deploy as pure 30–50% binary de-gross with no Sharpe claim.
- **H5 — vol-scaled momentum (Barroso-Santa-Clara):** 6mo rolling vol scaling, cap 2×, ex-ante. Threshold: OOS 24mo Sharpe +≥0.15 AND kurtosis −≥40%.
- **H6 — TSMOM-on-futures pivot:** 10-instrument micro-futures TSMOM. Threshold Sharpe≥0.6 OOS 2020–25, MaxDD≤15%.
- **H7 — microcap factor combo:** long-only top-quintile V+M+Q sub-$300M, 100bps RT. Threshold gross≥0.85, net≥0.55.
- **H8 — N × cap sweep:** N∈{5,10,15,20,30,50}, cap∈{10,15,20,30}%. Adopt higher-N only if +≥0.10; tighten to 15% if drop<0.03 AND MaxDD −≥2pp. LOW priority.
- **H9 — regime overfit audit:** HMM under purged-walk-forward+embargo. Threshold AUC≥0.75; bench if <0.65.
- **H10 — low-coverage PEAD:** ≤5 analysts AND below-median cap AND +SUE, hold 30–60d. Threshold alpha≥3% t≥2.0.
- **Dominant action:** H1 + the wrapper question, then H3 (reset MT accumulator). Everything else is rounding error vs these two.

## What softens the verdict
Roth/tax-deferred wrapper (+0.2–0.4 ceiling) · honest M_eff≤30 surviving bootstrap · 24mo untouched OOS clearing 0.5 CI>0 in one run. Absent ≥1 of these: **not yet investable in a taxable account at this scale; highest-EV next move is structural (wrapper/instrument/arena), not parametric.**

> **DIRECTOR NOTE (2026-05-31, user-confirmed):** BOTH arenas are live — a
> taxable individual account (Illinois) AND a Roth. The "Roth wrapper"
> softener is therefore **already realized**: in the Roth the +0.2–0.4
> ceiling lift is captured and the strategy IS investable pre-tax at this
> scale. H1 (after-tax viability) stays live but scoped to the TAXABLE
> sleeve — its job is to sort strategies into taxable-eligible vs
> Roth-only. Capital staging: ~$5K start → $50K → 100s K if it proves out
> (futures-scale instruments unlock later, not at the $5K start).
