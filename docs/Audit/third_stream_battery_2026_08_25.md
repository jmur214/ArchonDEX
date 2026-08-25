# The third-stream candidate battery — standing tool + first artifact (DBMF)

**Date:** 2026-08-25 · **Agent:** B · Branch `feature/third-stream-battery` · **0 N_trials** (infra/tooling)

Formalizes T-313's direct crisis-correlation measure into `scripts/third_stream_battery.py`:
any candidate proposed as the genuinely-independent 3rd return stream (tripwire #2 from
T-305/T-248) now gets a same-day verdict for **$0**, on free data, against the **same frozen
bar the live T-316 gate uses**.

## Why a standing tool
T-313 killed international equity **at the data-reality stage, without burning a trial**, by
measuring crisis correlation directly (corr +0.93 GFC / **+1.00 COVID** / +0.87 2022 — the
T-214 trap). That move is general: a 3rd stream must go uncorrelated-or-SHORT in *fast*
crashes, and that property is cheap to falsify. Paying honest N to rediscover a co-faller is
waste. The battery makes the cheap falsification the default first step.

## Design decisions that carry weight

**The bar is imported, never re-declared.** `CORR_MAX` comes from
`paper_trader.dbmf_shadow.GATE_A_CORR_MAX` (T-316 frozen, +0.30), so the backtest screen and
the live forward gate cannot silently drift apart. A test asserts the identity.

**The verdict reads the CI, not the point estimate** (`[NN-SHARPE-CI]`). Correlations carry a
**paired** block-bootstrap CI — row-blocks resampled so both legs move together, because
bootstrapping the legs independently would destroy the very dependence being measured and
manufacture a spurious PASS (locked by a test). Verdicts:

| status | meaning |
|---|---|
| **PASS** | the whole CI clears +0.30 — independence can be *affirmed* |
| **FAIL** | the whole CI sits above +0.30 — co-movement can be affirmed |
| **UNRESOLVED** | the CI straddles the bar — **this window cannot settle it** |
| **NOT_COVERED** | the candidate's history does not span the window, + the reason |
| **PARTIAL** | <90% coverage — deliberately **not scored** |

Crisis windows are short by construction, so UNRESOLVED is common and honest. A point
estimate under the bar is **not** a pass — that is the anti-goalpost-moving property.

**Fail-closed coverage** (`[NN-FAIL-CLOSED]`). A window the candidate only partly spans is
never silently shrunk to the overlap and reported as that window's correlation. `--file`
input requires an explicit `--file-kind price|return`; guessing is refused, because a return
series read as prices is wrong *silently*.

**Signed, not absolute.** The primary screen is the signed T-316 form (`corr <= +0.30`)
because a strongly **negative** crisis correlation is the property we actually want — the
stream goes short when equity crashes. The two-sided `|corr|` reading from the T-305
tripwire-#2 wording is reported alongside; where they disagree the panel says so.
**⚠ Flagged for the director:** the dispatch names the `|corr|<0.3` form while the frozen
T-316 gate is one-sided. I implemented the signed form as primary and emit both rather than
silently pick. If tripwire #2 is meant two-sided, say so and I will flip the primary.

**Window provenance is inherited, not invented.** GFC / COVID / 2022 are taken verbatim from
the merged T-311 `CRISES`; 2018-Q4 is added in the identical month-boundary style. A tighter
peak→trough COVID window (2020-02-19..03-23) was built first and **rejected during
construction**: it holds only 24 trading days, below `MIN_OBS`, making the single most
discriminating window **unscoreable for every candidate forever**. The window was changed on
observation count and repo convention — *not* on the answer it produced. Recorded here
because changing a window after seeing a result is exactly the move that needs a receipt.

## First artifact — the battery on DBMF (the known case, `[NN-FIRST-ARTIFACT]`)

```
=== THIRD-STREAM BATTERY — DBMF vs SPY | bar: corr <= +0.30 (T-316 GATE_A_CORR_MAX) ===
window          n    corr           95% CI  status
2008 GFC        —       —                —  NOT_COVERED  (history begins 2019-05-09)
2018-Q4         —       —                —  NOT_COVERED  (history begins 2019-05-09)
COVID-2020     62   +0.56   [+0.19, +0.79]  UNRESOLVED   (CI straddles the bar)
2022          209   -0.33   [-0.50, -0.15]  PASS         (whole CI clears)
FULL sample  1770   +0.18   [+0.05, +0.30]  UNRESOLVED

long-run carry vs cash (2019-05-09..2026-05-22, n=1770): +7.00%/yr  CI [-2.02, +14.44]
  └─ INDETERMINATE — CI straddles 0
SCREEN: INCONCLUSIVE — 2/4 windows covered, none FAIL but not all resolve;
        the backtest route cannot settle this candidate
```

**It reproduces the T-316-era facts, independently.** T-253 measured DBMF's convexity as
*regime-specific* — strong in the sustained 2022 bear (+33/+49%), **−6% in the fast 2020
crash**. The battery recovers exactly that shape from correlations alone: **PASS in 2022
(−0.33)** and a **strongly positive +0.56 in the fast COVID crash**. And its headline is the
T-316 thesis in one line — *the backtest route cannot settle this candidate* (2/4 windows) —
which is precisely why T-316 armed a live forward clock instead of running another proxy
backtest. The tool re-derives the reason it exists.

Note the carry line is **INDETERMINATE, not positive**, despite a +7.00%/yr point estimate:
the CI runs [−2.02, +14.44]. Seven years of a single fund cannot establish MF carry. That is
Gate B's falsifiability requirement showing up in the backtest view.

## Routing
`docs/Sources/Papers/README.md` now carries a standing fast-route: any submission proposing a
3rd return stream is flagged at triage and run through the battery **before** it may become a
PROBE. REJECT → SKIP with the failing window recorded. CLEARS → eligible for pre-registration
(*necessary, never sufficient* — it is a cheap falsifier, not evidence of an edge).
INCONCLUSIVE → the T-316 situation: a live forward clock, not a longer backtest.

## Tests
`tests/test_third_stream_battery.py` — 15 green. Bar-identity with the live gate; window
provenance vs T-311; **every crisis window long enough to be scoreable** (the regression that
would have caught my rejected COVID window); NOT_COVERED / PARTIAL / too-few-obs; PASS / FAIL
/ straddling-CI-does-not-pass; negative-corr passes the signed screen while `|corr|` disagrees;
paired bootstrap preserves correlation; determinism; zero-variance → NaN (`[NN-FP-GUARDS]`).
