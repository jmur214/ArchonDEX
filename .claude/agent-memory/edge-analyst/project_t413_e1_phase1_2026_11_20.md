---
name: project-t413-e1-phase1-2026-11-20
description: T-413 (E-1 earnings straddles vs own history) CLOSED UNRUN 2026-11-24 at 0 trials — updated P(H1b) 1–4 %, MDE 24–30 pp; refutes nothing; reopening conditions; plus my own errors (gate lowered after the census, false fail-closed claim, unreported contrary probe)
metadata:
  type: project
---

**CLOSED UNRUN 2026-11-24, 0 trials** (director's ruling after an independent review of `a9c12c1`: NOT READY, 4 blockers + 6 REQUIRED).
- Doc: `docs/Sources/prereg_e1_earnings_options_t413_DRAFT_2026-11-20.md`; corrections in §16–§18.
- Code: only on branch `worktree-agent-a44a03b091ff6efa5` at `a9c12c1`. Not on main; fetch/refresh unwritten.

**Why closed:**
- The reviewer's updated P(H1b) is 2–4 % (σ 1.0) / 1–2.5 % (σ 1.24). My 4.5–8 % reproduces from the T-410 priors but ignores the observed var(log q).
- MDE80 is 24–30 pp. A FAIL barely moves belief in 5–15 pp; a PASS is more likely a data fault.
- **It refutes nothing.** G1 (small-cap), G2 (short vol) and G4 (skew/term) stay as they were.

**Reopens if:** the T-416 forward options archive holds ≥ ~2 years of real quotes, or a quote/IV history becomes available (Cboe DataShop, OptionMetrics); or a conditioner raises the per-event effect. Mean-of-8 instead of median-of-8 is recorded, not adopted.

**Facts to reuse (with the corrections):**
- 4,304 S&P 500 candidates to 2026-06-10; about 41 % usable. No ≤ 7-day expiry in 44 % pooled (92/210), of which some is an Alpaca contract-LISTING GAP (FISV, CPAY, BRK.B; renames), not a listing fact.
- sd(log q) ≈ 0.39 is the NOISE FLOOR of a median of 8 half-normals (0.390). It is not evidence of signal. corr(log q, log m8) = −0.64.
- A weekly tercile sort is not tradeable: Monday's arm needs Friday's q.
- News panel files 2026-08/09 are truncated. `data/earnings/*_calendar.parquet` has an empty `hour`.

**My own errors, to not repeat:**
- I wrote a power gate of 2,400 before the census, saw it project ≈ 1,230, lowered it to 1,000, and presented 1,000 as the gate without saying so. Outcome-free is not the same as disclosed.
- I claimed "a missing expiry close halts, never dropped". An earlier stage dropped it, and my test called the later stage directly.
- My own probe showed a TSN weekly gap. I dismissed it and wrote "a listing fact, not a data gap", on a witness from the same source.
- I called 34 missing names "mostly later-acquired" without classifying them.
- I wrote "code path proven" on three controls that also pass with planted faults: payoff read at entry+1, payoff from adjusted closes, m8 always at k = 1, 10 % entry-price noise. Their 4-SE tolerance was the size of the effect.
- My exclusion labels hid data gaps: missing bars became "insufficient history", empty contracts became "no expiry", empty trades became "thin prints".
- I named descriptives in the prereg that the code never computed.

**How to apply:**
- Compare sd(log ratio) with the sampling-noise floor of its denominator BEFORE calling a conditioner alive.
- When a threshold moves after any census, state the old value, the new value and why, in the doc and the commit.
- Test a fail-closed promise through the whole pipeline entry point, never by calling the last stage.
- Witness an absence from a source independent of the one that reported it.
- Plant a fault in EACH stage (timestamp, price basis, horizon, entry price) and require the controls to miss. Set the tolerance well below the effect to be detected.
- Count a data gap under its own reason, apart from a market fact, and halt on it.
- Check that an input file COVERS its period, not only that it exists, and pin it.
- See [[feedback-signal-variance-collapse]], [[feedback-per-event-effect-to-noise]], [[reference-options-data-sources-2026-11-20]].
