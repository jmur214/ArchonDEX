---
title: "Taxable-wrapper frontier — SCOPE (micro-futures CTA + §1256 + wrapper-blocked triage)"
task: T-2026-07-02-281
status: SCOPE ONLY — nothing built, nothing run, 0 N_trials
---

# T-281 — the taxable-wrapper frontier (scope + go/no-go)

The user will open a regular taxable brokerage → the wrapper-blocked list
(margin / shorting / futures) reopens behind fresh pre-registered scopes. **This is
SCOPE ONLY.** Nothing is built or run.

## The two guardrails (load-bearing)
1. **A wrapper unlock reopens only strategies that were BLOCKED, never ones killed
   on the SCIENCE** (C's post-T-279 guardrail). A taxable account changes what we
   can HOLD, not whether a dead premium is alive.
2. **Premium-in-taxable is MOOT** — C/T-279's tier test refuted direct premium
   harvesting on the science at the implementable tier. Skip it.

## §0 — Which of the blocked list is BLOCKED vs SCIENCE-KILLED (the triage gate)

| Family | Status | Verdict |
|---|---|---|
| **Micro-futures CTA (levered long-short multi-asset trend)** | **BLOCKED** (Alpaca equity-only; no futures/leverage/shorts) — **never science-killed**; our long/flat sleeve is its *constrained shadow* and already validates the long side | **REOPEN — the ONE first test** |
| Short legs of long-short equity premia | long side was SCIENCE-KILLED (T-215 ensemble H0; cross-sectional 0/16) + short side faces retail borrow reality | **STAYS CLOSED** |
| Levered vol-targeting (T-252 continuous-lever) | SCIENCE-KILLED — added **negative skew** (against the tail-first objective) + needed borrow (T-252/T-262 mechanism-overlap H0) | **STAYS CLOSED** |
| Levered risk parity | externally REFUTED (2022 stock-bond joint drawdown = the classic RP blowup); LOW prior | **STAYS CLOSED** |

Only ONE family clears the guardrail. The rest were killed on evidence, not blocked.

## §1 — Micro-futures CTA replication feasibility (the reopen)

**The thesis.** Our trend sleeve is long/flat, unlevered, 3 assets (SPY/AGG/GLD) —
the gap audit's own finding: in an unlevered Roth the CTA upgrades are "SHAPE not
RETURN." The RETURN lever is precisely what the Roth blocks: **leverage + the SHORT
legs + multi-asset breadth** — the full AQR "century of evidence on trend-following"
family. Micro futures make that family accessible at a $35–65K taxable account.

**Contract specs + margins (CME micros; approximate late-2025, BROKER-DEPENDENT — confirm before any build):**

| Micro | Multiplier | ~Notional | ~Overnight margin | Asset bucket |
|---|---|---|---|---|
| MES (Micro S&P 500) | $5 × index | ~$30K | ~$1.6–2.3K | US large equity |
| M2K (Micro Russell 2000) | $5 × index | ~$12K | ~$0.8–1.1K | US small equity |
| MGC (Micro Gold) | 10 oz | ~$30K | ~$1.3–2.0K | metals |
| MCL (Micro Crude) | 100 bbl | ~$7K | ~$0.7–1.1K | energy |
| M6E (Micro EUR/USD) | €12,500 | ~$13K | ~$0.3–0.45K | FX |
| ZN (10-Yr T-Note)* | $1,000 × price | ~$110K | ~$1.2–2.0K | rates |

*No true "micro" 10-yr note; ZN's margin is small relative to notional (rates are
low-vol), or use the Micro 10-Yr Yield (10Y, $10/bp) as the thinner micro alternative.

**Tier breadth — the HONEST finding (leverage is the constraint, not contract count):**
A diversified trend CTA targets ~10–15% portfolio vol. Because a single micro's
notional often EXCEEDS a small account (MES ~$30K > a $15K account), the binding
limit is aggregate gross leverage / vol, not "can I afford 1 contract":
- **$15K — TOO SMALL for diversification at sane leverage.** One MES alone is ~2×
  the account; a 6-bucket basket at 1 micro each is ~7–8× gross → ~70%+ portfolio
  vol (absurd). Realistically ~1–2 micros at a ~12% vol target → NOT a diversified
  CTA. **Do not scope the CTA here.**
- **$35K — ~3–4 asset buckets** at a sane ~12–15% vol (e.g. MES + ZN + MGC + MCL).
  A real but narrow CTA; lumpy sizing (1-micro granularity bites at this size).
- **$65K — ~6–8 buckets, a genuine diversified multi-asset CTA** at ~12–18% vol
  with workable sizing granularity. **This is where the family actually fits.**

**Broker approval:** futures accounts need approval but are retail-accessible
(IBKR / Tradovate / AMP / NinjaTrader); micros are widely offered. Not a blocker.

**Data path (the scoped crack).** The micros are too young (~2019 launch) for a
15–20yr backtest → backtest on **full-size continuous futures** (ES/RTY/GC/CL/6E/ZN,
2005–2026), size positions in micro units (micro = 1/10 full-size, same underlying).
**Databento buy-and-own** historical futures, daily bars: a daily-signal / monthly-
turnover CTA does NOT need minute data → the **$125 Databento credit** plausibly
covers ~6 continuous symbols × ~20yr daily (CONFIRM the exact dataset pricing before
purchase). This is the cheapest honest-data reopen on the board.

## §2 — The §1256 tax math (why the CTA belongs in the TAXABLE column)

Regulated futures + broad-based index options are **§1256 contracts**: marked-to-
market at year-end, gains taxed **60% long-term / 40% short-term REGARDLESS of
holding period.** For a monthly-turnover strategy this is decisive:

| | Monthly-turnover EQUITY (taxable) | Monthly-turnover FUTURES (§1256) |
|---|---|---|
| Realization | ~all gains SHORT-term | 60/40 blend, holding-period-agnostic |
| Effective fed rate* | ~32% (ordinary ST) | 0.6·15% + 0.4·32% ≈ **21.8%** |
| On an 8%/yr all-ST return | after-tax **5.44%** | after-tax **6.26%** |

*illustrative mid bracket; scales with the user's actual bracket.

**→ §1256 keeps ~10pp more of every short-term gain → ~+0.8%/yr after-tax on an
~8%/yr strategy** — LARGER than the ~130 bps/yr equity-turnover TAX drag T-148
measured. **High turnover is a tax LIABILITY in equities and a tax ASSET in §1256
futures.** This is the structural reason the naturally-high-turnover CTA family is a
taxable-column strategy, not one to force into an equity-ETF wrapper. (It does NOT
help a Roth — Roth is already tax-free — so this advantage is *specific to the
taxable reopen*.)

## §3 — Recommended ONE first test (pre-registered arm — PROPOSED, not built)

**Micro-futures managed-futures CTA replication** — the levered long/SHORT multi-
asset trend family our sleeve is the constrained shadow of.
- **Universe:** ~6 liquid futures across asset classes (ES, RTY, ZN, GC, CL, 6E),
  positioned in micro units (MES/M2K/ZN/MGC/MCL/M6E) for the **$65K tier** (the
  tier where diversification is real; a $35K secondary arm for the narrow version).
- **Signal (FROZEN before running):** multi-speed trend ensemble ({~3,5,8-12}mo,
  the gap-audit-endorsed spec-luck insurance), **long/SHORT** (the key delta vs our
  long/flat sleeve), vol-targeted to ~12–15% portfolio vol.
- **Substrate:** Databento full-size continuous futures 2005–2026 daily (~$125 credit).
- **Gates (the honest bar, unchanged):** Sortino + block-bootstrap ci_low; MBL at
  honest-N; **beat the robo AND beat OUR trend sleeve** (the real question — does
  adding leverage + short legs + breadth beat the simple long/flat shadow *enough*
  to justify the taxable wrapper + futures operational complexity + margin risk?);
  **§1256 AFTER-TAX** (the structural tailwind); realistic futures costs (commission
  ~$0.25–0.50/micro/side, slippage, quarterly roll cost). `is_it_beta_or_edge`:
  trend IS the family, so the trend premium net-of-cost is EXPECTED — this is not an
  alpha hunt; the test is *deployable-net-after-tax vs the sleeve*.
- **Prior: MEDIUM-HIGH on the science** (the best-evidenced premium in the
  literature; our own sleeve already validates the long/flat shadow). The genuine
  OPEN questions are operational + scale, not "does trend work."

## §4 — Honest costs, risks, and the ask

- **Cost:** ~$125 Databento (data) + a from-scratch **futures backtest harness**
  (continuous-contract stitching, roll/margin modeling, §1256 after-tax, vol-target
  sizing) — a real build, NOT a reuse of the equity harness.
- **Operational step-change:** futures = roll management, daily mark-to-market,
  **margin-call risk in a fast adverse move**, 24h markets, overnight gaps. This is
  Engine-B / live_trader territory — propose-first, hard-gated. **Leverage is the
  return lever AND the tail risk**; a $35–65K taxable account at leverage is a
  materially bigger real-money commitment than the Roth ETF sleeve.
- **The ask (SCOPE conclusion):** the micro-futures CTA replication is the ONE
  taxable-column family that clears the guardrail (blocked, never science-killed)
  and has the strongest evidence. **RECOMMEND: propose it as a fully pre-registered
  experiment for the user's go** — the go authorizes (a) the ~$125 data purchase and
  (b) a from-scratch futures backtest harness. The other three wrapper-blocked
  families stay closed (science-killed or externally-refuted); do not spend on them.

**T-281 = scope only. One family earns an arm; the recommended first test is the
micro-futures CTA replication at the $65K tier. Nothing built or run; N_trials += 0.**
