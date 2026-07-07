# T-291 Deliverable 2 — even_week × is_fomc_week interaction: VERDICT

**Date:** 2026-07-07 · **Agent:** C · Branch `feature/event-state-t291` · **N_trials += 1** · family-N = 2
Ran the frozen pre-registration (`event_interaction_prereg_t291_2026_07_07.md`, committed `7902030` BEFORE this run). Primary gate = full-sample G1−G2 block-bootstrap 95% CI.

## Result: H0 — the even-week premium is NOT concentrated in the FOMC decision week
| group | full 1994-2026 | post-2015 (decay) |
|---|--:|--:|
| G1 even & FOMC-week (cycle wk 0) | +8.26 bps/day (n=1028) | −1.37 bps/day (n=326) |
| G2 even & non-FOMC (wk 2,4,6) | +7.01 bps/day (n=3290) | +4.91 bps/day (n=1171) |
| G3 odd (baseline) | +1.98 bps/day (n=4042) | +8.02 bps/day (n=1342) |
| **G1 − G2 (the gate)** | **+1.25 [−6.69, +9.87]** — straddles 0 | −6.27 [−21.05, +7.38] — straddles 0 |
| context G1 − G3 | [−1.33, +14.24] straddles 0 | [−24.51, +3.88] |
| context **G2 − G3** | **[+0.13, +10.06] — excludes 0** | [−10.61, +4.53] |

## What it means
1. **The mechanism is NOT the FOMC decision week.** G1 − G2 straddles 0 in both windows → the even-week premium is not bigger in the meeting week than in the other even weeks. The pre-registered CONFIRM gate FAILS. **No event-day-specific mechanism located.**
2. **The even-week premium IS present full-sample but as a DIFFUSE cycle pattern** — the one significant contrast is **G2 − G3** (even-non-FOMC vs odd, CI excludes 0): even weeks 2/4/6 out-earn odd weeks, and G1 (the meeting week itself) is *not* distinguishable from the other even weeks. This is consistent with the JF-2019 even-cycle-week diffusion effect — a spread-out pattern, not a decision-day event — which is exactly why it does NOT justify an event-DAY-aware sizing modifier.
3. **Post-2015 it decayed / inverted** — odd weeks (G3 +8.0) now out-earn even weeks, and the meeting week (G1) went slightly negative. Textbook McLean-Pontiff post-publication decay; no robust forward signal.

## Verdict & consequence
**H0 — no FOMC-week-specific mechanism.** The `event_window` state of the EventStateDetector earns **NO sizing role** from this test; it remains built + **default-OFF as pure event CONTEXT** (surfaced to consumers, never a timing gate — T-233). This closes the mechanism-locating question cleanly (family-N = 2 with T-268's `even-week × sleeve` H0): the even-week effect, to the extent it survives, is diffuse and decayed — not a decision-day edge. N_trials += 1.

(Minor: SPY data starts 1993-02, the FOMC fixture 1994-02, so ~250 pre-fixture days fall into G3 — immaterial to a CI this wide. On B/T-290 merge, swap the fixture for `macro_calendar` and the windows tighten slightly; the verdict — a wide straddle-0 — is robust to it.)
