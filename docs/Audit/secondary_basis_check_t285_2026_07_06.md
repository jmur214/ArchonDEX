---
task_id: T-2026-07-06-285
title: Basis-check the SECONDARY's bond/gold 2× legs vs real 2× ETFs (construction validation)
date: 2026-07-06
author: Agent D (fair-harness lane)
type: construction validation / CORRECTION of an existing arm (0 new N_trials)
status: DONE — SECONDARY was FLATTERED (gold synth +2%/yr optimistic; 2×-intermediate bond not tradeable). Branch feature/secondary-basis-check-t285
---

# T-285 — basis-check of the T-284 SECONDARY's levered bond/gold legs

The T-284 SECONDARY (3-leg 2×-gated: $76.3K / −22.6% DD / Sortino 0.999) was flagged EXPLORATORY because its
bond/gold 2× legs were synthetics, un-checked against real levered ETFs (unlike the SPY leg, which I
basis-checked vs SSO in T-282). This validates the construction and re-runs with honest assumptions. **0 new
N_trials** (validation of an existing arm, not a new hypothesis).

## Per-leg basis check (synthetic `2·underlying_gross − borrow − ER` vs the REAL 2× ETF)
| leg | synthetic vs real | window | TE/yr | CAGR gap | term ratio | verdict |
|---|---|---|---|---|---|---|
| **SPY** | 2×SPY vs **SSO** | 2006-2026 | 3.68% | **+0.23%/yr** | 1.040 | ✅ validated (T-282) |
| **BOND (method)** | 2×TLT vs **UBT** | 2010-2026 | 5.21% | **−0.68%/yr** | 0.896 | ✅ method reproduces UBT (conservative) |
| **GOLD** | 2×GLD vs **UGL** | 2008-2026 | 2.79% | **+2.01%/yr** | **1.356** | ❌ NOT trustworthy — materially optimistic |

- **GOLD is the problem: +2.01%/yr optimistic (term ratio 1.356).** My 2×-gold synthetic is built from gold
  SPOT (GLD/GC=F), but real UGL tracks gold **futures** → roll/contango drag the synthetic never pays. Over
  17yr the spot-gold 2× overstates the tradeable UGL by +2%/yr. The SECONDARY's gold leg was flattered.
- **BOND: the construction METHOD is validated** (2×TLT reproduces UBT to −0.68%/yr, conservative). BUT:
  **DURATION MISMATCH — the sleeve's bond leg is 2×-DGS10 (INTERMEDIATE ~7yr); there is NO clean liquid
  2×-intermediate-treasury ETF.** UBT is 2×-**20yr** (~2.5× the rate sensitivity). So the sleeve's levered
  bond leg is **NOT tradeable as-built** — the implementable version must use the far more volatile
  long-treasury 2× (UBT).

## SECONDARY re-run (tradeable window 2002-09→2025-12, TLT-limited)
| variant | $10k→ | CAGR | Sortino | MaxDD |
|---|---|---|---|---|
| as-built (2×-DGS10 bond, spot-gold) — the T-284 construction | 77,209 | 9.2% | 1.063 | −22.6% |
| IMPLEMENTABLE (2×-20yr/UBT bond, spot-gold) | 71,505 | 8.8% | 0.945 | −25.6% |
| **FULLY-CORRECTED (20yr bond + gold haircut to the UGL basis)** | **65,764** | **8.4%** | **0.908** | **−25.6%** |

_(2002-09 start is post-dotcom-bottom → not comparable to T-284's 2000-10 window; used here only to isolate the
correction deltas apples-to-apples, since TLT starts 2002-07.)_

**Two corrections, both material:** making the bond leg tradeable (intermediate→20yr) costs ~−7% wealth +0.12
Sortino +3pp DD; correcting the gold optimism costs another ~−8% wealth. Together they take the secondary from
its flattered $77.2k / Sortino 1.06 / −22.6% down to **$65.8k / Sortino 0.91 / −25.6%** — a ~15% wealth / ~0.15
Sortino / ~3pp DD haircut.

**2022 stress (the long-treasury rout):** the per-leg trend gate DID protect the levered 20yr bond leg —
fully-corrected 2022 was −12.8% / −11.6% MaxDD vs the as-built −10.1% / −11.1%. Only modestly worse, because the
bond leg's trend gate EXITED treasuries during the 2022 downtrend → the 2× long-bond crash was largely avoided.
So the secondary doesn't blow up on the tradeable bond leg — but it is no longer the low-DD standout T-284 showed.

## VERDICT — the SECONDARY was FLATTERED; it does NOT survive honest correction as a clear win. PRIMARY stands.
My T-284 flag was right to hold the secondary exploratory. Corrected: **(1) its gold leg is +2%/yr optimistic**
(spot-gold synthetic vs UGL's futures-roll reality); **(2) its intermediate-treasury bond leg is not tradeable
at 2×** — the real substitute (2×-20yr/UBT) is more volatile and degrades it. Fully honest, the secondary is a
reasonable diversified-levered strategy (~8.4% CAGR, −25.6% DD, Sortino 0.91) but **no longer the low-DD /
Sortino-~1.0 standout** the T-284 numbers suggested. It does not clearly beat the **PRIMARY** on risk-adjusted
terms once corrected.

**Carry-forward:** the **PRIMARY (100% SPY, 2×-gated, SSO-validated at +0.23%/yr)** remains the validated Roth
offense arm from T-284 — its basis is clean and its verdict is unchanged. The SECONDARY is **downgraded from
"promising follow-up" to "flattered by construction; not clearly superior"** — do not quote its T-284
$76.3k/−22.6%/0.999 numbers; the honest tradeable figures are ~$65.8k/−25.6%/0.91. If the diversified-levered
idea is revisited, it must use UGL/UBT real-fund returns directly (not spot synthetics) and account for the
20yr duration. `[NN-SUBSTRATE-REVERIFY]` applied. Reproducible: `scripts/secondary_basis_check_t285.py`.
