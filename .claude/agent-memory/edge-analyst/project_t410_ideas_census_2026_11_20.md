---
name: project-t410-ideas-census-2026-11-20
description: T-410 census (2026-11-20) of untested options-forward ideas and combinations. Top 3 are E-1 earnings options, O-1 stacked index premium and E-2 announcement basket, each ~4–18 %; the stay-dead list for this owner
metadata:
  type: project
---

**T-410 (2026-11-20):** design census `docs/Sources/ideas_census_desk_t410_2026-11-20.md`, commit `95a46f0` on the worktree branch, not merged. Nothing was measured; 0 trials.

**Top 3 (none frozen):**
- **E-1:** earnings straddles per event. Sort within each announcement week on q = implied move ÷ median of the firm's last 8 realized earnings moves.
  - Alpaca bars/trades 2024-01+; payoff = intrinsic at expiry; ~4–8k events.
  - P(pricing signal) ≈ 18 %; P(deployable, net of costs) ≈ 4–5 %.
- **O-1:** a defined-risk short-vol overlay (Cboe CNDR proxy, 1986+) stacked on the taxable core via Reg-T buying power, k = 0.10.
  - ≈ 10 %; retail XSP spread is the binding unknown.
  - Taxable only; needs leaving the robo.
- **E-2:** the Savor–Wilson announcement premium as a weekly basket of S&P stocks with predicted announcement dates (Roth).
  - ≈ 9 %; cost-fragile.
- **EV:** each is tens of $/yr at the owner's size. The structural items (T-409/T-400) dominate.

**Never tested, with the reason:**
- The announcement premium: the `earnings_proximity_5d` gene sat in the foundry (T-196 UNTESTED) and was excluded from B-1.
- Earnings straddles: G1/G2/G4/F-7 all stayed proposals.
- Premium selling stacked on equity: T-279/T-261 tested only substitution inside the trend sleeve.
- F-5/F-6/F-7 forward books: never built.

**Stay dead for this owner (wealth-max, never sells, accepts 0.5× S&P):**
- protective puts, collars, buffers;
- covered calls / CSPs (Israelov–Nielsen; granularity $71.8k/contract at SPX 7,176);
- LEAPS;
- every options-information signal used as core timing (VRP, VIX-term, SKEW, P/C, GEX, implied correlation): a regime count, not events;
- macro-event option trades (~32/yr);
- Kalshi × options (~150 events).

**Record contradictions found:**
- The T-174 and T-122 ledger rows say "refuted", but RR-1 §5 demotes both to UNTESTED (also T-129, T-144, T-145).
- T-184's skew-aversion rationale and T-279's trend-sleeve baseline are stale under the max-wealth objective.

**Why:** the owner's 2026-11-20 direction: "combine ideas into a better machine; especially options; work like a trade desk".

**How to apply:**
- Start any options prereg from the doc's §7 sketches.
- Never re-propose the stay-dead list without new data, a new instrument or a new wrapper.
- Check the displacement threshold ([[feedback-displacement-threshold]]) before any "add a diversifier" idea.
- Data facts: [[reference-options-data-sources-2026-11-20]].
