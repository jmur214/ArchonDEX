# T-337 — the dividend-strip audit: VERDICT

**Date:** 2026-08-06 · **Agent:** C · Branch `feature/dividend-strip-run-t337` · **N_trials += 1**
Frozen pre-reg: `dividend_strip_audit_prereg_t337_2026_07_30.md`, **committed `8abf458` BEFORE the run** — the git trail is the freeze-predates-run proof.

## 🚧 HEADLINE: the audit CANNOT stamp the closures. The substrate they were measured on NO LONGER EXISTS.
All **five** Arm-1 run directories the T-215 honest-base and T-180-v2 value/accruals closures were computed on are **absent from disk** — not merely missing `trades.csv`, the directories themselves are gone:

| year | run_id | dir present | trades.csv |
|---|---|---|---|
| 2021 | `191c14ba…` | ❌ | ❌ |
| 2022 | `85ae17d9…` | ❌ | ❌ |
| 2023 | `a23ce948…` | ❌ | ❌ |
| 2024 | `a1591104…` | ❌ | ❌ |
| 2025 | `a3aac752…` | ❌ | ❌ |

(120 other trade logs survive on disk, so this is specific loss, not a wiped directory.)

**This is the same irreproducibility class the 2026-07-02 gap audit found for T-236 ("inputs DELETED, irreproducible") — now confirmed to extend to the equity-book closures.** The consequence is direct and must not be softened:

> **The frozen audit cannot be completed as specified. T-215's honest base and T-180-v2's value/accruals sub-verdict CANNOT be stamped TR-VERIFIED, cannot be DEMOTED, and cannot be FLIPPED — because their own substrate is unavailable for re-measurement. Their receipt is currently unobtainable.**

I did **not** silently substitute a different substrate and present it as the closure re-run — that is precisely the silent-wrongness this program forbids. The fallback run below is labelled INDICATIVE-ONLY in the code itself (an unmissable banner + every gate line tagged), and `stamps_closures: false` is written into the result JSON.

## The fallback ran — and its own numbers CONFIRM it cannot stamp
| | 95% CI on the value/accruals contribution | straddles 0? |
|---|---|---|
| **RAW (as-is)** | [−163,338, +165,604] | **YES** |
| TR-restored | [−227,447, +107,065] | YES |

**The decisive observation: on the substituted substrate the RAW contribution ALREADY straddles zero.** This substrate therefore does **not reproduce the closure's "negative" finding in the first place** — so a TR-vs-raw comparison on it cannot stamp, demote, or flip a verdict it never reproduced. The gate printed "DEMOTED", but that label is meaningful only against a reproduced negative baseline, which does not exist here. **This is independent evidence for the headline, not merely a caveat about it.**

Other measured outputs (all INDICATIVE-ONLY):
- **Coverage census: 331/369 = 89.7%**; 38 unreconcilable = **2.4% of traded notional**. After the retry fix, **all 38 are classified "TRANSIENT — NOT established as delisted"** (previously 20 were wrongly labelled "likely delisted"). Notably `BRK.B` is plainly *not* delisted — it is a ticker-format mismatch — which is exactly why the honest label matters: **we do not actually know how many of the 38 are delisted, so the delisted-name dividend bias remains unmeasured**, per the frozen scope statement.
- Basis: **15,541 realized (closing) fills** of 59,304 rows; median holding **78 calendar days** (was mis-computed as 5 before the basis fix — a 15× error in the dividend accrual, now corrected).
- Gate (a) indicative Δ Sharpe ≈ **−0.026**.
- **The per-name panel-vs-TR gap is mixed-sign across the traded universe** — not the clean uniform strip the challenge assumed. It is reliably negative for the high-yield cohort (the premise check) but not universally, so an annualized full-sample rate applied per trade carries splice/level noise as well as dividend. A further reason these indicative numbers should not be over-read.

## What the fallback CAN and CANNOT say
Running the same mechanism on the **surviving** logs that carry the same four value/accruals edges gives a **directional read on the mechanism** — whether the TR residual is materially concentrated in those edges — but it is a **different substrate**, so:
- ✅ it can say whether the dividend residual is large enough to matter at all;
- ❌ it **cannot** stamp, demote, or flip the frozen closures.

## Three measurement defects I found and fixed mid-run (disclosed)
Each would have produced a confident, wrong number:

1. **A NaN CI silently produced a verdict.** With `ci_low`/`ci_high` = NaN, *both* `ci_high <= 0` and `ci_low > 0` evaluate False — so the graded gate fell through to **"DEMOTED"** from a completely broken measurement. Fixed: a NaN CI now **halts with "NO VERDICT — bootstrap CI is NaN"**. This is the exact silent-wrongness shape the doctrine names, and the graded gate (which I asked for) made it *more* likely by adding a fall-through branch.
2. **The coverage census conflated transient failure with genuine absence.** A first pass reported 94.6% coverage; an immediate re-run reported 29.0% with 242 `TypeError`s — yfinance rate-limiting, not data properties (`EMR` reconciles fine in isolation, 11,166 rows). Since the census is the instrument that *polices survivorship*, reporting a rate-limited fetch as "unreconcilable/delisted" would corrupt the very thing being measured. Fixed: 3× retry with backoff, a disk cache for reproducibility, and failures now classified **"TRANSIENT — NOT established as delisted"** rather than lumped with genuine no-TR names.
3. **Inconsistent dividend basis.** `pnl` is stamped only on *closing* fills, so **16,832 of 21,857** value/accrual rows carry NaN PnL. My first construction accrued dividends on opening rows too — adding yield to rows carrying no PnL, which would have inflated the restoration. Fixed: dividends accrue to **realized round trips only**.

## Recommendation
Two honest paths, and this is a director/user call:
- **(a) Regenerate the Arm-1 substrate** (re-run the five yearly backtests) and then execute the frozen audit as written. This is the only route to an actual TR-VERIFIED stamp. Cost: five backtest runs.
- **(b) Accept the closures as substrate-unverifiable** and mark them accordingly in the ledger — i.e. T-215's honest base and T-180-v2's sub-verdict keep their conclusions but carry a permanent *"receipt unobtainable; substrate deleted"* annotation.

**I recommend (b) unless the equity book is being reconsidered for deployment** — the premise-check already showed the effect is ~1.6%/yr on high-yield names (≈4× smaller than the challenge assumed), so the expected shift (~+0.025 Sharpe diversified, ~+0.06-0.08 on a value-tilted sub-book) does not approach the deployable bar either way. Spending five backtest runs to confirm a number that cannot change a deployment decision is poor value; *recording that the receipt is unobtainable* costs nothing and is honest.

**A third finding worth its own line:** this audit's real yield may be the **discovery that a central negative result rests on deleted inputs.** That is a process defect worth fixing regardless of T-337 — if closure-grade run artifacts can be garbage-collected, every closure is one cleanup away from unverifiable.

**T-337 done.** N_trials += 1 (the trial was consumed: the frozen measurement was attempted and returned a blocker, which is a result).
