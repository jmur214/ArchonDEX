# 02 — Route research: what could actually beat SPY (Phase 2, 2026-09-30)

> Alpha-frontier review, branch `research/alpha-frontier-2026-09-30`. Five research passes (one per
> route group plus a data-liveness sweep) using web search; the egress proxy blocked every page fetch,
> so **every claim below rests on search-result snippets plus prior knowledge**, labeled
> "search-verified 2026" (SV) or "from memory, not live-verified" (MEM) in the source passes. Nothing
> was read in full text. Before any pre-registration below is frozen, the worker must re-verify the
> named source. The project's own papers ledger has 15 entries; this pass adds ~90.

## The route table, filled in

| Route | What it means | Project status (verified in Phase 1) | Verdict for a $10–50k Roth at Alpaca (long-only, no margin/futures/shorts, options Level 2, no crypto in the IRA) | Best surviving hypothesis | Free data today? | Prior (ci_low Δ log TW vs SPY > 0 at ≤ 25% satellite) |
|---|---|---|---|---|---|---|
| **A. Alpha** | Return uncorrelated with SPY | H0 on 109 mega-caps through a stop-loss backtester with two critical referee defects; never tested as raw decile sorts; ML tested once at 1-day horizon over 8 edge signals | Re-test on the right construction (B-1) and universe (B-2/B-4). Non-micro published anomalies are ≈ 7 bp/month post-2005 (Chen-Welch 2026) — the mega-cap H0 will very likely stand | Raw-signal decile re-eval; 6–12-month-horizon GBM ranker on the small-cap panel | yes (on disk) | 20% (any signal, B-1); 12% (ML large-cap); 25% (ML small-cap) |
| **B. Compensated beta** | Premia SPY doesn't hold | Momentum deployed 15%; quality/small-value "straddle" — underpowered by construction (t ≈ 1.3 for a 20% tilt on 26 yr) | **Combinations of negatively correlated tilts at deployable weights were never tested**; that test doubles power. Quality, low-vol, equal-weight, credit, intl, factor rotation: dead for terminal wealth | 60/20/20 VOO/MTUM/AVUV vs 100% VOO on 26 yr (B-9) | yes (French + ETF NAV) | 25% |
| **C. Levered diversified at SPY vol** | Return stacking / risk parity | HRP and RSST refuted on free-borrowing, 0%-cash conventions | **Financing is not the binding constraint** (S&P swaps ≈ SOFR + 40–60 bp). Term premium and product ER are: NTSX-class ≈ 0; SSO/UBT/TMF-class negative under every assumption. HFEA lost 64% in 2022 | NTSX/RSSB-synthetic 90/60 and 1.9× SPY/TLT/GLD RP with honest ER + spread (B-5) | yes (T-306 substrate + product facts) | 15% (NTSX/RSSB), 20% (RP), 0% (SSO/UBT/TMF) |
| **D. Drawdown shaping** | Same CAGR, less depth | Trend sleeve = regime option; timing −5.16pp/yr net of cash | Collars, protective puts, tail funds, buffer ETFs: **dead on terminal wealth** (PPUT 6.6% vs 9.8% CAGR 1986–2018; "Rebuffed" 2025). Most need Level 3 anyway. The only live idea is **trend as a financed overlay** (RSST-class) — Route C with a managed-futures leg | 100% SPY + 25–50% SG-CTA overlay financed at T-bill + 50 bp, 1.0% ER (B-5 arm; F-2 forward) | yes (SG CTA, AQR TSMOM, CBOE indices) | 25% (overlay); < 5% (collars/puts/buffers); 10% (VIX-gated PPUT blend) |
| **E. Capacity-bounded niches** | What a $10B fund cannot hold | On the project's map; T-265 panel built and used only for PEAD (null); T-249 momentum killed on an assumed haircut; T-144 insiders tested on S&P names only; CEF t 2.31 parked | Reachable NOW with Alpaca + data on disk: small-cap momentum, insider clusters ($50M–$500M; §16(b) is the "can't stop"), CEF discount (satellite/forward), S&P deletion reversal. Microcap reversal thin (net SR 0.2–0.6; pro-cyclical). Spinoffs N-limited. ETF NAV gaps dead | Insider clusters (E1), small-cap momentum (A2), CEF 10% satellite + forward book | yes (T-265, Form 4, T-267/T-334) | 25–30% (insiders), 20–30% (momentum), 20–35% (CEF satellite), 15% (deletions), 12% (reversal), 10% (spinoffs) |
| **F. Structural / tax** | Wrapper, TLH, contributions, cash yield | Built; +225–430 bps/yr estimated, unmeasured | Stacks on any winner. Inside the Roth: no TLH/HIFO/state-tax exemption — but no turnover drag either, so the Roth holds whichever satellite clears. Alpaca High-Yield Cash 3.56% APY IRA-eligible; SGOV wins only the spread | (not a route; a multiplier) | — | n/a |
| **G. Volatility / options premia** | Put-write, vol crush, dispersion, gamma | Put-write refuted; everything else blocked on data | **Alpaca IRA = Level 2** (CC, CSP, long calls/puts only). Alpaca options history from 2024-02; real OPRA free after 15 min. Selling premium: dead. Single-stock skew: blocked + deflated (DJKMW RFS 2026: option-factor Sharpes inflated ~10× by ex-post filters). Survivors: long small-cap earnings straddles (forward), IV-conditioned covered calls on IBIT (forward), GEX regime conditioner (SqueezeMetrics CSV 2011+ is the only free true-PIT positioning history) | GEX conditioner; IV-conditioned CC on IBIT; long straddles | forward only | 25% / 20% / 15% |
| **H. Alternative assets** | BTC, crypto basis, commodities, managed futures | BTC 5% shadow; DBMF shadow; carry refuted as beta | **IRAs cannot hold crypto at Alpaca** → BTC leg is IBIT/MSBT-only in the Roth. Funding/basis capture: real premium (BIS "Crypto Carry" > 10% p.a.), **no execution path**; salvageable only as a de-risk signal on the IBIT leg. Home-built trend replication: no free continuous futures post-CHRIS → buy DBMF/KMLM. Gold: hedge case strong, wealth case thin (Erb-Harvey: post-ATH returns low) | RSST 20% stack (forward, 35% — highest on G/H); DBMF/KMLM blend; funding de-risk of IBIT; gold 10% (1 trial) | mostly forward | 35% / 20% / 25% / 25% |
| **I. Information edges** | Text/news/filings | LLM analyst forward-only; historical eval VOID ×2; Lazy Prices leaning H0 on a broken panel | Leak-free stack now exists free (ChronoBERT/GPT MIT yearly vintages; **PIT-4B monthly 2013–2024**). Published leak-free alpha is daily L/S small-cap gross — mismatched. Lazy Prices large-cap: free replication null (S&P 100, 2009–2026, α −0.9%/yr). **Opportunistic insiders** is the one filing signal with mechanism + PIT data + OOS support. Google Trends stays rejected; no free PIT retail-flow proxy | Lazy Prices on T-265 after repair (B-6); ChronoBERT small-cap tone forward book (F-8, AI track) | yes / forward | 10–20% / 10% |
| **J. Execution** | Auction, limits, overnight | Fills 0.26–1.02 bps measured | ≈ 5–15 bps/yr total; overnight drift ≈ 0 since 2021 (NY Fed, Jul 2026); broker/venue ceiling ≈ 0 at Alpaca. Two orders of magnitude below detectability → an implementation-shortfall KPI, not a hypothesis | LOC at close for integer shares; limit for fractional; KPI on real fills | own fills | ~0% visible in ci_low; 60% visible in the KPI |

**Routes dead for this operator (do not dispatch a worker):** fixed-income RV, dispersion, 0DTE,
cross-exchange crypto arb, crypto funding capture as a trade, short premium of any kind, single-stock
IV factors, buffer/collar/tail products, home-built futures trend, quality/low-vol/equal-weight/credit/
international as premia, factor-ETF rotation, small-ETF NAV gaps, spinoffs as a systematic satellite,
microcap reversal below $100M cap.

**The structural point every route runs into:** on 26 years a REAL 25% satellite with 2–4%/yr excess
return and 8–10% tracking error has t ≈ 1.5–2 — its paired `ci_low(Δ log TW)` sits near zero even
when it is real. The bar "ci_low > 0 vs SPY on terminal wealth" is hard for any small satellite; only
high-Sharpe alpha (CEF t 2.31, insider clusters) at 10–25% weight, or a structural stack (RSST-class)
has a realistic chance. The program's ranking reflects this.

## Route A — Alpha on the right universe and model class; Route E — capacity-bounded niches

**Executive verdict.** (1) The substrate math binds before the literature does: at N≈260 the
10-year Alpaca panel (2016→2026) can only clear DSR at point SR ≳ 1.05 (upper-bound form) /
≈ 0.9 (exact) — no long-only small-cap satellite here has that prior. Use the free long-history
portfolio panels (Open Source Asset Pricing 1926–2024; Jensen-Kelly-Pedersen size-split factors) as
the *existence* substrate and the Alpaca panel for *implementability* (costs, delistings, fills);
the satellite paired Δ log-wealth ci_low is the gate, the SR line is context. (2) Strongest Route-E
candidate: insider cluster purchases in the $50M–$500M band — data in hand, "who can't stop" is legally
enforced (§16(b)), capacity-bounded. Prior 25%. (3) Small-cap momentum with measured delisting
returns is worth one trial (T-249's kill was an assumed haircut applied symmetrically; the long
winner-leg's delisting rate within a 1–3-month hold is low — measure it). Prior 20%. (4) Microcap
reversal is structurally thin long-only: HFT liquidity providers are on the same side with better
tech; net Sharpe 0.2–0.6 at 50–100 bps RT, ≤ 0.3 below $300M, returns arrive in VIX spikes (Nagel
2012) — pro-cyclical with no hedge. Prior 12%. (5) GKX-style ML is not known to work post-2020 for
long-only retail; alpha lives in microcaps/distressed/short legs and evaporates at 1-month horizons
after cost. The one honest trial is a 6–12-month-horizon long-only ranker on the small-cap panel.
Prior 15%. (6) Dead: small-ETF NAV gaps; spinoffs as a systematic strategy (N too small, forced-seller
identification is now instant); any published non-micro anomaly (Chen & Welch 2026: 7 bp/month
post-2005 in non-micro stocks, "useless to non-micro-cap portfolio managers").

**Substrate realities.** Costs (bps RT, Alpaca PFOF routing, $500–$2,500 clips): $500M–$2B 40–80;
$100M–$500M 80–150; < $100M 150–400+. Limit-at-mid with 1-day patience; never model market orders.
Roth = asset: zero tax on turnover neutralizes the taxable kill of momentum (Patton-Weller JFE 2020:
7.2–7.6%/yr all-in). Cash-account: T+1, GFV rules, no PDT; multi-day holds fine. Delisting returns:
Shumway (1997) −30% NYSE/AMEX; Shumway-Warther (1999) −55% Nasdaq. The 36% CIK→ticker join loss is
usually delisting-skewed — audit it or it silently reintroduces survivorship bias.

**Free long-history panels.** Open Source Asset Pricing (Chen-Zimmermann; Oct-2025 v2.0.0, 209 signed
predictors, data through Dec 2024, `pip install openassetpricing`, code `OpenSourceAP/CrossSection`):
**viable as a portfolio-returns existence substrate, not for stock-level trading** — signals keyed by
CRSP permno; Price/Size/STreversal omitted; no free permno→ticker crosswalk. Use the per-leg decile
files (EW/VW, NYSE breaks) to test whether the LONG leg of any anomaly survives post-publication and
post-2016 at small-cap breakpoints. JKP global factors (jkpfactors.com, 153 factors, size buckets,
free non-commercial). SEC EDGAR (Form 4, 8-K, 10-12B, N-PORT, Form 25) all free.

### A1 Nonlinear cross-sectional ranker, small-cap panel, long horizon
Gu-Kelly-Xiu (RFS 2020): NN L/S decile SR 1.35 VW / 2.45 EW 1987–2016, gross. Avramov-Cheng-Metzker
(Mgmt Sci 2023): "excluding microcaps, distressed stocks, or high-volatility episodes considerably
attenuates profitability… further deteriorates in the presence of reasonable trading costs."
Blitz-Hanauer-Hoogteijling-Howard (JFDS 2023): 1-month ML net alpha post-2004 ≈ 0; 6–12-month
targets keep net alpha 2004–2021 but load on slow factors. Azevedo-Hoegner-Velikov (RFS forthcoming):
57% haircut after costs/decay/liquidity; LSTM L/S still SR 0.84 in hard-to-arbitrage names. Chen &
Welch (arXiv 2607.06502, 2026): median L/S 48 bp/mo pre-2006 → 7 bp/mo post-2005 non-micro.
**Other side:** mandate-blocked institutions (permanent), retail disposition/extrapolation
(persistent, crowd-sensitive), forced sellers at delisting/reconstitution — real for the long leg in
small caps, absent for non-micro. **Traps:** overlapping 6–12-month labels (purge = horizon + 21d
embargo; CPCV); restated fundamentals — rebuild pre-2020 from SEC FSDS keyed on `filed`; PIT shares
for cap at signal date. **Prior 15%.**

### A2 Small-cap momentum, long-only, measured delisting returns
Novy-Marx-Velikov (RFS 2016): ~50% turnover, 20–57 bps effective-spread costs. Frazzini-Israel-
Moskowitz (JFE 2018): live costs < 1/10 of academic estimates; UMD net 4.34%/yr at $3.7B. Chen-Velikov
(JFQA 2023): 50% → 72% (post-2005) → 93% after-cost decay; average anomaly nets 4 bp/mo. Medhat-
Schmeling (RFS 2022): high-turnover stocks show short-term MOMENTUM, low-turnover 1-month REVERSAL —
the panel spans both; the sign flips with turnover. **Other side:** style-box managers forced to sell
graduating winners (mandate), coverage scarcity (Hong-Lim-Stein 2000), disposition. Crashes (2009,
Nov-2020, 2023) are the price. Use skip-month, EW, buy/hold bands to halve turnover. **Prior 20%.**

### A3 Explicit answer (a): GKX-style ML OOS post-2020 for long-only retail?
**No, not as established.** ACM 2023 / Blitz 2023 / Chen-Welch 2026 / AHV 2023 agree: non-micro long
leg = factor exposure; micro = unimplementable turnover; the only net-alpha variant is long-horizon
and converges on slow factors. Consume ONE trial on the small-cap panel at a 6–12-month horizon with
hold bands (B-4 arm b) — not a 1-day GBM over 8 edge signals, which the literature predicted would
fail exactly as T-149 did.

### E1 Insider clusters / opportunistic purchases, $50M–$500M
Cohen-Malloy-Pomorski (JF 2012): opportunistic VW abnormal 82 bp/mo; most informed are local,
non-executive insiders at small, poorly governed firms. Lakonishok-Lee (RFS 2001): informativeness
concentrated in small firms. Zhao (arXiv 2602.06198 v2, Sept 2026): 17,237 open-market purchases,
1,343 issuers $30M–$500M, 2018–2024, GBM AUC 0.70 OOS-2024, distance-from-52w-high 36% of importance,
purchases after >10% appreciation mean CAR 6.3% — non-refereed but on-universe and recent. **Other
side:** tax-loss sellers, capitulating retail, cap-floor-mandated funds; the insider cannot flip for
six months (§16(b)) and faces enforcement risk; InsiderScore-class professionals cannot deploy in
$30–500M names. The cleanest "can't stop / can't compete" answer in the brief. **Traps:** event time =
acceptance datetime; code P only; drop M/A/F, 10b5-1 (checkbox since 2023; footnote regex before),
4/A amendments; cluster ≥ 3 distinct insiders in 10 trading days; cap at filing date. **Prior 25%.**

### E2 Microcap short-term reversal — explicit answer (b)
Nagel (RFS 2012): reversal = liquidity-provision compensation, VIX-predictable. Dai-Medhat-Novy-Marx-
Rizova (FAJ 2024): stronger in smaller/more volatile, persistent in low-turnover — DFA uses it as a
trade-timing overlay, not a strategy. Medhat-Schmeling: RSI(2)-style buy-the-dip is wrong-signed in the
high-turnover half. Quantitativo small-cap RSI(2): 30.3% CAGR since 1999, 35% MDD — gross, on Norgate.
**Arithmetic:** 3-day holds at 30% invested ≈ 25 round-trips/portfolio-dollar/yr → 19%/yr drag at
75 bps, 25% at 100 bps; a 30%/35% gross system nets 5–11% at 15–20% vol → **net Sharpe 0.2–0.6**,
≤ 0.3 below $300M, negative in 2021–24 meme conditions, returns in VIX spikes. Free survivorship-free
data: the operator's own Alpaca-SIP + SEC Form 25 panel is the best free option (EODHD/FMP delisted
endpoints exist, throttled free tiers; Norgate is the standard). **Prior 12%** — if it survives, as an
entry-timing overlay for E1/A2, not a satellite.

### E3 Small-cap spinoffs — mechanism real, N too small
Cusatis-Miles-Woolridge (1993); replications +12.9% 12-mo / +28.5% 36-mo CAAR; Bloomberg Spin-Off
Index +3–5 pp/yr 2002–2022, "premium narrowed"; Forbes Aug 2026: forced-seller identification is now
instant. ~30–50 US spinoffs/yr, ~10–20 small → ~100–150 events 2016–2026: cannot clear a bootstrap
gate. **Prior 10%.** Keep `spinoff_reversion_v1` as an event-desk input, not a trial.

### E4 CEF discount capture — variants
Pontiff (1995/96): 20% discount → +6%/yr expected. Patro-Piccotti-Wu (JFQA 2017): quintile L/S
14.9%/yr SR 1.52; parametric 18.2% SR 1.92 (gross, pre-2013); half-life 7.7 months. Operator: t_HAC
2.31, MDD −42.7%. **Other side:** ~90% retail-owned, tax-loss/panic selling with no redemption
mechanism — structural; Saba/Bulldog activism on the same side is multi-billion and compressing
discounts (decay, not confirmation). **Data:** NAV via yfinance `X<TKR>X` (unverified live), SEC N-PORT
monthly NAV 2019+, CEFConnect (no API). **Traps:** TR must include 8–12% distributions incl. return
of capital; mergers/liquidations/open-endings remove *winners* — survivorship cuts against the
strategy; ~30% embedded leverage explains the MDD. **Beta-hedge in a Roth:** long SH/PSQ at a
pre-registered fixed ratio (0.9% ER + vol drag), never fitted. **Prior 20%** (≤ 10% satellite unhedged);
10% (inverse-ETF-hedged).

### E5 Index-deletion reversal — durable, uncrowded by neglect, not capacity-bounded
Research Affiliates "Nixed" (2024): S&P 500 deletions outperform > 5%/yr for 5 years 1990–2022;
Vijh (Fin. Mgmt 2022) same for S&P 400; Greenwood-Sammon (HBS 23-025): the announcement-day effect
vanished — a different claim. **Other side:** index funds must sell on the effective date
(mandate, permanent) — but $3–15B names, so a $10B fund can do it; RA is selling it. Separate
demotions from M&A/bankruptcy; N ≈ 100 demotions 2016–2026. **Prior 15%.**

### E6 Small-ETF NAV gaps — DEAD
Persistent premiums only in bond/international/fractional-basket ETFs (Shim-Todorov 2021); equity
gaps are bps and closed intraday by APs; retail cannot redeem. Kill without a trial.

**Route A/E pre-registration summary (metric = ci_low Δ log TW vs SPY at fixed 25% satellite, 10% for
E4; secondary Sortino ci_low; threshold ci_low > 0 AND point ≥ +1%/yr; refute on ci_low ≤ 0 or
satellite MDD < −45%; N = 1 each, no sweeps):**

| ID | Universe | Window | Rebalance | Cost bps RT | Existence substrate |
|---|---|---|---|---|---|
| A1 ML ranker | $50M–$2B, ADV > $250k | 2016–26, CPCV purge 12mo+21d | monthly top decile EW, 20/40 hold bands | 60 / 120 | OSAP long-leg deciles 1963–2024 |
| A2 SC momentum | same, 12-1 skip-month | 2016–26 | monthly top decile EW, bands | 60 / 120 | OSAP `Mom12m` EW long leg 1927–2024 |
| E1 insider clusters | $50M–$500M, ≥3 insiders code P in 10d | 2008–26 ∩ 2016–26 prices | event, T+1 after 3rd filing, hold 126d, ≤ 40 names | 120 | Form 4 2006+ |
| E2 microcap reversal | $100M–$2B, ADV > $500k, low-turnover tercile | 2016–26 | daily, ≤ 5d hold, ≤ 20 names, limit-at-mid | 75 / 150 | JKP `ret_1_0` small/micro |
| E4 CEF | all US equity CEFs, z < −1.5 | 2016–26 TR | monthly, 10% sleeve; hedged arm SH at fixed 0.5β | 30 | Patro et al. 1985–2013 |
| E5 deletions | S&P 500 demotions still listed 30d | 1996–26 | effective+1, hold 36 mo, EW | 30 | RA 1990–2022 |

## Route B — Compensated beta; Route C — levered diversified via levered ETFs; Route D — drawdown shaping

**Executive verdict.** (B) The project's "straddles" are underpowered by construction: a 15–20%
single-factor tilt on 26 years has t ≈ 1.3 even if the long-only premium is real. The one legitimate
combination test — negatively correlated tilts (value × momentum) at deployable weights — roughly
doubles the t-stat for the same alpha per dollar and has never been run. Prior 25%. (C) The binding
constraint is NOT the financing spread (S&P swaps ≈ SOFR + 40–60 bp; the 2022 UPRO/BofA swap at 2.68%
vs SOFR 2.28% implies ~40 bp). It is (a) the forward term premium and (b) the product expense stack.
Δ(1.5× 60/40 − 1× SPY) ≈ 0.6·T − 0.1·E − 0.5·s − ER ± variance ≈ +0.05%/yr at T 1.5%, E 4%, s 0.5%,
ER 0.20% (NTSX-class) — i.e. zero; negative under every assumption with the SSO/UBT/TMF stack
(ER ≈ 0.9% each). Prior 15% (NTSX/RSSB class), ~0% (SSO/UBT/TMF). (D) For terminal wealth every
priced-protection structure is dead: PPUT 6.64% vs S&P 9.80% CAGR 1986–2018; buffer funds trail
reference assets and stock+cash beats them on average *and in drawdowns* (Asness-Cao-Ilmanen-Villalon
JPM 2025, 401 funds). Most options structures are not executable in the wrapper anyway (Alpaca IRA =
Level 2). The one Route-D idea with a live prior is **trend as a financed overlay** (RSST-class), which
is Route C with a managed-futures leg. Prior 25%; < 5% for collars/puts/buffers.

### Route B hypotheses
- **B1 Long-only momentum (deployed at 15%; question is weight).** Jegadeesh-Titman 1993; Asness-
  Moskowitz-Pedersen (JF 2013). MTUM 16.45%/yr vs S&P 13.59% since 2013 (low-quality snippet).
  McLean-Pontiff ~58% post-publication decay; momentum survived better than most; Daniel-Moskowitz
  crashes; Dec-2022 rebalance whipsaw is the live long-only version. **Other side:** benchmark-relative
  institutions with tracking-error budgets and 3-year horizons cannot hold 20-pp lags; taxable
  investors cannot bear 100%+ turnover. A Roth won't-sell holder is exactly the risk-bearer the
  literature pays. Decay channel: ETF crowding (a 2025 preprint, arXiv 2512.11913, unrefereed, claims
  factor half-lives fell from ~60 to ~18 months).
- **B2 Multi-factor at deployable weights — the missing test.** AMP 2013: value and momentum
  negatively correlated. Value not dead: Israel-Laursen-Richardson (JPM 2020); Blitz-Hanauer (JPM 2020)
  "Resurrecting the Value Premium." Live AVUV (small+value+profitability screen) 15.9%/yr vs S&P 8.1%
  since 2019-09 but 9.3% vs 25.0% in 2024. **Power arithmetic:** one 20% tilt with 2%/yr long-only
  alpha and 8% TE → t(26y) ≈ 1.3; two 20% tilts at ρ = −0.3 → α 0.8%, TE 1.9%, t ≈ 2.2. IR ≈ 0.42 is
  still below the 0.55–0.65 DSR line, so the combination is necessary to leave the underpowered regime
  and still likely to straddle unless long-only alphas exceed 2%/yr.
- **B3 Quality/profitability.** Novy-Marx 2013; Asness-Frazzini-Pedersen QMJ (RoF 2019): 4.7%/yr, SR
  0.47 L/S gross. Long-only QUAL is Mag-7-heavy; no convincing counterparty. **SPY with a tilt; do not
  spend trials.**
- **B4 Factor momentum.** Ehsani-Linnainmaa (JF 2022): 6 bp/mo after a losing year vs 51 after a
  winning year; Gupta-Kelly (JPM 2019). Retail form = rotating 4–5 factor ETFs = a timing sleeve the
  project already priced as value-destroying; the academic effect lives in the short leg and 100+
  factors. **Prior < 10%; dead here.**
- **B5 International/EM, equal-weight, low-vol, carry, credit.** VXUS +32% vs VTI +17% in 2025 on a
  −9% dollar vs 10-yr US 14.4% vs intl 8.5% — valuation/currency mean reversion, sign flips with start
  date. RSP ≈ tie. BAB is risk-adjusted only (no cheap levered low-vol product). Carry not implementable
  long-only beyond the term premium. HY excess 1–2% with equity-like drawdowns. **All dead for terminal
  wealth.**

**Free data / traps.** Ken French: Mom monthly through Jun-2026, 6 size×momentum portfolios, size×B/M,
size×OP — gross, monthly, includes microcaps → long-only ETFs capture roughly half (Novy-Marx-Velikov):
pre-register a 50% haircut on French-era alpha or use French only as a sign test. JKP (153 factors,
free non-commercial); OSAP (212 predictors, CC-BY-4.0). ETF NAV: MTUM/QUAL 2013, USMV 2011, AVUV 2019,
VTV/VBR 2004, IWN 2000, RSP 2003 — no factor ETF has 26 years except IWN/RSP; **pre-inception index
histories are backfilled with hindsight — do not use.** `^GSPC` is price-only (≈2%/yr error) — use
`^SP500TR` (1988–) or SPY adjusted; yfinance Adj Close silently changes on re-download; Stooq is
price-only for many ETFs; dozens of closed factor ETFs never appear in current lists.

**Route B pre-registration (B2 primary).** Universe VOO/SPY-TR base; MTUM (French big-high-mom
pre-2013); AVUV (French small-value-robust-profitability pre-2019). Arms (N = 4, pre-declared, no
further search): (i) 60/20/20 VOO/MTUM/AVUV; (ii) 70/15/15; (iii) 80/20/0 (current); (iv) 80/0/20.
Window 2000-01→2026-06; secondary French-only 1963→2026 sign test. Annual rebalance, Roth; cost = ER
(0.03/0.15/0.25%) + 5 bp per rebalanced dollar; 50% alpha haircut on French-era months. Metric Δ log
TW vs 1× SPY-TR, block-bootstrap ci_low > 0; refute on arm (i) ci_low ≤ 0 → multi-factor closed,
momentum stays 15%; any positive arm must also clear DSR at N ≈ 264. **Prior 25%.**

### Route C — the cost stack and the arithmetic
| Product | Exposure | ER | Borrow/NAV | Financing |
|---|---|---|---|---|
| SSO / UPRO | 2× / 3× S&P | 0.87–0.91% | 1.0 / 2.0 | swap ≈ SOFR + 40–60 bp |
| UBT / TMF | 2× / 3× 20y+ UST | 0.95% / 0.90% | 1.0 / 2.0 | swaps + futures (implied repo ≈ SOFR ± 10) |
| NTSX | 90/60 | 0.20% | 0.5 | UST futures implied repo |
| RSSB | 100/100 global stocks/bonds | 0.41% | 1.0 | futures |
| RSST | 100 US stocks / 100 managed futures | 0.99–1.04% | 1.0 | futures |
| ALLW (Bridgewater) | risk parity | 0.85% | ~1+ | futures/swaps |

SOFR 3.88–3.90% (29 Sep 2026); 10y 5.23%, 30y 5.57% → forward long-Treasury carry over cash ≈
1.3–1.7%. Vol drag (L² − L)·σ²/2: SPY 16% at 1.5× → 0.96%/yr; a 10%-vol 60/40 at 1.5× → 0.38%; an
8.5%-vol risk-parity book at 1.9× → 0.62%. **Drag is small for diversified books; not the constraint.**

**1.5× 60/40 vs 1× SPY:** Δ = −0.1·E + 0.6·T − 0.5·s − ER − (σ_p² − σ_e²)/2. At E 4%, T 1.5%, s 0.5%,
ER 0.20 (NTSX): +0.05% (ρ = 0) / −0.2% (ρ = +0.3, post-2022); ER 0.41 (RSSB): −0.16 / −0.4%; SSO+UBT
synthetic (blended ER ≈ 0.9%): −0.65 / −0.9%. **Break-even spread** s* = 2·(0.6T − 0.1E − ER): at
T 1.5, E 4, ER 0.2 → 0.6% (barely above actual); ER 0.9 → never; T 1.0 → 0 (dead); T 2.0 → 1.2%.
The higher the ERP, the worse 1.5× 60/40 looks (you give up 10% equity). **~1.9× SPY/TLT/GLD risk
parity at SPY vol:** break-even SR_rp ≈ (E + 0.9s + ER)/16.2 → 0.31 at E 4%, 0.40 at E 5.5%; realized
RP SR ≈ 0.6 (1972–2025), ≈ 0.45 (2010–25), ≈ 0.2 (2020–25) — straddles exactly where T-248 landed,
and T-248's free borrowing *overstated* it. HFEA (55/45 UPRO/TMF) lost 64.2% in 2022; a 33% one-day
S&P drop wipes UPRO. Bond-equity correlation: Brixton et al. (JPM 2023) positive when inflation
uncertainty dominates; 3-yr rolling ≈ +0.5–0.6 through 2025. **Constraint ranking:** (1) forward term
premium, (2) product ER — kills SSO/UBT/TMF, leaves NTSX/RSSB, (3) correlation regime, (4) spread.
Return-stacking source: Hoffstein-Gordillo 2021 (ReSolve/Newfound) ≈ 4 pp/yr over 60/40 gross, pre-2022.

**Route C data/traps.** Synthetic LETF pre-inception: SPY-TR + TLT/IEF-TR + gold (LBMA via FRED) with
explicit daily reset, ER, T-bill + s; SSO live from Jun 2006 (14.5%/yr vs SPY 8.6% Jun-2006→Jul-2026,
MDD −84.7% vs −55.2%), UPRO/TMF 2009, NTSX 2018, RSSB/RSST 2023 — validate the synthetic on the live
overlap before extending back. FRED: SOFR 2018+, DTB3, DGS10/30, `THREEFYTP10`. Traps: rf as free
borrowing (the T-248/T-296 defect); price-only TLT/GLD; ER on the whole NAV; NTSX rebalances quarterly.

**Route C pre-registration.** Arms (N = 3): (i) NTSX-synthetic 90/60; (ii) RSSB-synthetic 100/100
(US proxy); (iii) 1.9× equal-risk SPY/TLT/GLD via RSSB + GLD + UBT at ER-weighted cost. Cost: ER per
product; borrowed notional × (DTB3 + 50 bp) pre-2018, (SOFR + 50 bp) after; daily reset for
SSO/UBT-type legs, quarterly for NTSX-type; 5 bp per rebalanced dollar. Window 2000-01→2026-06;
robustness 1972-01→2026-06 synthetic. Metric Δ log TW vs SPY-TR, block-bootstrap ci_low; also report
Δ conditional on ρ(stock, bond) > 0 sub-samples. Refute on (i) and (iii) ci_low ≤ 0 → Route C closed;
do not reopen without T > 2% ex ante. **Prior 15% (NTSX/RSSB), 20% (RP at SPY vol), ~0% (SSO/UBT/TMF).**

### Route D hypotheses and verdicts
- **D1 Collars / put spreads (CLL 95-110, CLLZ; base 1986).** Israelov-Klein (JAI 2016): collars
  underperform — the bought put is rich, the sold call not rich enough; sell equity instead. Wilshire/
  Cboe 1986–2018: PPUT 6.64% vs S&P 9.80%; CLL ≈ 6.5–7%. **Dead by ~3 pp/yr for three decades**, and
  needs Level 2/3 — Alpaca IRA verified only for covered calls / CSPs (Level 2 also allows long puts).
- **D2 Covered call / put-write (BXM 10.22%, PUT 9.54% vs S&P 9.80%, 1986–2018).** Parity came from
  1987–2008's fat vol premium; post-2010 BXM lags ~5 pp/yr. Already refuted as a role. **Dead.**
- **D3 Tail hedge (PPUT / Universa).** Israelov-Nielsen "Still Not Cheap" (JPM 2015); Israelov
  "Pathetic Protection" (JAI 2019): position reduction dominates put buying; AQR 2020 "Tail Risk
  Hedging: Contrasting Put and Trend" prefers trend. Universa headlines are on hedge capital; TAIL/CAOS
  negative long-run. **Dead.**
- **D4 VIX-term-structure-gated hedge sizing.** Needs option prices the operator lacks; free proxy =
  blend SPX-TR and PPUT gated on VIX3M/VIX (CBOE CSVs). **Prior 10%**: "Still Not Cheap" is precisely
  the finding that low-VIX puts are still negative-EV. Every gate is a trial.
- **D5 Trend as a financed overlay (not substitution).** Hurst-Ooi-Pedersen (JPM 2017): TSMOM positive
  every decade 1880–2016, positive in 8 of 10 worst 60/40 drawdowns. The project's "value-destroying
  timing" result is the *substitution* result (cash drag); the overlay (100% SPY + x% managed futures,
  financed) is what RSST sells (ER 0.99–1.04%). Free data: SG CTA monthly 2000+, AQR TSMOM 1985+, DBMF
  2019 (0.85%), KMLM 2020 (0.90%), CTA (0.35%, re-check). **Prior 25%**: best-evidenced diversifier, but
  the 2010–19 CTA winter plus ~1.5% all-in overlay cost eats most of a 0.4-Sharpe sleeve's ~3% excess.
- **D6 Buffer ETFs.** Asness-Cao-Ilmanen-Villalon "Rebuffed" (JPM 2025): 401 funds, median fee 0.79%,
  trail reference assets, protection inconsistent; stock+cash beats them on average and in drawdowns.
  **Dead; negative by construction.**

**Route D pre-registration (D5 primary).** Arms (N = 2): (i) 100% SPY-TR + 50% SG-CTA overlay financed
at T-bill + 50 bp with 1.0% ER; (ii) same at 25%. Secondary sign test (N = 1): 90% SPY-TR / 10% PPUT
gated on VIX3M/VIX < 1. Window 2000-01→2026-06. Δ log TW vs SPY-TR, block-bootstrap ci_low; refute on
(i) ci_low ≤ 0 → trend overlay closed, the 5% DBMF shadow stays a clock. **Traps:** Cboe indices are
gross of fees with VWAP fills and include 1987; CLLZ/PPUT were backfilled to 1986 at launch (2008–15);
retail SPX bid-ask is materially worse.

**Dead for a retail Roth won't-sell holder (no trials):** quality, low-vol, equal-weight, credit,
international-as-premium, factor-ETF rotation, single-factor tilts beyond the deployed momentum,
SSO/UBT/TMF-based stacking, HFEA, collars, protective puts, tail funds, put-write, buffer ETFs.

## Route G — Volatility / options premia; Route H — Alternative assets

**Three wrapper facts that kill most of the menu (search-verified 2026).** (1) **Alpaca IRAs are capped
at options Level 2:** covered calls, cash-secured puts, long calls, long puts. No spreads, no short
straddles, no iron condors. (2) **Alpaca IRAs cannot trade crypto** ("Crypto is not supported for IRAs
at this time") — the project's BTC 5% leg is executable in the Roth ONLY via a spot ETF (IBIT; MSBT
0.14% ER launched 2026-04-08) or in the taxable cash account. The BTC shadow-book spec should carry this
line. (3) **Alpaca options data starts 2024-02**; Basic = the "indicative" feed (OPRA-derived but
perturbed — "should not be used for live trading"; trades 15-min delayed); **data older than 15 minutes
is real OPRA on all feeds** → mark forward books from the >15-min OPRA history endpoint, never from
paper-account fills (which hit the indicative feed with randomized partials); log the discrepancy as a
census field.

### G1 Long earnings straddles, small caps — the only earnings-vol trade the Roth can execute
Gao-Xing-Zhang (JFQA 2018): ATM straddles bought 3 days before earnings, held to the announcement,
+3.34% (1996–2013), strongest in small, high-vol, high-kurtosis, low-volume, **high-transaction-cost**
names — the effect lives where spreads are widest. Post-2013 practitioner data is two-sided.
**Duarte-Jones-Khorram-Mo-Wang "Too Good to Be True" (RFS 2026):** option-strategy Sharpes in the
literature are inflated by an order of magnitude by ex-post filters (dropping contracts later found to
have bad quotes); GXZ's OptionMetrics filters are not exempt. **Other side:** retail and institutions
short vol into earnings as a yield product — they cannot stop, but they have repriced. **Free data:**
none clean for 2018–2023 (Dolt mirror is survivorship-biased; OptionsDX is 10 large caps) → forward-only.
**Prereg (forward, N = 0):** Alpaca-optionable, cap $300M–$3B, confirmed earnings date, NBBO straddle
spread ≤ 8% of mid; entry t−3 close via long call + long put; exit first open after; 1.5% NAV per
straddle, ≤ 8 concurrent; costs = paid spread from the OPRA history + per-contract fee; twin = same cash
in SPY; falsifier: after 200 events (~two seasons) mean net straddle return ci_low ≤ 0 or book Δ log
wealth ci_low < 0; **evaluability 2027-06-30.** **Prior 15%.**

### G2 Earnings vol-crush selling — DEAD in the Roth (Level 3 + margin; a single small-cap condor is
5–15% of buying power at $10–50k; one −22% loser per 55% win rate is the month). No trial.

### G3 VRP harvesting — REFUTED as a long-only Roth instrument
The only long-only expression is SVXY: −95% NAV Feb 2018, leverage halved to −0.5×, 10-yr −1.53%/yr vs
5-yr +107% — wealth over any window excluding a crash, destroyed over any including one. Israelov-
Tummala (2017): the best-compensated index options to sell are front-month near-ATM — strikes a
$10–50k account cannot sell on SPX/XSP. **Dead.**

### G4 Single-stock skew / term-structure factors — blocked, and just deflated
Cao-Han (JFE 2013), Bali-Beckmeyer-Moerke-Weigert (2021/23): delta-hedged SHORT strategies needing PIT
surfaces, daily hedging, short options. DJKMW 2026: only a small set of characteristics survive;
headline Sharpes inflated ~10×. Stays "#1 to revisit if budget opens" — and the budget line is now a
PIT single-stock surface *plus* a taxable Level 3 account, not $99/mo ORATS. Not pre-registered.

### G5 Covered-call overlays — terminal-wealth NEGATIVE; one conditional variant survives
Israelov-Nielsen "Covered Calls Uncovered" (FAJ 2015): = long equity + short vol (SR ~1, < 10% of risk)
+ long equity reversal/timing (~25% of risk, no reward). Live: **JEPI +10.99%/yr vs SPY +12.85% since
2020-05; 5-yr 7.51% vs 13.25%; −3.5% vs −18.2% in 2022.** Other side: yield-seeking retail and income
funds — the yield is the product. The one variant with a case: **IV-conditioned** call selling (30-day
IV percentile ≥ 80% and IV−RV ≥ 5 vol pts), executable at Level 1 on the IBIT satellite. **Prereg
(forward, N = 0):** IBIT 5% leg, 30–45 DTE 20–30-delta call sold only on IV-pct ≥ 80% (indicative-feed IV
as trigger, OPRA history as mark); twin = unconditioned IBIT leg; falsifier: after 12 monthly cycles
ci_low < 0 or overlay short in ≥ 2 of the 3 largest up-months; **evaluability 2027-10-31.** **Prior 20%.**

### G6 Dealer-gamma / positioning — the only free TRUE-PIT options-positioning history; conditioner only
Barbon-Buraschi "Gamma Fragility" (2021); Baltussen-Da-Lammers-Martens (JFE 2021): intraday momentum
across 60+ futures 1974–2020 from option-MM and levered-ETF hedging; Baltussen-Da-Soebhag (2024; FRL
2026). **Other side:** option market makers and levered-ETF rebalancers MUST hedge — cannot stop. The
tradable effect is intraday (last 30 min) — untradeable here; the daily-close residue is a regime
variable (realized vol and autocorrelation differ in negative-GEX states) for Engine E. **Free data:**
SqueezeMetrics daily GEX/DIX CSV from 2011-05-02 (published daily → genuinely PIT); FlashAlpha/gextool
strike-level GEX (no archive; all assume dealers short calls/long puts on T−1 OCC OI — an assumption).
**Prereg (forward conditioner, N = 0; optional one-trial backtest 2011–26 "neg-GEX-day RV ≥ 1.3× other
days", N +1):** core with vol-target multiplier halved on days GEX ≤ trailing-252 20th pct; twin =
unconditioned; falsifier after 250 days: ci_low < 0 or conditional-RV ratio < 1.2; **evaluability
2027-10-15.** **Prior 25%** — mechanism real, counterparty compelled, but the executable residue is a
vol-timing tweak and vol-timing has failed `[NN-SUBSTRATE-REVERIFY]` twice.

### H1 Crypto funding / cash-and-carry — real premium, NO execution path; salvageable as a timing signal
Schmeling-Schrimpf-Todorov "Crypto Carry" (BIS WP 1087, rev. Oct 2025 / Mgmt Sci): carry > 10% p.a.
average, episodically > 40%, driven by leveraged trend-chasing retail and margin limits on arb capital;
**high carry predicts subsequent crashes.** 2024 BTC funding ~21%; ETF-vs-CME basis collapsed to ~2% by
Mar-2025 after spot-ETF approval crowded it; 2026 funding 8–15% in August. **Other side:** leveraged
longs paying funding — leverage is the product. **Free data:** Binance `fundingRate` (2019+), Bybit
(full), Hyperliquid (2023+), dYdX v3→v4 break; venue survivorship (FTX, BitMEX) overstates a
cross-venue average; funding ≠ basis. **Execution:** spot-only Alpaca cannot short a perp/future; the
Roth cannot hold spot. BITO *pays* contango; BITA (BlackRock 2026-06-16, 0.65%) is a BTC covered-call
fund (G5 in crypto clothing); ETHB (2026-03-12) captures staking (~2%), not carry. **Carry capture:
dead. Research clock only.** **Prereg (executable residue, forward, N = 0):** IBIT 5% leg → 0% when the
7-day mean Binance+Bybit funding ≥ 0.05%/8h (~55% annualized), else 5%; twin = unconditioned leg;
falsifier after 365 days: ci_low < 0 or < 3 de-risk episodes (unevaluable → extend); **evaluability
2027-09-30.** **Prior 25%.**

### H2 Managed-futures trend — buy, don't build
**Free futures data reality:** Nasdaq Data Link CHRIS deprecated, no replacement; Wiki Continuous
Futures deprecating; Stooq futures bot-walled; Yahoo `GC=F/CL=F/ZN=F` are front-month UNADJUSTED with
roll gaps that corrupt any trend signal; pysystemtrade's supported paths are Barchart (paid) and IBKR.
ReSolve gives away daily gross/net returns of their SG Trend replication 2000-01→2023-01 (form
download) — the only free cost-inclusive trend series, hypothetical, ends 2023. **ETF evidence:** DBMF
(0.85%) elastic-net replication of SG CTA, corr 0.88 since inception, TE 6.76%, since-inception
9.13%/yr vs SG CTA 5.36% (2026-03-31; "fee alpha" plus 2023's 3-sigma miss); KMLM (0.90%) rules-based
Mount Lucas; 2025 DBMF +13.85% / KMLM −2.98%; 2026 YTD +11.2% / +12.6%; MDD −20.4% / −27.5%. **Verdict:**
a home replication on Yahoo front-month data is worse than DBMF by construction. **Prereg (extension of
the accruing book, N = 0):** DBMF 5% leg → 50/50 DBMF/KMLM (replicator diversification; 2025 shows
near-zero same-year correlation); twin = DBMF-only; falsifier after 24 months: blended Δ log wealth
ci_low < 0 vs twin AND blended MDD not lower; **evaluability 2028-09-30.** **Prior 20% (vs SPY at
≤ 25%); 60% that it reduces MDD ≥ 5 pp** — terminal-wealth-vs-SPY is the wrong yardstick for this leg.

### H3 Gold / commodities as a permanent leg — hedge yes, wealth thin
Stock-bond correlation +0.52 in 2022 (range −0.64…+0.52); 12-mo rolling ~0.80 mid-2024 → ~0.16 late
2025. World Gold Council 2025: risk-minimizing gold weight rises in positive-correlation regimes.
Erb-Harvey "The Golden Dilemma" (FAJ 2013) and "Understanding Gold" (SSRN 5525138, 2025): long-run
real return ≈ 0; real price is the dominant predictor; **after all-time highs multi-year returns are
low or negative** — gold is at/near ATH in 2025–26. Other side: central banks (price-insensitive
reserve diversification). **Prereg (one trial + forward):** 10% gold (IAUM 0.09% ER; splice LBMA →
GLD → IAUM), 90% core, monthly, 1971–2026; Δ log TW vs 1× SPY ci_low > 0 AND MDD reduction ≥ 3 pp;
N +1; refute on ci_low < 0 on the full window OR on 2000–2026 alone; forward twin = core without gold,
evaluability 2028-09-30. **Prior 25%.**

### H4 Other long-only-ETF alt items
- **Return-stacked ETFs (RSST 100/100 equity/managed futures; RSSB 100/100 stocks/bonds; NTSX 90/60):**
  the one way a no-margin Roth gets > 100% notional. History short (RSST 2023+). **Prereg (forward, N =
  0):** RSST 20% replacing SPY 20%; twin = SPY; falsifier ci_low < 0 at 24 months; evaluability
  2028-09-30. **Prior 35% — the highest on Routes G/H, because it is beta plus a diversifier, not a
  claimed anomaly.** (Its backtest form is Route D5 / B-5 arm.)
- Buffer ETFs: dead (G5 in a different wrapper). TIPS/REITs/EM bonds: hedge cases only. ETHB staking:
  only if an ETH leg were justified; it is not.

**Dead for a $10–50k Roth at Alpaca:** short straddles/condors/premium selling beyond CC & CSP (Level
2 cap); VRP harvesting (SVXY record); single-stock skew factors (paid surface + short leg + DJKMW);
crypto funding/basis capture (needs a perp or CME short; Roth can't hold crypto at all); home-built
trend replication (no free continuous futures); unconditional covered-call / buffer / BITA-style
wrappers (JEPI −5.7 pp/yr vs SPY over 5 yrs); dispersion, 0DTE, intraday gamma trading.

**Ranked surviving pre-registrations (all forward unless noted):** H4 RSST stack (35%) · G6 GEX
conditioner (25%; optional 1 trial) · H1 funding de-risk of IBIT (25%) · H3 gold 10% (25%, 1 trial) ·
G5 IV-conditioned covered calls on IBIT (20%) · H2 DBMF/KMLM blend (20% vs SPY; 60% for MDD) · G1 long
small-cap straddles (15%). None is likely to move terminal wealth vs SPY alone; their value to the
integrated system is drawdown shaping (H2, H3, G6) and capital efficiency (H4). The data is now free
enough to *observe* options premia; the account rules only let the operator be a *buyer* of them, and
the literature that said buying pays was just deflated by an order of magnitude.

**Paid-tier note (Route G):** ORATS $99–199/mo or Databento historical (~$0.04/GB) unblocks exactly one
frozen pre-registration — G4 single-stock IV-percentile/term-slope conditioning of the G1 straddle
universe (buy only when IV-pct < 40 and term slope inverted), 2019–2026, N +1, hypothesis "conditioned
straddles ≥ 2× unconditioned mean return, ci_low > 0." Nothing else on Route G is worth paying for at
this account size.

## Route I — Information edges (text / filings / attention), leak-free only

**Bottom line.** A leak-free text-scoring stack now exists for free, so the ledger's "STILL OPEN"
ChronoBERT item is technically closable. But every published leak-free alpha is daily-rebalanced,
long/short, small-cap, gross of cost, and decays in days — structurally mismatched to a long-only
monthly core+satellite book. The one filing signal with free PIT data, a mechanism, a legally
rate-limited counterparty, and grey-literature 2008–2024 out-of-sample support is opportunistic
insider purchasing (Cohen-Malloy-Pomorski 2012). Lazy Prices on large caps is a clean null, now
independently replicated for free.

### I-1 Chronologically consistent language models (the scoring engine)
| Model | Vintages | Size | License | Repo (search-verified 2026) |
|---|---|---|---|---|
| ChronoBERT (He, Lv, Manela, **Wu** 2025, arXiv 2502.21206) | 26 yearly, cutoffs 1999-12-31…2024-12-31 | 150M ModernBERT | MIT | `manelalab/chrono-bert-v1-YYYY1231` |
| ChronoGPT (same) | 26 yearly | ~1.55B decoder | MIT (card) | `manelalab/chrono-gpt-v1-YYYY1231` |
| ChronoGPT-Instruct (arXiv 2510.11677) | 1999…2024 | — | — | `manelalab/chrono-gpt-instruct-v1-…` |
| **PIT-4B** (Kelly, Malamud, Schwab, Xu 2026, arXiv 2607.11889, NBER w35247) | **monthly 2013–2024** | 4.2B | not seen | `Diamegs/PIT-4B-YYYYMM` |
| StoriesLM (Sarkar 2024, SSRN 4881024) | 125 yearly | small | — | author site |

Protocol: score year-Y text with the vintage whose cutoff is Y−1. The authors' own return result
(news → next-day, daily L/S, 2008–2023) is Sharpe 4.80 realtime vs 4.90 for Llama-3.1-8B — their
headline is "look-ahead is modest for this task," not "here is alpha"; gross of cost at daily turnover.
No independent replication found; Look-Ahead-Bench (arXiv 2601.13770) is the only third-party PIT
benchmark (standard LLMs lose up to −21.8 pp of in-sample edge OOS; PIT models stable). Feasibility:
ChronoBERT-150M embeds the 771k-article panel on a laptop CPU in hours; PIT-4B needs one Batch GPU.
The return head must be fit on an expanding window ending before the scoring date (a second leak channel).
**Who is on the other side:** news-NLP funds harvest the first-day reaction at latency the operator
cannot match and *can* stop there; what survives is multi-day drift in small/illiquid names where
their capacity binds (Chen-Kelly-Xiu: persists "several days among small stocks").
**Prereg (forward book preferred):** Russell-2000-like tradeable set (price > $5, ADV > $2M), long-only
top-decile monthly-aggregated realtime tone, EW, ≤ 25% satellite; twin = same-universe EW without the
overlay; falsifier ci_low(Δ) ≤ 0 after 24 months of fills or turnover > 150%/yr; N = 0 (forward) or 1
(one frozen backtest spec 2016–2025). **Prior 10%.**

### I-2 Does LLM-text alpha survive leak-free evaluation and costs?
Lopez-Lira & Tang (arXiv 2304.07619 v5; post-cutoff Oct-2021→May-2024): drift concentrated in small
stocks and negative news; L/S profitable at 5–10 bps RT, **unprofitable at 20 bps**. Chen-Kelly-Xiu
(SSRN 4416687, rev. 2026): short-horizon news momentum, several days, small caps only. Kirtac-Germano
(FRL 2024): not leak-free (OPT evaluated inside its training period). Glasserman-Lin (JFDS 2024):
anonymization does not remove identity — consistent with T-339/b. Chen-Green-Gulen-Zhou (AEA 2026):
LLMs over-extrapolate return histories. Gao-Jiang-Yan (arXiv 2512.23847): direct lookahead test.
**Synthesis:** the surviving effect is small-cap, negative-news, multi-day, cost-fragile — the one part
of the space a long-only monthly book cannot harvest except as "exclude the bottom-decile-tone names,"
which no paper tests. Dead for the deploy candidate; alive only as a separate exploration track under
`[NN-AI-GATE]`.

### I-3 Filing-based signals with free PIT data
Data: EDGAR full-text search `efts.sec.gov/LATEST/search-index` (2001+, 10 req/s, UA required);
DERA Financial Statement & Notes monthly ZIPs through 2026-08; Form 4 two-business-day rule since 2002.
- **Lazy Prices (Cohen-Malloy-Nguyen JF 2020).** Free OOS replication `github.com/iqueipopg/lazy-prices`
  (S&P 100, 2009-03→2026-09, 54 variants): headline −0.9%/yr, FF5+MOM α −0.9% (t −0.5); similarity ≈ 1
  for nearly every large cap. The project's "leaning H0" independently confirmed. The short leg carried
  CMN's alpha; LLM reading tools have made the mechanism cheap since 2020. Residual, if any: small/mid
  caps with sparse coverage. **Prior 10% (long leg, S&P); 20% (T-265).**
- **Loughran-McDonald tone.** Index-level 2025 FRL claim (>70% directional, weak); firm-level 0/25
  significant in a FinBERT-vs-LM study. **Prior 5%.**
- **8-K.** Zhao (Mgmt Sci 2017): filing intensity → lower future returns. No item-specific low-coverage
  OOS evidence post-2020. **Prior 5%.**
- **Opportunistic insiders (Cohen-Malloy-Pomorski JF 2012).** Routine = same calendar month 3 years
  running; opportunistic-only VW abnormal 82 bps/month (1986–2007); an Aalto MSc thesis re-ran
  2008–2024 and "reinforced" that only opportunistic trades carry information (grey). Counterparty:
  the insider is legally rate-limited (blackouts, 10b5-1, §16(b)) and Form 4 is public in two days —
  persistence is structural even if quant funds have shaved it. Long-only implementable as an
  overweight on cluster-purchase names. MBL note: a 2010–2025 backtest at SR_target 0.5 needs ≈44 yrs
  at N≈262 → the forward book is the decision instrument; the backtest is exploratory. **Prior 20%**
  (best-in-class free event signal; the 82 bps is a 1986–2007 number).

### I-4 Free point-in-time attention / flow data
- **Wikipedia pageviews** (Wikimedia REST, daily from 2015-07-01; 2026 rate limits 10/min unidentified,
  200/min with UA). Pyun (Econ Letters 2024): rising-view firms earn higher returns through 2023 —
  small journal, no cost/CI. Traps: 2020 agent-taxonomy break; renames/redirects; short-horizon
  reversal. **Prior 7%.**
- **Google Trends — stays rejected.** gtab and pytrends `dailydata` fix cross-window comparability,
  not vintage: every pull is scaled to the requested window's max with Google's *current* classifier.
  pytrends archived Apr 2025; official API alpha-gated (Aug 2026). Only forward capture is clean.
- **Reddit:** Pushshift mod-only since 2023; Arctic Shift free 2005→present; WSB "DD" effect
  (Bradley et al. RFS 2024) is 2020+ meme-concentrated. **Prior 5%.** StockTwits API closed.
- **Retail flow:** BJZZ needs TAQ; Nasdaq RTAT $10/mo (free top-10 only); Robintrack dead. **No free
  PIT retail-flow proxy exists.**

## Route J — Execution as a free, compounding edge (small; run as a KPI, not a hypothesis)
- **Where Alpaca fills sit.** Schwarz-Barber-Huang-Jorion-Odean (JF 2025): 85k simultaneous market
  orders across five brokers, mean round-trip −0.07% to −0.46%, dispersion from wholesalers not PFOF.
  Alpaca's 606 (2025Q3) routes to Virtu/Citadel. The project's measured 0.26–1.02 bps/fill ≈ 1–2 bps RT
  is already at the best end. **Broker/venue ceiling ≈ 0.**
- **Limit vs marketable.** Anand-Samadi-Sokobin (RoF 2026): retail limit orders' implementation
  shortfall ≈ −8 bps net of ~16 bps unfilled opportunity cost. At 0.6× NAV/yr turnover ≈ 5 bps/yr.
- **Overnight as timing.** Lou-Polk-Skouras (JFE 2019; "The Day Destroys the Night" 2024): the split
  is cross-sectional. **NY Fed Liberty Street (July 2026, "The Disappearing Overnight Drift"): ≈ 0
  since 2021; NightShares NSPY/NIWM liquidated Aug 2023.** For a monthly rebalancer: < 2 bps/yr
  historically, ≈ 0 now.
- **Auction choice.** Close is the deepest print; Alpaca supports `opg`/`cls` for whole-share
  market/limit; fractional orders are `day` only. Rule: integer shares LOC at close, fractional
  residual as day-limit near the close. ≈ 2–3 bps/yr.
- **Turn-of-month.** Etula-Rinne-Suominen-Vaittinen (RFS 2020): selling t−8…t−4, reversal t−3…t−1;
  Quantseeker 2025: the classic window is indistinguishable from other days over the last decade.
  ≤ 5 bps/yr, undetectable at 120 monthly obs.
- **Integer vs fractional.** At $10k/30 names, integer lots give 20–45% gross weight error → fractional
  mandatory (loses auction access); at $50k, 2–4% → integer + auction viable.
- **Total ≈ 5–15 bps/yr, ~20 at most** — two orders of magnitude below what Δ log terminal wealth can
  detect in 10 years. **Pre-register as an implementation-shortfall KPI** (per-order IS vs arrival mid,
  by order type × TIF × time-of-day, real accounts only — paper fills at the quote), N = 0, refutation
  = LOC/limit IS not ≤ marketable IS over ≥ 500 fills. Prior the KPI shows the saving: 60%; prior it is
  visible in ci_low terminal wealth: ~0%.

## Route F — what stacks (one paragraph)
Vanguard Advisor's Alpha 2025 itemizes TLH up to 150 bps, asset location 0–60, rebalancing 12,
behavioral coaching up to 200 (assumption-heavy, taxable-only for the first two); Morningstar Gamma
(~1.59%/yr) is decumulation-phase and mostly does not apply; Betterment's 0.77%/yr TLH is self-reported.
For the Roth + taxable pair, on top of whatever wins: put the highest-turnover, highest-expected-return
satellite in the Roth; index core + TLH in taxable with the cross-account wash guard (Rev. Rul. 2008-5:
a loss is permanently disallowed if repurchased in an IRA within 30 days); lump-sum on the first
eligible day; cash-yield capture — Alpaca High-Yield Cash pays 3.56% APY, IRA-eligible, so SGOV/BIL
wins only the T-bill-minus-3.56% spread (state-tax exemption is irrelevant in the Roth). **Does not apply
inside the Roth:** TLH, HIFO, qualified-dividend treatment, Treasury state-tax exemption — and,
positively, turnover tax drag, which is why the Roth is the right wrapper for any satellite that clears.

## Appendix A — Free-data liveness, September 2026 (search-verified unless marked MEM)

| Source | Provides | Depth | Free-tier limits | Traps | Change vs June 2026 |
|---|---|---|---|---|---|
| Alpaca options historical | bars/trades/quotes/snapshots, OPRA-derived | **from 2024-02 only** | Basic: `indicative` feed (non-tradeable quotes; trades 15-min delayed), 200 calls/min; Algo Trader Plus $99/mo = real OPRA | snapshots are current-chain → ex-post filtered; 2.5 yr cannot clear MBL | none |
| Alpaca stock bars | IEX real-time on Basic; SIP > 15-min-old on all plans | ≈2016 SIP (MEM); IEX minutes from 2020-07 (project measurement) | 200 calls/min, 10k bars/req | IEX ≈ 2–3% of volume | none |
| Alpaca `/v2/assets?status=inactive`, corp-actions | delisted asset master | prices for delisted ≈2016+ | free | status is current-state, not dated; symbol recycling | none |
| Alpaca News (Benzinga) | symbol-tagged full text | 2015+ (2016 gap) | 200 calls/min | tags are current mapping, not PIT | none |
| CBOE index dashboards | VIX/VIX3M/VIX9D/VVIX/SKEW/PUT/BXM/BXMD/CLL/CLLZ/PPUT/CMBO daily | VIX 1990; PUT/BXM 1986–88 | free CSV (cdn URL pattern MEM) | pre-launch values reconstructed; methodology breaks 2003/2014 | none |
| CBOE DataShop | EOD option quotes/greeks | 2000+ | one free sample file per product | samples are single-day | none |
| OptionsDX | EOD→1-min chains, 10 tickers | 2010–2023 | some year×freq combos free | no 2024+; cherry-picked years | none |
| ORATS | EOD 2007+, 1-min 2020+ | — | **no free tier**; $199/mo delayed | — | none |
| ThetaData | tick/1-min options | 4/8/12 yr at $40/$80/$160/mo | **free tier appears retired** (30-Aug-2026 pricing page) | terminal-based, cloud-hostile | free tier gone |
| Polygon → **Massive** (rebrand Oct 2025) | stocks/options REST | free 2y EOD; options is a separate paid sub | 5 calls/min per unsubscribed class | expired-contract lookups patchy | rebrand + price shuffle |
| Databento | OPRA trades/CBBO/definitions | +10y | pay-as-you-go from $0.04/GB; OPRA Standard $199/mo; usage-based live ended Jun 2025 | best PIT integrity (dated definitions) | plan change |
| Dolt `post-no-preference/options` | community EOD chains | 2019→2026-09 | free SQL-over-HTTP (branch `master`) | ~210 SPY contracts/day, 4 expiries — ex-post filtered | live |
| Nasdaq Data Link CHRIS | continuous futures | frozen | deprecated, **no free NDL replacement** | undocumented rolls | docs site retired 2026-08-31 |
| Sharadar SF1/SEP | PIT fundamentals + prices incl. delisted, 1998+ | full | no true free tier; ≈$69/mo ($499/yr) bundle (conflicting) | SF1 genuinely PIT | unverifiable live |
| Stooq | daily global | decades | bot-wall ("Exceeded the daily hits limit") still the failure mode | survivorship-biased; roll rule undocumented | assume unchanged |
| Yahoo / yfinance | prices; `ES=F GC=F CL=F ZN=F` front-month | ≈2000 (MEM) | 429s endemic from cloud IPs; curl_cffi impersonation | front-month splice, no back-adjustment; ETF backfills | tightened 2025–26 |
| Ken French | FF3/FF5/Mom/portfolios | 1926+ | free | monthly restatements, not vintaged | Aug-2026 update posted |
| **Open Source Asset Pricing** (Chen-Zimmermann) | 212 predictor portfolio returns + characteristics | **Oct-2025 release through Dec 2024** | free; `pip install openassetpricing`; code `github.com/OpenSourceAP/CrossSection` 2.0.0 (Python) | portfolio returns reconstructed ex-post from CRSP/Compustat, not vintaged; signals not redistributable | annual; expect Oct 2026 |
| SEC FSDS / FS&Notes | quarterly XBRL num/sub/tag | 2009Q1→2026Q2 | free | as-filed (PIT-friendly); key on `filed` | none |
| SEC XBRL companyfacts/frames | JSON | 2009+ | 10 req/s, UA required | `frames` = latest value per period → look-ahead; use FSDS | none |
| EDGAR full-text search | filings + exhibits | 2001+ | 10 req/s | — | none |
| SEC Form 4 / 13F zips; FTD | insider txns; holdings 2013Q2+; FTD half-month | FTD ≥ Jun 2026 | free | FTD = balances not flows; 13F 45-day lag | none |
| FINRA RegSHO short volume | daily per symbol per TRF | 2009+ (MEM) | free Query API | off-exchange only (~40–50%) | none |
| FINRA short interest | bi-monthly | Query API `consolidatedShortInterest` with historical filters; "one rolling year online, archive via download" | free | publication lag ~8 bd — use publication date | earliest date unresolved |
| FINRA margin stats | monthly | Jan 1997+ | free Excel | 3-week lag | none |
| Polymarket | markets, `/prices-history`, resolutions | 2020+ | free reads | full history only from Polygon chain | none |
| Kalshi | `/historical/` markets, candles, trades | 2021+ | free; 5,000-candle cap/req | live/historical tier split | none |
| Binance `fundingRate` + data.binance.vision | funding | Sep 2019+ (MEM) | 1000 rows/req; monthly zips | delistings drop silently | none |
| Bybit / OKX | funding | Bybit full; **OKX ~3 months only** | free | archive locally | none |
| Hyperliquid / dYdX v4 / Coinbase Derivatives | funding | HL 500/call hourly; dYdX v4 late 2023+ | free | Coinbase unverified | — |
| Deribit DVOL | vol index candles | 2021-04+ | free | historical option quotes NOT free (Tardis) | none |
| Wikimedia pageviews REST | per-article daily | 2015-07+ | **new 2026 limits: 10/min unidentified, 200/min with UA** | renames/redirects; 2020 agent-taxonomy break | new rate limits |
| Google Trends / pytrends | search interest | 2004+ | pytrends archived Apr 2025; official API alpha-gated (Aug 2026); `trendspy` works | renormalization per window — not vintage | API still not GA |
| Pushshift / Reddit; StockTwits | archives | — | Pushshift mod-only; Arctic Shift free; StockTwits gated | deleted-post bias | none |
| ChronoBERT / ChronoGPT | chronologically consistent LMs | 26 yearly vintages 1999–2024 | free, MIT | yearly granularity | **PIT-4B monthly 2013–2024 (Kelly et al. 2026)** is new |
| Norgate Platinum US | EOD + delisted + PIT constituents, 1990+ | 1990+ | **$346.50/6mo, $630/yr — unchanged** | Windows-only NDU | none |
| EODHD | EOD/fundamentals/delisted | delisted pre-2018 EOD only | $99.99/mo all-in; free 20 calls/day (MEM) | fundamentals not PIT | none |
| Tiingo | EOD + 5y fundamentals | delisted ≈2015+ only | free 500 symbols/mo, 50 req/hr | too shallow for 2000–2016 | none |
| FRED / ALFRED | DGS3MO/DGS10/DFII10/VIXCLS | full | free | **`BAMLH0A0HYM2` (HY OAS) truncated to a rolling 3-year window since April 2026** — pin local snapshots, fail closed if the fetched start date moves | major |
| CEF NAV (CEFConnect; yfinance `X<TKR>X`) | daily NAV/discount | — | free web; no bulk export | gaps; distribution-adjusted | none |
| Free survivorship-complete US daily prices, delisted 2000–2016 | — | — | **none found** (Kaggle Arandkei unknown quality; Quandl WIKI frozen 2018; Zipline bundle dead) | — | Norgate ($630/yr) or Sharadar remain the cheapest honest options |
| Managed-futures ETF NAVs; SG CTA / BTOP50 | ETF NAV; CTA indices | SG CTA daily 2000+ (registration); BTOP50 monthly | free | index survivorship; ETFs short-lived (DBMF 2019, KMLM 2020, CTA 2022) | none |

**Still-live traps the project catalogued:** Yahoo 429 from cloud IPs; Stooq bot-wall; Google Trends
renormalization (plus the client is dead); ETF/index backfills (CBOE PUT/BXM pre-launch reconstructed);
option-chain ex-post filtering in every free source (only Databento definitions or DataShop paid files
are chain-complete). **New trap:** vendor series served through FRED can be truncated retroactively.

## Bibliography (consolidated; SV = search-verified 2026 snippet, MEM = not live-verified)

**Multiple testing, decay, costs**
- Bailey, Borwein, López de Prado, Zhu (2014). Pseudo-Mathematics and Financial Charlatanism. *Notices AMS* 61(5). MEM
- Bailey, López de Prado (2014). The Deflated Sharpe Ratio. *JPM* 40(5). MEM
- McLean, Pontiff (2016). Does Academic Research Destroy Stock Return Predictability? *JF* 71(1). SV (secondary)
- Chen, Velikov (2023). Zeroing In on the Expected Returns of Anomalies. *JFQA* 58(3). https://www.ssrn.com/abstract=3073681 SV
- Chen, Welch (2026). What Useful Alphas? arXiv 2607.06502. SV
- Chen, Zimmermann (2022; Oct-2025 release). Open Source Cross-Sectional Asset Pricing. *CFR*; https://www.openassetpricing.com/data/ ; https://github.com/OpenSourceAP/CrossSection SV
- Jensen, Kelly, Pedersen (2023). Is There a Replication Crisis in Finance? *JF* 78(5); https://jkpfactors.com/data SV
- Novy-Marx, Velikov (2016). A Taxonomy of Anomalies and Their Trading Costs. *RFS*; NBER w20721. SV
- Frazzini, Israel, Moskowitz (2018). Trading Costs of Asset Pricing Anomalies. SSRN 2294498. SV
- Patton, Weller (2020). What You See Is Not What You Get. *JFE*. SV
- Duarte, Jones, Khorram, Mo, Wang (2026). Too Good to Be True: Look-ahead Bias in Empirical Options Research. *RFS*; SSRN 4590083. SV
- Harvey, Liu, Zhu (2016). …and the Cross-Section of Expected Returns. *RFS* 29(1). MEM
- Hou, Xue, Zhang (2020). Replicating Anomalies. *RFS* 33(5). MEM

**Route A / E**
- Gu, Kelly, Xiu (2020). Empirical Asset Pricing via Machine Learning. *RFS* 33(5). SV
- Avramov, Cheng, Metzker (2023). Machine Learning versus Economic Restrictions. *Management Science*. SV
- Blitz, Hanauer, Hoogteijling, Howard (2023). The Term Structure of Machine Learning Alpha. *JFDS*; SSRN 4474637. SV
- Azevedo, Hoegner, Velikov (2023, RFS forthcoming). The Expected Returns on Machine-Learning Strategies. SSRN 4702406. SV
- Medhat, Schmeling (2022). Short-term Momentum. *RFS* 35(3). SV
- Israel, Moskowitz (2013). The Role of Shorting, Firm Size, and Time on Market Anomalies. *JFE*. MEM
- Hong, Lim, Stein (2000). Bad News Travels Slowly. *JF*. MEM
- Cohen, Malloy, Pomorski (2012). Decoding Inside Information. *JF* 67(3); SSRN 1692517. SV
- Lakonishok, Lee (2001). Are Insider Trades Informative? *RFS*. MEM
- Zhao (2026). Insider Purchases Far Below the 52-Week High. arXiv 2602.06198 v2. SV
- Nagel (2012). Evaporating Liquidity. *RFS* 25(7). SV
- Dai, Medhat, Novy-Marx, Rizova (2024). Reversals and the Returns to Liquidity Provision. *FAJ* 80(2); NBER w30917. SV
- Cusatis, Miles, Woolridge (1993). Restructuring through Spinoffs. *JFE*. MEM
- Pontiff (1995/1996). Closed-end fund premia / Costly arbitrage. *JFE / QJE*. MEM
- Patro, Piccotti, Wu (2017). Exploiting Closed-End Fund Discounts. *JFQA*. SV
- Research Affiliates (2024). Nixed: The Upside of Getting Dumped. SV
- Vijh (2022). Negative returns on addition to the S&P 500…? *Financial Management*. SV
- Greenwood, Sammon (2022). The Disappearing Index Effect. HBS WP 23-025. SV
- Shim, Todorov (2021). ETFs, Illiquid Assets, and Fire Sales. SV (venue MEM)
- Shumway (1997); Shumway, Warther (1999). Delisting bias. *JF*. SV (secondary)
- Quantpedia short-term reversal screener; Quantitativo cumulative-RSI post. SV

**Route B / C / D**
- Jegadeesh, Titman (1993). Returns to Buying Winners and Selling Losers. *JF*. MEM
- Asness, Moskowitz, Pedersen (2013). Value and Momentum Everywhere. *JF* 68(3). SV
- Daniel, Moskowitz (2016). Momentum Crashes. *JFE*. MEM
- Israel, Laursen, Richardson (2020). Is (Systematic) Value Investing Dead? *JPM* 47(2). SV
- Blitz, Hanauer (2020). Resurrecting the Value Premium. *JPM* 47(2). SV
- Asness, Frazzini, Pedersen (2019). Quality Minus Junk. *RoF*. MEM
- Ehsani, Linnainmaa (2022). Factor Momentum and the Momentum Factor. *JF* 77(3). SV
- Gupta, Kelly (2019). Factor Momentum Everywhere. *JPM*. MEM
- Frazzini, Pedersen (2014). Betting Against Beta. *JFE*. MEM
- Koijen, Moskowitz, Pedersen, Vrugt (2018). Carry. *JFE*. MEM
- Brixton, Brooks, Hecht, Ilmanen, Maloney, McQuinn (2023). A Changing Stock–Bond Correlation. *JPM* 49(4). SV
- Hoffstein, Gordillo et al. (2021). Return Stacking. ReSolve/Newfound. SV
- Hurst, Ooi, Pedersen (2017). A Century of Evidence on Trend-Following Investing. *JPM* 44(1). SV
- Ilmanen, Thapar, Tummala, Villalon (2020). Tail Risk Hedging: Contrasting Put and Trend Strategies. AQR. SV
- Israelov, Nielsen (2015). Still Not Cheap. *JPM* 41(4). SV
- Israelov (2019). Pathetic Protection. *JAI*. SV
- Israelov, Klein (2016). Risk and Return of Equity Index Collar Strategies. *JAI*. SV
- Asness, Cao, Ilmanen, Villalon (2025). Rebuffed: An Empirical Review of Buffer Funds. *JPM* 51(10). SV
- Wilshire/Cboe (2019). Options-Based Benchmark Indexes. SV; Cboe Collar Indices Methodology. SV
- arXiv 2512.11913 (2025). Not All Factors Crowd Equally. unrefereed. SV
- Product facts: SSO/UPRO/UBT/TMF/NTSX/RSSB/RSST/ALLW/DBMF/KMLM/CTA ERs (issuer pages, etfdb). SV; SOFR/DGS10 (FRED). SV; HFEA 2022 (blog). SV-lowq

**Route G / H**
- Gao, Xing, Zhang (2018). Anticipating Uncertainty: Straddles around Earnings Announcements. *JFQA* 53(6). SV
- Israelov, Nielsen (2014, 2015). One Fact and Eight Myths; Covered Calls Uncovered. *FAJ*. SV
- Israelov, Tummala (2017). Which Index Options Should You Sell? SSRN 2990542. SV
- Cao, Han (2013). Cross section of option returns and idiosyncratic stock volatility. *JFE* 108(1). SV
- Bali, Beckmeyer, Moerke, Weigert (2021/23). Option Return Predictability with Machine Learning. SV
- Barbon, Buraschi (2021). Gamma Fragility. SV
- Baltussen, Da, Lammers, Martens (2021). Hedging Demand and Market Intraday Momentum. *JFE*. SV
- Baltussen, Da, Soebhag (2024; FRL 2026). End-of-Day Reversal; Does gamma survive the close? SV
- Schmeling, Schrimpf, Todorov (2023, rev. 2025). Crypto Carry. BIS WP 1087 / *Mgmt Sci*. SV
- Erb, Harvey (2013). The Golden Dilemma. *FAJ*; (2025) Understanding Gold. SSRN 5525138. SV
- ReSolve (2023). Peering Around Corners: How to Replicate Trend Following Managed Futures (+ free daily data). SV
- World Gold Council (2025). Gold's optimal portfolio weight in a higher correlated environment. SV
- DBMF factsheet (Apr 2026); "DBMF Deconstructed" (Substack). SV; CoinDesk (2025-03-21) ETF cash-and-carry collapse. SV
- Alpaca docs: historical option data; IRA overview; option levels; IRA crypto. SV; SqueezeMetrics GEX/DIX. SV (secondary); Binance/Bybit/Hyperliquid funding APIs. SV

**Route I / J / F**
- He, Lv, Manela, Wu (2025). Chronologically Consistent Large Language Models. arXiv 2502.21206; https://huggingface.co/manelalab SV
- He, Lv, Manela, Wu (2025). Instruction Tuning Chronologically Consistent LMs. arXiv 2510.11677. SV
- Kelly, Malamud, Schwab, Xu (2026). Scaling Point-in-Time Language Models. arXiv 2607.11889 / NBER w35247; https://huggingface.co/Diamegs SV
- Sarkar (2024). StoriesLM. SSRN 4881024. SV; Sarkar, Vafa (2024). Lookahead Bias in Pretrained LMs. SSRN 4754678. SV
- Staffini et al. (2026). Look-Ahead-Bench. arXiv 2601.13770; github.com/benstaf/lookaheadbench. SV
- Gao, Jiang, Yan (2025). A Test of Lookahead Bias in LLM Forecasts. arXiv 2512.23847. SV
- Lopez-Lira, Tang (2023–24). Can ChatGPT Forecast Stock Price Movements? arXiv 2304.07619. SV
- Chen, Kelly, Xiu (2022–26). Expected Returns and Large Language Models. SSRN 4416687. SV
- Kirtac, Germano (2024). Sentiment trading with LLMs. *FRL* 62. SV
- Glasserman, Lin (2024). Assessing Look-Ahead Bias in Stock Return Predictions Generated by GPT Sentiment Analysis. *JFDS* 6(1). SV
- Chen, Green, Gulen, Zhou (2024/AEA 2026). What Does ChatGPT Make of Historical Stock Returns? arXiv 2409.11540. SV
- Cohen, Malloy, Nguyen (2020). Lazy Prices. *JF* 75(3). SV; free replication https://github.com/iqueipopg/lazy-prices SV
- Zhao (2017). Does Information Intensity Matter for Stock Returns? Evidence from Form 8-K. *Mgmt Sci*. SV
- Pyun (2024). The Wikipedia Effect. *Econ Letters* / SSRN 5172055. SV; Moat et al. (2013). *Sci. Rep.* MEM
- Djorno, Santillana, Yang (2025/26). Restoring the Forecasting Power of Google Trends. arXiv 2504.07032 / *IJF*. SV; gtab (EPFL). SV
- Boehmer, Jones, Zhang, Zhang (2021). Tracking Retail Investor Activity. *JF*. SV; Barber et al. (2024). A (Sub)penny for Your Thoughts. *JF*. SV
- Schwarz, Barber, Huang, Jorion, Odean (2025). The "Actual Retail Price" of Equity Trades. *JF*. SV
- Anand, Samadi, Sokobin (2024–26). Retail Limit Orders. *RoF* 30(2). SV
- Lou, Polk, Skouras (2019). A Tug of War. *JFE*; (2024) The Day Destroys the Night. SV
- Knuteson (2019/2020). arXiv 1912.01708; 2010.01727. SV
- NY Fed Liberty Street Economics (Jul 2026). The Disappearing Overnight Drift. SV
- Bogousslavsky, Muravyev (2023). Who Trades at the Close? *JFE*. MEM
- Etula, Rinne, Suominen, Vaittinen (2020). Dash for Cash. *RFS* 33(1). SV; Quantseeker (2025). Turn-of-the-Month. SV
- Alpaca Rule 606 2025Q3; orders docs; High-Yield Cash. SV; SEC EDGAR FTS; DERA FS&Notes; Wikimedia rate limits; Arctic Shift; Nasdaq RTAT. SV
- Vanguard Advisor's Alpha 2025; Morningstar Gamma; Betterment TLH. SV; IRS Rev. Rul. 2008-5. MEM
