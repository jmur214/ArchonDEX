---
name: project-t407-pm-information-2026-11-19
description: T-407 prediction markets as an INFORMATION source for the long-only Roth book — free Kalshi/Polymarket history census, why every tradeable use fails the bar, H1 validity-only DRAFT prereg; recommendation close
metadata:
  type: project
---

T-407 (2026-11-19): pre-run design note + DRAFT prereg (validity check only), on the worktree branch. Files: `docs/Sources/design_note_prediction_market_information_t407_2026-11-19.md`, `docs/Sources/prereg_t407_kalshi_surprise_validity_DRAFT_2026-11-19.md`. No trial count stated; nothing measured.

**Why:** after T-403 the user re-framed prediction markets as "a source of data to help direct our actions/trades" (2026-11-18). The director asked whether any such use can be tested to the bar on free data.

**Facts worth not re-deriving:**
- **Kalshi history is free and deep.**
  - `/historical/markets/{t}/candlesticks` (no auth) serves 1-minute, hourly and daily bid/ask/trade OHLC for every settled market since 2021. The cutoff moves (2026-09-19 on 11-19); newer markets sit on `/series/{s}/markets/{t}/candlesticks`.
  - Legacy tickers (`CPI-22JUN`, `PROLLS-…`, `FED-…`) are listed INSIDE the KX series via `/events?series_ticker=KX…`. The legacy series return 0 events.
  - `expiration_value` carries the released print.
  - `forecast_percentile_history` needs an account.
  - No published unauthenticated rate limit; ~3,700 requests at ≤ 1.7/s drew no 429.
- **Polymarket.** `data-api /v2/prices-history` keeps 3h/12h prices permanently since 2022-11-18; finer grains expire. There is no bid/ask history. `clob /prices-history` is empty for resolved markets. Gamma `/events` above limit 50 needs gzip (otherwise HTTP 406).
- **The project archive is NOT the bottleneck for any historical test.** Its unique content is Kalshi top-of-book sizes and Polymarket bid/ask (from 2026-11-18).
- **Diercks–Katz–Wright** (FEDS 2026-010) find:
  - Kalshi ≥ the Bloomberg consensus on CPI (headline MAE 0.069/0.063 against 0.081);
  - the Fed ladder exact the day before every FOMC since 2022;
  - payroll surprises insignificant for the fed-funds distribution.
  They do not test asset returns.
- **Every tradeable form for a held long-only book fails the arithmetic:**
  - per-event effect/σ ≈ 0.1;
  - 600–2,400 releases are needed at z 2.96, which is 14–55 years.
  "Kalshi minus survey" needs a non-free consensus, and Campbell–Sharpe says markets see through the anchoring.
- **Statistical trap: uncertainty-scaled event rules are regime timing in disguise.** Kalshi-implied uncertainty is persistent, so "high-uncertainty events" sorts by regime. The effective N is the number of regimes.
  - Quotes-only proxy (strikes priced 10–90c): CPI 3.9 in 2022 → 1.25 in 2025.
  - It is also contaminated by contract redesigns: the payrolls proxy jumped from ~3 to 10.4 in 2026 when Kalshi re-cut the strikes. Any ladder-width measure breaks at a redesign.
- **Statistical trap: "per-event" framing does not rescue a time-series timing rule.** The fresh-eyes per-event class needs effect/σ per event of order ≥ 0.3 (odd-lot tenders). Macro-release timing is about 0.1.

**How to apply:**
- If prediction-market "signals" come up again, start from the design note's §3–§5.
- Do not re-propose release-day timing, recession switches or uncertainty-scaled leverage.
- The only open item is H1 (validity on ~100 usable release days: ≈ 70 % pass at z 2.96, ≈ 92 % at z 1.645).
  - FOMC ladders are one-sided before the meeting, and core PCE ladders are thin; CPI, payrolls and GDP carry the N. Run it only if the owner wants Kalshi forecasts and surprises shown in the digest. A pass licenses display, never a trade.

See [[project-t403-prediction-markets-2026-11-17]], [[feedback-held-book-timing-trap]].
