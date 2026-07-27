# T-320 — the AGGRESSIVE-tilt decision measurement: PRE-REG DRAFT (awaiting director freeze)

**Date:** 2026-07-27 · **Agent:** C · Branch `feature/aggressive-tilt-t320` · **0 N_trials until frozen** (N += 1 at run, one family jointly reported)
The complement to T-318 (small-value). The user's aggressive directive opens the other side: **what does the aggressive-tilt menu honestly offer a won't-sell 40-year holder vs plain SPY?** Same methodology as T-318 (rolling-40yr win fractions, log-wealth-ratio CI, **the regret metric leading**), same decision-support framing — *not* an alpha claim.

## Part 1 — DATA REALITY (measured 2026-07-27, before the pre-reg — T-264 discipline)
| arm | deep series | window | deployable wrapper | wrapper window |
|---|---|---|---|---|
| 1 Momentum | FF `F-F_Momentum_Factor` (MOM) | **1927-01 → 2026-05 (99yr)** | MTUM-class | **2013-04+ (13yr)** |
| 2 Growth/tech | Nasdaq Composite `^IXIC` | **1971-02 → 2026-07 (55yr)** | QQQ | **1999-03+ (27yr)** |
| 3 Quality/profitability | FF 5-factor RMW + OP portfolios | **1963-07 → 2026-05 (63yr)** | QUAL-class | **2013-07+ (13yr)** |
Baseline: SPY / FF market (`^GSPC` 1927+). **Honest limit carried to every arm: the deep legs are academic long-short or index constructs; the deployable wrappers are 13-27 years old, so wrapper basis (ER + tracking + long-only-vs-long-short) is a named caveat, never assumed away.** Momentum's deep leg in particular is a LONG-SHORT factor — a long-only deployable tilt captures only part of it, and I will report the long-only portfolio version alongside, not the factor alone.

## Part 2 — THE MEASURED ADVERSARIES (these set the priors; measured, not asserted)
**Arm 1 — momentum crash risk (measured on FF MOM):**
| window | year return | worst month | in-window MaxDD |
|---|--:|--:|--:|
| 1932 crash | **−64.5%** | −52.6% | −74.2% |
| 2009 crash | **−52.9%** | −34.4% | −56.4% |
| 2001 | −10.3% | −25.4% | −16.3% |
Full 1927-2026: **+6.2%/yr with a −78.5% worst drawdown.** Momentum's premium is real and replicated — but it is paid for with violent, *fast*, post-crash-rebound crashes. This is the arm where "aggressive" has a measurable body count.

**Arm 2 — the QQQ regret (the number the dispatch asked to replace a vibe with):**
- Dot-com: peak 2000-03 → trough 2002-09, **MaxDD −81.1%**; **reclaimed its high 2014-10 = 14.6 YEARS underwater.**
- **RELATIVE to SPY: worst drawdown −68.5% → a $10k tilt trails by $6,847 at the worst point** — and it has **NEVER regained its Feb-2000 relative high** (26 years and counting).
- Era return: QQQ +10.5%/yr vs SPY +8.5%/yr since 1999 — real, but **that window is ONE era and QQQ is its survivor.**

**Arm 3 — quality/profitability:** the replicated factor that pairs best with leverage (a higher-quality book survives leverage better). **Flag the interaction with D/T-315 explicitly** if the data supports it — i.e. report whether a quality-tilted book would have changed T-315's levered conclusions, as a cross-reference, *not* as a new levered arm here.

## Part 3 — ARMS (pre-registered, no sweep; jointly reported as ONE family)
Deployable long-only blends vs 100% SPY, monthly-rebalanced, **net of an honest wrapper ER** (momentum/quality 0.15-0.25%, QQQ 0.20%):
1. **80/20 and 70/30 SPY / momentum** (long-only momentum portfolio leg; the long-short factor reported separately as the academic upper bound)
2. **80/20 and 70/30 SPY / Nasdaq-growth** (deep leg `^IXIC` 1971+, deployable QQQ 1999+ reported separately)
3. **80/20 and 70/30 SPY / quality-profitability** (FF high-OP leg)
Each arm additionally reported with a **post-publication-decay variant** (premium haircut to its *measured* post-publication realized level — momentum post-1993, quality post-2013), so no decision rests on a premium that may no longer exist.

## Part 4 — REPORTED METRICS (decision-support, NOT pass/fail gates) — regret LEADS
For every arm, in this order:
1. **THE REGRET METRIC (leads):** worst rolling **15-year RELATIVE drawdown** vs SPY, **in dollars per $10k**, plus **time-to-recover the relative high** (and "never" where that is the truth — as it is for QQQ). This is what the user must consciously accept.
2. Fraction of rolling **40-year** windows the blend beats 100% SPY on terminal wealth (N windows + overlap stated honestly).
3. **Log-wealth-ratio 95% CI** (`ln(blend/SPY)`), block-bootstrapped — **CI excluding zero is the "real edge" bar.**
4. Supporting: arm MaxDD, worst absolute 15yr window, and the deployable-wrapper-era slice (13-27yr) as a *reality check* on the deep result.

## Part 5 — HONEST PRIORS, PER ARM (they differ sharply — that IS the finding)
- **Momentum: MEDIUM (~40-50% CI-excludes-zero).** The one aggressive tilt with cross-country, post-publication survival. But crash risk is severe (−64.5%/1932, −52.9%/2009), turnover/cost is higher than value, and the long-only wrapper captures only part of the factor. Highest-quality evidence of the three; genuinely painful failure mode.
- **Growth/tech: LOW (~15-25%).** Factor history says **naive growth is the LOW-return leg** (the value premium's mirror). QQQ's era-win is real but is **a sector bet that has never regained its 2000 relative high**. The honest prior is that the popular reach for "aggressive" buys concentration risk, not a premium. **Expect this arm to fail the CI bar and to carry the worst regret number** — measuring it is the point.
- **Quality/profitability: MEDIUM-LOW (~30-40%).** Replicated and the most robust *shape* (it is the one that pairs with leverage), but the smallest standalone premium and the shortest deployable history.
- **The fourth aggressive door — BTC — stays where it is:** already in **forward validation** via the T-272/T-276 shadow (clock running, un-degraded post-T-307). It is NOT re-measured here; noted so the aggressive menu is complete.

## Part 6 — what a result CANNOT be used for (pre-stated)
No in-house-edge claim (these are external, replicated, published factors). No timing/sizing rule on any tilt (that re-opens closed vocabulary and would be a new trial). No change to the deploying sleeve — this is a **satellite allocation decision for the user**, and the deploying sleeve is untouched by every outcome. A positive CI on one arm does **not** license stacking arms.

**T-320 DRAFT — awaiting freeze.** Nothing run. On freeze I execute exactly this and report regret-first, per arm.
