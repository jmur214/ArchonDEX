---
task_id: T-2026-07-27-315
title: STATIC un-gated leverage — the config a genuine won't-sell holder actually wants
date: 2026-07-27
author: Agent D (fair-harness lane)
type: PRE-REGISTRATION DRAFT (draft → director freeze → run; N_trials += 1, one family with T-312)
status: DRAFT — NOT RUN. Awaiting freeze.
---

# T-315 (DRAFT) — static, un-gated, modest leverage held forever

The entire offense arc tested **GATED** leverage, and the gate is what died: 23.98 exposure-units/yr of turnover
× measured slippage, plus the chop-exit leak (T-294 execution-bound; T-297/298). **Nobody ever ran the config a
confirmed won't-sell holder actually wants: static, un-gated, modest leverage, held forever.** Turnover ≈ nothing,
so the 5 bps gate-flip cost the arc died of **simply does not exist here**. This is the program's #1 open question
and the honest answer to "was 2× ever the target?"

## ⚠️ PRE-RUN MEASUREMENTS (computed BEFORE the run, so the verdict cannot be rationalized afterwards)

### 1. The red-team's break-even — VERIFIED, and one correction
For a static daily-reset L× LETF, log-growth vs 1×:
`Δg = (L−1)·μₑ − (L−1)·spread − ER − ½(L²−1)σ²`, so the **break-even equity excess-over-cash** is
`μₑ* = spread + [ER + ½(L²−1)σ²]/(L−1)` (spread = 0.60%, SSO ER = 0.89%).

| L | break-even μₑ (σ=16%) |
|---|---|
| 1.25× | **7.04%** |
| 1.35× | 6.15% |
| 1.50× | **5.58%** ← the red-team's ~5.6%, **CONFIRMED** |
| 2.00× | 5.33% |

**Correction the red-team's single number hides: the break-even is NOT monotone in L — it is HIGHEST at LOW
leverage** (7.04% at 1.25× vs 5.33% at 2×), because the fixed 0.89% ER is amortized over a tiny borrowed fraction.
This inverts the natural intuition that "modest leverage is the safe version": at 1.25× you pay nearly the whole ER
to borrow 25%. **If a modest-leverage arm fails while 2× passes, that is the ER, not the risk** — and the honest fix
would be a cheaper vehicle, not less leverage. (At L=2 the break-even is σ-sensitive: 4.43% at σ=14% → 7.49% at σ=20%.)

### 2. Realized ERP on the actual substrate (measured; equity levels → returns, cash already a return)
| window | equity CAGR | cash | **realized ERP** | σ |
|---|---|---|---|---|
| ~99yr (1926+) | 10.19% | 3.19% | **7.00%** | 17.1% |
| D-A/D-B 1968+ | 10.60% | 4.45% | **6.15%** | 16.7% |
| 2000-2026 | 8.13% | 1.84% | 6.29% | 19.2% |

**Implied pre-run expectation (realized ERP vs break-even):**
| | 1.25× | 1.5× | 2.0× |
|---|---|---|---|
| ~99yr | **−0.46%/yr (LOSES)** | +0.95%/yr | +1.10%/yr |
| 1968+ | **−1.16%/yr (LOSES)** | +0.27%/yr | +0.46%/yr |

So on *realized* history static leverage roughly pays at 1.5-2× and **loses at 1.25×** — but the margins at 1968+
are thin (+0.27%/yr at 1.5×), which is precisely why the **forward-ERP haircut is the whole question**, not the
backtest. _(Substrate note: `equity_tr` is a cumulative INDEX LEVEL, `cash_ret` is a daily RETURN — mixing them
naively produces nonsense; the run converts levels→returns first. Flagged so nobody repeats it.)_

## The arms (FROZEN on freeze)
- **Static {1.25, 1.35, 1.5}×** via the validated SSO synthetic (`L·equity_gross − (L−1)·(cash+60bps) − ER`,
  daily reset — the honest LETF mechanic), **held forever, annual rebalance only**. Cost: E's measured **0.51 bps**
  on the annual rebalance turnover only (~nothing). Windows: **D-A ~64yr** primary + the **~99yr equity+cash
  extension** (adds 1929 + the Depression — the most adversarial regime available), both labeled.
- **Age-glide variant:** de-lever linearly over the final 10-15 yr.
- **Bar:** buy-hold 1× equity (the SPY-equivalent), same window, same cost treatment.
- **Reference:** the T-298 gated arm (so gated-vs-static is read on one substrate, jointly with T-312).

## Vehicles / tax (the Roth-OR-taxable directive)
- **Primary: Roth SSO** (zero tax).
- **Taxable static SSO — and an honest premise check.** T-294b's verdict was about a *futures* vehicle with
  **annual §1256 mark-to-market**. A **never-sold static SSO defers exactly like buy-hold SPY**, so the deferral
  advantage that killed the futures arm **does not apply to a static ETF hold** — only the small SSO distribution
  is taxed annually. This materially changes the taxable premise and will be priced, not assumed.
- **Taxable static futures** (lower carry ~0.3%/yr but the §1256 annual mark): expected still deferral-killed —
  **prove it**, don't import T-294b's conclusion.

## MANDATORY adversarial adds (pre-registered)
1. **Forward-ERP haircut sensitivity at −2% and −3%** (i.e. μₑ = 5.0% / 4.0% at the 1968+ level, 4.0%/3.0% at the
   ~99yr level). Report **exactly where each L's edge crosses zero** against the verified break-even table above.
   At a −2% haircut the 1968+ ERP (4.15%) is **below every break-even** ⇒ the pre-run expectation is that **all**
   static arms lose at consensus-minus-2%. That is the finding, if it holds.
2. **Lost-decades tail overlay** (Japan-style path) to size the left tail honestly.
3. **The $7k/yr ACCUMULATION race** via B/T-283's machinery (not lump-sum only) — the glide de-levers exactly when
   the balance is largest, so the dollar-weighted number is the honest one.
4. **Kelly-optimal L at each ERP assumption** (`L* = μₑ/σ²`), stated explicitly so the sizing claim is never
   imported from in-sample μ. At σ=16.7%: L* = 2.2 at ERP 6.15%, **1.4 at 4.15%**, **1.1 at 3.0%** — i.e. under a
   −2 to −3% haircut, *fractional-Kelly discipline alone* argues for ≈1×.

## Gate (FROZEN)
Paired **Δwealth 95% block-bootstrap CI vs buy-hold 1× equity, per arm per ERP scenario** — the same
exclude-zero standard as T-312. Scorecard (non-gating, reported honestly): terminal wealth, CAGR, **MaxDD** (a
static 1.5× through 1929/1973-74 is brutal — say the number), Sortino/Calmar, and the accumulation-race dollar
result.

## Honest prior — the answer is probably "it regresses toward 1× at consensus forward ERP"
On *realized* history 1.5-2× static pays (+0.27 to +1.10%/yr) and 1.25× loses. But the edge is entirely a bet on
the **forward** premium: at a −2% haircut every arm is below break-even, and Kelly at that ERP says ≈1×. So my
honest prior is **break-even-to-slightly-negative at consensus forward ERP**, matching the red-team. **Either
verdict answers the user's core question** — and a clean "it regresses to 1× at consensus ERP" closes the leverage
door with a NUMBER instead of an argument, which is the most valuable outcome available here.

## Sequencing + N
Runs in ONE campaign with T-312, **after B/T-311** (shared substrate + honest-N). N_trials += 1 (one family,
jointly reported). Costs are measured data; `calendar_guard` asserted; cash reindexed onto the equity calendar.

---
**DRAFT — NOT RUN.** Awaiting director freeze. Any change after the freeze line = a new pre-registration.
