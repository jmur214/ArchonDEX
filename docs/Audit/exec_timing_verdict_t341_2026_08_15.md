# T-341 — the execution-timing probe: VERDICT (door closed with a receipt)

**Date:** 2026-08-15 · **Agent:** C · Branch `feature/exec-timing-run-t341` · **N_trials += 1**
Frozen (narrowed) pre-reg committed **`85bf551` BEFORE this run** — the git trail is the freeze-predates-run proof.

## TL;DR — the question is CLOSED, and closed honestly: **not "no effect measured," but "no effect is resolvable at proportionate cost, and the ceiling is ~1 bp."**

## Arm A — open-vs-close effective spread: **NOT MEASURABLE** (not failed, not passed)
Daily OHLC carries **no quote data**, and the standard OHLC substitute — **Corwin-Schultz (JF 2012)** — is unusable at our liquidity tier: on our own panels it estimates SPY's spread at **mean 23.0 bps (median 0.0, negatives clipped)** against a true spread of **~0.5-1 bp**, i.e. wrong by **20-40×** (AGG 5.0, GLD 14.4 show the same inflation).

**So no Arm A statistic is emitted.** Reporting a Corwin-Schultz number would have produced a confident, badly wrong figure — the exact fabrication class this program exists not to produce (`[NN-FAIL-CLOSED]`). **The frozen gate (CI-excludes-zero AND ≥0.5 bps) is NOT EVALUATED** — that is a third state, deliberately distinct from pass and fail, and the same MEASUREMENT-INVALID branch T-337 taught us graded gates must carry.

## Arm B — open-vs-close return delta (CI + MDE, **no verdict**, as pre-registered)
Monthly rebalance dates, 2000-2026, executing at close vs at open:

| leg | n | close − open | 95% CI | MDE |
|---|--:|--:|---|--:|
| SPY | 316 | +6.8 bps | [−4.8, +17.7] | 16.2 bps |
| AGG | 273 | −2.6 bps | [−5.9, +0.6] | 4.7 bps |
| GLD | 73 | +8.0 bps | [−6.7, +22.4] | 20.5 bps |

**Every CI straddles zero, and every MDE exceeds the plausible 1-3 bps effect by 3-10×.** This is precisely the pre-registered expected result: **Arm B is uninformative BY CONSTRUCTION and carries no verdict in either direction.** Pre-stating that is what stops the +6.8 bps SPY point estimate from being read as a finding — it is noise with a CI four times its width.

## Real fills (validation-only, n=3)
**0.26 / 0.51 / 1.02 bps** vs arrival (mean 0.60). We execute within ~1 bp of arrival, so **the maximum recoverable saving from any timing change is ~1 bp** — below every available instrument's resolution.

## Why this closes the door properly
Three independent facts, each sufficient on its own:
1. **The ceiling is ~1 bp** (our own realized slippage) — a timing change cannot save more than we currently pay.
2. **No instrument we hold can resolve a ~1 bp effect** — Corwin-Schultz is off by 20-40×, and daily OHLC has no quotes.
3. **Acquiring an instrument that could is negative-EV** — the minute-bar build was declined against this ceiling, and B's T-341 verdict independently killed the free-1-min-data path on survivorship grounds.

**The honest closure is therefore "unresolvable at proportionate cost with a ~1 bp ceiling," not "measured and found zero."** Those are different claims and only the first is supported. Recording the weaker, true one is what makes this a receipt rather than a rationalization.

## What may NOT be cited from this
- No return claim (Arm B has no verdict, by pre-registration).
- No "execution timing doesn't matter" claim in general — only **at our size, with our instruments, against a ~1 bp ceiling.** A different size or a quote-level dataset would re-open it, and the ceiling argument would have to be re-run first.

**N_trials += 1** (consumed by Arm A as frozen; Arm B consumed none, as pre-registered).

**T-341 done.**
