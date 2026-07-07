# Paper-Run EXECUTION-FIDELITY Gates + Go-Live Checklist (T-238, 2026-07-02)

**Pre-registered** (`[NN-MBL]`) BEFORE the sleeve paper run accrues data. A
critic finding (gap audit 2026-07-02): a **monthly-signal** sleeve produces
**~1-2 independent trend observations in a 6-12 month paper window** — so
paper **CANNOT confirm Sortino / tail / drawdown-edge in-window.** It can only
confirm **EXECUTION FIDELITY**. This doc fixes, up front, exactly what the
paper run is allowed to conclude — so nobody later reads "6 good months" as a
validated edge.

## What the paper run CAN and CANNOT establish (state it plainly)
- **CAN (execution fidelity):** the machine trades the sleeve correctly,
  cheaply, and reliably — orders match the target book, fills are near the
  assumed cost, the loop never silently breaks.
- **CANNOT (performance):** that the sleeve's backtested edge (Sortino 1.085 /
  MaxDD −12% — T-236, *pending the T-255 fair re-run*) is real out-of-sample.
  The edge lives or dies in the **backtest gauntlet**, not in a 6-12 month
  forward window with ~zero independent observations. **A string of good
  forward months is NOT validated edge and must not be quoted as such.**

## Pre-registered EXECUTION gates (report-only; no auto-kill)
`sleeve_tracker.execution_gates()` reports each gate's status
(pass / fail / accruing) — it does NOT change trading (default-OFF behavior
unchanged). Thresholds fixed here:

| # | gate | metric | threshold (pass) | rationale |
|---|---|---|---|---|
| a | **position tracking error** | median (and p95) of `|held_wt − target_wt|` summed across the 3 ETFs, marked daily | median ≤ **2.0%**, p95 ≤ **5.0%** | the paper book should track the sleeve's target weights; drift = whole-share rounding + deadband + missed fills |
| b | **fill slippage vs ARRIVAL** | median / p95 of `|fill − arrival price|` (bps) over rebalance fills — arrival = the latest trade at submission | median ≤ **5 bps**, p95 ≤ **20 bps** | the T-146 §5.2 bar. **Paper-DAY correction (Option A):** with a ~9:45 ET DAY fill, `|fill − open print|` would fold in ~15 min of market drift the machine can't control — so paper measures vs the **arrival price** (the quality it CAN control). Live-OPG can annotate vs-open separately. |
| c | **order-state errors** | count of rejects / ORDER_UNKNOWN / halts / non-canonical cycles | **0** over the window | the machine must never silently break (dead-man's-switch + reconcile) |
| d | **clean duration** | count of canonical trading days | ≥ **60** | the §5.1 duration bar; below it the sample is too thin even for execution |

A gate reads **accruing** until it has data; **fail** flips the go-live
execution verdict to NOT-READY (report loudly, do not auto-act). These gate
**performance's admissibility, not performance itself** — they only certify
the machine is faithfully running the sleeve.

## Go-Live checklist (schedule stays DISABLED until ALL gates clear)
Deploying spec = the **T-260 {2,5,10}mo ensemble**; paper execution = **market
DAY post-open (~9:45 ET)** per Option A (paper fills DAY, expires OPG); live
keeps OPG (env-gated `ARCHONDEX_SLEEVE_TIF`).
| # | gate | owner | status (2026-07-02) |
|---|---|---|---|
| 1 | **Armed run clean** — one DAY in-window run on the ensemble spec: submit → **real fill** → held-reconcile adopts → canonical + tracker first entry | E | **PREP DONE — fires Mon Jul 6 post-open on the user's nudge** |
| 2 | **T-255 — the fair, reproducible T-236 re-run** | D | ✅ **CLEARED** — sleeve BEATS schwab_like (wealth+Sortino+DD) + ties 60_40 with 3× shallower DD |
| 3 | **SNS alert email CONFIRMED** | USER | ✅ **CONFIRMED** 2026-06-26 |
| 4 | **Execution gates (a-d above) all PASS** over ≥ 60 clean days of forward paper tracking | E-tracker | ACCRUING (starts at the armed fill; accrues post-enable) |
| 5 | **ENABLE the schedule** (`archondex-paper-daily`, DISABLED) — the user's explicit word, ONLY after 1 | USER | GATED |

Gates 2 + 3 are **cleared**. After the Monday armed run (gate 1) comes back
clean, **the only remaining gate is #5 — the user's explicit enable word.**
Gate 4 (60 clean days) then accrues forward post-enable. Performance is
explicitly out of scope for the enable decision (settled — or not — in the
gauntlet, now the CLEARED T-255).

## Honest framing to carry to the user (verbatim-worthy)
> The paper run proves the MACHINE trades the sleeve correctly and cheaply —
> nothing more. A monthly-signal sleeve gives us essentially no independent
> performance signal in a year of paper, so we will NOT claim the edge is
> "confirmed" from forward paper. The edge stands or falls on the backtest
> gauntlet (T-236 → the T-255 fair re-run). Paper is an execution rehearsal,
> not an edge test.
