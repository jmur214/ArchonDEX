# SCOPE — Path B Layer 2: managed-futures trend sleeve (diagnose-first). Ready to dispatch to A as T-108.

**Status:** DRAFT scope, ready to drop into A's inbox when T-107 completes.
**Date:** 2026-06-05 · **Author:** director
**Decision context:** T-092 Path B Layer 2 — the STRUCTURAL skew fix (vs the de-gross band-aids). User picked option 1 (trend sleeve, diagnose-then-build) 2026-06-05.

---

## The single most important framing (do NOT skip)

**Equity-trend is already DOUBLY FALSIFIED — do not re-test it.** Per `health_check.md:554` (T-007):
- Mega-cap equity-trend: Sortino +1.467 BUT MDD **-23.30%** (kill-threshold tripped) and **skewness NEGATIVE (-0.133)** — the opposite of the positive-skew property we want.
- Wider-universe equity-trend: WORSE — Sortino +0.456, MDD -43.14%, Sharpe +0.340. "Trend on the long tail has higher idiosyncratic vol that becomes drawdown-amplified, not skew-amplified."
- Documented conclusion: **"the asymmetric-upside property requires structural convexity (LEAPS / event-driven / MANAGED-FUTURES), not just more equity universe."**

**Therefore the built `engines/engine_c_portfolio/sleeves/TrendFollowingSleeve` is the WRONG tool** — it filters `signals` (Engine A's EQUITY tickers) by momentum+inverse-vol, i.e. it IS equity-trend, the falsified thing. Wiring it would re-run a dead test. The capability audit's "scaffold already exists" is true but misleading: the scaffold implements the wrong asset class.

**The actual cure** the external research named is **cross-asset managed-futures / diversified-futures trend** — trend-following across bonds/commodities/FX/equities (different asset classes with genuine positive skew + low equity correlation), NOT momentum on stocks. Infra for THIS already exists too, separately: `scripts/run_diversified_futures_trend.py` carries R2's 8-ETF basket `[SPY, TLT, GLD, USO, UUP, EEM, IEF, DBC]` with a `sortino_skew_upside` objective — but it's a standalone script, never integrated or verified on the canonical substrate.

So this task is NOT "wire the existing sleeve." It is: **does cross-asset managed-futures trend produce real positive skew + crisis-alpha on OUR data, at OUR scale — and if so, what's the cleanest integration?**

---

## Phase 0 — DIAGNOSE (do this first; it may end the task)

**Q1 — Data viability.** Do we have clean daily history for a diversified-futures basket back far enough to test crises (ideally to ~2006 for 2008, like T-103/T-105)? The 8-ETF basket: SPY/EEM (equities), TLT/IEF (bonds), GLD/USO/DBC (commodities), UUP (USD). Check inception + local cache:
  - GLD 2004, USO 2006, DBC 2006, UUP 2007, EEM 2003, IEF/TLT 2002 → basket is only complete from ~2007. Report the binding floor. (Pre-2007 would need futures data or proxies — flag, don't fake.)
  - If the basket can't reach 2008, say so — managed-futures' whole selling point is crisis-alpha (2008 SG Trend +20.9%), so a test that can't see 2008 is weak. COVID 2020 + 2022 are testable and are the priority if 2008 is out of reach.

**Q2 — Standalone skew/crisis test (the make-or-break).** Run `run_diversified_futures_trend.py` (or a corrected copy) on the basket over the deepest clean window. The ONLY questions that matter:
  - Is realized-return **skewness POSITIVE** (vs equity-trend's -0.133)? This is the structural property; if skew is still negative, managed-futures-on-ETFs doesn't deliver the cure either and the task ends NEGATIVE (a valuable result).
  - Does it make money (or lose much less) in **2008 / COVID / 2022** — the crisis-alpha claim? Report per-crisis return.
  - Standalone Sharpe/Sortino/MDD with block-bootstrap CI (CLAUDE.md `[NN-SHARPE-CI]`).

**Q3 — Correlation to the base.** Compute the diversified-trend sleeve's return correlation to the existing 6-edge equity book. The diversification value is the whole point — if it's highly correlated to the base, it adds little even if standalone-decent.

**Phase 0 verdict:** does cross-asset managed-futures trend show (a) positive skew AND (b) crisis-alpha AND (c) low base-correlation on our substrate? → PROCEED to Phase 1 / RECONSIDER (e.g. the research's DBMF/KMLM managed-futures ETF route instead of self-built) / DEAD (skew still negative → managed-futures isn't viable for us either).

---

## Phase 1 — INTEGRATE + A/B (ONLY if Phase 0 clears)

If Phase 0 shows real positive-skew crisis-alpha, design the sleeve as a **capital-partitioned allocation** alongside the equity book (the `MultiSleeveAggregator` is the natural host — it does capital_pct partitioning + per-sleeve isolation). NOT a replacement for the base; a co-equal sleeve funded from a slice of capital.
- A/B: base-only vs base + X% trend-sleeve (sweep X ∈ {10%, 20%, 30%} of capital), 16-yr + 26-yr, block-bootstrap CI.
- PRIMARY KPIs: **portfolio skewness** (does the sleeve flip the book's skew positive?) + **crisis-period return** (2008/COVID/2022) + MDD. Secondary: Sharpe ci_low not down.
- The research's specific candidate to test if self-built trend is marginal: **DBMF / KMLM managed-futures ETFs** (30-50% of headline trend at 1-share min, §1256 tax treatment) — a buy-the-ETF route that sidesteps building a futures engine. Flag as the fallback if self-built trend is close-but-not-clean.

---

## Hard constraints (for the eventual dispatch)
- **Phase 0 is diagnostic/measurement — autonomous.** Phase 1 integration touches Engine C allocation (the aggregator) — that's autonomous-scope (NOT Engine B), BUT if it requires wiring into `BacktestController` or changing how capital is partitioned at the portfolio level, treat the wiring as a reviewable change (show canon-md5 OFF=identical, default-OFF).
- Do NOT re-run or re-litigate equity-trend (T-007 falsified it twice). If you find yourself filtering Engine A equity signals by momentum, you're building the wrong thing.
- New data fetch for the futures basket: assess cloud vs local; the multi-decade fetch may want cloud.
- Block-bootstrap CI on every Sharpe/skew headline. Determinism --runs 3 on any integrated path (T-099 floor merged).
- Don't manually edit `data/governor/*`. Don't touch `cockpit/dashboard/`. Branch push only; director merges.

## Why this is the right Path-B bet regardless of T-106
The de-gross levers (drawdown switch T-106, HMM repoint, correlation cap T-107) all attack the problem from the RISK-REDUCTION side — they make crashes hurt less. The trend sleeve is the only lever that attacks from the RETURN side — positive-skew crisis-alpha that can MAKE money in a crash. It's additive to whatever T-106 concludes, and it's the only thing in the queue that could change the strategy's CHARACTER rather than just trim drawdowns. That's why it's worth the diagnose-first investment even with the equity-trend falsification on the record — managed-futures is a genuinely different asset class, not more of the thing that failed.

## Open question for the director to resolve before dispatch
Self-built diversified-futures-ETF trend (Phase 0 Q2) vs going straight to the DBMF/KMLM managed-futures-ETF route. The self-built test is more work but tells us whether the EFFECT is real on our substrate; the ETF route is faster to deploy but adds an external product dependency. Recommend: Phase 0 tests self-built (it's cheap, uses existing infra, and answers the "is the effect real for us" question) → if positive, compare self-built vs DBMF/KMLM in Phase 1.
