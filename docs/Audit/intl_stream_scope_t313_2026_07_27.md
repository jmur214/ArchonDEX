# T-313 — international-equity 3rd stream: DATA-REALITY SCOPE + VERDICT

**Date:** 2026-07-27 · **Agent:** C · Branch `feature/intl-stream-scope-t313` · **0 N_trials** (scope only, T-264 style)
Scopes whether a deep, free, honest international-equity trend leg can be the genuinely-independent 3rd return stream (tripwire #2 from B/T-305: ≥3 streams with pairwise |corr| < ~0.3 across crises — the still-unfilled "awaits 3rd" from T-248/T-263).

## VERDICT: PARK — refuted at the DATA-REALITY stage. Don't burn a trial.
International equity **co-falls with US in every tail crisis** (corr 0.87–1.00 in 2008/2020/2022 — the T-214 trap, confirmed directly), the free honest floor (1990) **cannot test the one era decorrelation was plausible (1970s)**, and a *trend-ruled* international leg simply flattens to cash in crises = no gain over the sleeve's existing legs. This is a stronger park than T-264/CEF: there the data was merely unavailable; here the data EXISTS (1990+) and the mechanism fails on it.

## Part 1 — Data reality (measured, Ken French library, 2026-07-27)
| source | window | nature | verdict |
|---|---|---|---|
| **Ken French Developed / Developed-ex-US / Japan factors** | **1990-07 → 2026-05 (~36yr, monthly)** | free, academic, honest (Mkt = Mkt-RF + RF) | the deepest FREE honest series — but **shallower than the domestic ~58-64yr** |
| EFA (live intl ETF, tr_reconciled) | 2005 → 2026 (~21yr, daily) | tradeable, TR-reconciled | the live leg; splice onto FF-developed for the 1990-2005 pre-ETF window |
| deep pre-1990 (1970s stagflation) | — | Global Financial Data (PAID); no free honest equivalent found | **the 1970s — where regional decorrelation was most plausible pre-globalization — is UNTESTABLE free** |

**Splice story (if ever built):** FF Developed-ex-US market TR (1990-2005, monthly) → EFA TR (2005+, daily→monthly), chained by returns. Honest floor = 1990. No free path to the 1970s.

## Part 2 — The mechanism, measured directly (this is why it parks)
**intl (Dev-ex-US) vs US (North-Am) correlation — the tripwire-#2 bar is |corr| < ~0.3 across crises:**

| window | corr | reading |
|---|--:|---|
| FULL 1990-2026 | **+0.78** | international is mostly US beta |
| **2008 GFC** | **+0.93** | co-falls |
| **COVID-2020** | **+1.00** | co-falls perfectly — the exact T-214 trap |
| 2022 | **+0.87** | co-falls |

In every crisis that threatens the tail, correlation is **0.87–1.00 — nowhere near the <0.3 bar.** International equity provides **zero crisis diversification**; it is more equity beta, exactly as T-214 (breadth widens correlations in crises) predicted.

**The one candidate decorrelation — Japan's lost decade (1990-2000):** JPN vs US corr **+0.32** (genuinely lower) — BUT Japan returned **−2.2%/yr while US did +15.3%/yr**. That is a slow *divergence where the international leg was a DRAG*, not a crisis where it *protected the tail*. A trend-ruled Japan leg over that decade would have gone flat (downtrend) → parked in cash — i.e. it adds nothing the sleeve's existing cash-when-flat behavior doesn't already do. Decorrelation in a slow bear ≠ tail protection in a fast crash.

## Why trend-ruling doesn't rescue it
A *trend-ruled* international leg flattens to cash when international downtrends — so in 2008/2020/2022 it is just cash, no better than the sleeve's other legs going flat. Its only potential value is in calm times when international trends up while decorrelated from US — but in calm times the correlation is still **+0.78**. Neither regime delivers diversification.

## Recommendation
**PARK the international-equity 3rd stream** — it is the T-214 trap on a shorter substrate, refuted before any backtest. Do NOT pre-register an arm. The genuinely-independent 3rd stream (tripwire #2) must come from a stream that goes *uncorrelated or short* in fast crises — which is managed-futures/CTA trend (T-296 — hit the hypothetical-basis wall, not the mechanism) or BTC (T-272 — genuinely low-corr and exits the winters, but one bull era / forward-validating). International *equity* is not a candidate; the "awaits 3rd" gap stays open.

**T-313 scope ready.** Data-reality PARK; no arm to run. Reproducer: `scripts/intl_stream_corr_probe_t313.py`.
