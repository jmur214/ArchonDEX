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

---
## RESULTS (run 2026-07-27; amended grid {1.25,1.35,1.5,1.75,2.0}×; costs = measured 0.51bps on the annual rebalance)
Reproducible: `scripts/offense_campaign_t312_t315.py`. Bar = buy-hold 1× equity, same window/cost treatment.

### The frontier — D-B ~58yr (1968+), realized ERP 6.15%, σ 16.7%
| arm | $10k→ | CAGR | MaxDD | paired Δwealth 95% CI vs bar | verdict |
|---|---|---|---|---|---|
| **buy-hold 1× (THE BAR)** | **3,363,893** | 10.50% | −55.2% | — | — |
| static 1.25× | 1,740,848 | 9.26% | −68.7% | **[−371, −7]** | **LOSES (excludes zero)** |
| static 1.35× | 2,067,540 | 9.58% | −72.5% | [−160, +1471] | straddles zero |
| static 1.50× | 2,593,908 | 10.01% | −77.7% | [−96, +5417] | straddles zero |
| static 1.75× | 3,482,188 | 10.57% | −84.5% | [−74, +18744] | straddles zero |
| static 2.00× | 4,208,246 | 10.93% | **−89.6%** | [−78, +47392] | straddles zero |
| glide 2.0×→1× (final 12y) | 5,865,931 | 11.57% | −88.3% | [−66, +55141] | straddles zero |

**The pre-registered non-monotonicity is CONFIRMED, and it is the headline.** Static **1.25× is the only arm that
CI-significantly LOSES** to buy-hold, while 2.0× has the highest terminal wealth. Exactly as pre-computed: at 1.25×
you pay nearly the whole 0.89% ER to borrow 25%, so the break-even (7.04%) sits ABOVE the realized ERP (6.15%),
while at 2× the break-even (5.33%) sits below it. **"Modest leverage is the safe version" is false on cost** — it is
the *expensive* end per unit of exposure. The same ordering holds on D-A ~64yr and ~99yr (1.25× loses at every
window; every other arm straddles).

### ⚠️ But NO static arm CI-BEATS the bar at ANY leverage, in ANY window
Every arm above 1.25× straddles zero — wide, and asymmetrically (e.g. 2×: [−78, +47,392]). Higher leverage buys a
higher *point* estimate and a fatter right tail, **not statistical significance**. The frontier's peak is real in
point terms and unproven in CI terms.

### The forward-ERP haircut — the whole question, and it is decisive
Terminal $10k, D-B ~58yr:
| haircut | 1.00× (bar) | 1.25× | 1.35× | 1.50× | 1.75× | 2.00× |
|---|---|---|---|---|---|---|
| none | 3,363,893 | 1,740,848 | 2,067,540 | 2,593,908 | 3,482,188 | **4,208,246** |
| **−2%** | **1,050,392** | 406,296 | 429,514 | 452,519 | **454,063** | 410,131 |
| **−3%** | **586,937** | 196,273 | 195,755 | 188,992 | 163,946 | 128,018 |

**At a −2% forward-ERP haircut EVERY static arm loses to buy-hold 1× (best is 1.75× at $454k vs the bar's
$1,050k — less than half). At −3% the ordering fully inverts: more leverage = strictly less wealth.** The
pre-registered expectation is confirmed exactly. Kelly agrees: **L\* = 2.20 (no haircut) → 1.49 (−2%) → 1.13 (−3%)**.
**The entire static-leverage case is a bet on the forward equity premium being at or above its realized history.**

### The 1929 ruin test — in DOLLARS (the amendment's question: what is left to compound?)
| arm | 1929-32 drawdown | trough from $10,000 | years to recover |
|---|---|---|---|
| buy-hold 1× | −84.1% | $1,594 | 12.5 |
| **gated T-298** | **−21.6%** | **$7,874** | **0.0** |
| static 1.25× | −91.3% | $873 | 18.1 |
| static 1.50× | −95.0% | $499 | 18.4 |
| static 1.75× | −97.2% | $278 | 19.1 |
| **static 2.00×** | **−98.5%** | **$152** | **20.6** |

**A won't-sell holder survives 2× in temperament; the capital does not survive in wealth.** $10,000 → **$152**, and
**two decades** to get back. "Survivable" and "worth holding" are different questions and this table separates them.
(The daily-reset mechanic means this is not literal ruin, but it is functionally indistinguishable from it for a
compounding horizon.)

### Cash-rate regime split (mirrors B/T-311) — the static edge is REGIME-CONCENTRATED, opposite to the sleeve
| era | avg cash | bar | static 1.5× | static 2.0× | gated T-298 |
|---|---|---|---|---|---|
| 1962-1989 | 6.6% | 9.97% | **8.55%** | **8.79%** | 12.81% |
| 1990-2026 | 2.7% | 10.64% | 10.94% | **12.54%** | 9.45% |

**Static leverage LOSES to buy-hold in the high-cash-rate era and wins only in the low-rate era** — the financing
cost is the mechanism, and it is the mirror image of the sleeve's dependence (T-311: the sleeve won when cash was
high). Today's EFFR ≈3.6% sits between the eras, so **neither regime is a clean forecast** — but any claim that
static leverage "works" is implicitly a bet that financing stays cheap.

### Lost-decades (Japan-style) overlay + the $7k/yr accumulation race
- **Japan path (final 20yr at −2%/yr drift):** bar $2,255,147 vs 1.25× $1,055,992 / 1.5× $1,423,740 / 2.0×
  $1,891,063 — **every static arm loses**, monotonically worse as the path degrades.
- **$7k/yr accumulation (dollar-weighted):** bar $35.0M; 1.25× $23.1M; 1.5× $36.5M; **2.0× $70.1M**; **glide
  2.0×→1× $86.5M**; gated T-298 $26.6M. The glide wins the dollar-weighted race — it holds high leverage while the
  balance is small and de-levers as it grows — **but this inherits the full no-haircut ERP assumption**, so it is a
  conditional win, not an unconditional one.

## VERDICT — the leverage door closes with a NUMBER, as hoped
1. **No static arm CI-beats buy-hold at any leverage in any window.** The only CI-significant static result is
   **1.25× LOSING** — and its mechanism is the ER-amortization non-monotonicity, not risk.
2. **At a −2% forward-ERP haircut every static arm loses; at −3% the ordering inverts.** Kelly falls 2.20 → 1.13.
   **The static case is entirely a bet on the forward ERP matching realized history**, and it regresses toward 1×
   the moment that bet is haircut — the pre-registered honest prior, confirmed.
3. **The 1929 dollar test disqualifies the high arms on compounding grounds** ($10k → $152, 20.6yr to recover),
   independent of temperament.
4. **The edge is regime-concentrated in cheap financing** (loses 1962-89, wins 1990-2026) — the opposite dependence
   to the sleeve, and not forecastable today.

**Recommendation: no static-leverage arm earns a row.** If the user wants aggression, the honest form is not more
leverage on this vehicle — it is either (a) accepting 1× buy-hold as the wealth-maximizing choice under any
haircut, or (b) the glide *conditional on* an explicit forward-ERP assumption the user states and owns.

### Vehicle-implication (required by the amendment)
The frontier's point-wise peak sits at high L, where **SSO's cost structure is the binding constraint** — the 0.89%
ER + 60bps spread is what pushes 1.25× below break-even and eats ~1.3%/yr at 2×. So the named (NOT run) follow-up
if aggression is pursued: **LEAPS-embedded leverage at the $65k+ tier** (deep-ITM long-dated calls — no forced
liquidation, financing defined by implied vol rather than a fund ER, and no daily-reset decay) and **box-spread
financing at $125k+** (borrow at near-treasury rates against portfolio margin). Both change the break-even table
directly by attacking `ER + spread`; neither is validated here and each requires its own pre-registration.
N_trials += 1 (one family with T-312).
