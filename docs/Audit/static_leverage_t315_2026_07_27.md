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

---
---
# AMENDMENT 1 (T-399, 2026-11-14) — a cost defect in the static arms; the corrected re-run, PRE-DECLARED

**Nothing above this line is edited.** This amendment is committed alone, before the fix and before any
re-run. Found by the T-396 design note (`docs/Sources/design_note_lifecycle_leverage_t396_2026-11-14.md`
§1.2, branch `research/lifecycle-leverage-note-t396`); verified by the director by execution.

## A1.1 The defect

`scripts/offense_campaign_t312_t315.py:37-38`, inside `static_arm`:

```python
yr = r.index.to_period("Y")
cost[yr != yr.shift(1)] = SLIP_EQ * rebal_per_yr    # ~nothing
```

`PeriodIndex.shift(1)` shifts each PERIOD forward one year; it does not shift positions. The mask is true
on every row, so every static arm above 1× paid the 0.51 bp "annual rebalance" cost every DAY — about
1.29 %/yr of phantom cost. The published D-B table above fits a fixed cost of 2.00 %/yr across its five
static arms (largest residual 0.2 bp) against the specified 0.71 %/yr; the gap is 0.51 bp × 252.

- **Affected:** every `static_arm` result above — the frontier table in all three windows, the haircut
  table, the 1929 table's static rows, the cash-rate regime split's static columns, the lost-decades
  overlay, and the static rows of the $7k/yr accumulation race.
- **Not affected:** the 1× bar (built without `static_arm`), the glide arm and the gated T-312/T-298 arm
  (both charge cost on `diff()` of the exposure).

## A1.2 The fix

A positional year-change mask: the cost is charged on the first bar of the series and on the first bar of
each later calendar year — the positional reading the original line intended. One regression test plants a
two-year series and asserts the count of charged bars; it is proven by reversion.

## A1.3 What is unchanged

Arms {1.25, 1.35, 1.5, 1.75, 2.0}× and the 2×→1× glide over the final 12 years; windows D-B (1968+),
D-A (1962+) and ~99yr (1926+), each to the substrate's last bar; the fund model
(`L·gross − (L−1)·(cash + 60 bp) − 0.89 %` on the whole balance); costs 0.51 bp and 2.2 bp; financing from
the T-306 cash leg; haircuts 0 / −2 % / −3 % on D-B; the bootstrap (`paired_dw`, 21-day blocks, 1,000
draws, seed 0); the 1929 window; the regime split; the lost-decades overlay; the $7k/yr race. The gate is
the frozen one: the paired Δwealth 95 % CI vs buy-hold 1× excludes zero.

**N_trials: 0 new** (director ruling, the B-5 A2.2 precedent): a defect-corrected re-run of a frozen
pre-registration consumes no trial provided the spec is otherwise unchanged and both runs stay on the
record.

## A1.4 What the re-run will report

- **ORIGINAL beside CORRECTED** for every static arm in every window and haircut: terminal wealth, CAGR,
  MaxDD, Δ log growth per year vs the bar, and the paired Δwealth CI.
- **The ORIGINAL column is reproduced by code**, because the July run's output was not stored: a labelled
  function in the T-399 runner charges the cost every day, exactly as the defect did. **Acceptance check,
  fail-closed:** the reproduction must equal the published D-B table (`:113-118`), the haircut table
  (`:137-139`), the 1929 table (`:149-154`) and the accumulation race (`:175`) to the printed precision,
  and the bar and the gated arm must equal the published T-312 values
  (`deep_reverify_offense_t312_2026_07_27.md:93-95`). If any differs, the run halts and nothing is quoted.
- **Per-haircut CIs.** The gate text (`:87`) asks for a CI "per arm per ERP scenario"; the July run printed
  wealth only for the haircut rows. The re-run adds the CI for both columns.
- The wealth race (the glide against the static arms), the 1929 path, the regime split and the overlay,
  each ORIGINAL beside CORRECTED.
- Determinism ×2 by md5 of the result file.

## A1.5 Two SENSITIVITIES, declared now — labelled, never the headline

- **(S1) The blended-fee model for L < 2.** A holder who wants L holds SPY and SSO in the proportions that
  give L, and pays SSO's expense ratio on the SSO slice only:
  `r = (2 − L)·(equity − 0.09 %/252) + (L − 1)·lev_daily(equity, cash, 2.0)` — the expression the gated arm
  already uses (`scripts/offense_campaign_t312_t315.py:70-73`) — less the corrected annual cost. Arms 1.25,
  1.35, 1.5, 1.75; at 2.0 it must equal the headline arm (a self-check). All three windows; haircuts on D-B.
- **(S2) Financing from B-5's H.15 / SOFR snapshot** (`data/research/b5/inputs/`, md5-verified against its
  manifest) instead of the T-306 cash leg, which is quantized to 1 bp/day. B-5's `financing_base()` and
  `financing_arrays()` are imported unchanged: the daily charge on the borrowed fraction is
  `(base[t−1] + 60 bp) × calendar days / 360`. The snapshot's SOFR ends 2025-12-31 and its bill begins 1954,
  so S2 runs on D-B and D-A **truncated to 2025-12-31** and not on the ~99yr window. Its comparison column
  is the corrected headline arm recomputed on the same truncated window. All five static arms and the
  glide. The 1× bar holds no cash and is unchanged.
- S1 and S2 are separate tables. They are not combined.

## A1.6 Erratum to the pre-run section — Kelly and the break-even comparison

`L* = ERP / σ²` above (`:82-84`, `:143`) used the difference of CAGRs as the ERP. Kelly takes the
arithmetic mean excess return. The re-run prints both, labelled. The break-even formula (`:22-23`) also
takes an arithmetic mean, so the "implied pre-run expectation" table (`:45-49`), which subtracts it from a
CAGR gap, understates leverage by about ½σ² per unit borrowed. Neither changes a run number.

## A1.7 Expectation, stated before the re-run

From arithmetic on the published table (T-396 §1.2): corrected 1.25× is about +0.16 %/yr against the bar
and straddles zero; corrected 2× is about +1.7 %/yr with t ≈ 0.76; no arm is expected to CI-beat the bar on
D-B. At −2 % every arm is expected still to trail the bar, by roughly 9–18 % rather than by more than
half; at −3 % the ordering is expected still to invert. The glide's win in the accumulation race is
expected to disappear. Under S1 the 1.25× arm on the ~99yr window is expected near the line (t ≈ 1.8). If
it excludes zero, that is a labelled sensitivity on a window in which no such fund existed for eighty
years, below the deflated bar (T-396 §4), and not a pass.

**Frozen at this commit.** Results and the corrected verdict are appended below; nothing above is rewritten.

---
# AMENDMENT 1 — RESULTS (T-399, run 2026-11-14 on the spec frozen above at `ccd60c8`)

**Nothing above this line is edited.** N_trials consumed: 0. Both runs are on the record: the July run is
reproduced beside the corrected one in every table.

## R.1 How it was run, and what was checked before any number was read

- **The fix:** `scripts/offense_campaign_t312_t315.py`, `year_change_mask` (positional) in `static_arm`.
  Regression: `tests/test_offense_campaign_static_cost_t399.py` (15 tests at the fix; 24 after review
  round 1 added the acceptance-halt tests). **Proven by reversion:** with the July line restored, 8 fail
  (520 bars charged where 2 are due on a two-year series; 784 where 4 are due) and the rest — 7 at the fix,
  16 at 24 tests — which pin the unaffected arms, the idiom and the acceptance halt, still pass.
- **The runner:** `scripts/t315_static_cost_rerun_t399.py`. ORIGINAL = the July cost path reproduced on
  purpose; CORRECTED = the fixed campaign functions, imported.
- **Acceptance: PASS.** The reproduced ORIGINAL equals the published D-B table, the haircut table, the
  1929 table and the accumulation race above, and the bar and gated arm equal T-312's published values in
  all three windows. The unmodified July script, run before the fix, also reprints the July tables to the
  dollar (stdout md5 `1f1d6a17…`, twice).
- **Determinism ×2:** `results.json` md5 `5238dff1706a0bc31600d0fab634d244` on runs A and B. The fixed
  campaign script's stdout is md5 `54cdd120…` twice.
- **The unaffected arms are byte-unchanged — proven by execution.** The pre-fix source (`ccd60c8`) was
  executed beside the fixed module on the real substrate: the bar, glide and gated return series have
  identical md5s in all three windows, and the static series differ. A diff of the July stdout against
  the corrected stdout touches only the static rows and the added Kelly lines. No July output file was on
  disk, so the comparison is against the published tables and a fresh run of the unmodified script.
- **Reading the columns.** "Δwealth CI" is the frozen gate: the paired 95 % block-bootstrap CI of terminal
  wealth per $1, arm minus bar. "Δlog" is the difference in log growth, %/yr, with a 95 % CI from the same
  draws; "ahead" is the share of draws with the arm ahead. Δlog and "ahead" are reported, not gating.

## R.2 The frontier — ORIGINAL beside CORRECTED

**D-B ~58yr (1968-01-02 to 2026-04-17).** Bar $3,363,893, CAGR 10.50 %, MaxDD −55.2 %. Δlog and "ahead" are reported, not gating.

| arm | ORIGINAL $10k→ | ORIGINAL Δwealth CI | CORRECTED $10k→ | CAGR | MaxDD | Δlog %/yr [95 % CI] | ahead | CORRECTED Δwealth CI (the gate) |
|---|---|---|---|---|---|---|---|---|
| static 1.25× | 1,740,848 | [−371, −7] **LOSES** | **3,666,822** | 10.67 % | −65.2 % | +0.15 [−0.95, +1.17] | 56 % | [−22, +3,333] straddles |
| static 1.35× | 2,067,540 | [−160, +1,471] | 4,354,958 | 10.99 % | −69.2 % | +0.44 [−1.10, +1.88] | 66 % | [−20, +6,791] straddles |
| static 1.50× | 2,593,908 | [−96, +5,417] | 5,463,713 | 11.43 % | −75.0 % | +0.83 [−1.37, +2.89] | 73 % | [−21, +15,101] straddles |
| static 1.75× | 3,482,188 | [−74, +18,744] | 7,334,909 | 11.99 % | −82.6 % | +1.34 [−1.98, +4.44] | 75 % | [−27, +43,161] straddles |
| static 2.00× | 4,208,246 | [−78, +47,392] | **8,864,568** | 12.36 % | −88.3 % | +1.66 [−2.76, +5.83] | 72 % | [−37, +103,631] straddles |
| glide 2×→1× (unaffected) | 5,865,931 | [−66, +55,141] | 5,865,931 | 11.57 % | −88.3 % | +0.95 [−3.16, +4.78] | 64 % | [−66, +55,141] straddles |
| gated T-298 (unaffected) | 3,294,909 | [−1,486, +1,438] | 3,294,909 | 10.48 % | −47.9 % | −0.04 [−2.94, +3.22] | 51 % | [−1,486, +1,438] straddles |

**D-A ~64yr (1962-01-02 to 2026-04-17).** Bar $5,647,734, CAGR 10.37 %. Δlog and "ahead" are reported, not gating.

| arm | ORIGINAL $10k→ | ORIGINAL Δwealth CI | CORRECTED $10k→ | CAGR | Δlog %/yr [95 % CI] | ahead | CORRECTED Δwealth CI |
|---|---|---|---|---|---|---|---|
| static 1.25× | 2,754,187 | [−815, −24] **LOSES** | 6,263,922 | 10.55 % | +0.16 [−0.89, +1.15] | 64 % | [−34, +7,484] straddles |
| static 1.35× | 3,347,078 | [−295, +3,065] | 7,612,364 | 10.89 % | +0.46 [−1.00, +1.86] | 74 % | [−30, +15,697] straddles |
| static 1.50× | 4,341,332 | [−157, +12,300] | 9,873,692 | 11.34 % | +0.87 [−1.23, +2.87] | 80 % | [−31, +36,557] straddles |
| static 1.75× | 6,141,082 | [−118, +43,990] | 13,967,219 | 11.95 % | +1.41 [−1.77, +4.43] | 82 % | [−39, +109,712] straddles |
| static 2.00× | 7,789,320 | [−121, +111,875] | 17,716,503 | 12.37 % | +1.78 [−2.50, +5.83] | 80 % | [−53, +264,238] straddles |
| glide (unaffected) | 11,727,107 | [−84, +148,810] | 11,727,107 | 11.65 % | +1.14 [−2.62, +4.97] | 74 % | same |
| gated T-298 (unaffected) | 7,988,176 | [−2,635, +6,285] | 7,988,176 | 10.95 % | +0.53 [−2.14, +3.78] | 63 % | same |

**~99yr (1926-07-02 to 2026-04-17).** Bar $145,842,174, CAGR 10.08 %, MaxDD −84.1 %. Δlog and "ahead" are reported, not gating.

| arm | ORIGINAL $10k→ | ORIGINAL Δwealth CI | CORRECTED $10k→ | CAGR | MaxDD | Δlog %/yr [95 % CI] | ahead | CORRECTED Δwealth CI |
|---|---|---|---|---|---|---|---|---|
| static 1.25× | 50,991,161 | [−68,507, −159] **LOSES** | 193,163,406 | 10.39 % | −90.9 % | +0.28 [−0.71, +1.15] | 70 % | [−445, +940,048] straddles |
| static 1.35× | 72,783,785 | [−12,700, +300,301] | 275,718,486 | 10.78 % | −92.7 % | +0.64 [−0.76, +1.86] | 80 % | [−293, +2,349,715] straddles |
| static 1.50× | 117,113,737 | [−3,827, +1,568,259] | 443,653,201 | 11.31 % | −94.8 % | +1.11 [−0.90, +2.87] | 85 % | [−253, +7,155,489] straddles |
| static 1.75× | 221,489,542 | [−2,003, +8,721,526] | 839,080,344 | 12.02 % | −97.1 % | +1.75 [−1.29, +4.40] | 86 % | [−317, +34,254,804] straddles |
| static 2.00× | 344,512,747 | [−1,864, +34,240,093] | 1,305,205,777 | 12.52 % | −98.4 % | +2.20 [−1.88, +5.75] | 84 % | [−464, +130,929,167] straddles |
| glide (unaffected) | 865,542,460 | [−756, +84,302,633] | 865,542,460 | 12.06 % | −98.4 % | +1.78 [−2.17, +5.20] | 82 % | same |
| gated T-298 (unaffected) | 1,960,925,542 | [+86, +5,133,571] SIGNIFICANT | 1,960,925,542 | 12.99 % | −54.3 % | +2.61 [+0.01, +5.41] | 98 % | same — T-312's published single-episode result (1929 alone; see T-312) |

- **In every window, no static arm CI-beats the bar and no static arm CI-loses to it.** The July
  "1.25× LOSES" appears in all three windows and disappears in all three.
- **On point, inside the frozen model, every static arm at 1.35× and above is ahead of the bar at the
  realized premium in all three windows, and the frontier rises with L.** The July "non-monotone" shape,
  with 1.25× at about half the bar, was the daily cost.
- **At 1.25× on D-B and D-A the sign of the point estimate is not established.** The +0.15 and
  +0.16 %/yr leads are smaller than the frozen model's two leverage-favouring conventions, which are
  worth about 0.10 and 0.07 %/yr there (R.8).
- The effect of the fix is the same in every row: about +1.4 pp of CAGR, a terminal value about 2.1× the
  July figure on D-B and about 3.8× on the ~99yr window (more bars, and six-day weeks before 1952).

## R.3 Forward-ERP haircuts — D-B

Terminal $10k and its multiple of the bar. The July run printed no haircut CIs; both columns carry them now. Δlog and "ahead" are reported, not gating.

| haircut | arm | bar | ORIGINAL (× bar) | ORIGINAL Δwealth CI | CORRECTED (× bar) | Δlog %/yr [95 % CI] | ahead | CORRECTED Δwealth CI |
|---|---|---|---|---|---|---|---|---|
| −2 % | 1.25× | 1,050,392 | 406,296 (0.39) | [−306, −7] LOSES | 855,862 (0.81) | −0.35 [−1.45, +0.67] | 23 % | [−22, +514] straddles |
| −2 % | 1.35× | | 429,514 (0.41) | [−144, −2] LOSES | 904,779 (0.86) | −0.26 [−1.80, +1.18] | 33 % | [−20, +1,062] straddles |
| −2 % | 1.50× | | 452,519 (0.43) | [−88, +480] | 953,253 (0.91) | −0.17 [−2.37, +1.89] | 40 % | [−22, +2,175] straddles |
| −2 % | 1.75× | | 454,063 (0.43) | [−71, +1,838] | 956,540 (0.91) | −0.16 [−3.48, +2.95] | 42 % | [−28, +5,024] straddles |
| −2 % | 2.00× | | 410,131 (0.39) | [−74, +3,854] | 864,032 (0.82) | −0.34 [−4.76, +3.84] | 40 % | [−38, +9,352] straddles |
| −3 % | 1.25× | 586,937 | 196,273 (0.33) | [−240, −4] LOSES | 413,464 (0.70) | −0.60 [−1.70, +0.42] | 10 % | [−21, +170] straddles |
| −3 % | 1.35× | | 195,755 (0.33) | [−137, −3] LOSES | 412,377 (0.70) | −0.61 [−2.15, +0.83] | 17 % | [−19, +377] straddles |
| −3 % | 1.50× | | 188,992 (0.32) | [−83, +43] | 398,139 (0.68) | −0.67 [−2.87, +1.39] | 23 % | [−21, +762] straddles |
| −3 % | 1.75× | | 163,946 (0.28) | [−68, +444] | 345,391 (0.59) | −0.91 [−4.22, +2.20] | 25 % | [−27, +1,609] straddles |
| −3 % | 2.00× | | 128,018 (0.22) | [−71, +928] | 269,716 (0.46) | −1.33 [−5.76, +2.84] | 24 % | [−35, +2,645] straddles |

(The no-haircut rows are the D-B frontier above.)

- **At −2 % every static arm still ends below the bar, by 9–19 %** (July: by 57–61 %). **At −3 % the
  ordering still inverts**, 0.70× down to 0.46×.
- **No arm CI-loses at either haircut.** Every corrected CI straddles zero.

**Kelly — D-B** (σ 16.72 %; CAGR gap 6.15 %; arithmetic mean excess 7.13 %):

| haircut | July: CAGR gap ÷ σ² | erratum A1.6: arithmetic mean excess ÷ σ² |
|---|---|---|
| none | 2.20 | **2.55** |
| −2 % | 1.49 | **1.83** |
| −3 % | 1.13 | **1.48** |

## R.4 The 1929 path, the regime split, the overlay, the wealth race

**1929-09 → 1932-07, from $10,000** (the bar: −84.1 %, $1,594, 12.5 yr; the gated arm: −21.6 %, $7,874, 0.0 yr —
both unaffected):

| arm | ORIGINAL dd / trough / years to recover | CORRECTED |
|---|---|---|
| static 1.25× | −91.3 % / $873 / 18.1 | −90.9 % / $911 / 13.3 |
| static 1.50× | −95.0 % / $499 / 18.4 | −94.8 % / $521 / 17.6 |
| static 1.75× | −97.2 % / $278 / 19.1 | −97.1 % / $291 / 18.3 |
| static 2.00× | −98.5 % / $152 / 20.6 | **−98.4 % / $158 / 19.0** |

**Cash-rate regime split (CAGR):**

| era | avg cash | bar | 1.5× ORIGINAL | 1.5× CORRECTED | 2.0× ORIGINAL | 2.0× CORRECTED | gated |
|---|---|---|---|---|---|---|---|
| 1962–1989 | 6.6 % | 9.97 % | 8.55 % | **9.95 %** | 8.79 % | **10.19 %** | 12.81 % |
| 1990–2026 | 2.7 % | 10.64 % | 10.94 % | 12.37 % | 12.54 % | 13.99 % | 9.45 % |

The split has no CI. To three decimals 1962–1989 reads bar 9.974 %, 1.5× 9.946 %, 2× 10.191 %. That era
is entirely before the 1993 splice, where convention (b) of R.8 is worth 0.135 and 0.180 pp, so both
gaps are inside the model's convention error.

**Lost-decades overlay** (final 20 years at −2 %/yr; bar $2,255,147):

| arm | ORIGINAL | CORRECTED (× bar) |
|---|---|---|
| static 1.25× | 1,055,992 | 2,224,338 (0.99) |
| static 1.50× | 1,423,740 | 2,999,006 (1.33) |
| static 2.00× | 1,891,063 | 3,983,640 (1.77) |

**The $7k/yr accumulation race** (D-B, one cohort from 1968, the full realized premium, no CI). Bar
$35,000,003; glide 2×→1× $86,453,022 and gated $26,581,118, both unaffected:

| arm | ORIGINAL final $ | CORRECTED final $ |
|---|---|---|
| static 1.25× | 23,066,857 | 42,762,044 |
| static 1.35× | 27,990,886 | 51,973,595 |
| static 1.50× | 36,468,358 | 67,833,770 |
| static 1.75× | 52,863,754 | **98,483,279** |
| static 2.00× | 70,133,424 | **130,684,196** |

## R.5 SENSITIVITY S1 — the blended fee for L < 2 (labelled; not the headline)

SPY + SSO in the proportions that give L. Against the headline fund model it saves
`(2 − L) × (0.89 % − 2 × 0.09 %)` a year: 0.53 %/yr at 1.25×, 0.36 % at 1.5×, 0.18 % at 1.75×, nothing at 2×
(self-check: S1 at 2.0× equals the headline arm in every window). Δlog and "ahead" are reported, not gating.

| window | arm | headline CORRECTED $ | S1 blend $ | Δlog %/yr [95 % CI] | ahead | S1 Δwealth CI |
|---|---|---|---|---|---|---|
| D-B | 1.25× | 3,666,822 | 4,998,888 | +0.68 [−0.42, +1.70] | 88 % | [−6, +5,805] straddles |
| D-B | 1.35× | 4,354,958 | 5,696,704 | +0.90 [−0.64, +2.34] | 87 % | [−9, +9,912] straddles |
| D-B | 1.50× | 5,463,713 | 6,717,562 | +1.19 [−1.02, +3.24] | 84 % | [−13, +19,332] straddles |
| D-B | 1.75× | 7,334,909 | 8,133,135 | +1.51 [−1.80, +4.62] | 79 % | [−23, +48,220] straddles |
| D-A | 1.25× | 6,263,922 | 8,816,412 | +0.69 [−0.35, +1.69] | 91 % | [−8, +13,200] straddles |
| D-A | 1.50× | 9,873,692 | 12,400,650 | +1.22 [−0.88, +3.23] | 88 % | [−18, +47,585] straddles |
| ~99yr | 1.25× | 193,163,406 | 336,127,258 | +0.84 [−0.16, +1.71] | 95 % | [−39, +1,956,903] straddles |
| ~99yr | 1.35× | 275,718,486 | 445,623,661 | +1.12 [−0.28, +2.34] | 94 % | [−63, +4,064,824] straddles |
| ~99yr | 1.50× | 443,653,201 | 641,847,027 | +1.48 [−0.53, +3.24] | 92 % | [−111, +10,545,209] straddles |
| ~99yr | 1.75× | 839,080,344 | 1,009,252,214 | +1.94 [−1.10, +4.59] | 89 % | [−238, +41,288,467] straddles |

S1 under the haircuts, D-B (terminal $ and × bar; every CI straddles zero):

| haircut | 1.25× | 1.35× | 1.50× | 1.75× | 2.00× |
|---|---|---|---|---|---|
| −2 % (bar 1,050,392) | 1,166,812 (1.11) | 1,183,572 (1.13) | 1,172,041 (1.12) | 1,060,651 (1.01) | 864,032 (0.82) |
| −3 % (bar 586,937) | 563,691 (0.96) | 539,452 (0.92) | 489,525 (0.83) | 382,987 (0.65) | 269,716 (0.46) |

- **No S1 arm excludes zero in any window.** The 1.25× blend on the ~99yr window is at the line, as
  pre-declared: 95 % of draws ahead, CI [−39, +1,956,903].
- **Under S1 the −2 % point estimate changes sign at low leverage:** 1.25–1.5× ends 11–13 % above the bar,
  1.75× level, 2× below. At −3 % every blend still ends below. This is a sensitivity and a point
  estimate: the leads are +0.18 to +0.20 %/yr, and the two conventions of R.8 are worth 0.10–0.21 %/yr on
  those blends, so the sign of the flip is not established.
- S1 accumulation race: 1.25× $55.5M, 1.5× $80.7M, 1.75× $107.4M, 2× $130.7M. S1 1929 path: 1.25×
  −90.8 % / $928 / 13.2 yr; 2× unchanged.

## R.6 SENSITIVITY S2 — B-5's H.15 / SOFR financing (labelled; not the headline)

Windows end 2025-12-31. Δlog is reported, not gating. On the borrowed fraction the T-306 cash leg + 60 bp charged 4.96 %/yr on D-B and
4.88 %/yr on D-A; B-5's base + 60 bp charges **5.25 %** and **5.17 %** — about 0.29 pp/yr more.

| window | arm | T-306 cash: $ / Δlog %/yr | B-5 financing: $ / Δlog %/yr [95 % CI] | B-5 Δwealth CI |
|---|---|---|---|---|
| D-B (bar 3,222,258) | 1.25× | 3,494,673 / +0.14 | 3,351,044 / +0.07 [−0.95, +1.17] | [−26, +3,723] straddles |
| D-B | 1.50× | 5,171,933 / +0.82 | 4,754,920 / +0.67 [−1.38, +2.87] | [−24, +16,613] straddles |
| D-B | 1.75× | 6,898,784 / +1.31 | 6,080,241 / +1.09 [−2.01, +4.42] | [−32, +46,329] straddles |
| D-B | 2.00× | 8,287,288 / +1.63 | 7,000,961 / +1.34 [−2.83, +5.81] | [−43, +107,700] straddles |
| D-B | glide | 5,511,171 / +0.93 | 4,645,613 / +0.63 [−3.41, +4.88] | [−80, +55,828] straddles |
| D-A (bar 5,409,939) | 1.25× | 5,969,845 / +0.15 | 5,697,888 / +0.08 [−0.92, +1.19] | [−40, +9,090] straddles |
| D-A | 1.50× | 9,346,405 / +0.85 | 8,513,009 / +0.71 [−1.30, +2.93] | [−36, +44,355] straddles |
| D-A | 2.00× | 16,562,767 / +1.75 | 13,732,461 / +1.46 [−2.57, +5.92] | [−62, +356,553] straddles |

- **The T-306 cash leg was slightly generous to leverage.** It is Fama-French's one-month bill rate on
  trading days; B-5's base is the three-month bill and SOFR accrued on calendar days over 360. The gap is
  not decomposed here. B-5's financing lowers every arm by 0.07–0.30 %/yr and changes no verdict.
- The 1.35× rows, the 1.75× D-A row and the D-A glide are not printed here. Regenerate them with the
  runner (`python scripts/t315_static_cost_rerun_t399.py --tag A`): `results.json` md5 `5238dff1…`,
  `tables.md` md5 `36ce2589…`. The run directory is worktree-local and not committed.

## R.7 Against the expectation stated in A1.7 before the run

t here is Δlog divided by a standard error read off its own bootstrap interval (width ÷ 3.92).

| expected (A1.7) | measured |
|---|---|
| corrected 1.25× about +0.16 %/yr, straddling | +0.15 %/yr, t ≈ 0.27, straddles |
| corrected 2× about +1.7 %/yr, t ≈ 0.76 | +1.66 %/yr, t ≈ 0.76 |
| no arm CI-beats on D-B | none does, in any window |
| at −2 % every arm trails by roughly 9–18 % | 9–19 % |
| at −3 % the ordering still inverts | it does |
| the glide's win in the race disappears | static 2× and 1.75× finish ahead; the glide still beats 1.5× and below |
| S1 1.25× on ~99yr near the line, t ≈ 1.8 | t ≈ 1.76, 95 % of draws ahead, CI straddles |

Nothing came out differently from what was declared.

## R.8 Two leverage-favouring conventions of the frozen model (pre-existing; outside this fix)

The fix removed a cost that was not in the specification. Two things that are in the frozen model lean
toward the levered arms. Neither was changed and no arm was re-run under a changed model: that would be a
new configuration and needs its own pre-registration. The sizes below are arithmetic on bar counts and on
the tables above.

- **(a) The cash leg.** S2 measures it. With B-5's bill / SOFR financing the Δlog of the 1.25× arm falls
  by 0.07 %/yr (D-B +0.14 → +0.07, D-A +0.15 → +0.08, windows to 2025-12-31), 1.35× by 0.10, 1.5× by
  0.15, 1.75× by 0.22 and 2× by 0.29.
- **(b) The fund fee.** `scripts/offense_campaign_t312_t315.py:28` adds the 1× fund's 9 bp back to the
  equity return before multiplying by L (`gross = eq_ret + ER["equity"] / TD`), and the bar at `:143`
  subtracts 9 bp (`bar = (er - ER["equity"] / TD).dropna()`). The equity leg is a gross index before the
  1993-02-01 splice (Fama-French broad market) and SPY's adjusted close, already net of SPY's fee, after
  it (`data/research/substrate_multidecade/provenance.json`). Before the splice the add-back gives the
  fund L × 9 bp/yr it should not have; after it the bar pays 9 bp/yr twice. Arm minus bar is overstated by
  L × 9 bp/yr before the splice and 9 bp/yr after. Bars before / after the splice: D-B 6,310 / 8,360,
  D-A 7,821 / 8,360, ~99yr 17,863 / 8,360.

| overstatement of Δlog from (b), %/yr | 1.25× | 1.35× | 1.50× | 1.75× | 2.00× |
|---|---|---|---|---|---|
| D-B | 0.100 | 0.103 | 0.109 | 0.119 | 0.129 |
| D-A | 0.101 | 0.105 | 0.112 | 0.122 | 0.133 |
| ~99yr | 0.110 | 0.116 | 0.126 | 0.142 | 0.158 |
| 1962–1989 (all before the splice) | 0.112 | 0.121 | 0.135 | 0.157 | 0.180 |

What that does to the point estimates (Δlog %/yr; subtraction, not a re-run):

| arm | frozen model | less (b) | less (a) as well |
|---|---|---|---|
| D-B 1.25× | +0.15 | +0.05 | **−0.02** |
| D-A 1.25× | +0.16 | +0.06 | **−0.01** |
| ~99yr 1.25× | +0.28 | +0.17 | S2 does not cover this window |
| D-B 1.35× | +0.44 | +0.34 | +0.24 |
| D-A 1.35× | +0.46 | +0.36 | +0.26 |
| D-B 2.00× | +1.66 | +1.53 | +1.24 |

- **At 1.35× and above the point lead survives both conventions in every window. At 1.25× on D-B and D-A
  it does not:** the sign of the point estimate is not established. No interval is affected in kind; every
  static-arm CI straddled zero before this subtraction and would after it.
- **Both columns carry both conventions.** ORIGINAL and CORRECTED are shifted alike, and so are the
  haircut rows: on point the shortfalls at −2 % and −3 % are about 0.17 %/yr (1.25×) to 0.42 %/yr (2×)
  deeper than printed.
- **S1 carries less of (b)**, because only the SSO slice gets the add-back: 0.03 %/yr at 1.25×, 0.06 at
  1.5×, 0.10 at 1.75× on D-B. With (a), the S1 leads at −2 % (+0.18, +0.20, +0.19 %/yr at 1.25×, 1.35×,
  1.5×) become about +0.08, +0.06 and −0.02. At the realized premium the 1.25× blend goes from +0.68 to
  about +0.58.
- The gated arm mixes the two conventions by its exposure and is not sized here.
- Recorded as an open MEDIUM in `docs/State/health_check.md`.

## R.9 Notes on the frozen mechanics

- **The first-bar reading.** The fix charges the cost on the first bar of the series and on the first bar
  of each later calendar year. The first-bar charge is one 0.51 bp entry cost the bar does not pay; on the
  ~99yr window, which starts mid-year (1926-07-02), it is an extra charge relative to "once per calendar
  year". It is immaterial: about $190 of $3.67M on D-B 1.25×, about $66,000 of $1.305bn on ~99yr 2×.
- **The bootstrap** is a fixed 21-day moving block, 1,000 draws, seed 0. That is T-315's frozen setting,
  not the Politis–White automatic block length.
- **Per-bar accrual.** Fees and the spread accrue at 1/252 per bar. 1927–1951 has about 294 bars a year
  (six-day weeks), so those years are charged about 17 % too much. Pre-existing; it touches only the
  ~99yr window.
- **S1's direction was known before it was declared.** T-396 §1.2 had already computed that the fund model
  overcharges low leverage, so S1 could only help the low arms. A1.5 fixed its form before the run, not
  its sign.

---
# CORRECTED VERDICT (T-399) — which sentences of the verdict above survive

The verdict section above is left as written. This section supersedes it.

| Sentence of the July verdict | Status | What the corrected run says |
|---|---|---|
| "No static arm CI-beats buy-hold at any leverage in any window." | **SURVIVES** | Every static arm straddles zero in D-B, D-A and ~99yr, and in both sensitivities. |
| "The only CI-significant static result is 1.25× LOSING … its mechanism is the ER-amortization non-monotonicity." | **DOES NOT SURVIVE** | It was the daily cost. Corrected 1.25× straddles in all three windows (D-B $3.67M vs $3.36M, +0.15 %/yr [−0.95, +1.17]). Its point estimate is positive inside the frozen model, but on D-B and D-A the sign is not established: the lead is smaller than the model's two leverage-favouring conventions (R.8). |
| "The pre-registered non-monotonicity is CONFIRMED, and it is the headline"; "'Modest leverage is the safe version' is false on cost." | **DOES NOT SURVIVE** | At the realized premium the corrected frontier rises with L, and inside the frozen model every arm at 1.35× and above is above the bar on point. At 1.25× the arm is level with the bar within the model's conventions (R.8). The fund model does overcharge low leverage (0.53 %/yr at 1.25×, S1). |
| "At a −2 % forward-ERP haircut EVERY static arm loses." | **SURVIVES on point in the frozen model, not in size, not as a CI, and not under S1** | 0.81–0.91× of the bar, not "less than half"; every CI straddles. In the S1 sensitivity 1.25–1.5× ends 11–13 % above on point, a lead whose sign is not established (R.5, R.8). |
| "At −3 % the ordering fully inverts: more leverage = strictly less wealth." | **SURVIVES on point** | 0.70× at 1.25× down to 0.46× at 2×; under S1 0.96× down to 0.46×. No CI excludes zero. |
| "Kelly agrees: L* = 2.20 → 1.49 → 1.13"; "fractional-Kelly discipline alone argues for ≈1×." | **NUMBERS WITHDRAWN; the half-Kelly reading survives** | Kelly on the arithmetic mean is 2.55 → 1.83 → 1.48, before costs. Half of that is 1.28, 0.92, 0.74. |
| "The entire static-leverage case is a bet on the forward equity premium being at or above its realized history." | **SURVIVES, restated** | On point the break-even haircut sits between 0 and −2 % for every arm in the frozen model (at 1.25× it is at about zero once R.8 is counted), and near −2 % for the low blends in the S1 sensitivity. |
| "The 1929 dollar test disqualifies the high arms" ($10,000 → $152, 20.6 yr). | **SURVIVES** | $158 and 19.0 years at 2×. At 1.25× the recovery is 13.3 years, not 18.1, against the bar's 12.5. |
| "Static leverage LOSES to buy-hold in the high-cash-rate era and wins only in the low-rate era." | **"LOSES" IS NOT ESTABLISHED, and neither is "ahead"; the concentration survives** | 1962–89: bar 9.974 %, 1.5× 9.946 %, 2× 10.191 %. That era is all before the 1993 splice, where convention (b) is worth 0.135 and 0.180 pp (R.8), so both gaps are inside the model's convention error, and the split has no CI. The July gaps (−1.42 and −1.18 pp) were the daily cost. 1990–2026: +1.73 and +3.35 pp. The point edge is still almost all in the cheap-financing era. |
| "Japan path: every static arm loses, monotonically worse as the path degrades." | **DOES NOT SURVIVE** | 1.25× 0.99× of the bar, 1.5× 1.33×, 2× 1.77×. |
| "The glide wins the dollar-weighted race." | **DOES NOT SURVIVE** | Static 2× ($130.7M) and 1.75× ($98.5M) finish ahead of the glide ($86.5M). One cohort, the full premium, no CI. |
| "SSO's cost structure … is what pushes 1.25× below break-even." | **DOES NOT SURVIVE as stated** | The July 1.25× shortfall was the daily cost, not SSO's fee. Whether 1.25× sits just above or just below break-even at the realized premium is not established (R.8). |
| "Recommendation: no static-leverage arm earns a row." | **SURVIVES on the frozen gate** | No static-arm CI excludes zero. |
| "(a) accepting 1× buy-hold as the wealth-maximizing choice under any haircut." | **RESTATED** | 1× is not beaten with confidence by any static arm at any haircut. On point, inside the frozen model, it is behind every static arm at 1.35× and above at the realized premium (at 1.25× the sign is not established) and ahead of every one at −2 % and −3 %. |

**The corrected verdict in three sentences.** Static leverage on this vehicle is not refuted and not
supported: at the realized premium of the D-B window (1968-01-02 to 2026-04-17), inside the frozen model,
every arm at 1.35× and above ends ahead of 1× on point (+0.44 %/yr at 1.35× to +1.66 %/yr at 2×) and at
1.25× the sign of the point estimate is not established (+0.15 %/yr, smaller than the model's two
leverage-favouring conventions, R.8); the drawdown is −65 % to −88 % against −55 %, and no static-arm
interval excludes zero in any window. A −2 % haircut turns the frozen model negative by 0.2–0.4 %/yr and a −3 % haircut by 0.6–1.3 %/yr,
again inside the noise. It is a decision about how much equity-premium risk to hold and what forward
premium to believe (T-396 §4), and the 1929 path still says what the high arms cost when that belief is
wrong.

**T-315's status.** "refuted" was the right word for "does any static arm CI-beat the bar" and remains so.
It was the wrong word for "leverage loses": the July run showed that only through the defect.

---
# REVIEW ROUND 1 (2026-11-14) — what changed in the T-399 part of this document, and why

An independent review by execution reproduced from scratch every static-arm frontier and haircut cell with
its CI, the static rows of the race, the 1929 path, the regime split and the lost-decades overlay, S1
terminal values (22 cells, no CIs) and S2 on four cells; the glide and gated arms were checked by pre/post
identity and against the published values, not re-implemented (wording corrected by the director after the
delta review, 2026-11-14). It confirmed the reversion split and the unaffected arms. It
found the write-up claimed more than the run shows at 1.25×. No code in the fix changed and nothing was
re-run. Edits are confined to the part of this document T-399 appended (from "AMENDMENT 1 — RESULTS" down);
the July text and the pre-declared amendment are untouched.

| Where | Was | Now | Why |
|---|---|---|---|
| R.2, second bullet | "On point every static arm is ahead of the bar at the realized premium" | 1.35× and above ahead on point inside the frozen model; at 1.25× on D-B and D-A the sign is not established | The +0.15 / +0.16 %/yr lead is smaller than two leverage-favouring conventions of the frozen model (new R.8): the cash leg (S2: −0.07) and the fund-fee add-back (−0.10). |
| Verdict rows on "1.25× LOSING", the non-monotone frontier, "below break-even", and "wealth-maximizing under any haircut" | "ahead on point in all three windows"; "every arm is above the bar"; "not below break-even"; "behind every static arm" | Each now says 1.35× and above, with the sign at 1.25× not established | The same finding. |
| The three-sentence verdict | "at the realized 1968–2025 premium every arm ends ahead of 1× on point (+0.15 … +1.66 %/yr) … no interval excludes zero in any window" | The D-B span as run (1968-01-02 to 2026-04-17); 1.35× and above ahead; 1.25× sign not established; "no static-arm interval" | Only S2 ends 2025-12-31. The gated arm's ~99yr interval [+86, +5,133,571] excludes zero (T-312's published single-episode result), so "no interval" was too broad. |
| Verdict row on the regime split; R.4 | "1.5× 9.95 % vs 9.97 % (level), 2× 10.19 % (ahead) … +1.7 and +3.4 pp" | "LOSES" not established and neither is "ahead"; 9.974 / 9.946 / 10.191 %; +1.73 and +3.35 pp; no CI for the split | 1962–89 is all before the splice, where convention (b) is worth 0.135 and 0.180 pp. |
| Verdict rows on the −2 % haircut and the break-even; R.5 bullet | "with the blended fee 1.25–1.5× ends 11–13 % above"; "changes sign" | Called a sensitivity and a point estimate whose sign is not established | The S1 leads at −2 % (+0.18 to +0.20 %/yr) are the size of the same two conventions on a blend. This one was not asked for by the review; it follows from R.8. |
| R.2, D-A and ~99yr tables | no gated row | gated row added | The ~99yr gated interval is the one that excludes zero; leaving it out hid that. |
| R.2, R.3, R.5, R.6 leads | the non-gating label stated once, in R.1 | stated on each table that shows Δlog or "ahead"; R.2 leads carry the exact spans | A table is read on its own. |
| R.6, last bullet | pointed at `data/t399_local/run_A/tables.md` | how to regenerate, with the md5s | That file is not committed. |
| New R.8 | — | the two conventions, sized by arithmetic | Finding 2. Convention (b) is a pre-existing property of the frozen model, outside this fix; changing it is a new pre-registration. |
| New R.9 | — | the first-bar reading, the bootstrap setting, per-bar accrual, S1's direction | Disclosures the review asked for. |

The corrected verdict's first row ("no static arm CI-beats"), the 1929 row, the Kelly row, the Japan-path
row and the glide row are unchanged.
