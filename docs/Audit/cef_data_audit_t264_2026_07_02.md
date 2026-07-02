# T-264 — CEF-discount capture: DATA / FEASIBILITY AUDIT (Wave 2.2)

**Date:** 2026-07-02 · **Agent:** C · Branch `feature/cef-data-audit-t264`
Feasibility only (T-249-style) — **0 N_trials, nothing run.** Question: can free CEF data yield a point-in-time, survivorship-honest panel of discounts to test the discount-reversion alpha (gap audit Part 4: long-quintile significant in BOTH OOS halves 1998-2011, no decay, ~10%/yr over market, institutions structurally excluded)?

## VERDICT
**A PIT / survivorship-HONEST free panel: NO** (the T-249 trap repeats). **A free SURVIVOR-ONLY panel: YES — and for THIS strategy that is a defensible CONSERVATIVE LOWER BOUND, not the usual inflationary bias.** Depth, liquidity, and NAV are all adequate free; survivorship is the one failure, and its direction is (unusually) in our favor.

## What free data delivers (all verified live 2026-07-02, yfinance)
- **NAV is free** via the `X<TKR>X` pseudo-ticker (e.g. PTY↔XPTYX, GAB↔XGABX, USA↔XUSAX). discount = price/NAV − 1 computes cleanly and matches known CEF behaviour: PTY **+5.2%** premium (PIMCO always-premium — correct), GAB **−8.4%**, USA **−14.0%** chronic discount (correct). The convention is not universal (ADX's XADXX is empty) → the NAV ticker must be discovered per fund.
- **Depth:** NAV history back to **1999** (XGABX, XUSAX), 2003 (XPTYX), 2012 (XPDIX). Covers the academic 1998-2011 window AND extends 15yr past it → a genuine post-publication decay test (McLean-Pontiff).
- **Liquidity at $5-15K is a NON-ISSUE:** the ~10-20 liquid CEFs run $2-43M/day ADV → a $10K position is **0.02-0.5% of ADV**. The paper's "4th-5th NYSE decile" capacity worry is institutional; it does not bind at retail Roth size. Clean pass.
- **NAV staleness:** manageable yellow flag — NAV-unchanged-days 8% (GAB/USA) to 20% (PTY). Must lag-align (compare price to the correctly-dated NAV) and prefer funds with clean daily NAV; a naive same-day discount on a stale-NAV fund is noise.

## The one failure — survivorship (structural, but conservative here)
Dead / merged / open-ended / liquidated CEFs **vanish entirely** from yfinance (price AND NAV gone): confirmed TICC (→merged 2018), BQH, FGB, JPS, BLE, MUE, JMT — **7 of a 25-name sample** returned zero rows. CEFConnect (the purpose-built source) is bot-blocked from here (persistent timeout) and is itself survivor-oriented. So a panel built today = **survivor-only**. Same trap as T-249 (Stooq) / Norgate-Silver.

**BUT the bias direction is unusual and in our favour.** For discount-CAPTURE the corporate events that REALISE the discount — liquidation, open-ending, merger, activist termination (Saba et al.) — are the SAME events that delist the fund. Wide-discount funds are the strategy's targets, their termination-at-NAV is the strategy's biggest WIN, and that termination is the delisting. So a survivor-only panel systematically **drops the biggest winners** → it **UNDERSTATES** the edge. This makes a survivor-only backtest a conservative **LOWER BOUND**: if discount-reversion clears the gauntlet even survivor-only (missing its best trades), the edge is real and bias-defeating; if it fails, the result is inconclusive (the wins may be in the delisted tail). (Caveat: not perfectly one-sided — a minority of funds delist at chronic wide discounts without reverting, i.e. held losers also dropped; but event-driven terminations dominate, so the net lean is conservative.)

## Pricing the survivorship-honest alternatives (free failed)
- **CRSP (WRDS) / Morningstar Direct** — the paper's substrate, survivorship-complete with delisted funds + daily NAV. Institutional/academic pricing (WRDS ~$$$$ /yr, not retail). This is the clean two-sided tier — the CEF analogue of T-249's Platinum.
- **cefdata.com** returned 200 (349KB) — an unverified possible source; would itself need a survivorship audit before trust (assume survivor-oriented until proven).
- **SEC EDGAR** gives a PIT survivorship-honest fund LIST (N-CEN/N-2 filings persist for dead funds) but only periodic (monthly/quarterly) NAV, not daily — it can validate WHICH funds existed as-of a date, but cannot resurrect the dead funds' daily price/NAV series for free.
- **Forward PIT capture** (start recording the universe today, incl. deaths) is survivorship-honest going forward but has ZERO usable history now.

## PRE-REGISTRATION (do NOT run — director gate) — survivor-only LOWER-BOUND probe
Written because the data qualifies as a conservative lower bound. If the director prefers a clean two-sided test, that requires paid CRSP.
- **Universe:** ~15-20 liquid CEFs with clean daily NAV coverage back to ≥2005 (PTY/PDI/GAB/USA/RVT/UTF/DNP/ADX/BME/… — NAV-ticker-verified, ADV>$2M, NAV-stale-days<15%). **Survivor-only — this is the pre-registered central caveat; the verdict is a LOWER BOUND.**
- **Signal:** monthly, long-only z-score of each fund's discount vs its own trailing 1-yr mean (rich-cheap within-fund), long the cheapest quintile (widest relative discount). No leverage (Roth).
- **Gates (pre-registered):** (1) Sortino + block-bootstrap ci_low vs BOTH robos; (2) **is_it_beta_or_edge** — regress quintile returns on equity (SPY-TR) + credit (HYG/LQD-TR) + the CEF-universe-average return; the alpha claim is the **residual discount-reversion t_HAC**, NOT the (ETF-replicable) beta of the long leg; (3) corr-to-trend-sleeve (does it diversify?); (4) MBL at effective-N; (5) realistic retail cost (spread verified trivial, but include the heavy bid/ask of small CEFs). Distributions are heavy → **irrelevant in the Roth** (a structural Roth fit — a taxable-account edge published as net-of-tax-failing transfers to us tax-free).
- **Honest priors carried:** academic sample ends 2011 (this extends to 2026 = the decay test); Saba CEFS live corroboration is confounded by leverage+activism; survivor-only ⇒ pass=real, fail=inconclusive.
- **N_trials:** ONE pre-registered config (no discount-window or quintile sweep).

**T-264 done.** Feasibility only, 0 N_trials, nothing run.
